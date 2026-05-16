"""
Client notification and filtering logic for gameplay updates.

This module handles all WebSocket communication with game clients,
including filtering state and updates based on what each player should see.
"""

import asyncio
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)

# Timeout for sending updates via channel layer.
# Prevents Celery workers from blocking indefinitely if Redis is unresponsive.
SEND_TIMEOUT = 5.0


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
    opposing_side = "side_b" if viewing_side == "side_a" else "side_a"

    for update in updates:
        update_dict = (
            update.model_dump(mode="json") if hasattr(update, "model_dump") else update
        )

        # DrawCardUpdate: hide card details if opponent drew
        if update_dict.get("type") == "update_draw_card":
            if update_dict.get("side") == opposing_side:
                # Opponent drew - hide which card
                filtered.append(
                    {
                        **update_dict,
                        "card_id": None,  # Hide the actual card ID
                        "hidden": True,  # Flag for client to show card back
                    }
                )
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
    from apps.gameplay.agents.observation import filter_state_for_player

    return filter_state_for_player(state, viewing_side)


async def _send_with_timeout(channel_layer, group_name: str, message: dict):
    """Send to channel group with timeout to prevent blocking."""
    try:
        await asyncio.wait_for(
            channel_layer.group_send(group_name, message), timeout=SEND_TIMEOUT
        )
    except asyncio.TimeoutError:
        logger.error(f"Timeout sending to channel group {group_name}")
    except Exception as e:
        logger.error(f"Error sending to channel group {group_name}: {e}")


def send_game_updates_to_clients(game_id: int, state, updates: list, errors: list = []):
    """
    Send game updates to WebSocket clients with per-player filtering.

    Each player receives their own filtered version of the state and updates,
    hiding information they shouldn't see (opponent's hand, deck, etc.).
    Spectators (staff viewing games) receive unfiltered full state.

    Uses timeout to prevent blocking if Redis channel layer is unresponsive.

    Args:
        game_id: The game ID
        state: GameState object or dict
        updates: List of update objects/dicts
        errors: List of error objects/dicts (optional)
    """
    channel_layer = get_channel_layer()

    # Send side-specific messages to per-player groups
    for side in ["side_a", "side_b"]:
        side_group_name = f"game_{game_id}_{side}"
        filtered_updates = filter_updates_for_side(updates, side)
        filtered_state = filter_state_for_side(state, side)

        async_to_sync(_send_with_timeout)(
            channel_layer,
            side_group_name,
            {
                "type": "game_updates",
                "updates": filtered_updates,
                "errors": errors,
                "state": filtered_state,
            },
        )

    # Send unfiltered state to spectators (staff viewing games)
    spectator_group_name = f"game_{game_id}_spectator"
    state_dict = (
        state.model_dump(mode="json") if hasattr(state, "model_dump") else state
    )
    updates_list = [
        u.model_dump(mode="json") if hasattr(u, "model_dump") else u for u in updates
    ]

    async_to_sync(_send_with_timeout)(
        channel_layer,
        spectator_group_name,
        {
            "type": "game_updates",
            "updates": updates_list,
            "errors": errors,
            "state": state_dict,
        },
    )


def send_matchmaking_success(user_id: int, game_id: int, title_slug: str):
    """
    Send a matchmaking success notification to a specific user.

    Uses timeout to prevent blocking if Redis channel layer is unresponsive.

    Args:
        user_id: The user's ID
        game_id: The created game ID
        title_slug: The title slug for routing
    """
    channel_layer = get_channel_layer()
    user_group_name = f"user_{user_id}"

    async_to_sync(_send_with_timeout)(
        channel_layer,
        user_group_name,
        {
            "type": "matchmaking_success",
            "game_id": game_id,
            "title_slug": title_slug,
        },
    )
