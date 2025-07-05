from celery import shared_task
from django.db import transaction
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Game
from .schemas import GameState, GameUpdates

@shared_task
def process_player_action(game_id: int, action: dict):
    with transaction.atomic():
        game = (Game.objects
                    .select_for_update()
                    .get(id=game_id))

        new_state_dict, emitted = apply_action(game.state, action)

        new_state = GameState.model_validate(new_state_dict)
        game.state = new_state_dict
        game.status = Game.GAME_STATUS_IN_PROGRESS
        game.winner = new_state_dict.get("winner")
        game.save(update_fields=["state", "status", "winner"])

    # Send updates to WebSocket clients
    _send_game_updates_to_clients(game_id, new_state_dict, emitted)

@shared_task
def process_ai_action(game_id: int):
    """
    Process AI action for the given game.
    This could involve AI decision making, applying the action, and notifying clients.
    """
    from .services import GameService

    print("======= Process AI Action =======")

    with transaction.atomic():
        game = (Game.objects
                    .select_for_update()
                    .get(id=game_id))

        game_state = GameState.model_validate(game.state)

        # Make sure that the active side is the AI side
        if not getattr(game, game_state.active).is_ai_deck:
            raise ValueError("AI is not the active side")

        ai_side = game_state.active

        if game_state.phase == "start":
            result = GameService.submit_action(game.id, {
                'type': 'phase_transition',
                'phase': 'refresh',
            })
        elif game_state.phase == "refresh":
            result = GameService.submit_action(game.id, {
                'type': 'phase_transition',
                'phase': 'draw',
            })
        elif game_state.phase == "draw":
            result = GameService.submit_action(game.id, {
                'type': 'phase_transition',
                'phase': 'main',
            })
        elif game_state.phase == "main":
            cards_in_hand = [
                game_state.cards[card_id]
                for card_id in game_state.hands[game_state.active]
            ]

            mana_available = (
                game_state.mana_pool[game_state.active]
                - game_state.mana_used[game_state.active])

            played = False
            for card in cards_in_hand:
                if card.cost <= mana_available:
                    result = GameService.submit_action(game.id, {
                        'type': 'play',
                        'card_id': card.card_id,
                        'position': 0,
                    })
                    played = True

            # If we were not able to play a card, then end the turn
            if not played:
                result = GameService.submit_action(game.id, {
                    'type': 'phase_transition',
                    'phase': 'start',
                })

        _send_game_updates_to_clients(game_id, result['state'], result['updates'])

        if result['state']['active'] == ai_side:
            process_ai_action.apply_async(args=[game_id], countdown=2)

        return


        # TODO: Implement AI decision logic here
        # For now, let's assume we have an AI action to apply
        ai_action = {
            'type': 'phase_transition',
            'phase': 'end',
            'player': game.state.get('active', 'side_b')  # Assuming AI is side_b
        }

        # Apply the AI action to the game state
        new_state_dict, emitted = apply_action(game.state, ai_action)

        new_state = GameState.model_validate(new_state_dict)
        game.state = new_state_dict
        game.status = Game.GAME_STATUS_IN_PROGRESS
        game.winner = new_state_dict.get("winner")
        game.save(update_fields=["state", "status", "winner"])

    # Send updates to WebSocket clients
    _send_game_updates_to_clients(game_id, new_state_dict, emitted)

def _send_game_updates_to_clients(game_id: int, state_dict: dict, updates: list):
    """
    Send game updates to all WebSocket clients connected to this game.
    """
    channel_layer = get_channel_layer()
    game_group_name = f'game_{game_id}'

    # Convert to sync call since we're in a sync context (Celery task)
    async_to_sync(channel_layer.group_send)(
        game_group_name,
        {
            'type': 'game_updates',
            'updates': updates,
            'state': state_dict
        }
    )