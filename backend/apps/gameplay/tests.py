from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.builder.models import (
    AIPlayer,
    CardTemplate,
    HeroTemplate,
    Title,
)
from apps.builder.schemas import (
    Battlecry,
    DamageAction,
    DrawAction,
    Charge,
    HeroPower,
)
from apps.collection.models import Deck, DeckCard
from apps.gameplay.engine.dispatcher import resolve
from apps.gameplay.schemas.engine import Success, Prevented, Rejected
from apps.gameplay.schemas.effects import (
    DamageEffect,
    DrawEffect,
    PlayEffect,
    StartGameEffect,
    UseHeroEffect,
)
from apps.gameplay.schemas.events import PlayEvent
from apps.gameplay.schemas.game import GameState, CardInPlay, HeroInPlay
from apps.gameplay.services import GameService
from apps.gameplay import traits

User = get_user_model()


class ServiceTestsBase(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="testuser@example.com",
            username="testuser"
        )
        self.ai_player = AIPlayer.objects.create(name='AI')

        self.title = Title.objects.create(slug='title', author=self.user)

        self.hero_a = HeroTemplate.objects.create(
            title=self.title, slug='hero-a', name="Hero A", health=10)
        self.hero_b = HeroTemplate.objects.create(
            title=self.title, slug='hero-b', name="Hero B", health=10)
        self.deck_a = Deck.objects.create(
            title=self.title, user=self.user, name="Deck A", hero=self.hero_a)
        self.deck_b = Deck.objects.create(
            title=self.title, ai_player=self.ai_player, name="Deck B", hero=self.hero_b)

        for i in range(0, 4):
            card = CardTemplate.objects.create(
                title=self.title,
                slug='card-%s' % i,
                name='Card %s' % i,
            )
            DeckCard.objects.create(deck=self.deck_a, card=card)
            DeckCard.objects.create(deck=self.deck_b, card=card)

        self.game = GameService.start_game(self.deck_a, self.deck_b)


class ServiceTests(ServiceTestsBase):

    def test_create_game(self):
        game = self.game

        self.assertEqual(game.side_a, self.deck_a)
        self.assertEqual(game.side_b, self.deck_b)
        self.assertEqual(game.status, 'init')
        self.assertEqual(game.state['heroes']['side_a']['template_slug'], 'hero-a')
        self.assertEqual(game.state['heroes']['side_b']['template_slug'], 'hero-b')
        self.assertEqual(game.state['turn'], 0)
        self.assertEqual(game.state['active'], 'side_a')
        self.assertEqual(game.state['phase'], 'start')
        self.assertEqual(game.state['cards']["1"]['template_slug'], 'card-0')
        # Queue is now stored separately in game.queue field
        self.assertEqual(game.queue[0]['type'], 'effect_start_game')

    def test_start_game_effect(self):
        while self.game.queue:
            GameService.step(self.game.id)
            self.game.refresh_from_db()

        #self.assertEqual(self.game.queue, [])
        self.assertEqual(self.game.state['turn'], 1)
        self.assertEqual(self.game.state['active'], 'side_a')
        self.assertEqual(self.game.state['phase'], 'main')
        self.assertEqual(len(self.game.state['hands']['side_a']), 4)
        self.assertEqual(len(self.game.state['hands']['side_b']), 3)


class ProcessCommandTests(ServiceTestsBase):

    def setUp(self):
        super().setUp()
        while self.game.queue:
            GameService.step(self.game.id)
            self.game.refresh_from_db()

    def test_attack(self):
        self.game.state['board']['side_a'] = ["card-1"]
        self.game.state['board']['side_b'] = ["card-2"]
        command = {
            'type': 'cmd_attack',
            'card_id': 'card-1',
            'target_id': 'card-2',
            'target_type': 'creature'
        }
        GameService.process_command(self.game.id, command, 'side_a')
        self.game.refresh_from_db()
        self.assertEqual(len(self.game.queue), 1)
        self.assertEqual(self.game.queue[0]['type'], 'effect_attack')
        self.assertEqual(self.game.queue[0]['target_type'], 'creature')
        self.assertEqual(self.game.queue[0]['target_id'], 'card-2')
        self.assertEqual(self.game.queue[0]['card_id'], 'card-1')

    def test_end_turn(self):
        command = {'type': 'cmd_end_turn'}
        GameService.process_command(self.game.id, command, 'side_a')
        self.game.refresh_from_db()
        self.assertEqual(len(self.game.queue), 1)
        self.assertEqual(self.game.queue[0]['type'], 'effect_end_turn')


class GamePlayTestBase(TestCase):

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self.game_state = GameState(
            turn=1,
            active="side_a",
            phase="start",
            queue=[],
            event_queue=[],
            cards={},
            decks={'side_a': [], 'side_b': []},
            mana_pool={'side_a': 0, 'side_b': 0},
            mana_used={'side_a': 0, 'side_b': 0},
            board={'side_a': [], 'side_b': []},
            hands={'side_a': [], 'side_b': []},
            heroes={
                'side_a': HeroInPlay(
                    hero_id="1",
                    template_slug="hero_a",
                    health=10,
                    name="Hero A",
                    hero_power=HeroPower(
                        actions=[
                            DamageAction(
                                amount=1,
                                target="enemy",
                            )
                        ]
                    ),
                ),
                'side_b': HeroInPlay(
                    hero_id="2",
                    template_slug="hero_b",
                    health=10,
                    name="Hero B",
                    hero_power=HeroPower(
                        actions=[
                            DamageAction(
                                amount=1,
                                target="enemy",
                            )
                        ]
                    ),
                ),
            },
        )


class EngineTests(GamePlayTestBase):
    "Tests effect resolution by the game engine."

    def test_start_game_effect(self):
        effect = StartGameEffect(side='side_a')
        result = resolve(effect, self.game_state)
        self.assertTrue(isinstance(result, Success))
        self.assertEqual(len(result.child_effects), 7)
        self.assertEqual(result.child_effects[0].type, 'effect_draw')
        self.assertEqual(result.child_effects[0].side, 'side_a')
        self.assertEqual(result.child_effects[1].type, 'effect_draw')
        self.assertEqual(result.child_effects[1].side, 'side_a')
        self.assertEqual(result.child_effects[2].type, 'effect_draw')
        self.assertEqual(result.child_effects[2].side, 'side_a')
        self.assertEqual(result.child_effects[3].type, 'effect_draw')
        self.assertEqual(result.child_effects[3].side, 'side_b')
        self.assertEqual(result.child_effects[4].type, 'effect_draw')
        self.assertEqual(result.child_effects[4].side, 'side_b')
        self.assertEqual(result.child_effects[5].type, 'effect_draw')
        self.assertEqual(result.child_effects[5].side, 'side_b')
        self.assertEqual(result.child_effects[6].type, 'effect_phase')

    def test_play_creature_card_to_board(self):
        creature = CardInPlay(
            card_type="creature",
            card_id="1",
            template_slug="test",
            name="test",
            attack=1,
            health=1,
            cost=1,
            exhausted=False,
        )
        self.game_state.cards["1"] = creature
        self.game_state.hands["side_a"] = ["1"]
        self.game_state.mana_pool["side_a"] = 1
        self.game_state.mana_used["side_a"] = 0

        effect = PlayEffect(
            side="side_a",
            source_id="1",
            position=0,
        )
        result = resolve(effect, self.game_state)
        new_state = result.new_state
        self.assertEqual(new_state.board["side_a"], ["1"])

    def test_use_hero_power_on_hero(self):
        effect = UseHeroEffect(
            side="side_a",
            source_id="hero_a",
            target_type="hero",
            target_id="2",
        )

        # Hero power can't be used if the hero is exhausted
        self.assertTrue(self.game_state.heroes["side_a"].exhausted)
        result = resolve(effect, self.game_state)
        self.assertTrue(isinstance(result, Rejected))
        self.assertEqual(result.reason, "Hero is exhausted")

        # Hero power can be used if the hero is not exhausted
        self.game_state.heroes["side_a"].exhausted = False
        result = resolve(effect, self.game_state)
        self.assertTrue(isinstance(result, Success))
        self.assertEqual(len(result.child_effects), 2)
        self.assertEqual(result.child_effects[0].type, 'effect_damage')
        self.assertEqual(result.child_effects[1].type, 'effect_mark_exhausted')

    def test_play_spell_card(self):
        spell_card = CardInPlay(
            card_type="spell",
            card_id="1",
            template_slug="small-nuke",
            name="Small Nuke",
            cost=1,
            traits=[
                Battlecry(
                    actions=[
                        DamageAction(
                            amount=1,
                            target="enemy",
                        )
                    ]
                )
            ],
        )

        # Play can't afford the spell
        self.game_state.mana_pool["side_a"] = 1
        self.game_state.mana_used["side_a"] = 1
        self.game_state.cards["1"] = spell_card
        self.game_state.hands["side_a"] = ["1"]
        play_effect = PlayEffect(
            side="side_a",
            source_id="1",
            position=0,
            target_type="hero",
            target_id="2",
        )
        result = resolve(play_effect, self.game_state)
        self.assertTrue(isinstance(result, Rejected))
        self.assertIn("energy", result.reason.lower())

        # Play can afford the spell
        self.game_state.mana_pool["side_a"] = 1
        self.game_state.mana_used["side_a"] = 0
        self.game_state.cards["1"] = spell_card
        self.game_state.hands["side_a"] = ["1"]

        play_effect = PlayEffect(
            side="side_a",
            source_id="1",
            position=0,
            target_type="hero",
            target_id="2",
        )
        result = resolve(play_effect, self.game_state)
        self.assertTrue(isinstance(result, Success))
        new_state = result.new_state

        # PlayEffect generates a PlayEvent that triggers battlecry actions
        self.assertEqual(result.events[0].type, 'event_play')
        self.assertEqual(new_state.hands["side_a"], [])
        self.assertEqual(new_state.graveyard["side_a"], ["1"])
        self.assertEqual(new_state.mana_used["side_a"], 1)

    def test_play_spell_card_on_creature(self):
        spell_card = CardInPlay(
            card_type="spell",
            card_id="1",
            template_slug="small-nuke",
            name="Small Nuke",
            cost=1,
            traits=[
                Battlecry(
                    actions=[
                        DamageAction(
                            amount=1,
                            target="enemy",
                        )
                    ]
                )
            ],
        )

        creature_card = CardInPlay(
            card_type="creature",
            card_id="2",
            template_slug="test",
            name="test",
            attack=1,
            health=10,
            cost=1,
            exhausted=False,
        )

        self.game_state.mana_pool["side_a"] = 1
        self.game_state.mana_used["side_a"] = 0
        self.game_state.cards["1"] = spell_card
        self.game_state.cards["2"] = creature_card
        self.game_state.hands["side_a"] = ["1"]
        self.game_state.board["side_b"] = ["2"]

        play_effect = PlayEffect(
            side="side_a",
            source_id="1",
            position=0,
            target_type="creature",
            target_id="2",
        )
        result = resolve(play_effect, self.game_state)
        self.assertTrue(isinstance(result, Success))
        new_state = result.new_state

        # PlayEffect generates a PlayEvent that triggers battlecry actions
        self.assertEqual(result.events[0].type, 'event_play')
        self.assertEqual(new_state.hands["side_a"], [])
        self.assertEqual(new_state.graveyard["side_a"], ["1"])
        self.assertEqual(new_state.mana_used["side_a"], 1)

        # Now process the PlayEvent through traits to trigger the battlecry
        play_event = result.events[0]
        trait_result = traits.apply(new_state, play_event)
        self.assertEqual(len(trait_result.child_effects), 1)
        self.assertEqual(trait_result.child_effects[0].type, 'effect_damage')

        # Actually resolve the DamageEffect that was generated by the battlecry
        damage_effect = trait_result.child_effects[0]
        damage_result = resolve(damage_effect, new_state)
        self.assertTrue(isinstance(damage_result, Success))
        # This should work without errors - creature should take 1 damage
        self.assertEqual(damage_result.new_state.cards["2"].health, 9)


class TestDamage(GamePlayTestBase):

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self.creature = CardInPlay(
            card_type="creature",
            card_id="1",
            template_slug="test",
            name="test",
            attack=1,
            health=1,
            cost=1,
            exhausted=False,
        )

    def test_creature_to_hero_damage(self):
        self.game_state.cards["1"] = self.creature
        self.game_state.board['side_a'] = ["1"]
        damage_effect = DamageEffect(
            side="side_a",
            damage_type="physical",
            source_type="card",
            source_id="1",
            target_type="hero",
            target_id="2",
            damage=1,
        )

        result = resolve(damage_effect, self.game_state)
        self.assertTrue(isinstance(result, Success))
        new_state = result.new_state

        # The target hero's health went down
        self.assertEqual(new_state.heroes['side_b'].health, 9)

        # A DamageEvent is created for UI updates
        self.assertEqual(len(result.events), 1)
        self.assertEqual(result.events[0].type, 'event_damage')

        # Attacking creature is exhausted
        self.assertTrue(new_state.cards["1"].exhausted)

    def test_creature_to_creature_damage(self):
        target_creature = CardInPlay(
            card_type="creature",
            card_id="2",
            template_slug="test",
            name="test",
            attack=2,
            health=10,
            cost=1,
            exhausted=False,
        )

        self.game_state.cards["1"] = self.creature
        self.game_state.cards["2"] = target_creature
        self.game_state.board['side_a'] = ["1"]
        self.game_state.board['side_b'] = ["2"]
        damage_effect = DamageEffect(
            side="side_a",
            damage_type="physical",
            source_type="card",
            source_id="1",
            target_type="card",
            target_id="2",
            damage=1,
            retaliate=True,
        )

        result = resolve(damage_effect, self.game_state)
        self.assertTrue(isinstance(result, Success))
        new_state = result.new_state

        # The target creature's health went down
        self.assertEqual(new_state.cards["2"].health, 9)

        # Two events created: initial damage and retaliation
        self.assertEqual(len(result.events), 2)
        self.assertEqual(result.events[0].type, "event_damage")
        self.assertEqual(result.events[1].type, "event_damage")
        # Retaliation event is the second one
        # Retaliation source is the target creature
        self.assertEqual(result.events[1].source_id, "2")
        self.assertEqual(result.events[1].source_type, "card")
        # Retaliation targets the source creature
        self.assertEqual(result.events[1].target_id, "1")
        self.assertEqual(result.events[1].target_type, "card")
        # Retaliation damage is the target creature's attack
        self.assertEqual(result.events[1].damage, 2)
        # Retaliation doesn't retaliate to avoid an infinite loop
        self.assertFalse(result.events[1].retaliate)

    def test_creature_to_creature_retaliation(self):
        """
        Make sure that a retaliation effect does not generate another
        retaliation event even if it otherwise would.
        """
        target_creature = CardInPlay(
            card_type="creature",
            card_id="2",
            template_slug="test",
            name="test",
            attack=2,
            health=10,
            cost=1,
            exhausted=False,
        )

        self.game_state.cards["1"] = self.creature
        self.game_state.cards["2"] = target_creature
        self.game_state.board['side_a'] = ["1"]
        self.game_state.board['side_b'] = ["2"]
        damage_effect = DamageEffect(
            side="side_a",
            damage_type="physical",
            source_type="card",
            source_id="1",
            target_type="card",
            target_id="2",
            damage=1,
            retaliate=False,
        )

        result = resolve(damage_effect, self.game_state)
        self.assertTrue(isinstance(result, Success))

        # Only one event created (the initial damage), no retaliation
        self.assertEqual(len(result.events), 1)
        self.assertEqual(result.events[0].type, "event_damage")

    def test_hero_to_creature_damage(self):
        self.creature.health = 10
        self.game_state.cards["1"] = self.creature
        self.game_state.board['side_b'] = ["1"]
        damage_effect = DamageEffect(
            side="side_a",
            damage_type="physical",
            source_type="hero",
            source_id="1",
            target_type="card",
            target_id="1",
            damage=1,
        )

        result = resolve(damage_effect, self.game_state)
        self.assertTrue(isinstance(result, Success))
        new_state = result.new_state

        # The target creature's health went down
        self.assertEqual(new_state.cards["1"].health, 9)

        # Two events created: initial damage and retaliation from creature
        self.assertEqual(len(result.events), 2)
        self.assertEqual(result.events[0].type, "event_damage")
        self.assertEqual(result.events[1].type, "event_damage")
        # Creatures retaliate against heroes
        self.assertEqual(result.events[1].retaliate, False)
        self.assertEqual(result.events[1].source_id, "1")
        self.assertEqual(result.events[1].source_type, "card")
        self.assertEqual(result.events[1].target_id, "1")
        self.assertEqual(result.events[1].target_type, "hero")

    def test_hero_to_hero_damage(self):
        self.game_state.heroes['side_a'].health = 10
        self.game_state.heroes['side_b'].health = 10
        damage_effect = DamageEffect(
            side="side_a",
            damage_type="physical",
            source_type="hero",
            source_id="1",
            target_type="hero",
            target_id="2",
            damage=1,
        )
        result = resolve(damage_effect, self.game_state)
        self.assertTrue(isinstance(result, Success))
        self.assertEqual(result.new_state.heroes['side_b'].health, 9)


class TestTraits(GamePlayTestBase):

    def test_battlecry_draw(self):
        battlecry_draw = CardInPlay(
            card_type="creature",
            card_id="1",
            template_slug="battlecry-draw",
            name="Battlecry Draw",
            description="Battlecry: Draw a card.",
            attack=1,
            health=1,
            cost=1,
            traits=[
                Battlecry(
                    type="battlecry",
                    actions=[
                        DrawAction()
                    ],
                )
            ],
        )

        self.game_state.cards["1"] = battlecry_draw
        self.game_state.hands["side_a"] = ["1"]
        self.game_state.mana_pool["side_a"] = 1
        self.game_state.mana_used["side_a"] = 0

        # First, resolve the play effect
        play_effect = PlayEffect(
            side="side_a",
            source_id="1",
            position=0,
        )

        result = resolve(play_effect, self.game_state)
        self.assertTrue(isinstance(result, Success))
        new_state = result.new_state

        # Card is on the board
        self.assertEqual(new_state.board["side_a"], ["1"])
        # PlayEvent is generated
        self.assertEqual(result.events[0].type, 'event_play')

        # Now process the PlayEvent through the trait system to trigger battlecry
        play_event = result.events[0]
        trait_result = traits.apply(new_state, play_event)

        # The DrawAction should create a DrawEffect as a child effect
        self.assertEqual(len(trait_result.child_effects), 1)
        self.assertEqual(trait_result.child_effects[0].type, 'effect_draw')
        self.assertEqual(trait_result.child_effects[0].side, 'side_a')


class TestEndGame(GamePlayTestBase):

    def test_decking_out_via_card_action(self):
        # Ensure the deck is empty
        self.game_state.decks["side_a"] = []

        draw_effect = DrawEffect(
            side="side_a",
            amount=1,
        )
        result = resolve(draw_effect, self.game_state)
        self.assertTrue(isinstance(result, Success))
        # When deck is empty, a GameOverEvent is generated
        self.assertEqual(len(result.events), 1)
        self.assertEqual(result.events[0].type, 'event_game_over')
        # The opposing side wins
        self.assertEqual(result.events[0].winner, 'side_b')

    def test_hero_death_by_damage(self):
        damage_effect = DamageEffect(
            side="side_a",
            damage_type="physical",
            source_type="hero",
            source_id="1",
            target_type="hero",
            target_id="2",
            damage=10,
        )

        result = resolve(damage_effect, self.game_state)
        self.assertTrue(isinstance(result, Success))
        new_state = result.new_state
        self.assertEqual(result.events[0].type, 'event_damage')
        self.assertEqual(result.events[1].type, 'event_game_over')
        self.assertEqual(result.events[1].winner, 'side_a')


class TestTraitProcessing(GamePlayTestBase):
    """Tests for the event-driven trait processing system."""

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        # Add test cards with traits
        self.game_state.cards["card_1"] = CardInPlay(
            card_type="creature",
            card_id="card_1",
            template_slug="test-card",
            name="Test Card",
            attack=2,
            health=3,
            cost=2,
            traits=[Charge()],
            exhausted=True
        )
        self.game_state.cards["card_2"] = CardInPlay(
            card_type="creature",
            card_id="card_2",
            template_slug="battlecry-card",
            name="Battlecry Card",
            attack=1,
            health=2,
            cost=1,
            traits=[Battlecry(actions=[DrawAction(amount=2)])],
            exhausted=True
        )

    def test_charge_trait(self):
        """Test that charge trait sets exhausted to False on play."""
        # Create a play event for a card with charge
        play_event = PlayEvent(
            side="side_a",
            source_type="card",
            source_id="card_1",
            position=0
        )

        # Card should start exhausted
        self.assertTrue(self.game_state.cards["card_1"].exhausted)

        # Apply traits
        result = traits.apply(self.game_state, play_event)

        # Card should no longer be exhausted
        self.assertFalse(self.game_state.cards["card_1"].exhausted)
        self.assertEqual(len(result.child_effects), 0)

    def test_damage_battlecry(self):
        self.game_state.board["side_b"] = ["card_1"]
        self.assertEqual(self.game_state.cards["card_1"].health, 3)

        battlecry_damage = CardInPlay(
            card_type="creature",
            card_id="card_3",
            template_slug="battlecry-damage",
            name="Battlecry Damage",
            description="Battlecry: Deal 1 damage to a target.",
            attack=1,
            health=1,
            cost=1,
            traits=[Battlecry(actions=[DamageAction(amount=1, target="enemy")])],
            exhausted=False,
        )
        self.game_state.cards["card_3"] = battlecry_damage
        self.game_state.hands["side_a"] = ["card_3"]
        event = PlayEvent(
            side="side_a",
            source_type="card",
            source_id="card_3",
            position=0,
            target_type="creature",
            target_id="card_1",
        )
        result = traits.apply(self.game_state, event)
        self.assertTrue(isinstance(result, Success))
        self.assertEqual(result.child_effects[0].type, "effect_damage")
        self.assertEqual(result.child_effects[0].side, "side_a")
        self.assertEqual(result.child_effects[0].source_type, "card")
        self.assertEqual(result.child_effects[0].source_id, "card_3")
        self.assertEqual(result.child_effects[0].target_type, "creature")
        self.assertEqual(result.child_effects[0].target_id, "card_1")
        self.assertEqual(result.child_effects[0].damage, 1)
        self.assertEqual(result.child_effects[0].retaliate, False)

    def test_battlecry_trait_direct(self):
        """Test that battlecry trait generates child effects on play."""
        # Create a play event for a card with battlecry
        play_event = PlayEvent(
            side="side_a",
            source_type="card",
            source_id="card_2",
            position=0
        )

        # Apply traits
        result = traits.apply(self.game_state, play_event)

        # Should generate a DrawEffect
        self.assertEqual(len(result.child_effects), 1)
        self.assertIsInstance(result.child_effects[0], DrawEffect)
        self.assertEqual(result.child_effects[0].amount, 2)
        self.assertEqual(result.child_effects[0].side, "side_a")

    def test_no_trait_triggers(self):
        """Test that non-triggering events don't generate effects."""
        from apps.gameplay.schemas.events import EndTurnEvent

        # Create an event that doesn't trigger any traits
        end_turn_event = EndTurnEvent(side="side_a")

        # Apply traits
        result = traits.apply(self.game_state, end_turn_event)

        # Should not generate any effects
        self.assertEqual(len(result.child_effects), 0)
        self.assertEqual(len(result.events), 0)

    def test_trait_on_card_without_traits(self):
        """Test that cards without traits don't cause issues."""
        # Create a card without traits
        self.game_state.cards["card_3"] = CardInPlay(
            card_type="creature",
            card_id="card_3",
            template_slug="plain-card",
            name="Plain Card",
            attack=1,
            health=1,
            cost=1,
            traits=[],
            exhausted=True
        )

        play_event = PlayEvent(
            side="side_a",
            source_type="card",
            source_id="card_3",
            position=0
        )

        # Apply traits
        result = traits.apply(self.game_state, play_event)

        # Should not generate any effects
        self.assertEqual(len(result.child_effects), 0)
