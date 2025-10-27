from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status


from apps.collection.models import Deck
from apps.gameplay.models import Game
from apps.gameplay.schemas import GameSummary, GameList
from apps.gameplay.schemas.game import GameState
from apps.gameplay.services import GameService
from apps.gameplay.tasks import step


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def game_detail(request, game_id):
    game = get_object_or_404(Game, id=game_id)

    game_data = GameState.model_validate(game.state).model_dump()

    # In addition to the game data, we also have to return who the viewing user
    # is.
    if game.side_a.user == request.user:
        game_data['viewer'] = 'side_a'
    else:
        game_data['viewer'] = 'side_b'

    game_data['is_vs_ai'] = game.is_vs_ai

    return Response(game_data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_games(request):
    games = Game.objects.filter(
        Q(side_a__user=request.user) | Q(side_b__user=request.user)
    ).exclude(
        status=Game.GAME_STATUS_ENDED
    ).order_by('-created_at')

    #games = Game.objects.all()

    game_summaries = []

    for game in games:
        if game.side_a.user == request.user:
            game_summaries.append(GameSummary(
                id=game.id,
                name=game.side_b.owner_name,
            ))
        else:
            game_summaries.append(GameSummary(
                id=game.id,
                name=game.side_a.owner_name,
            ))

    return Response(GameList(games=game_summaries).model_dump())


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def game_queue(request, game_id):
    """
    Get the current effect queue for a game.
    """
    game = get_object_or_404(Game, id=game_id)

    # Verify the user has access to this game
    if game.side_a.user != request.user and game.side_b.user != request.user:
        return Response(
            {'error': 'You do not have access to this game'},
            status=status.HTTP_403_FORBIDDEN
        )

    return Response({'queue': game.queue})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def advance_game(request, game_id):
    game = get_object_or_404(Game, id=game_id)
    from .tasks import step
    step.delay(game_id)
    return Response(status=200)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_game(request):
    """
    Create a new game between two decks.
    Supports both PvE (vs AI) and PvP (vs another player).
    """
    import logging
    logger = logging.getLogger(__name__)

    logger.debug(f"create_game called with data: {request.data}")

    player_deck_id = request.data.get('player_deck_id')
    ai_deck_id = request.data.get('ai_deck_id')
    opponent_deck_id = request.data.get('opponent_deck_id')

    # Validate input - must have player deck
    if not player_deck_id:
        logger.error("player_deck_id is missing")
        return Response(
            {'error': 'player_deck_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Must have either ai_deck_id or opponent_deck_id, but not both
    if not ai_deck_id and not opponent_deck_id:
        logger.error("Neither ai_deck_id nor opponent_deck_id provided")
        return Response(
            {'error': 'Either ai_deck_id or opponent_deck_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if ai_deck_id and opponent_deck_id:
        logger.error("Both ai_deck_id and opponent_deck_id provided")
        return Response(
            {'error': 'Cannot specify both ai_deck_id and opponent_deck_id'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Get player deck and verify ownership
        logger.debug(f"Looking for player deck with id: {player_deck_id}")
        player_deck = get_object_or_404(Deck, id=player_deck_id, user=request.user)
        logger.debug(f"Found player deck: {player_deck}")

        # Determine opponent deck based on game type
        if ai_deck_id:
            # PvE mode - get AI deck and verify it's an AI deck
            logger.debug(f"Looking for AI deck with id: {ai_deck_id}")
            opponent_deck = get_object_or_404(Deck, id=ai_deck_id, ai_player__isnull=False)
            logger.debug(f"Found AI deck: {opponent_deck}")
            game_type = "PvE"
        else:
            # PvP mode - get opponent's deck and verify it's a player deck (not AI)
            logger.debug(f"Looking for opponent deck with id: {opponent_deck_id}")
            opponent_deck = get_object_or_404(Deck, id=opponent_deck_id, user__isnull=False)
            logger.debug(f"Found opponent deck: {opponent_deck}")

            # Verify it's not the same user playing against themselves
            if opponent_deck.user == request.user:
                logger.error("User attempted to play against their own deck")
                return Response(
                    {'error': 'Cannot create a game against your own deck'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            game_type = "PvP"

        # Verify both decks are from the same title
        if player_deck.title != opponent_deck.title:
            logger.error(f"Title mismatch: player deck title {player_deck.title} != opponent deck title {opponent_deck.title}")
            return Response(
                {'error': 'Both decks must be from the same title'},
                status=status.HTTP_400_BAD_REQUEST
            )

        logger.debug("About to call GameService.start_game")
        # Create the game using GameService with randomized starting player
        # TODO: In the future, this could be enhanced to alternate starting players
        # between the same two opponents based on previous game history
        game = GameService.start_game(player_deck, opponent_deck, randomize_starting_player=True)
        logger.debug(f"Game created successfully: {game}")

        step.delay(game.id)

        return Response({
            'id': game.id,
            'status': game.status,
            'game_type': game_type,
            'player_deck': {
                'id': player_deck.id,
                'name': player_deck.name,
                'hero': player_deck.hero.name
            },
            'opponent_deck': {
                'id': opponent_deck.id,
                'name': opponent_deck.name,
                'hero': opponent_deck.hero.name
            },
            'message': f'Game created successfully: {player_deck.hero.name} vs {opponent_deck.hero.name}'
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.exception(f"Error creating game: {str(e)}")
        return Response(
            {'error': f'Failed to create game: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
