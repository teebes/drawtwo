#!/usr/bin/env python3
"""
Django Model Manipulation Script Template

This template provides a foundation for creating scripts that interact with Django models.
Copy this file and modify it for your specific needs.

Usage:
    python backend/scripts/template.py
    # or from the backend directory:
    python scripts/template.py
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path so we can import Django
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

# Now you can import your Django models and other modules
from django.contrib.auth import get_user_model

from apps.builder.models import CardTemplate
from apps.core.serializers import serialize_cards_with_traits
from apps.gameplay.engine.handlers import spawn_creature
from apps.gameplay.models import Game
from apps.gameplay.schemas.game import GameState
from apps.gameplay.services import GameService


User = get_user_model()


def main(args):
    """
    Modify the game state manually, for example load a creature onto one side of
    the board.
    """
    game = Game.objects.get(id=args.game_id)
    game_state = GameState.model_validate(game.state)

    if args.side:
        side = args.side
    elif args.opposite:
        if game_state.active == 'side_a':
            side = 'side_b'
        else:
            side = 'side_a'
    else:
        side = game_state.active

    position = args.position

    if args.command == 'load':

        try:
            card_template = CardTemplate.objects.get(slug=args.creature_slug)

            cards = serialize_cards_with_traits(CardTemplate.objects.filter(slug=args.creature_slug))
            card = cards[0]

            # Get the card ID by taking the greatest card ID and adding 1
            card_id = str(max(int(card_id) for card_id in game_state.cards.keys()) + 1)

            card_in_play = GameService.get_card_in_play(card, card_id)
            game_state.decks[side].append(card_id)
            game_state.cards[card_id] = card_in_play

            if card_template.card_type == 'spell':
                game_state.hands[side].append(card_id)
            elif card_template.card_type == 'creature':
                creature = spawn_creature(card_in_play, game_state, side, args.position)


            game.state = game_state.model_dump()
            game.save()

        except CardTemplate.DoesNotExist:
            print(f"❌ Card template not found: {args.creature_slug}")
            return


    else:
        print("OK")


if __name__ == '__main__':
    # Parse command line arguments if needed
    import argparse

    parser = argparse.ArgumentParser(description='Django model manipulation script')
    # example command:
    # $ mod_game.py 123 load creature_slug --side side_a --position 0

    parser.add_argument(
        'game_id',
        type=int,
        help='The ID of the game to modify'
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands', required=True)

    # Load subcommand
    load_parser = subparsers.add_parser('load', help='Load a creature onto the board')
    load_parser.add_argument(
        'creature_slug',
        type=str,
        help='The slug of the creature to load onto the board'
    )
    load_parser.add_argument(
        '--side',
        choices=['side_a', 'side_b'],
        type=str,
        help='The side of the board to load the creature onto (side_a or side_b). Leave empty for default.',
        default=None,
    )

    load_parser.add_argument(
        '--opposite',
        action='store_true',
        help='Use the opposite side; defaults to False unless flag is present.'
)

    load_parser.add_argument(
        '--position',
        type=int,
        help='The position on the board to load the creature onto',
        default=0
    )

    args = parser.parse_args()

    try:
        main(args)
        pass

    except KeyboardInterrupt:
        print("\n🛑 Script interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Script failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)