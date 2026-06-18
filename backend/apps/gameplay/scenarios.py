import uuid
from datetime import timedelta
from typing import Literal

import yaml
from django.conf import settings
from django.db import transaction
from pydantic import BaseModel, Field, model_validator

from apps.builder.models import AIPlayer, CardTemplate, HeroTemplate, Title
from apps.builder.schemas import HeroPower, SummonAction, TitleConfig
from apps.collection.models import Deck
from apps.core.card_assets import get_hero_art_url
from apps.core.serializers import to_card_schema
from apps.gameplay.models import Game
from apps.gameplay.schemas.effects import NewPhaseEffect
from apps.gameplay.schemas.game import CardInPlay, GameState, HeroInPlay
from apps.gameplay.services import GameService

Side = Literal["side_a", "side_b"]

MANIFEST_DIR = settings.BASE_DIR / "apps" / "gameplay" / "scenario_manifests"


class ScenarioConfigurationError(ValueError):
    pass


class ScenarioHero(BaseModel):
    slug: str
    health: int | None = None


class ScenarioAI(BaseModel):
    fallback_strategy: str = "control"
    opening: list[dict] = Field(default_factory=list)


class ScenarioSide(BaseModel):
    controller: Literal["ai", "guest", "human"] = "guest"
    hero: ScenarioHero
    opening_hand: list[str] = Field(default_factory=list)
    deck: list[str] = Field(default_factory=list)
    ai: ScenarioAI | None = None


class ScenarioManifest(BaseModel):
    slug: str
    title: str
    viewer_side: Side = "side_b"
    guest_token_ttl_minutes: int = 120
    player_name: str = "You"
    opponent_name: str = "CPU"
    sides: dict[Side, ScenarioSide]

    @model_validator(mode="after")
    def require_both_sides(self) -> "ScenarioManifest":
        missing_sides = {"side_a", "side_b"} - set(self.sides)
        if missing_sides:
            missing = ", ".join(sorted(missing_sides))
            raise ValueError(f"Scenario is missing side configuration: {missing}")
        return self


class ScenarioGameService:
    @staticmethod
    def load_manifest(slug: str) -> ScenarioManifest:
        for path in sorted(MANIFEST_DIR.glob("*.yaml")):
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
            scenarios = data if isinstance(data, list) else [data]
            for raw_scenario in scenarios:
                scenario = ScenarioManifest.model_validate(raw_scenario)
                if scenario.slug == slug:
                    return scenario
        raise ScenarioConfigurationError(f"Scenario manifest not found: {slug}")

    @staticmethod
    @transaction.atomic
    def start_scenario(slug: str) -> tuple[Game, str]:
        scenario = ScenarioGameService.load_manifest(slug)
        game = ScenarioGameService._create_game(scenario)
        token = game.issue_guest_access_token(
            scenario.viewer_side,
            ttl=timedelta(minutes=scenario.guest_token_ttl_minutes),
        )
        return game, token

    @staticmethod
    def _create_game(scenario: ScenarioManifest) -> Game:
        title = ScenarioGameService._get_title(scenario.title)
        heroes = {
            side: ScenarioGameService._get_hero(title, config.hero.slug)
            for side, config in scenario.sides.items()
        }
        system_decks = {
            side: ScenarioGameService._get_or_create_system_deck(
                title=title,
                side=side,
                scenario=scenario,
                hero=heroes[side],
            )
            for side in ("side_a", "side_b")
        }

        cards, hands, decks = ScenarioGameService._build_card_zones(title, scenario)
        summonable_cards = ScenarioGameService._build_summonable_cards(
            title=title,
            cards=cards,
            heroes=list(heroes.values()),
        )
        config = TitleConfig.model_validate(title.config or {})
        game_state = GameState(
            turn=0,
            active="side_a",
            phase="start",
            cards=cards,
            heroes={
                side: ScenarioGameService._build_hero_in_play(
                    title=title,
                    side=side,
                    scenario=scenario,
                    hero_template=heroes[side],
                )
                for side in ("side_a", "side_b")
            },
            hands=hands,
            decks=decks,
            ai_sides=[
                side
                for side, side_config in scenario.sides.items()
                if side_config.controller == "ai"
            ],
            config=config,
            summonable_cards=summonable_cards,
            mulligan_done={"side_a": True, "side_b": True},
            mulligan_options={"side_a": [], "side_b": []},
            rng_seed=f"scenario:{scenario.slug}:{uuid.uuid4().hex}",
        )

        from apps.gameplay.agents.ruleset import compute_ruleset_id

        game = Game.objects.create(
            status=Game.GAME_STATUS_INIT,
            type=Game.GAME_TYPE_INTRO,
            ladder_type=None,
            side_a=system_decks["side_a"],
            side_b=system_decks["side_b"],
            state=game_state.model_dump(),
            ruleset_id=compute_ruleset_id(title),
        )
        game.enqueue([NewPhaseEffect(side="side_a", phase="start")], trigger=False)
        return game

    @staticmethod
    def _get_title(title_slug: str) -> Title:
        try:
            return Title.objects.get(slug=title_slug, is_latest=True)
        except Title.DoesNotExist as exc:
            raise ScenarioConfigurationError(
                f'Scenario title "{title_slug}" does not exist.'
            ) from exc

    @staticmethod
    def _get_hero(title: Title, hero_slug: str) -> HeroTemplate:
        try:
            return HeroTemplate.objects.get(
                title=title,
                slug=hero_slug,
                is_latest=True,
            )
        except HeroTemplate.DoesNotExist as exc:
            raise ScenarioConfigurationError(
                f'Scenario hero "{hero_slug}" does not exist for {title.slug}.'
            ) from exc

    @staticmethod
    def _get_cards(title: Title, slugs: set[str]) -> dict[str, CardTemplate]:
        cards = {
            card.slug: card
            for card in CardTemplate.objects.filter(
                title=title,
                slug__in=slugs,
                is_latest=True,
            ).prefetch_related("cardtrait_set", "allowed_heroes")
        }
        missing = sorted(slugs - set(cards))
        if missing:
            raise ScenarioConfigurationError(
                f"Scenario references missing card slugs for {title.slug}: "
                f"{', '.join(missing)}"
            )
        return cards

    @staticmethod
    def _get_or_create_system_deck(
        title: Title,
        side: Side,
        scenario: ScenarioManifest,
        hero: HeroTemplate,
    ) -> Deck:
        ai_player, _ = AIPlayer.objects.get_or_create(
            name="Intro Scenario",
            difficulty=AIPlayer.AI_DIFFICULTY_EASY,
        )
        deck_name = f"Intro {scenario.slug} {side}"
        deck = Deck.objects.filter(
            ai_player=ai_player,
            title=title,
            name=deck_name,
            archived_at__isnull=True,
        ).first()
        if deck is None:
            deck = Deck.objects.create(
                ai_player=ai_player,
                title=title,
                name=deck_name,
                hero=hero,
                description="System deck for the intro scenario.",
            )
        deck.hero = hero
        deck.description = "System deck for the intro scenario."
        side_config = scenario.sides[side]
        if side_config.controller == "ai":
            ai_config = side_config.ai or ScenarioAI()
            deck.script = {
                "strategy": ai_config.fallback_strategy,
                "opening": ai_config.opening,
            }
        else:
            deck.script = {}
        deck.save(update_fields=["hero", "description", "script"])
        return deck

    @staticmethod
    def _build_card_zones(
        title: Title,
        scenario: ScenarioManifest,
    ) -> tuple[dict[str, CardInPlay], dict[str, list[str]], dict[str, list[str]]]:
        required_slugs: set[str] = set()
        for side_config in scenario.sides.values():
            required_slugs.update(side_config.opening_hand)
            required_slugs.update(side_config.deck)

        cards_by_slug = ScenarioGameService._get_cards(title, required_slugs)
        cards: dict[str, CardInPlay] = {}
        hands: dict[str, list[str]] = {"side_a": [], "side_b": []}
        decks: dict[str, list[str]] = {"side_a": [], "side_b": []}
        next_card_id = 0

        def add_card(slug: str) -> str:
            nonlocal next_card_id
            next_card_id += 1
            card_template = cards_by_slug[slug]
            card_schema = to_card_schema(card_template)
            card_id = str(next_card_id)
            cards[card_id] = GameService.get_card_in_play(card_schema, next_card_id)
            return card_id

        for side in ("side_a", "side_b"):
            side_config = scenario.sides[side]
            hands[side] = [add_card(slug) for slug in side_config.opening_hand]
            decks[side] = [add_card(slug) for slug in side_config.deck]

        return cards, hands, decks

    @staticmethod
    def _build_summonable_cards(
        title: Title,
        cards: dict[str, CardInPlay],
        heroes: list[HeroTemplate],
    ) -> dict[str, CardInPlay]:
        summonable_slugs: set[str] = set()

        for card in cards.values():
            for trait in card.traits:
                for action in trait.actions:
                    if isinstance(action, SummonAction):
                        summonable_slugs.add(action.target)

        for hero in heroes:
            hero_power = HeroPower.model_validate(hero.hero_power or {})
            for action in hero_power.actions:
                if isinstance(action, SummonAction):
                    summonable_slugs.add(action.target)

        summonable_templates = ScenarioGameService._get_cards(title, summonable_slugs)
        summonable_cards: dict[str, CardInPlay] = {}
        for slug, card_template in summonable_templates.items():
            card_schema = to_card_schema(card_template)
            summonable_cards[slug] = CardInPlay(
                card_type=card_schema.card_type,
                card_id="",
                template_slug=slug,
                name=card_schema.name,
                description=card_schema.description,
                attack=card_schema.attack,
                health=card_schema.health,
                cost=card_schema.cost,
                traits=card_schema.traits,
                art_url=card_schema.art_url,
            )
        return summonable_cards

    @staticmethod
    def _build_hero_in_play(
        title: Title,
        side: Side,
        scenario: ScenarioManifest,
        hero_template: HeroTemplate,
    ) -> HeroInPlay:
        side_config = scenario.sides[side]
        health = side_config.hero.health or hero_template.health
        player_name = (
            scenario.opponent_name
            if side_config.controller == "ai"
            else scenario.player_name
        )
        return HeroInPlay(
            hero_id=f"scenario_{scenario.slug}_{side}_{hero_template.id}",
            template_slug=hero_template.slug,
            health=health,
            health_max=health,
            name=hero_template.name,
            description=hero_template.description,
            hero_power=hero_template.hero_power,
            exhausted=False,
            art_url=get_hero_art_url(title.slug, hero_template.slug),
            player_name=player_name,
        )
