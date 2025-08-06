from celery import shared_task
from django.db import transaction, DatabaseError
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Game
from .schemas import (
    GameOverUpdate,
    GameState,
    ResolvedEvent,)

STEP_DELAY = 1

from dataclasses import dataclass

@dataclass
class StepResult:
    needs_continuation: bool

@shared_task
def step(game_id: int):
    from .engine import resolve_event, determine_ai_move
    from .services import GameService

    with transaction.atomic():
        try:
            game = (Game.objects
                        .select_for_update(nowait=True)
                        .get(id=game_id))
        except DatabaseError:
            return

        if game.status == Game.GAME_STATUS_ENDED:
            return

        game_state = GameState.model_validate(game.state)

        if len(game_state.event_queue) <= 0:
            return

        # Process multiple events in a batch to reduce DB round-trips
        events_processed = 0
        max_events_per_step = 10  # Prevent infinite loops and stack overflow
        all_updates = []

        while len(game_state.event_queue) > 0 and events_processed < max_events_per_step:
            resolved_event: ResolvedEvent = resolve_event(state=game_state)
            game_state = resolved_event.state

            # Accumulate all updates for batch sending
            all_updates.extend(resolved_event.updates)
            events_processed += 1

            # Check for game over - if found, stop processing and handle it
            game_over_update = None
            for update in resolved_event.updates:
                if isinstance(update, GameOverUpdate):
                    game_over_update = update
                    break

            if game_over_update:
                game.status = Game.GAME_STATUS_ENDED

                winner_side = game_over_update.winner
                if winner_side == 'side_a':
                    winner = game.side_a
                elif winner_side == 'side_b':
                    winner = game.side_b

                game.winner = winner
                game.save(update_fields=["status", "winner"])

                game_state.event_queue = []
                break

        # Single DB save for all processed events
        game.state = game_state.model_dump()
        game.save(update_fields=["state"])

        # Single WebSocket send with all accumulated updates
        _send_game_updates_to_clients(
            game.id,
            game_state.model_dump(),
            [update.model_dump() for update in all_updates])

        # Continue processing if there are more events
        if len(game_state.event_queue) > 0:
            step.apply_async(args=[game_id], countdown=STEP_DELAY)

        return game

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

    with transaction.atomic():
        try:
            game = (Game.objects
                        .select_for_update(nowait=True)
                        .get(id=game_id))
        except DatabaseError:
            print('DB Lock, skipping')
            return

        if game.status == Game.GAME_STATUS_ENDED:
            return

        game_state = GameState.model_validate(game.state)

        print("Advancing game at state %s for %s " % (
            game_state.phase, game_state.active))

        if len(game_state.event_queue) > 0:
            print('Event queue, resolving')

            resolved_event: ResolvedEvent = resolve_event(state=game_state)
            new_state = resolved_event.state

            print("==== Resolution ====")
            print("Events: %s" % resolved_event.events)
            print("Updates: %s" % resolved_event.updates)
            print("==== End Resolution ====")

            for update in resolved_event.updates:
                if isinstance(update, GameOverUpdate):

                #if GameOverUpdate in resolved_event.updates:
                    print("game over")
                    game.status = Game.GAME_STATUS_ENDED

                    winner_side = resolved_event.updates[0].winner
                    if winner_side == 'side_a':
                        winner = game.side_a
                    elif winner_side == 'side_b':
                        winner = game.side_b

                    game.winner = winner
                    game.save(update_fields=["status", "winner"])

                    new_state.event_queue = []
                    break

            game.state = new_state.model_dump()
            game.save(update_fields=["state"])

            _send_game_updates_to_clients(
                game.id,
                new_state.model_dump(),
                [ update.model_dump() for update in resolved_event.updates ])
            advance_game.apply_async(args=[game_id], countdown=STEP_DELAY)
            return

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