from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.authentication.models import Friendship
from apps.builder.models import (
    AIPlayer,
    CardTemplate,
    Faction,
    HeroTemplate,
    Tag,
    Title,
    TraitOverride,
)
from apps.builder.services import TitleService
from apps.collection.models import Deck, DeckCard, OwnedCard, OwnedHero
from apps.collection.validation import validate_deck_for_play
from apps.gameplay.models import (
    ELORatingChange,
    FriendlyChallenge,
    Game,
    GameUpdate,
    MatchmakingQueue,
    UserTitleRating,
)
from apps.gameplay.engine.handlers import spawn_creature
from apps.gameplay.schemas.game import GameState
from apps.gameplay.services import GameService

User = get_user_model()


class Command(BaseCommand):
    help = "Seed local Archetype data for iOS UI testing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default="password",
            help="Password for seeded local users.",
        )
        parser.add_argument(
            "--queue-ladder",
            choices=[Game.LADDER_TYPE_DAILY, Game.LADDER_TYPE_RAPID],
            default=Game.LADDER_TYPE_DAILY,
            help="Ranked ladder to seed as queued for the local iOS user.",
        )
        parser.add_argument(
            "--queue-age-seconds",
            type=int,
            default=0,
            help=(
                "Age in seconds for the seeded queue entry. Negative values place "
                "the queue timestamp in the future for deterministic screenshot captures."
            ),
        )
        parser.add_argument(
            "--game-age-seconds",
            type=int,
            default=0,
            help=(
                "Age in seconds for seeded games. Negative values place game "
                "timestamps in the future for deterministic relative-time UI captures."
            ),
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("This command can only be run when DEBUG is enabled.")

        with transaction.atomic():
            password = options["password"]
            users = self.seed_users(password)
            title = self.seed_title(users["author"])
            self.clear_title_content(title)
            self.seed_content(title)
            decks = self.seed_decks(title, users)
            self.normalize_ai_decks(title)
            self.seed_friendships(users)
            self.seed_challenges(title, users, decks)
            self.seed_ratings_and_history(title, users, decks)
            self.seed_ranked_queue(
                title,
                users,
                decks,
                options["queue_ladder"],
                options["queue_age_seconds"],
            )
            active_game = self.seed_active_game(
                title, users["ios"], decks["ios"], decks["ai"]
            )
            mulligan_game = self.seed_mulligan_game(
                title, users["ios"], decks["ios"], decks["ai_mulligan"]
            )
            self.normalize_game_timestamps(
                title,
                users["ios"],
                options["game_age_seconds"],
            )

        self.stdout.write(self.style.SUCCESS("Seeded Archetype local UI data."))
        self.stdout.write(f"  User: ios@devdata.local")
        self.stdout.write(f"  Password: {options['password']}")
        self.stdout.write(f"  Title: {title.slug}")
        self.stdout.write(f"  Queue ladder: {options['queue_ladder']}")
        self.stdout.write(f"  Queue age seconds: {options['queue_age_seconds']}")
        self.stdout.write(f"  Game age seconds: {options['game_age_seconds']}")
        self.stdout.write(f"  Active game: {active_game.id}")
        self.stdout.write(f"  Mulligan game: {mulligan_game.id}")

    def seed_users(self, password):
        seeded = {}
        user_specs = [
            ("author", "author@devdata.local", "ArchetypeBuilder", False, False),
            ("ios", "ios@devdata.local", "Thibaud", False, False),
            ("finding", "finding@devdata.local", "FindingDevo", False, False),
            ("ink", "ink@devdata.local", "Inkgoblin", False, False),
            ("pilot", "pilot@devdata.local", "DevPilot", False, False),
            ("spindle", "spindle@devdata.local", "Spindle", False, False),
        ]

        for key, email, username, is_staff, is_superuser in user_specs:
            user, _ = User.objects.get_or_create(email=email)
            user.username = username
            user.is_staff = is_staff
            user.is_superuser = is_superuser
            user.is_email_verified = True
            user.is_active = True
            user.status = User.STATUS_APPROVED
            user.set_password(password)
            user.save()
            seeded[key] = user

        return seeded

    def seed_title(self, author):
        title, _ = Title.objects.get_or_create(
            slug="archetype",
            version=1,
            defaults={
                "name": "Archetype",
                "description": "A tactical card battle title.",
                "author": author,
                "status": Title.STATUS_PUBLISHED,
                "published_at": timezone.now(),
                "config": {
                    "deck_size_limit": 30,
                    "min_cards_in_deck": 10,
                    "deck_card_max_count": 9,
                    "hand_start_size": 3,
                    "side_b_compensation": None,
                    "death_retaliation": False,
                    "ranked_time_per_turn": 60,
                },
            },
        )
        title.name = "Archetype"
        title.description = "A tactical card battle title."
        title.author = author
        title.status = Title.STATUS_PUBLISHED
        title.is_latest = True
        title.published_at = title.published_at or timezone.now()
        title.config = {
            "deck_size_limit": 30,
            "min_cards_in_deck": 10,
            "deck_card_max_count": 9,
            "hand_start_size": 3,
            "side_b_compensation": None,
            "death_retaliation": False,
            "ranked_time_per_turn": 60,
        }
        title.save()
        return title

    def clear_title_content(self, title):
        FriendlyChallenge.objects.filter(title=title).delete()
        MatchmakingQueue.objects.filter(deck__title=title).delete()
        Game.objects.filter(title=title).delete()
        UserTitleRating.objects.filter(title=title).delete()
        OwnedCard.objects.filter(card__title=title).delete()
        OwnedHero.objects.filter(hero__title=title).delete()
        Deck.objects.filter(title=title).delete()
        CardTemplate.objects.filter(title=title).delete()
        HeroTemplate.objects.filter(title=title).delete()
        TraitOverride.objects.filter(title=title).delete()
        Tag.objects.filter(title=title).delete()
        Faction.objects.filter(title=title).delete()

    def seed_content(self, title):
        manifest_path = Path(settings.BASE_DIR) / "dev_data" / "archetypes.yaml"
        if not manifest_path.exists():
            raise CommandError(f"Missing manifest: {manifest_path}")

        TitleService(title).ingest_yaml(manifest_path.read_text(encoding="utf-8"))

    def seed_decks(self, title, users):
        bloodmage = HeroTemplate.objects.get(
            title=title, slug="bloodmage", is_latest=True
        )
        balanced = HeroTemplate.objects.get(
            title=title, slug="balanced", is_latest=True
        )
        offensive = HeroTemplate.objects.get(
            title=title, slug="offensive", is_latest=True
        )
        defensive = HeroTemplate.objects.get(
            title=title, slug="defensive", is_latest=True
        )

        for hero in [bloodmage, balanced, offensive, defensive]:
            OwnedHero.objects.get_or_create(user=users["ios"], hero=hero)

        cards = list(
            CardTemplate.objects.filter(
                title=title,
                is_latest=True,
                is_collectible=True,
            ).order_by("cost", "name")
        )
        for card in cards:
            OwnedCard.objects.update_or_create(
                user=users["ios"],
                card=card,
                defaults={"count": 9},
            )

        ai_player, _ = AIPlayer.objects.get_or_create(
            name="Control",
            difficulty=AIPlayer.AI_DIFFICULTY_MEDIUM,
        )

        decks = {
            "ios": self.upsert_deck(
                title=title,
                owner=users["ios"],
                name="Bloodmage",
                hero=bloodmage,
                cards=cards,
            ),
            "finding": self.upsert_deck(
                title=title,
                owner=users["finding"],
                name="FindingDevo",
                hero=balanced,
                cards=cards,
            ),
            "ink": self.upsert_deck(
                title=title,
                owner=users["ink"],
                name="Inkgoblin",
                hero=offensive,
                cards=cards,
            ),
            "ai": self.upsert_deck(
                title=title,
                owner=ai_player,
                name="Control",
                hero=defensive,
                cards=cards,
            ),
            "ai_mulligan": self.upsert_deck(
                title=title,
                owner=ai_player,
                name="Control Opening",
                hero=defensive,
                cards=cards,
            ),
        }
        return decks

    def normalize_ai_decks(self, title):
        min_size = int(title.config.get("min_cards_in_deck", 10))
        ai_decks = Deck.objects.filter(
            title=title,
            ai_player__isnull=False,
            archived_at__isnull=True,
        ).select_related("hero")

        for deck in ai_decks:
            if validate_deck_for_play(deck) is None:
                continue

            eligible_cards = [
                card
                for card in CardTemplate.objects.filter(
                    title=title,
                    is_latest=True,
                    is_collectible=True,
                ).order_by("cost", "name")
                if card.is_available_to_hero(deck.hero)
            ]
            selected_cards = eligible_cards[:min_size]

            DeckCard.objects.filter(deck=deck).delete()
            for card in selected_cards:
                DeckCard.objects.create(deck=deck, card=card, count=1)

    def upsert_deck(self, title, owner, name, hero, cards):
        owner_field = "ai_player" if isinstance(owner, AIPlayer) else "user"
        deck = Deck.objects.filter(
            title=title,
            name=name,
            **{owner_field: owner},
            archived_at__isnull=True,
        ).first()
        if deck is None:
            deck = Deck.objects.create(
                title=title,
                name=name,
                hero=hero,
                description="Seeded local test deck.",
                **{owner_field: owner},
            )

        deck.title = title
        deck.hero = hero
        deck.description = "Seeded local test deck."
        deck.user = None
        deck.ai_player = None
        setattr(deck, owner_field, owner)
        deck.save()

        eligible_cards = [card for card in cards if card.is_available_to_hero(hero)]
        selected_cards = self.include_required_cards(
            eligible_cards[:10], eligible_cards, ["drawtwo"]
        )
        for card in selected_cards:
            DeckCard.objects.update_or_create(
                deck=deck,
                card=card,
                defaults={"count": 1},
            )
        DeckCard.objects.filter(deck=deck).exclude(
            card_id__in=[card.id for card in selected_cards]
        ).delete()
        return deck

    def include_required_cards(self, selected_cards, eligible_cards, required_slugs):
        selected_by_slug = {card.slug: card for card in selected_cards}
        eligible_by_slug = {card.slug: card for card in eligible_cards}
        selected = list(selected_cards)

        for slug in required_slugs:
            if slug in selected_by_slug or slug not in eligible_by_slug:
                continue
            if selected:
                selected[-1] = eligible_by_slug[slug]
            else:
                selected.append(eligible_by_slug[slug])
            selected_by_slug = {card.slug: card for card in selected}

        return selected

    def seed_friendships(self, users):
        self.upsert_friendship(
            users["ios"], users["finding"], Friendship.STATUS_ACCEPTED
        )
        self.upsert_friendship(users["ios"], users["ink"], Friendship.STATUS_PENDING)

    def upsert_friendship(self, user, friend, status):
        Friendship.objects.update_or_create(
            user=user,
            friend=friend,
            defaults={"status": status, "initiated_by": friend},
        )
        Friendship.objects.update_or_create(
            user=friend,
            friend=user,
            defaults={"status": status, "initiated_by": friend},
        )

    def seed_challenges(self, title, users, decks):
        FriendlyChallenge.objects.update_or_create(
            title=title,
            challenger=users["finding"],
            challengee=users["ios"],
            status=FriendlyChallenge.STATUS_PENDING,
            defaults={
                "challenger_deck": decks["finding"],
                "challengee_deck": None,
                "game": None,
            },
        )

    def seed_ranked_queue(self, title, users, decks, ladder_type, queue_age_seconds):
        MatchmakingQueue.objects.filter(
            user=users["ios"],
            deck__title=title,
            game__isnull=True,
        ).delete()

        rating = UserTitleRating.objects.filter(
            user=users["ios"],
            title=title,
            ladder_type=ladder_type,
        ).first()
        queue_entry = MatchmakingQueue.objects.create(
            user=users["ios"],
            deck=decks["ios"],
            ladder_type=ladder_type,
            status=MatchmakingQueue.STATUS_QUEUED,
            elo_rating=rating.elo_rating if rating else 1200,
            matched_with=None,
            game=None,
        )
        if queue_age_seconds:
            queued_at = timezone.now() - timedelta(seconds=queue_age_seconds)
            MatchmakingQueue.objects.filter(pk=queue_entry.pk).update(
                created_at=queued_at,
                updated_at=queued_at,
            )

    def seed_ratings_and_history(self, title, users, decks):
        rating_specs = [
            (users["ios"], 1285),
            (users["finding"], 1340),
            (users["ink"], 1215),
            (users["pilot"], 1180),
            (users["spindle"], 1125),
        ]

        ladder_offsets = {
            Game.LADDER_TYPE_DAILY: 0,
            Game.LADDER_TYPE_RAPID: -35,
        }
        for ladder_type, offset in ladder_offsets.items():
            for user, rating in rating_specs:
                UserTitleRating.objects.update_or_create(
                    user=user,
                    title=title,
                    ladder_type=ladder_type,
                    defaults={"elo_rating": rating + offset},
                )

        matchup_pairs = [
            (decks["ios"], decks["finding"], users["ios"], users["finding"]),
            (decks["finding"], decks["ios"], users["finding"], users["ios"]),
            (decks["ios"], decks["ink"], users["ios"], users["ink"]),
            (decks["ink"], decks["ios"], users["ink"], users["ios"]),
            (decks["finding"], decks["ink"], users["finding"], users["ink"]),
            (decks["ink"], decks["finding"], users["ink"], users["finding"]),
            (decks["ios"], decks["finding"], users["ios"], users["finding"]),
            (decks["ios"], decks["ink"], users["ios"], users["ink"]),
            (decks["finding"], decks["ios"], users["finding"], users["ios"]),
            (decks["finding"], decks["ink"], users["finding"], users["ink"]),
            (decks["ink"], decks["ios"], users["ink"], users["ios"]),
            (decks["ink"], decks["finding"], users["ink"], users["finding"]),
        ]

        for ladder_type in ladder_offsets:
            existing_games = ELORatingChange.objects.filter(
                title=title,
                ladder_type=ladder_type,
            ).count()
            if existing_games >= len(matchup_pairs):
                continue
            self.seed_ranked_history(title, matchup_pairs, ladder_type)

    def seed_ranked_history(self, title, matchup_pairs, ladder_type):
        rating_base = 1250 if ladder_type == Game.LADDER_TYPE_DAILY else 1200

        for index, (deck_a, deck_b, winner, loser) in enumerate(matchup_pairs):
            game = GameService.create_game(
                deck_a, deck_b, randomize_starting_player=False
            )
            game.type = Game.GAME_TYPE_RANKED
            game.ladder_type = ladder_type
            game.status = Game.GAME_STATUS_ENDED
            game.winner = deck_a if deck_a.user == winner else deck_b
            state = game.state
            state["winner"] = "side_a" if game.winner_id == game.side_a_id else "side_b"
            state["phase"] = "end"
            game.state = state
            game.save()

            ELORatingChange.objects.update_or_create(
                game=game,
                defaults={
                    "title": title,
                    "ladder_type": ladder_type,
                    "winner": winner,
                    "loser": loser,
                    "winner_old_rating": rating_base + index * 10,
                    "winner_new_rating": rating_base + 12 + index * 10,
                    "winner_rating_change": 12,
                    "loser_old_rating": rating_base - index * 5,
                    "loser_new_rating": rating_base - 12 - index * 5,
                    "loser_rating_change": -12,
                },
            )

    def seed_active_game(self, title, user, player_deck, ai_deck):
        active_game = self.find_in_progress_pve_game_by_phase(title, user, "main")
        if active_game:
            self.configure_active_game_for_ui(active_game)
            return active_game

        game = GameService.create_game(
            player_deck, ai_deck, randomize_starting_player=False
        )
        game.type = Game.GAME_TYPE_PVE
        game.ladder_type = None
        game.status = Game.GAME_STATUS_IN_PROGRESS
        game.queue = []
        game.save(update_fields=["type", "ladder_type", "status", "queue"])
        game.refresh_from_db()
        self.configure_active_game_for_ui(game)
        return game

    def seed_mulligan_game(self, title, user, player_deck, ai_deck):
        mulligan_game = self.find_in_progress_pve_game_by_phase(
            title, user, "mulligan"
        )
        if mulligan_game:
            self.configure_mulligan_game_for_ui(mulligan_game)
            return mulligan_game

        game = GameService.create_game(
            player_deck, ai_deck, randomize_starting_player=False
        )
        game.type = Game.GAME_TYPE_PVE
        game.ladder_type = None
        game.status = Game.GAME_STATUS_IN_PROGRESS
        game.queue = []
        game.save(update_fields=["type", "ladder_type", "status", "queue"])
        game.refresh_from_db()
        self.configure_mulligan_game_for_ui(game)
        return game

    def find_in_progress_pve_game_by_phase(self, title, user, phase):
        games = (
            Game.objects.for_title(title)
            .for_user(user)
            .filter(type=Game.GAME_TYPE_PVE, status=Game.GAME_STATUS_IN_PROGRESS)
            .order_by("-created_at")
        )

        for game in games:
            try:
                state = GameState.model_validate(game.state)
            except Exception:
                continue

            if state.phase == phase:
                return game

        return None

    def configure_active_game_for_ui(self, game):
        state = GameState.model_validate(game.state)
        side_a_cards = self.cards_by_slug_for_side(state, "side_a")
        side_b_cards = self.cards_by_slug_for_side(state, "side_b")

        state.active = "side_a"
        state.phase = "main"
        state.turn = 3
        state.winner = "none"
        state.rng_seed = "archetype-ui-active"
        state.rng_counter = 0
        state.heroes["side_a"].hero_id = "hero_side_a"
        state.heroes["side_b"].hero_id = "hero_side_b"
        state.queue = []
        state.event_queue = []
        state.mana_pool = {"side_a": 6, "side_b": 3}
        state.mana_used = {"side_a": 0, "side_b": 0}
        state.mulligan_done = {"side_a": True, "side_b": True}
        state.mulligan_options = {"side_a": [], "side_b": []}
        state.board = {"side_a": [], "side_b": []}
        state.creatures = {}
        state.last_creature_id = 0

        side_a_hand_slugs = ["drawtwo", "zap", "bandage", "mongoose"]
        side_a_board_slugs = ["archer"]
        side_a_deck_slugs = ["cleave", "decoy", "hornet", "sharpen", "harbinger", "brute"]
        side_b_hand_slugs = ["zap", "bandage", "mongoose"]
        side_b_board_slugs = ["decoy", "brute"]
        side_b_deck_slugs = ["archer", "cleave", "hornet", "sharpen", "harbinger"]

        side_a_hand = self.card_ids_for_slugs(side_a_cards, side_a_hand_slugs)
        side_a_board = [
            side_a_cards[slug] for slug in side_a_board_slugs if slug in side_a_cards
        ]
        side_a_deck = self.card_ids_for_slugs(side_a_cards, side_a_deck_slugs)
        side_b_hand = self.card_ids_for_slugs(side_b_cards, side_b_hand_slugs)
        side_b_board = [
            side_b_cards[slug] for slug in side_b_board_slugs if slug in side_b_cards
        ]
        side_b_deck = self.card_ids_for_slugs(side_b_cards, side_b_deck_slugs)

        state.hands["side_a"] = side_a_hand
        state.hands["side_b"] = side_b_hand
        state.decks["side_a"] = side_a_deck
        state.decks["side_b"] = side_b_deck

        for position, card in enumerate(side_a_board):
            creature = spawn_creature(card, state, "side_a", position)
            creature.exhausted = False

        for position, card in enumerate(side_b_board):
            creature = spawn_creature(card, state, "side_b", position)
            creature.exhausted = False

        game.state = state.model_dump(mode="json")
        game.save(update_fields=["state"])
        self.seed_active_game_updates(game, state)

    def configure_mulligan_game_for_ui(self, game):
        state = GameState.model_validate(game.state)
        side_a_cards = self.cards_by_slug_for_side(state, "side_a")
        side_b_cards = self.cards_by_slug_for_side(state, "side_b")

        state.active = "side_a"
        state.phase = "mulligan"
        state.turn = 1
        state.winner = "none"
        state.rng_seed = "archetype-ui-mulligan"
        state.rng_counter = 0
        state.heroes["side_a"].hero_id = "hero_side_a"
        state.heroes["side_b"].hero_id = "hero_side_b"
        state.queue = []
        state.event_queue = []
        state.mana_pool = {"side_a": 0, "side_b": 0}
        state.mana_used = {"side_a": 0, "side_b": 0}
        state.mulligan_done = {"side_a": False, "side_b": True}
        state.board = {"side_a": [], "side_b": []}
        state.creatures = {}
        state.last_creature_id = 0

        side_a_hand_slugs = ["zap", "bandage", "mongoose"]
        side_a_deck_slugs = [
            "cleave",
            "decoy",
            "hornet",
            "sharpen",
            "harbinger",
            "archer",
            "brute",
        ]
        side_b_hand_slugs = ["decoy", "brute", "zap"]
        side_b_deck_slugs = [
            "archer",
            "cleave",
            "hornet",
            "sharpen",
            "harbinger",
            "bandage",
            "mongoose",
        ]

        side_a_hand = self.card_ids_for_slugs(side_a_cards, side_a_hand_slugs)
        side_b_hand = self.card_ids_for_slugs(side_b_cards, side_b_hand_slugs)
        state.hands["side_a"] = side_a_hand
        state.hands["side_b"] = side_b_hand
        state.decks["side_a"] = self.card_ids_for_slugs(
            side_a_cards, side_a_deck_slugs
        )
        state.decks["side_b"] = self.card_ids_for_slugs(
            side_b_cards, side_b_deck_slugs
        )
        state.mulligan_options = {
            "side_a": list(side_a_hand),
            "side_b": [],
        }

        game.state = state.model_dump(mode="json")
        game.save(update_fields=["state"])
        GameUpdate.objects.filter(game=game).delete()

    def seed_active_game_updates(self, game, state):
        GameUpdate.objects.filter(game=game).delete()

        base_timestamp = timezone.now()
        updates = []
        for side in ["side_a", "side_b"]:
            for card_id in state.hands.get(side, [])[:3]:
                timestamp = (
                    base_timestamp + timedelta(microseconds=len(updates))
                ).isoformat().replace("+00:00", "Z")
                updates.append(
                    {
                        "side": side,
                        "type": "update_draw_card",
                        "card_id": card_id,
                        "target_type": "card",
                        "target_id": card_id,
                        "timestamp": timestamp,
                    }
                )

        for update in updates:
            GameUpdate.objects.create(game=game, update=update)

    def normalize_game_timestamps(self, title, user, game_age_seconds):
        games = list(
            Game.objects.where_user_is_side(title, user)
            .filter(
                status__in=[
                    Game.GAME_STATUS_ENDED,
                    Game.GAME_STATUS_IN_PROGRESS,
                ]
            )
            .order_by("created_at", "id")
        )
        if not games:
            return

        latest_timestamp = timezone.now() - timedelta(seconds=game_age_seconds)
        first_timestamp = latest_timestamp - timedelta(seconds=len(games) - 1)

        for index, game in enumerate(games):
            timestamp = first_timestamp + timedelta(seconds=index)
            Game.objects.filter(pk=game.pk).update(
                created_at=timestamp,
                updated_at=timestamp,
            )

    def cards_by_slug_for_side(self, state, side):
        zone_ids = self.card_ids_for_side(state, side)
        return {
            state.cards[card_id].template_slug: state.cards[card_id]
            for card_id in zone_ids
            if card_id in state.cards
        }

    def card_ids_for_slugs(self, cards_by_slug, slugs):
        return [
            cards_by_slug[slug].card_id
            for slug in slugs
            if slug in cards_by_slug
        ]

    def card_ids_for_side(self, state, side):
        seen = set()
        ordered = []

        for creature_id in state.board.get(side, []):
            creature = state.creatures.get(creature_id)
            if creature is None or creature.card_id in seen:
                continue
            seen.add(creature.card_id)
            ordered.append(creature.card_id)

        for zone in (state.hands, state.decks, state.graveyard):
            for card_id in zone.get(side, []):
                if card_id in seen:
                    continue
                seen.add(card_id)
                ordered.append(card_id)
        return ordered
