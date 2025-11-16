from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status


from apps.builder.models import Title
from apps.collection.models import Deck
from apps.gameplay.models import Game, MatchmakingQueue, UserTitleRating
from apps.gameplay.schemas import GameSummary, GameList
from apps.gameplay.schemas.game import GameState
from apps.gameplay.services import GameService
from apps.gameplay.tasks import step


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def game_detail(request, game_id):
    game = get_object_or_404(
        Game.objects.select_related(
            'side_a__user',
            'side_b__user',
            'winner__user'
        ).prefetch_related('elo_change'),
        id=game_id
    )

    game_data = GameState.model_validate(game.state).model_dump()

    # Determine which side the viewing user is on
    # Verify the user has access to this game
    if game.side_a.user == request.user:
        game_data['viewer'] = 'side_a'
    elif game.side_b.user == request.user:
        game_data['viewer'] = 'side_b'
    else:
        # User is not a participant in this game
        return Response(
            {'error': 'You do not have access to this game'},
            status=status.HTTP_403_FORBIDDEN
        )

    game_data['is_vs_ai'] = game.is_vs_ai

    # Include ELO rating changes if available (for completed PvP games)
    if hasattr(game, 'elo_change') and game.elo_change:
        elo_change = game.elo_change
        game_data['elo_change'] = {
            'winner': {
                'user_id': elo_change.winner.id,
                'display_name': elo_change.winner.display_name,
                'old_rating': elo_change.winner_old_rating,
                'new_rating': elo_change.winner_new_rating,
                'change': elo_change.winner_rating_change,
            },
            'loser': {
                'user_id': elo_change.loser.id,
                'display_name': elo_change.loser.display_name,
                'old_rating': elo_change.loser_old_rating,
                'new_rating': elo_change.loser_new_rating,
                'change': elo_change.loser_rating_change,
            }
        }

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

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def queue_for_ranked_match(request):
    """
    Queue a player for a ranked match.
    Creates a matchmaking queue entry for the player with their selected deck.
    """
    import logging
    logger = logging.getLogger(__name__)

    logger.debug(f"queue_for_ranked_match called with data: {request.data}")

    deck_id = request.data.get('deck_id')

    # Validate input
    if not deck_id:
        logger.error("deck_id is missing")
        return Response(
            {'error': 'deck_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Get the deck and verify ownership
        deck = get_object_or_404(Deck, id=deck_id, user=request.user)
        logger.debug(f"Found deck: {deck}")


        # Check if the user is already in queue for this title
        existing_queue = MatchmakingQueue.objects.filter(
            user=request.user,
            deck__title=deck.title,
            status=MatchmakingQueue.STATUS_QUEUED
        ).first()

        if existing_queue:
            logger.info(f"User already in queue: {existing_queue}")
            return Response(
                {
                    'error': 'You are already in queue for this title',
                    'queue_entry_id': existing_queue.id
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get or create the user's rating for this title
        user_rating, created = UserTitleRating.objects.get_or_create(
            user=request.user,
            title=deck.title,
            defaults={'elo_rating': 1200}
        )
        logger.debug(f"User rating: {user_rating.elo_rating}")

        # Create the matchmaking queue entry
        queue_entry = MatchmakingQueue.objects.create(
            user=request.user,
            deck=deck,
            elo_rating=user_rating.elo_rating,
            status=MatchmakingQueue.STATUS_QUEUED
        )
        logger.debug(f"Queue entry created: {queue_entry}")

        # Trigger matchmaking task to attempt to find a match
        from apps.gameplay.tasks import process_matchmaking
        process_matchmaking.delay(deck.title.id)

        return Response({
            'id': queue_entry.id,
            'status': queue_entry.status,
            'title': {
                'slug': deck.title.slug,
                'name': deck.title.name
            },
            'deck': {
                'id': deck.id,
                'name': deck.name,
                'hero': deck.hero.name
            },
            'elo_rating': user_rating.elo_rating,
            'message': f'Successfully queued for ranked match in {deck.title.name}'
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.exception(f"Error queueing for ranked match: {str(e)}")
        return Response(
            {'error': f'Failed to queue for match: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def matchmaking_queue_status(request, title_slug):
    """
    Return the current matchmaking queue status for the requesting user within a title.
    """
    title = get_object_or_404(Title, slug=title_slug)

    queue_entry = MatchmakingQueue.objects.select_related('deck', 'deck__hero').filter(
        user=request.user,
        deck__title=title,
        status=MatchmakingQueue.STATUS_QUEUED
    ).first()

    if not queue_entry:
        return Response({
            'in_queue': False,
            'queue_entry': None
        })

    return Response({
        'in_queue': True,
        'queue_entry': {
            'id': queue_entry.id,
            'status': queue_entry.status,
            'elo_rating': queue_entry.elo_rating,
            'queued_at': queue_entry.created_at,
            'deck': {
                'id': queue_entry.deck.id,
                'name': queue_entry.deck.name,
                'hero': queue_entry.deck.hero.name
            },
            'title': {
                'id': title.id,
                'name': title.name,
                'slug': title.slug
            }
        }
    })