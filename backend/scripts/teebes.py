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

User = get_user_model()


def main():
    """
    Main function - put your script logic here.

    This template includes several common patterns you can use or remove as needed.
    """
    from apps.builder.models import CardTemplate, AIPlayer, HeroTemplate
    from apps.collection.models import Deck, DeckCard
    from apps.gameplay.models import Game
    from apps.gameplay.schemas import DrawEvent
    from apps.gameplay.services import GameService


    game = Game.objects.get(pk=2)

    # reset game
    state = game.state

    state['phase'] = "start"
    state['turn'] = 1
    state['active'] = "side_a"

    for card_id in state['board']['side_a']:
        state['decks']['side_a'].append(card_id)
    for card_id in state['board']['side_b']:
        state['decks']['side_b'].append(card_id)

    state['board']['side_a'] = []
    state['board']['side_b'] = []

    for i in ["1", "2", "3", "4", "5", "6"]:
        try:
            state['decks']['side_a'].remove(i)
        except ValueError:
            pass

    for i in ["1", "2", "3", "4", "5", "6"]:
        try:
            state['decks']['side_b'].remove(i)
        except ValueError:
            pass

    state['hands']['side_a'] = ["1", "3", "5"]
    state['hands']['side_b'] = ["2", "4", "6"]

    game.state = state
    game.save()


    #print(game_service.game_state.event_queue)

    return

    leonidas = HeroTemplate.objects.get(pk=1)
    pausania = HeroTemplate.objects.get(pk=3)

    teebes = User.objects.get(email="teebes@gmail.com")
    ai = AIPlayer.objects.get(pk=1)

    teebes_deck, created = Deck.objects.get_or_create(
        user=teebes,
        name="Test Deck",
        hero=leonidas,
    )

    ai_deck, created = Deck.objects.get_or_create(
        ai_player=ai,
        name="Test Deck",
        hero=pausania,
    )

    for card_template in CardTemplate.objects.filter(
            card_type=CardTemplate.CARD_TYPE_MINION
        ).order_by('id')[0:25]:
        DeckCard.objects.get_or_create(
            deck=teebes_deck,
            card=card_template,
            count=1,
        )
        DeckCard.objects.get_or_create(
            deck=ai_deck,
            card=card_template,
            count=1,
        )

    for card_template in CardTemplate.objects.filter(
            card_type=CardTemplate.CARD_TYPE_SPELL
        ).order_by('id')[0:5]:
        DeckCard.objects.get_or_create(
            deck=teebes_deck,
            card=card_template,
            count=1,
        )
        DeckCard.objects.get_or_create(
            deck=ai_deck,
            card=card_template,
            count=1,
        )

    from apps.gameplay.services import GameService
    game_service = GameService()
    game = game_service.start_game(teebes_deck, ai_deck)
    print(game.id)

    print(type(game.state))

    from apps.gameplay.schemas import GameState
    print(GameState.model_validate(game.state))




if __name__ == '__main__':
    # Parse command line arguments if needed
    import argparse

    parser = argparse.ArgumentParser(description='Django model manipulation script')
    args = parser.parse_args()

    try:
        main()

    except KeyboardInterrupt:
        print("\n🛑 Script interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Script failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)