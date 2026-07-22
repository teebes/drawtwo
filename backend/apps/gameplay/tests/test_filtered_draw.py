from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.builder.models import CardTemplate, Faction, Tag, Title
from apps.builder.schemas import Battlecry, DrawAction, Unique
from apps.core.serializers import to_card_schema
from apps.gameplay.agents.ruleset import compute_ruleset_id
from apps.gameplay.agents.simulator import apply_effects
from apps.gameplay.engine.dispatcher import resolve
from apps.gameplay.schemas.effects import DrawEffect, PlayEffect
from apps.gameplay.schemas.game import CardInPlay
from apps.gameplay.services import GameService
from apps.gameplay.tests import GamePlayTestBase

User = get_user_model()


class FilteredDrawTests(GamePlayTestBase):
    def add_card(
        self,
        card_id: str,
        *,
        traits=None,
        spec=None,
        tags=None,
        card_type="creature",
    ) -> CardInPlay:
        card = CardInPlay(
            card_type=card_type,
            card_id=card_id,
            template_slug=card_id,
            name=card_id,
            traits=traits or [],
            spec=spec or {},
            tags=tags or [],
        )
        self.game_state.cards[card_id] = card
        return card

    def test_draws_first_matching_card_without_reordering_nonmatches(self):
        self.add_card("regular-1")
        self.add_card("unique-1", traits=[Unique()])
        self.add_card("regular-2")
        self.game_state.decks["side_a"] = ["regular-1", "unique-1", "regular-2"]

        result = resolve(
            DrawEffect(
                side="side_a",
                amount=1,
                spec={"traits": [{"type": "unique"}]},
            ),
            self.game_state,
        )

        self.assertEqual(result.new_state.hands["side_a"], ["unique-1"])
        self.assertEqual(result.new_state.decks["side_a"], ["regular-1", "regular-2"])
        self.assertEqual([event.card_id for event in result.events], ["unique-1"])

    def test_draws_available_matches_then_stops_without_game_over(self):
        self.add_card("unique-1", traits=[Unique()])
        self.add_card("unique-2", traits=[Unique()])
        self.game_state.decks["side_a"] = ["unique-1", "unique-2"]

        result = resolve(
            DrawEffect(
                side="side_a",
                amount=3,
                spec={"traits": ["unique"]},
            ),
            self.game_state,
        )

        self.assertEqual(result.new_state.hands["side_a"], ["unique-1", "unique-2"])
        self.assertEqual(result.new_state.decks["side_a"], [])
        self.assertEqual(
            [event.type for event in result.events], ["event_draw", "event_draw"]
        )
        self.assertEqual(result.new_state.winner, "none")

    def test_empty_filtered_draw_stops_without_game_over(self):
        result = resolve(
            DrawEffect(
                side="side_a",
                amount=1,
                spec={"traits": ["unique"]},
            ),
            self.game_state,
        )

        self.assertEqual(result.events, [])
        self.assertEqual(result.new_state.winner, "none")

    def test_filtered_miss_leaves_nonmatching_cards_in_the_deck(self):
        self.add_card("regular")
        self.game_state.decks["side_a"] = ["regular"]

        result = resolve(
            DrawEffect(
                side="side_a",
                spec={"traits": ["unique"]},
            ),
            self.game_state,
        )

        self.assertEqual(result.events, [])
        self.assertEqual(result.new_state.hands["side_a"], [])
        self.assertEqual(result.new_state.decks["side_a"], ["regular"])

    def test_matches_card_metadata_as_a_partial_spec(self):
        self.add_card(
            "common",
            spec={"rarity": "common", "school": {"name": "arcane"}},
            tags=["spellcraft"],
        )
        self.add_card(
            "legendary",
            spec={
                "rarity": "legendary",
                "school": {"name": "arcane", "rank": 2},
            },
            tags=["spellcraft", "signature"],
        )
        self.game_state.decks["side_a"] = ["common", "legendary"]

        result = resolve(
            DrawEffect(
                side="side_a",
                spec={
                    "rarity": "legendary",
                    "school": {"name": "arcane"},
                    "tags": ["signature"],
                },
            ),
            self.game_state,
        )

        self.assertEqual(result.new_state.hands["side_a"], ["legendary"])
        self.assertEqual(result.new_state.decks["side_a"], ["common"])

    def test_spell_battlecry_draws_a_unique_card_end_to_end(self):
        spell = self.add_card(
            "seek-the-unique",
            card_type="spell",
            traits=[
                Battlecry(
                    actions=[
                        DrawAction(
                            amount=1,
                            spec={"traits": [{"type": "unique"}]},
                        )
                    ]
                )
            ],
        )
        spell.cost = 1
        self.add_card("regular")
        self.add_card("unique", traits=[Unique()])
        self.game_state.hands["side_a"] = [spell.card_id]
        self.game_state.decks["side_a"] = ["regular", "unique"]
        self.game_state.mana_pool["side_a"] = 1

        result = apply_effects(
            self.game_state,
            [PlayEffect(side="side_a", source_id=spell.card_id, position=0)],
        )

        self.assertEqual(result.errors, [])
        self.assertEqual(result.state.hands["side_a"], ["unique"])
        self.assertEqual(result.state.decks["side_a"], ["regular"])
        self.assertEqual(result.state.graveyard["side_a"], [spell.card_id])
        self.assertEqual(
            [event["type"] for event in result.events],
            ["event_play", "event_draw"],
        )


class FilterableCardStateTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            email="filtered-draw-author@example.com",
            username="filtered-draw-author",
        )
        self.title = Title.objects.create(
            slug="filtered-draw",
            name="Filtered Draw",
            author=self.author,
        )
        self.faction = Faction.objects.create(
            title=self.title,
            slug="mystic",
            name="Mystic",
        )
        self.tag = Tag.objects.create(
            title=self.title,
            slug="signature",
            name="Signature",
        )
        self.template = CardTemplate.objects.create(
            title=self.title,
            slug="legendary-card",
            name="Legendary Card",
            card_type=CardTemplate.CARD_TYPE_CREATURE,
            cost=2,
            attack=2,
            health=2,
            faction=self.faction,
            spec={"rarity": "legendary"},
        )
        self.template.tags.add(self.tag)
        self.template.add_trait("unique")

    def test_card_metadata_is_preserved_in_gameplay_state(self):
        template = (
            CardTemplate.objects.select_related("title", "faction")
            .prefetch_related("cardtrait_set", "allowed_heroes", "tags")
            .get(pk=self.template.pk)
        )

        card = GameService.get_card_in_play(to_card_schema(template), card_id=1)

        self.assertEqual(card.faction, "mystic")
        self.assertEqual(card.spec, {"rarity": "legendary"})
        self.assertEqual(card.tags, ["signature"])
        self.assertTrue(card.has_trait("unique"))

    def test_ruleset_id_includes_filterable_card_metadata(self):
        initial_id = compute_ruleset_id(self.title)

        self.template.spec = {"rarity": "common"}
        self.template.save(update_fields=["spec"])
        changed_spec_id = compute_ruleset_id(self.title)

        self.template.tags.clear()
        changed_tags_id = compute_ruleset_id(self.title)

        self.template.faction = None
        self.template.save(update_fields=["faction"])
        changed_faction_id = compute_ruleset_id(self.title)

        self.assertNotEqual(initial_id, changed_spec_id)
        self.assertNotEqual(changed_spec_id, changed_tags_id)
        self.assertNotEqual(changed_tags_id, changed_faction_id)
