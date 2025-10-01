from celery import shared_task
from django.db import transaction, DatabaseError
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Game, GameUpdate
from .schemas import (
    GameOverUpdate,
    GameState,
    ResolvedEvent,
)

from apps.builder.schemas import DeckScript

from apps.gameplay.schemas.events import (
    ChooseAIMoveEvent,
    DrawPhaseEvent,
    MainPhaseEvent,
)


STEP_DELAY = 1

from dataclasses import dataclass

@dataclass
class StepResult:
    needs_continuation: bool

@shared_task
def step(game_id: int):
    print("==== STEP FUNCTION ====")
    from .engine import resolve_event

    with transaction.atomic():
        try:
            game = (Game.objects
                        .select_for_update(nowait=True)
                        .get(id=game_id))
        except DatabaseError:
            return

        print("['event_queue']:")
        print(game.state['event_queue'])

        if game.status == Game.GAME_STATUS_ENDED:
            return

        game.status = Game.GAME_STATUS_IN_PROGRESS

        game_state = GameState.model_validate(game.state)

        if len(game_state.event_queue) <= 0:

            # Look for games that may be stuck. If there's no more events but
            # we're not in a main phase, then we need to try to move the game
            # forward.
            if game_state.phase == "refresh":
                game_state.event_queue.append(DrawPhaseEvent(side=game_state.active))
            elif game_state.phase == "draw":
                print('Advancing to main phase')
                game_state.event_queue.append(MainPhaseEvent(side=game_state.active))
            else:
                return

        # Process multiple events in a batch to reduce DB round-trips
        events_processed = 0
        max_events_per_step = 10  # Prevent infinite loops and stack overflow
        all_updates = []
        all_errors = []

        while len(game_state.event_queue) > 0 and events_processed < max_events_per_step:
            resolved_event: ResolvedEvent = resolve_event(state=game_state)
            game_state = resolved_event.state

            # Accumulate all updates for batch sending
            all_updates.extend(resolved_event.updates)
            all_errors.extend(resolved_event.errors)
            events_processed += 1

            # Check for game over - if found, stop processing and handle it
            game_over_update = None
            for update in resolved_event.updates:

                GameUpdate.objects.create(
                    game=game,
                    update=update.model_dump(mode="json"),
                )

                if isinstance(update, GameOverUpdate):
                    game_over_update = update
                    break

            if game_over_update:
                print("Game over Detected")
                game.status = Game.GAME_STATUS_ENDED

                winner_side = game_over_update.winner
                if winner_side == 'side_a':
                    winner = game.side_a
                elif winner_side == 'side_b':
                    winner = game.side_b

                game.winner = winner
                game.save(update_fields=["status", "winner"])

                game_state.winner = winner_side
                game_state.event_queue = []
                break

            if len(all_errors) > 0:
                break

        # If it's an AI's turn and there's no more events queued, see if it can
        # take another action. If not, it will queue an end turn event.
        if (len(game_state.event_queue) == 0
            and game_state.phase == "main"
            and game_state.active in game_state.ai_sides):

            deck = getattr(game, game_state.active)

            event = ChooseAIMoveEvent(
                side=game_state.active,
                script=DeckScript.model_validate(deck.script or {}))

            game_state.event_queue.append(event)

        # Single DB save for all processed events
        game.state = game_state.model_dump()
        game.save(update_fields=["state"])

        # Single WebSocket send with all accumulated updates
        _send_game_updates_to_clients(
            game.id,
            game_state.model_dump(mode="json"),
            updates=[update.model_dump(mode="json") for update in all_updates],
            errors=[error.model_dump(mode="json") for error in all_errors])

        # Continue processing if there are more events
        if len(game_state.event_queue) > 0:
            step.apply_async(args=[game_id], countdown=STEP_DELAY)

        return {"game_id": game_id, "events_processed": events_processed}

        """
        if game_state.phase != "main":
            return

        active_side = game_state.active
        active_deck = getattr(game, active_side)
        if not active_deck.is_ai_deck:
            return

        # If we're here, we're in the main phase and it's an AI's turn.
        # Determine which move the AI is making next.
        event = determine_ai_move(game_state)
        game_state.event_queue.append(event)
        game.state = game_state.model_dump()
        game.save(update_fields=["state"])

        _send_game_updates_to_clients(
            game.id,
            game_state.model_dump(),
            [])
        advance_game.apply_async(args=[game_id], countdown=STEP_DELAY)
        """

@shared_task
def advance_game(game_id: int):
    from .engine import resolve_event, determine_ai_move
    from .services import GameService

    # Call step synchronously first
    step(game_id)
    return


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


def _send_game_updates_to_clients(game_id: int, state_dict: dict, updates: list, errors: list = []):
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
            'errors': errors,
            'state': state_dict
        }
    )