# Gameplay Tests Structure

This directory contains all tests for the gameplay app, organized by functionality.

## Test Files

### `__init__.py`
Contains base test classes used across all test modules:
- `ServiceTestsBase` - Base class for tests requiring a complete game with decks
- `GamePlayTestBase` - Base class for tests requiring a simple game state

### `test_services.py`
Tests for high-level game service operations:
- `ServiceTests` - Game initialization tests
- `SmokeTests` - Integration tests that process full command flows

### `test_commands.py`
Tests for command processing and validation:
- `ProcessCommandTests` - Basic command processing (attack, end turn)
- `AttackValidationTestBase` - Base class for attack validation tests
- `AttackCommandValidationTests` - Command-level attack validation
- `AttackEffectValidationTests` - Effect handler attack validation
- `AttackValidationEdgeCasesTests` - Edge cases (both sides, turn validation)

### `test_engine.py`
Tests for game engine effect resolution:
- `EngineTests` - Core effect resolution (start game, play card, hero powers, spells)

### `test_damage.py`
Tests for damage mechanics and combat:
- `TestDamage` - Damage effects (creature-to-creature, creature-to-hero, retaliation)

### `test_traits.py`
Tests for trait processing:
- `TestTraits` - Basic trait tests (battlecry with draw)
- `TestTraitProcessing` - Event-driven trait system tests (charge, battlecry, no triggers)

### `test_endgame.py`
Tests for game ending conditions:
- `TestEndGame` - Deck exhaustion and hero death

## Running Tests

Run all gameplay tests:
```bash
docker-compose exec backend python manage.py test apps.gameplay.tests --settings=config.settings.test
```

Run a specific test file:
```bash
docker-compose exec backend python manage.py test apps.gameplay.tests.test_commands --settings=config.settings.test
```

Run a specific test class:
```bash
docker-compose exec backend python manage.py test apps.gameplay.tests.test_commands.AttackCommandValidationTests --settings=config.settings.test
```

Run with verbose output:
```bash
docker-compose exec backend python manage.py test apps.gameplay.tests --settings=config.settings.test -v 2
```

## Migration from Old Structure

Previously, tests were in:
- `apps/gameplay/tests.py` - Monolithic test file (867 lines)
- `apps/gameplay/test_attack_validation.py` - Separate attack validation tests

These have been refactored into the organized `tests/` directory structure for better maintainability and clarity.
