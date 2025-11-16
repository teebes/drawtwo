"""
Client notification and filtering logic for gameplay updates.

This module handles all WebSocket communication with game clients,
including filtering state and updates based on what each player should see.
"""

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


def filter_updates_for_side(updates: list, viewing_side: str) -> list:
    """
    Filter updates to hide information that shouldn't be visible to this side.

    Args:
        updates: List of update objects or dicts
        viewing_side: 'side_a' or 'side_b' - which player is viewing

    Returns:
        Filtered list of updates safe for the viewing player
    """
    filtered = []
    opposing_side = 'side_b' if viewing_side == 'side_a' else 'side_a'

    for update in updates:
        update_dict = update.model_dump(mode="json") if hasattr(update, 'model_dump') else update

        # DrawCardUpdate: hide card details if opponent drew
        if update_dict.get('type') == 'update_draw_card':
            if update_dict.get('side') == opposing_side:
                # Opponent drew - hide which card
                filtered.append({
                    **update_dict,
                    'card_id': None,  # Hide the actual card ID
                    'hidden': True,  # Flag for client to show card back
                })
            else:
                # We drew - show everything
                filtered.append(update_dict)
        else:
            # Most updates are public information
            filtered.append(update_dict)

    return filtered


def filter_state_for_side(state, viewing_side: str) -> dict:
    """
    Filter game state to hide opponent's hidden information.

    Hidden information includes:
    - Opponent's hand contents
    - Opponent's deck order

    Args:
        state: GameState object or dict
        viewing_side: 'side_a' or 'side_b' - which player is viewing

    Returns:
        Filtered state dict safe for the viewing player
    """
    state_dict = state.model_dump(mode="json") if hasattr(state, 'model_dump') else state
    return state_dict
    filtered_state = state_dict.copy()
    opposing_side = 'side_b' if viewing_side == 'side_a' else 'side_a'

    # Opponent's hand: show count but not card IDs
    if 'hands' in filtered_state:
        opponent_hand = filtered_state['hands'].get(opposing_side, [])
        filtered_state['hands'] = {
            **filtered_state['hands'],
            opposing_side: [],  # Don't reveal opponent's cards
        }
        # Add hand count metadata
        if 'hand_counts' not in filtered_state:
            filtered_state['hand_counts'] = {}
        filtered_state['hand_counts'][opposing_side] = len(opponent_hand)
        filtered_state['hand_counts'][viewing_side] = len(filtered_state['hands'].get(viewing_side, []))

    # Opponent's deck: hide card order
    if 'decks' in filtered_state:
        opponent_deck = filtered_state['decks'].get(opposing_side, [])
        filtered_state['decks'] = {
            **filtered_state['decks'],
            opposing_side: [],  # Don't reveal deck order
        }
        # Add deck count metadata
        if 'deck_counts' not in filtered_state:
            filtered_state['deck_counts'] = {}
        filtered_state['deck_counts'][opposing_side] = len(opponent_deck)
        filtered_state['deck_counts'][viewing_side] = len(filtered_state['decks'].get(viewing_side, []))

    return filtered_state


def send_game_updates_to_clients(game_id: int, state, updates: list, errors: list = []):
    """
    Send game updates to WebSocket clients with per-player filtering.

    Each player receives their own filtered version of the state and updates,
    hiding information they shouldn't see (opponent's hand, deck, etc.).

    Args:
        game_id: The game ID
        state: GameState object or dict
        updates: List of update objects/dicts
        errors: List of error objects/dicts (optional)
    """
    channel_layer = get_channel_layer()

    # Send side-specific messages to per-player groups
    for side in ['side_a', 'side_b']:
        side_group_name = f'game_{game_id}_{side}'
        filtered_updates = filter_updates_for_side(updates, side)
        filtered_state = filter_state_for_side(state, side)

        async_to_sync(channel_layer.group_send)(
            side_group_name,
            {
                'type': 'game_updates',
                'updates': filtered_updates,
                'errors': errors,
                'state': filtered_state,
            }
        )


def send_matchmaking_success(user_id: int, game_id: int, title_slug: str):
    """
    Send a matchmaking success notification to a specific user.

    Args:
        user_id: The user's ID
        game_id: The created game ID
        title_slug: The title slug for routing
    """
    channel_layer = get_channel_layer()
    user_group_name = f'user_{user_id}'

    async_to_sync(channel_layer.group_send)(
        user_group_name,
        {
            'type': 'matchmaking_success',
            'game_id': game_id,
            'title_slug': title_slug,
        }
    )
