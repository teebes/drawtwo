"""
Tests for command processing - including attack validation and game flow commands.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.builder.models import AIPlayer, CardTemplate, HeroTemplate, Title
from apps.builder.schemas import HeroPower, DamageAction, Taunt, Stealth
from apps.collection.models import Deck, DeckCard
from apps.gameplay.engine.dispatcher import resolve
from apps.gameplay.schemas.effects import AttackEffect, UseHeroEffect
from apps.gameplay.schemas.game import GameState, Creature, HeroInPlay
from apps.gameplay.services import GameService
from apps.gameplay.ai import AIMoveChooser
from apps.gameplay.tests import ServiceTestsBase

User = get_user_model()


class ProcessCommandTests(ServiceTestsBase):
    """Tests for basic command processing."""

    def test_attack_with_retaliation(self):
        # Create creatures on the board (not cards)
        self.game.state['creatures'] = {
            '1': {
                'creature_id': '1',
                'card_id': 'card_1',
                'name': 'Test Creature 1',
                'attack': 1,
                'health': 10,
                'exhausted': False,
                'traits': []
            },
            '5': {
                'creature_id': '5',
                'card_id': 'card_5',
                'name': 'Test Creature 5',
                'attack': 1,
                'health': 10,
                'exhausted': False,
                'traits': []
            }
        }
        self.game.state['board']['side_a'].append('1')
        self.game.state['board']['side_b'].append('5')
        self.game.save()

        command = {
            'type': 'cmd_attack',
            'card_id': '1',
            'target_id': '5',
            'target_type': 'creature'
        }
        GameService.process_command(self.game.id, command, 'side_a')
        self.game.refresh_from_db()
        self.assertEqual(self.game.state['creatures']['5']['health'], 9)
        self.assertEqual(self.game.state['creatures']['1']['health'], 9)
        self.assertEqual(len(self.game.queue), 0)

    def test_end_turn(self):
        self.assertEqual(self.game.state['turn'], 1)
        self.assertEqual(self.game.state['active'], 'side_a')
        self.assertEqual(self.game.state['phase'], 'main')
        command = {'type': 'cmd_end_turn'}
        GameService.process_command(self.game.id, command, 'side_a')
        self.game.refresh_from_db()
        self.assertEqual(self.game.state['turn'], 2)
        self.assertEqual(self.game.state['active'], 'side_a')
        self.assertEqual(self.game.state['phase'], 'main')


class AttackValidationTestBase(TestCase):
    """Base test class that sets up a game with creatures on both sides."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="testuser@example.com",
            username="testuser"
        )
        self.ai_player = AIPlayer.objects.create(name='AI')

        self.title = Title.objects.create(slug='title', author=self.user)

        # Create heroes with simple hero powers
        self.hero_a = HeroTemplate.objects.create(
            title=self.title,
            slug='hero-a',
            name="Hero A",
            health=30,
            hero_power={
                'cost': 2,
                'actions': [{'action': 'damage', 'amount': 1, 'target': 'enemy'}]
            }
        )
        self.hero_b = HeroTemplate.objects.create(
            title=self.title,
            slug='hero-b',
            name="Hero B",
            health=30,
            hero_power={
                'cost': 2,
                'actions': [{'action': 'damage', 'amount': 1, 'target': 'enemy'}]
            }
        )

        self.deck_a = Deck.objects.create(
            title=self.title, user=self.user, name="Deck A", hero=self.hero_a)
        self.deck_b = Deck.objects.create(
            title=self.title, ai_player=self.ai_player, name="Deck B", hero=self.hero_b)

        # Add some cards to the decks
        for i in range(4):
            card = CardTemplate.objects.create(
                title=self.title,
                slug=f'card-{i}',
                name=f'Card {i}',
                cost=1,
                attack=2,
                health=3,
            )
            DeckCard.objects.create(deck=self.deck_a, card=card)
            DeckCard.objects.create(deck=self.deck_b, card=card)

        self.game = GameService.start_game(self.deck_a, self.deck_b)
        self.game.refresh_from_db()

        # Create a game state with creatures on both sides
        self.game_state = GameState.model_validate(self.game.state)

        # Clear boards
        self.game_state.board['side_a'] = []
        self.game_state.board['side_b'] = []

        # Create creatures for side_a
        self.side_a_creature_1 = Creature(
            creature_id='creature_a_1',
            card_id='card_a_1',
            name='Side A Creature 1',
            description='',
            attack=3,
            attack_max=3,
            health=5,
            health_max=5,
            traits=[],
            exhausted=False
        )
        self.side_a_creature_2 = Creature(
            creature_id='creature_a_2',
            card_id='card_a_2',
            name='Side A Creature 2',
            description='',
            attack=2,
            attack_max=2,
            health=4,
            health_max=4,
            traits=[],
            exhausted=False
        )

        # Create creatures for side_b
        self.side_b_creature_1 = Creature(
            creature_id='creature_b_1',
            card_id='card_b_1',
            name='Side B Creature 1',
            description='',
            attack=3,
            attack_max=3,
            health=5,
            health_max=5,
            traits=[],
            exhausted=False
        )
        self.side_b_creature_2 = Creature(
            creature_id='creature_b_2',
            card_id='card_b_2',
            name='Side B Creature 2',
            description='',
            attack=2,
            attack_max=2,
            health=4,
            health_max=4,
            traits=[],
            exhausted=False
        )

        # Add creatures to the state
        self.game_state.creatures['creature_a_1'] = self.side_a_creature_1
        self.game_state.creatures['creature_a_2'] = self.side_a_creature_2
        self.game_state.creatures['creature_b_1'] = self.side_b_creature_1
        self.game_state.creatures['creature_b_2'] = self.side_b_creature_2

        # Add creatures to boards
        self.game_state.board['side_a'] = ['creature_a_1', 'creature_a_2']
        self.game_state.board['side_b'] = ['creature_b_1', 'creature_b_2']

        # Set active player to side_a
        self.game_state.active = 'side_a'
        self.game_state.phase = 'main'


class AttackCommandValidationTests(AttackValidationTestBase):
    """Test validation in the compile_cmd method (command to effect translation)."""

    def test_valid_attack_on_enemy_creature(self):
        """Test that a valid attack on enemy creature succeeds."""
        command = {
            'type': 'cmd_attack',
            'card_id': 'creature_a_1',  # Side A creature
            'target_type': 'creature',
            'target_id': 'creature_b_1',  # Side B creature
        }

        # Should not raise an exception
        effects = GameService.compile_cmd(self.game_state, command, 'side_a')
        self.assertEqual(len(effects), 1)
        self.assertIsInstance(effects[0], AttackEffect)

    def test_valid_attack_on_enemy_hero(self):
        """Test that a valid attack on enemy hero succeeds."""
        hero_b_id = self.game_state.heroes['side_b'].hero_id
        command = {
            'type': 'cmd_attack',
            'card_id': 'creature_a_1',  # Side A creature
            'target_type': 'hero',
            'target_id': hero_b_id,  # Side B hero
        }

        # Should not raise an exception
        effects = GameService.compile_cmd(self.game_state, command, 'side_a')
        self.assertEqual(len(effects), 1)
        self.assertIsInstance(effects[0], AttackEffect)

    def test_cannot_attack_with_opponent_creature(self):
        """Test that you cannot attack with opponent's creature."""
        command = {
            'type': 'cmd_attack',
            'card_id': 'creature_b_1',  # Side B creature (opponent's)
            'target_type': 'creature',
            'target_id': 'creature_a_1',  # Side A creature (your own)
        }

        with self.assertRaises(ValueError) as context:
            GameService.compile_cmd(self.game_state, command, 'side_a')

        self.assertIn("do not control", str(context.exception).lower())

    def test_cannot_attack_own_creature(self):
        """Test that you cannot attack your own creature."""
        command = {
            'type': 'cmd_attack',
            'card_id': 'creature_a_1',  # Side A creature
            'target_type': 'creature',
            'target_id': 'creature_a_2',  # Another Side A creature (friendly fire)
        }

        with self.assertRaises(ValueError) as context:
            GameService.compile_cmd(self.game_state, command, 'side_a')

        self.assertIn("not on opponent's board", str(context.exception).lower())

    def test_cannot_attack_own_hero(self):
        """Test that you cannot attack your own hero."""
        hero_a_id = self.game_state.heroes['side_a'].hero_id
        command = {
            'type': 'cmd_attack',
            'card_id': 'creature_a_1',  # Side A creature
            'target_type': 'hero',
            'target_id': hero_a_id,  # Side A hero (your own)
        }

        with self.assertRaises(ValueError) as context:
            GameService.compile_cmd(self.game_state, command, 'side_a')

        self.assertIn("not the opponent's hero", str(context.exception).lower())

    def test_cannot_attack_with_nonexistent_creature(self):
        """Test that you cannot attack with a creature that doesn't exist."""
        command = {
            'type': 'cmd_attack',
            'card_id': 'nonexistent_creature',
            'target_type': 'creature',
            'target_id': 'creature_b_1',
        }

        with self.assertRaises(ValueError) as context:
            GameService.compile_cmd(self.game_state, command, 'side_a')

        self.assertIn("does not exist", str(context.exception).lower())

    def test_cannot_attack_with_creature_not_on_board(self):
        """Test that you cannot attack with a creature that exists but is not on board."""
        # Create a creature that's in the creatures dict but not on any board
        orphan_creature = Creature(
            creature_id='orphan',
            card_id='card_orphan',
            name='Orphan Creature',
            description='',
            attack=5,
            attack_max=5,
            health=5,
            health_max=5,
            traits=[],
            exhausted=False
        )
        self.game_state.creatures['orphan'] = orphan_creature

        command = {
            'type': 'cmd_attack',
            'card_id': 'orphan',
            'target_type': 'creature',
            'target_id': 'creature_b_1',
        }

        with self.assertRaises(ValueError) as context:
            GameService.compile_cmd(self.game_state, command, 'side_a')

        self.assertIn("do not control", str(context.exception).lower())


class AttackEffectValidationTests(AttackValidationTestBase):
    """Test validation in the attack effect handler (second line of defense)."""

    def test_effect_handler_validates_creature_ownership(self):
        """Test that the effect handler also validates creature ownership."""
        # Try to create an effect that attacks with opponent's creature
        effect = AttackEffect(
            side='side_a',  # Claiming to be side_a
            card_id='creature_b_1',  # But using side_b's creature
            target_type='creature',
            target_id='creature_a_1',
        )

        result = resolve(effect, self.game_state)
        self.assertEqual(result.type, 'outcome_rejected')
        self.assertIn("do not control", result.reason.lower())

    def test_effect_handler_validates_target_is_enemy(self):
        """Test that the effect handler validates target is an enemy."""
        # Try to create an effect that targets own creature
        effect = AttackEffect(
            side='side_a',
            card_id='creature_a_1',
            target_type='creature',
            target_id='creature_a_2',  # Own creature
        )

        result = resolve(effect, self.game_state)
        self.assertEqual(result.type, 'outcome_rejected')
        self.assertIn("opponent", result.reason.lower())

    def test_effect_handler_rejects_exhausted_creature(self):
        """Test that the effect handler rejects attacks from exhausted creatures."""
        # Exhaust the creature
        self.game_state.creatures['creature_a_1'].exhausted = True

        effect = AttackEffect(
            side='side_a',
            card_id='creature_a_1',
            target_type='creature',
            target_id='creature_b_1',
        )

        result = resolve(effect, self.game_state)
        self.assertEqual(result.type, 'outcome_rejected')
        self.assertIn("exhausted", result.reason.lower())

    def test_valid_attack_succeeds_in_handler(self):
        """Test that a valid attack succeeds in the effect handler."""
        effect = AttackEffect(
            side='side_a',
            card_id='creature_a_1',
            target_type='creature',
            target_id='creature_b_1',
        )

        result = resolve(effect, self.game_state)
        self.assertEqual(result.type, 'outcome_success')
        # Should have child effects (mark exhausted and damage)
        self.assertGreater(len(result.child_effects), 0)


class AttackValidationEdgeCasesTests(AttackValidationTestBase):
    """Test edge cases and complex scenarios."""

    def test_side_b_attacking_side_a(self):
        """Test that validation works correctly when side_b is active."""
        self.game_state.active = 'side_b'

        command = {
            'type': 'cmd_attack',
            'card_id': 'creature_b_1',  # Side B creature (now active player)
            'target_type': 'creature',
            'target_id': 'creature_a_1',  # Side A creature (opponent)
        }

        # Should succeed
        effects = GameService.compile_cmd(self.game_state, command, 'side_b')
        self.assertEqual(len(effects), 1)

    def test_side_b_cannot_attack_own_creatures(self):
        """Test that side_b also cannot attack own creatures."""
        self.game_state.active = 'side_b'

        command = {
            'type': 'cmd_attack',
            'card_id': 'creature_b_1',  # Side B creature
            'target_type': 'creature',
            'target_id': 'creature_b_2',  # Another Side B creature (friendly fire)
        }

        with self.assertRaises(ValueError) as context:
            GameService.compile_cmd(self.game_state, command, 'side_b')

        self.assertIn("not on opponent's board", str(context.exception).lower())

    def test_cannot_attack_when_not_your_turn(self):
        """Test that you cannot attack when it's not your turn."""
        # Side A is active, but try to compile command as side B
        command = {
            'type': 'cmd_attack',
            'card_id': 'creature_b_1',
            'target_type': 'creature',
            'target_id': 'creature_a_1',
        }

        with self.assertRaises(ValueError) as context:
            GameService.compile_cmd(self.game_state, command, 'side_b')

        self.assertIn("not your turn", str(context.exception).lower())


class HeroPowerValidationTests(AttackValidationTestBase):
    """Test validation for hero power usage."""

    def test_valid_hero_power_on_enemy_creature(self):
        """Test that a valid hero power on enemy creature succeeds."""
        hero_a_id = self.game_state.heroes['side_a'].hero_id
        command = {
            'type': 'cmd_use_hero',
            'hero_id': hero_a_id,
            'target_type': 'creature',
            'target_id': 'creature_b_1',  # Side B creature
        }

        # Should not raise an exception
        effects = GameService.compile_cmd(self.game_state, command, 'side_a')
        self.assertEqual(len(effects), 1)
        self.assertIsInstance(effects[0], UseHeroEffect)

    def test_valid_hero_power_on_enemy_hero(self):
        """Test that a valid hero power on enemy hero succeeds."""
        hero_a_id = self.game_state.heroes['side_a'].hero_id
        hero_b_id = self.game_state.heroes['side_b'].hero_id
        command = {
            'type': 'cmd_use_hero',
            'hero_id': hero_a_id,
            'target_type': 'hero',
            'target_id': hero_b_id,
        }

        # Should not raise an exception
        effects = GameService.compile_cmd(self.game_state, command, 'side_a')
        self.assertEqual(len(effects), 1)
        self.assertIsInstance(effects[0], UseHeroEffect)

    def test_cannot_use_opponent_hero(self):
        """Test that you cannot use opponent's hero power."""
        hero_b_id = self.game_state.heroes['side_b'].hero_id
        command = {
            'type': 'cmd_use_hero',
            'hero_id': hero_b_id,  # Side B hero (opponent's)
            'target_type': 'creature',
            'target_id': 'creature_a_1',
        }

        with self.assertRaises(ValueError) as context:
            GameService.compile_cmd(self.game_state, command, 'side_a')

        self.assertIn("do not control", str(context.exception).lower())

    def test_cannot_target_own_creature_with_hero_power(self):
        """Test that you cannot target your own creature with hero power."""
        hero_a_id = self.game_state.heroes['side_a'].hero_id
        command = {
            'type': 'cmd_use_hero',
            'hero_id': hero_a_id,
            'target_type': 'creature',
            'target_id': 'creature_a_1',  # Own creature
        }

        with self.assertRaises(ValueError) as context:
            GameService.compile_cmd(self.game_state, command, 'side_a')

        self.assertIn("not on opponent's board", str(context.exception).lower())

    def test_cannot_target_own_hero_with_hero_power(self):
        """Test that you cannot target your own hero with hero power."""
        hero_a_id = self.game_state.heroes['side_a'].hero_id
        command = {
            'type': 'cmd_use_hero',
            'hero_id': hero_a_id,
            'target_type': 'hero',
            'target_id': hero_a_id,  # Own hero
        }

        with self.assertRaises(ValueError) as context:
            GameService.compile_cmd(self.game_state, command, 'side_a')

        self.assertIn("not the opponent's hero", str(context.exception).lower())


class HeroPowerEffectValidationTests(AttackValidationTestBase):
    """Test validation in the use_hero effect handler."""

    def test_effect_handler_validates_hero_ownership(self):
        """Test that the effect handler validates hero ownership."""
        hero_b_id = self.game_state.heroes['side_b'].hero_id

        # Try to use opponent's hero
        effect = UseHeroEffect(
            side='side_a',
            source_id=hero_b_id,  # Side B hero (opponent's)
            target_type='creature',
            target_id='creature_b_1',
        )

        result = resolve(effect, self.game_state)
        self.assertEqual(result.type, 'outcome_rejected')
        self.assertIn("do not control", result.reason.lower())

    def test_effect_handler_validates_target_is_enemy_creature(self):
        """Test that the effect handler validates target is enemy creature."""
        hero_a_id = self.game_state.heroes['side_a'].hero_id
        self.game_state.heroes['side_a'].exhausted = False

        # Try to target own creature
        effect = UseHeroEffect(
            side='side_a',
            source_id=hero_a_id,
            target_type='creature',
            target_id='creature_a_1',  # Own creature
        )

        result = resolve(effect, self.game_state)
        self.assertEqual(result.type, 'outcome_rejected')
        self.assertIn("opponent", result.reason.lower())

    def test_effect_handler_validates_target_is_enemy_hero(self):
        """Test that the effect handler validates target is enemy hero."""
        hero_a_id = self.game_state.heroes['side_a'].hero_id
        self.game_state.heroes['side_a'].exhausted = False

        # Try to target own hero
        effect = UseHeroEffect(
            side='side_a',
            source_id=hero_a_id,
            target_type='hero',
            target_id=hero_a_id,  # Own hero
        )

        result = resolve(effect, self.game_state)
        self.assertEqual(result.type, 'outcome_rejected')
        self.assertIn("opponent", result.reason.lower())

    def test_valid_hero_power_succeeds_in_handler(self):
        """Test that a valid hero power succeeds in the effect handler."""
        hero_a_id = self.game_state.heroes['side_a'].hero_id
        self.game_state.heroes['side_a'].exhausted = False

        effect = UseHeroEffect(
            side='side_a',
            source_id=hero_a_id,
            target_type='creature',
            target_id='creature_b_1',  # Enemy creature
        )

        result = resolve(effect, self.game_state)
        self.assertEqual(result.type, 'outcome_success')
        # Should have child effects
        self.assertGreater(len(result.child_effects), 0)


class HealingHeroPowerTests(AttackValidationTestBase):
    """Test healing hero powers that target friendly units."""

    def setUp(self):
        super().setUp()
        # Override hero A with a healing hero power in the game state
        from apps.builder.schemas import HeroPower, HealAction
        self.game_state.heroes['side_a'].hero_power = HeroPower(
            name='Heal',
            actions=[
                HealAction(
                    amount=2,
                    target='friendly',
                    scope='single'
                )
            ]
        )

    def test_can_target_own_hero_with_healing_power(self):
        """Test that you can target your own hero with a healing hero power."""
        hero_a_id = self.game_state.heroes['side_a'].hero_id
        command = {
            'type': 'cmd_use_hero',
            'hero_id': hero_a_id,
            'target_type': 'hero',
            'target_id': hero_a_id,  # Own hero
        }

        # Should not raise an exception
        effects = GameService.compile_cmd(self.game_state, command, 'side_a')
        self.assertEqual(len(effects), 1)
        self.assertIsInstance(effects[0], UseHeroEffect)

    def test_can_target_own_creature_with_healing_power(self):
        """Test that you can target your own creature with a healing hero power."""
        hero_a_id = self.game_state.heroes['side_a'].hero_id
        command = {
            'type': 'cmd_use_hero',
            'hero_id': hero_a_id,
            'target_type': 'creature',
            'target_id': 'creature_a_1',  # Own creature
        }

        # Should not raise an exception
        effects = GameService.compile_cmd(self.game_state, command, 'side_a')
        self.assertEqual(len(effects), 1)
        self.assertIsInstance(effects[0], UseHeroEffect)

    def test_cannot_target_enemy_hero_with_healing_power(self):
        """Test that you cannot target enemy hero with a healing hero power."""
        hero_a_id = self.game_state.heroes['side_a'].hero_id
        hero_b_id = self.game_state.heroes['side_b'].hero_id
        command = {
            'type': 'cmd_use_hero',
            'hero_id': hero_a_id,
            'target_type': 'hero',
            'target_id': hero_b_id,  # Enemy hero
        }

        with self.assertRaises(ValueError) as context:
            GameService.compile_cmd(self.game_state, command, 'side_a')

        self.assertIn("not your hero", str(context.exception).lower())

    def test_cannot_target_enemy_creature_with_healing_power(self):
        """Test that you cannot target enemy creature with a healing hero power."""
        hero_a_id = self.game_state.heroes['side_a'].hero_id
        command = {
            'type': 'cmd_use_hero',
            'hero_id': hero_a_id,
            'target_type': 'creature',
            'target_id': 'creature_b_1',  # Enemy creature
        }

        with self.assertRaises(ValueError) as context:
            GameService.compile_cmd(self.game_state, command, 'side_a')

        self.assertIn("not on your board", str(context.exception).lower())


class TauntMechanicTests(AttackValidationTestBase):
    """Test the Taunt trait mechanic."""

    def setUp(self):
        super().setUp()
        # Add a taunt creature to side_b
        self.taunt_creature = Creature(
            creature_id='taunt_b_1',
            card_id='card_taunt_b_1',
            name='Taunt Creature',
            description='Has Taunt',
            attack=1,
            attack_max=1,
            health=3,
            health_max=3,
            traits=[Taunt()],
            exhausted=False
        )
        self.game_state.creatures['taunt_b_1'] = self.taunt_creature
        self.game_state.board['side_b'].append('taunt_b_1')

    def test_cannot_attack_hero_with_taunt_on_board(self):
        """Test that you cannot attack the enemy hero when taunt creatures exist."""
        hero_b_id = self.game_state.heroes['side_b'].hero_id

        effect = AttackEffect(
            side='side_a',
            card_id='creature_a_1',
            target_type='hero',
            target_id=hero_b_id,
        )

        result = resolve(effect, self.game_state)
        self.assertEqual(result.type, 'outcome_rejected')
        self.assertIn("taunt", result.reason.lower())

    def test_cannot_attack_non_taunt_creature_with_taunt_on_board(self):
        """Test that you cannot attack non-taunt creatures when taunt exists."""
        effect = AttackEffect(
            side='side_a',
            card_id='creature_a_1',
            target_type='creature',
            target_id='creature_b_1',  # Non-taunt creature
        )

        result = resolve(effect, self.game_state)
        self.assertEqual(result.type, 'outcome_rejected')
        self.assertIn("taunt", result.reason.lower())

    def test_can_attack_taunt_creature(self):
        """Test that you CAN attack a creature with taunt."""
        effect = AttackEffect(
            side='side_a',
            card_id='creature_a_1',
            target_type='creature',
            target_id='taunt_b_1',  # Taunt creature
        )

        result = resolve(effect, self.game_state)
        self.assertEqual(result.type, 'outcome_success')

    def test_can_attack_hero_when_no_taunt_on_board(self):
        """Test that you CAN attack hero when no taunt creatures exist."""
        # Remove the taunt creature
        self.game_state.board['side_b'].remove('taunt_b_1')
        del self.game_state.creatures['taunt_b_1']

        hero_b_id = self.game_state.heroes['side_b'].hero_id
        effect = AttackEffect(
            side='side_a',
            card_id='creature_a_1',
            target_type='hero',
            target_id=hero_b_id,
        )

        result = resolve(effect, self.game_state)
        self.assertEqual(result.type, 'outcome_success')

    def test_can_attack_any_creature_when_no_taunt_on_board(self):
        """Test that you CAN attack any creature when no taunt exists."""
        # Remove the taunt creature
        self.game_state.board['side_b'].remove('taunt_b_1')
        del self.game_state.creatures['taunt_b_1']

        effect = AttackEffect(
            side='side_a',
            card_id='creature_a_1',
            target_type='creature',
            target_id='creature_b_1',  # Non-taunt creature
        )

        result = resolve(effect, self.game_state)
        self.assertEqual(result.type, 'outcome_success')

    def test_multiple_taunt_creatures(self):
        """Test that any taunt creature can be attacked when multiple exist."""
        # Add another taunt creature
        taunt_creature_2 = Creature(
            creature_id='taunt_b_2',
            card_id='card_taunt_b_2',
            name='Taunt Creature 2',
            description='Also has Taunt',
            attack=2,
            attack_max=2,
            health=2,
            health_max=2,
            traits=[Taunt()],
            exhausted=False
        )
        self.game_state.creatures['taunt_b_2'] = taunt_creature_2
        self.game_state.board['side_b'].append('taunt_b_2')

        # Can attack first taunt creature
        effect1 = AttackEffect(
            side='side_a',
            card_id='creature_a_1',
            target_type='creature',
            target_id='taunt_b_1',
        )
        result1 = resolve(effect1, self.game_state)
        self.assertEqual(result1.type, 'outcome_success')

        # Can attack second taunt creature
        effect2 = AttackEffect(
            side='side_a',
            card_id='creature_a_2',
            target_type='creature',
            target_id='taunt_b_2',
        )
        result2 = resolve(effect2, self.game_state)
        self.assertEqual(result2.type, 'outcome_success')

        # Still cannot attack non-taunt creature
        effect3 = AttackEffect(
            side='side_a',
            card_id='creature_a_1',
            target_type='creature',
            target_id='creature_b_1',
        )
        result3 = resolve(effect3, self.game_state)
        self.assertEqual(result3.type, 'outcome_rejected')

    def test_taunt_only_affects_opponent_side(self):
        """Test that taunt on side_a doesn't affect side_a's own attacks."""
        # Add taunt to side_a
        taunt_creature_a = Creature(
            creature_id='taunt_a_1',
            card_id='card_taunt_a_1',
            name='Taunt Creature A',
            description='Has Taunt',
            attack=1,
            attack_max=1,
            health=3,
            health_max=3,
            traits=[Taunt()],
            exhausted=False
        )
        self.game_state.creatures['taunt_a_1'] = taunt_creature_a
        self.game_state.board['side_a'].append('taunt_a_1')

        # Side_a can still attack side_b's hero (side_b has taunt, but we check opponent's board)
        # Actually, side_b still has taunt, so this should fail
        hero_b_id = self.game_state.heroes['side_b'].hero_id
        effect = AttackEffect(
            side='side_a',
            card_id='creature_a_1',
            target_type='hero',
            target_id=hero_b_id,
        )
        result = resolve(effect, self.game_state)
        # Should be rejected because side_b has taunt
        self.assertEqual(result.type, 'outcome_rejected')

        # Now test side_b attacking - side_a's taunt should matter
        self.game_state.active = 'side_b'
        hero_a_id = self.game_state.heroes['side_a'].hero_id
        effect_b = AttackEffect(
            side='side_b',
            card_id='creature_b_1',
            target_type='hero',
            target_id=hero_a_id,
        )
        result_b = resolve(effect_b, self.game_state)
        # Should be rejected because side_a has taunt
        self.assertEqual(result_b.type, 'outcome_rejected')
        self.assertIn("taunt", result_b.reason.lower())


class SpellTargetingWithTauntTests(AttackValidationTestBase):
    """Test that spells can target non-taunt creatures even when taunt creatures exist."""

    def setUp(self):
        super().setUp()
        # Add a taunt creature to side_b
        self.taunt_creature = Creature(
            creature_id='taunt_b_1',
            card_id='card_taunt_b_1',
            name='Taunt Creature',
            description='Has Taunt',
            attack=1,
            attack_max=1,
            health=3,
            health_max=3,
            traits=[Taunt()],
            exhausted=False
        )
        self.game_state.creatures['taunt_b_1'] = self.taunt_creature
        self.game_state.board['side_b'].append('taunt_b_1')

        # Add a non-taunt creature with 1 HP to side_b
        self.weak_creature = Creature(
            creature_id='weak_b_1',
            card_id='card_weak_b_1',
            name='Weak Creature',
            description='1 HP, no taunt',
            attack=1,
            attack_max=1,
            health=1,
            health_max=1,
            traits=[],
            exhausted=False
        )
        self.game_state.creatures['weak_b_1'] = self.weak_creature
        self.game_state.board['side_b'].append('weak_b_1')

        # Create a spell card that deals 2 damage
        from apps.builder.schemas import Battlecry
        from apps.gameplay.schemas.game import CardInPlay
        self.spell_card = CardInPlay(
            card_type="spell",
            card_id="spell_damage_2",
            template_slug="damage-spell",
            name="Damage Spell",
            cost=1,
            traits=[
                Battlecry(
                    actions=[
                        DamageAction(
                            amount=2,
                            target="enemy",
                        )
                    ]
                )
            ],
        )
        self.game_state.cards["spell_damage_2"] = self.spell_card
        self.game_state.hands["side_a"] = ["spell_damage_2"]
        self.game_state.mana_pool["side_a"] = 1
        self.game_state.mana_used["side_a"] = 0

    def test_spell_can_target_non_taunt_creature_with_taunt_on_board(self):
        """Test that a spell can target a non-taunt creature even when taunt creatures exist.

        This test verifies that the backend allows spells to target non-taunt creatures
        even when taunt creatures are present. Taunt should only affect creature attacks,
        not spell targeting.
        """
        from apps.gameplay.engine.dispatcher import resolve
        from apps.gameplay.schemas.effects import PlayEffect
        from apps.gameplay.schemas.engine import Success

        # Try to play the spell targeting the weak (non-taunt) creature
        play_effect = PlayEffect(
            side="side_a",
            source_id="spell_damage_2",
            position=0,
            target_type="creature",
            target_id="weak_b_1",  # Non-taunt creature
        )

        result = resolve(play_effect, self.game_state)

        # Should succeed - spells are NOT affected by taunt
        # If this fails, it means the backend is incorrectly applying taunt restrictions to spells
        self.assertEqual(result.type, 'outcome_success')
        self.assertIsInstance(result, Success)

        # Verify the spell was played (moved from hand to graveyard)
        new_state = result.new_state
        self.assertNotIn("spell_damage_2", new_state.hands["side_a"])
        self.assertIn("spell_damage_2", new_state.graveyard["side_a"])

        # Verify a PlayEvent was created with the correct target
        self.assertEqual(len(result.events), 1)
        self.assertEqual(result.events[0].type, 'event_play')
        self.assertEqual(result.events[0].target_type, 'creature')
        self.assertEqual(result.events[0].target_id, 'weak_b_1')

    def test_spell_can_target_taunt_creature_with_taunt_on_board(self):
        """Test that a spell can also target a taunt creature (should work too)."""
        from apps.gameplay.engine.dispatcher import resolve
        from apps.gameplay.schemas.effects import PlayEffect
        from apps.gameplay.schemas.engine import Success

        # Try to play the spell targeting the taunt creature
        play_effect = PlayEffect(
            side="side_a",
            source_id="spell_damage_2",
            position=0,
            target_type="creature",
            target_id="taunt_b_1",  # Taunt creature
        )

        result = resolve(play_effect, self.game_state)

        # Should succeed - spells can target any valid target
        self.assertEqual(result.type, 'outcome_success')
        self.assertIsInstance(result, Success)


class AITauntTests(TestCase):
    """Test that AI respects taunt mechanics when choosing moves."""

    def setUp(self):
        from apps.builder.schemas import DeckScript
        from apps.gameplay.schemas.game import GameState, Creature, HeroInPlay, CardInPlay

        # Create a basic game state with creatures on both sides
        self.game_state = GameState(
            turn=1,
            active='side_a',
            phase='main',
            cards={
                'card_a_1': CardInPlay(
                    card_id='card_a_1',
                    card_type='creature',
                    name='AI Creature',
                    description='',
                    attack=2,
                    health=2,
                    cost=1,
                    traits=[],
                    template_slug='ai-creature',
                ),
                'card_b_1': CardInPlay(
                    card_id='card_b_1',
                    card_type='creature',
                    name='Regular Creature',
                    description='',
                    attack=1,
                    health=1,
                    cost=1,
                    traits=[],
                    template_slug='regular-creature',
                ),
            },
            creatures={
                'creature_a_1': Creature(
                    creature_id='creature_a_1',
                    card_id='card_a_1',
                    name='AI Creature',
                    description='',
                    attack=2,
                    attack_max=2,
                    health=2,
                    health_max=2,
                    traits=[],
                    exhausted=False,
                ),
                'creature_b_1': Creature(
                    creature_id='creature_b_1',
                    card_id='card_b_1',
                    name='Regular Creature',
                    description='',
                    attack=1,
                    attack_max=1,
                    health=1,
                    health_max=1,
                    traits=[],
                    exhausted=False,
                ),
            },
            board={
                'side_a': ['creature_a_1'],
                'side_b': ['creature_b_1'],
            },
            heroes={
                'side_a': HeroInPlay(
                    hero_id='hero_a',
                    template_slug='hero-a',
                    name='Hero A',
                    health=30,
                    health_max=30,
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
                    hero_id='hero_b',
                    template_slug='hero-b',
                    name='Hero B',
                    health=30,
                    health_max=30,
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
            hands={'side_a': [], 'side_b': []},
            decks={'side_a': [], 'side_b': []},
            graveyard={'side_a': [], 'side_b': []},
            mana_pool={'side_a': 10, 'side_b': 10},
            mana_used={'side_a': 0, 'side_b': 0},
            ai_sides=['side_a'],
        )

        self.script_rush = DeckScript(strategy='rush')

    def test_ai_attacks_taunt_creature_instead_of_hero(self):
        """Test that AI attacks taunt creature instead of hero when taunt exists."""
        # Add a taunt creature to side_b
        taunt_creature = Creature(
            creature_id='taunt_b_1',
            card_id='card_taunt_b_1',
            name='Taunt Creature',
            description='Has Taunt',
            attack=1,
            attack_max=1,
            health=3,
            health_max=3,
            traits=[Taunt()],
            exhausted=False
        )
        self.game_state.creatures['taunt_b_1'] = taunt_creature
        self.game_state.board['side_b'].append('taunt_b_1')

        # Test with rush strategy (normally attacks hero)
        effect = AIMoveChooser.choose_move(self.game_state, self.script_rush)

        # Verify that the AI chose to attack
        self.assertIsNotNone(effect)
        self.assertEqual(effect.type, 'effect_attack')

        # Verify that it attacked a creature (not hero) due to taunt
        self.assertEqual(effect.target_type, 'creature')

        # Verify that it attacked the taunt creature specifically
        self.assertEqual(effect.target_id, 'taunt_b_1')

    def test_ai_attacks_hero_when_no_taunt(self):
        """Test that AI with rush strategy attacks hero when no taunt exists."""
        # No taunt creatures on board
        effect = AIMoveChooser.choose_move(self.game_state, self.script_rush)

        # Verify that the AI chose to attack
        self.assertIsNotNone(effect)
        self.assertEqual(effect.type, 'effect_attack')

        # Verify that it attacked the hero (rush strategy)
        self.assertEqual(effect.target_type, 'hero')
        self.assertEqual(effect.target_id, 'hero_b')

    def test_ai_attacks_taunt_with_multiple_taunt_creatures(self):
        """Test that AI attacks one of the taunt creatures when multiple exist."""
        # Add two taunt creatures to side_b
        taunt_creature_1 = Creature(
            creature_id='taunt_b_1',
            card_id='card_taunt_b_1',
            name='Taunt Creature 1',
            description='Has Taunt',
            attack=1,
            attack_max=1,
            health=3,
            health_max=3,
            traits=[Taunt()],
            exhausted=False
        )
        taunt_creature_2 = Creature(
            creature_id='taunt_b_2',
            card_id='card_taunt_b_2',
            name='Taunt Creature 2',
            description='Has Taunt',
            attack=2,
            attack_max=2,
            health=2,
            health_max=2,
            traits=[Taunt()],
            exhausted=False
        )
        self.game_state.creatures['taunt_b_1'] = taunt_creature_1
        self.game_state.creatures['taunt_b_2'] = taunt_creature_2
        self.game_state.board['side_b'].extend(['taunt_b_1', 'taunt_b_2'])

        effect = AIMoveChooser.choose_move(self.game_state, self.script_rush)

        # Verify that the AI chose to attack
        self.assertIsNotNone(effect)
        self.assertEqual(effect.type, 'effect_attack')

        # Verify that it attacked a creature (not hero)
        self.assertEqual(effect.target_type, 'creature')

        # Verify that it attacked one of the taunt creatures
        self.assertIn(effect.target_id, ['taunt_b_1', 'taunt_b_2'])


class StealthMechanicTests(AttackValidationTestBase):
    """Test the Stealth trait mechanic."""

    def setUp(self):
        super().setUp()
        # Add a stealth creature to side_b
        self.stealth_creature = Creature(
            creature_id='stealth_b_1',
            card_id='card_stealth_b_1',
            name='Stealth Creature',
            description='Has Stealth',
            attack=2,
            attack_max=2,
            health=2,
            health_max=2,
            traits=[Stealth()],
            exhausted=False
        )
        self.game_state.creatures['stealth_b_1'] = self.stealth_creature
        self.game_state.board['side_b'].append('stealth_b_1')

    def test_cannot_target_stealthed_creature(self):
        """Test that you cannot directly target a stealthed creature."""
        effect = AttackEffect(
            side='side_a',
            card_id='creature_a_1',
            target_type='creature',
            target_id='stealth_b_1',  # Stealth creature
        )

        result = resolve(effect, self.game_state)
        self.assertEqual(result.type, 'outcome_rejected')
        self.assertIn("stealth", result.reason.lower())

    def test_can_attack_non_stealth_creature(self):
        """Test that you CAN attack non-stealth creatures even when stealth exists."""
        effect = AttackEffect(
            side='side_a',
            card_id='creature_a_1',
            target_type='creature',
            target_id='creature_b_1',  # Non-stealth creature
        )

        result = resolve(effect, self.game_state)
        self.assertEqual(result.type, 'outcome_success')

    def test_stealth_removed_after_attack(self):
        """Test that stealth is removed after the creature attacks."""
        # Make the stealth creature attack
        effect = AttackEffect(
            side='side_b',
            card_id='stealth_b_1',
            target_type='creature',
            target_id='creature_a_1',
        )

        # Change active side to side_b so the attack is valid
        self.game_state.active = 'side_b'

        result = resolve(effect, self.game_state)
        self.assertEqual(result.type, 'outcome_success')

        # Check that stealth trait was removed
        updated_creature = result.new_state.creatures['stealth_b_1']
        has_stealth = any(trait.type == 'stealth' for trait in updated_creature.traits)
        self.assertFalse(has_stealth)

    def test_can_attack_creature_after_stealth_removed(self):
        """Test that a creature can be targeted after its stealth is removed."""
        # First, have the stealth creature attack to remove stealth
        self.game_state.active = 'side_b'
        attack_effect = AttackEffect(
            side='side_b',
            card_id='stealth_b_1',
            target_type='creature',
            target_id='creature_a_1',
        )

        result = resolve(attack_effect, self.game_state)
        self.assertEqual(result.type, 'outcome_success')

        # Update game state
        new_state = result.new_state

        # Now try to attack the creature that lost stealth
        new_state.active = 'side_a'
        counter_attack = AttackEffect(
            side='side_a',
            card_id='creature_a_1',
            target_type='creature',
            target_id='stealth_b_1',
        )

        result2 = resolve(counter_attack, new_state)
        self.assertEqual(result2.type, 'outcome_success')

    def test_can_attack_hero_with_stealth_on_board(self):
        """Test that you CAN attack hero even when stealth creatures exist (unlike taunt)."""
        hero_b_id = self.game_state.heroes['side_b'].hero_id

        effect = AttackEffect(
            side='side_a',
            card_id='creature_a_1',
            target_type='hero',
            target_id=hero_b_id,
        )

        result = resolve(effect, self.game_state)
        # Should succeed - stealth doesn't force you to attack it like taunt does
        self.assertEqual(result.type, 'outcome_success')
