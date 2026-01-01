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


def _update_game_time_per_turn(game: Game):
    """Update time_per_turn in game state based on game type and title config."""
    game_state = GameState.model_validate(game.state)

    if game.type == Game.GAME_TYPE_RANKED:
        if game.ladder_type == Game.LADDER_TYPE_DAILY:
            game_state.time_per_turn = 60 * 60 * 24
        else:
            # Use ranked_time_per_turn from title config (rapid ladder)
            game_state.time_per_turn = game_state.config.ranked_time_per_turn
    else:
        # Friendly and PvE games have no time limit
        game_state.time_per_turn = 0

    # Update the state in the database
    game.state = game_state.model_dump()
    game.save(update_fields=['state'])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def game_detail(request, game_id):
    game = get_object_or_404(
        Game.objects.select_related(
            'side_a__user',
            'side_b__user',
            'winner__user',
            'player_a_user',
            'player_b_user',
            'title'
        ).prefetch_related('elo_change'),
        id=game_id
    )

    game_data = GameState.model_validate(game.state).model_dump()

    # Determine which side the viewing user is on
    # Verify the user has access to this game
    if game.player_a_user == request.user:
        game_data['viewer'] = 'side_a'
    elif game.player_b_user == request.user:
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
    # Note: This endpoint doesn't filter by title, so we use the old query method
    # In the future, if we want title-scoped queries here, we'd need to pass title
    games = Game.objects.filter(
        Q(player_a_user=request.user) | Q(player_b_user=request.user)
    ).exclude(
        status=Game.GAME_STATUS_ENDED
    ).order_by('-created_at')

    game_summaries = []

    for game in games:
        if game.player_a_user == request.user:
            user_side = 'side_a'
            opposing_deck = game.side_b
        else:
            user_side = 'side_b'
            opposing_deck = game.side_a

        # Determine if it's the user's turn
        game_state = game.game_state
        is_user_turn = game_state.active == user_side

        game_summaries.append(GameSummary(
            id=game.id,
            name=opposing_deck.owner_name if not opposing_deck.is_ai_deck else opposing_deck.name,
            type=game.type,
            is_user_turn=is_user_turn,
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
    if game.player_a_user != request.user and game.player_b_user != request.user:
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

        logger.debug("About to call GameService.create_game")
        # Create the game using GameService with randomized starting player
        # TODO: In the future, this could be enhanced to alternate starting players
        # between the same two opponents based on previous game history
        game = GameService.create_game(player_deck, opponent_deck, randomize_starting_player=True)

        # Set game type based on whether it's PvE or PvP
        if ai_deck_id:
            game.type = Game.GAME_TYPE_PVE
            game.ladder_type = None
        else:
            game.type = Game.GAME_TYPE_RANKED
            if not game.ladder_type:
                game.ladder_type = Game.LADDER_TYPE_RAPID
        game.save(update_fields=['type', 'ladder_type'])

        # Update time_per_turn in game state based on game type
        _update_game_time_per_turn(game)

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
    ladder_type = request.data.get('ladder_type', Game.LADDER_TYPE_RAPID)

    if ladder_type not in dict(Game.LADDER_TYPE_CHOICES):
        return Response(
            {'error': 'Invalid ladder type'},
            status=status.HTTP_400_BAD_REQUEST
        )

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


        if ladder_type == Game.LADDER_TYPE_DAILY:
            active_daily_games = Game.objects.filter(
                Q(player_a_user=request.user) | Q(player_b_user=request.user),
                status=Game.GAME_STATUS_IN_PROGRESS,
                type=Game.GAME_TYPE_RANKED,
                ladder_type=Game.LADDER_TYPE_DAILY,
            ).count()
            if active_daily_games >= 3:
                return Response(
                    {'error': 'Daily ladder limit reached (3 active games).'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Check if the user is already in queue for this title
        existing_queue = MatchmakingQueue.objects.filter(
            user=request.user,
            deck__title=deck.title,
            status=MatchmakingQueue.STATUS_QUEUED
        ).first()

        if existing_queue:
            logger.info(f"User already in queue: {existing_queue}")
            ladder_msg = f" for {existing_queue.get_ladder_type_display()}"
            return Response(
                {
                    'error': f'You are already in queue for this title{ladder_msg}',
                    'queue_entry_id': existing_queue.id,
                    'ladder_type': existing_queue.ladder_type,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get or create the user's rating for this title
        user_rating, created = UserTitleRating.objects.get_or_create(
            user=request.user,
            title=deck.title,
            ladder_type=ladder_type,
            defaults={'elo_rating': 1200}
        )
        logger.debug(f"User rating: {user_rating.elo_rating}")

        # Create the matchmaking queue entry
        queue_entry = MatchmakingQueue.objects.create(
            user=request.user,
            deck=deck,
            elo_rating=user_rating.elo_rating,
            ladder_type=ladder_type,
            status=MatchmakingQueue.STATUS_QUEUED
        )
        logger.debug(f"Queue entry created: {queue_entry}")

        # Trigger matchmaking task to attempt to find a match
        from apps.gameplay.tasks import process_matchmaking
        process_matchmaking.delay(deck.title.id, ladder_type)

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
            'ladder_type': ladder_type,
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

    ladder_type = request.query_params.get('ladder_type', Game.LADDER_TYPE_RAPID)
    if ladder_type not in dict(Game.LADDER_TYPE_CHOICES):
        return Response(
            {'error': 'Invalid ladder type'},
            status=status.HTTP_400_BAD_REQUEST
        )

    queue_entry = MatchmakingQueue.objects.select_related('deck', 'deck__hero').filter(
        user=request.user,
        deck__title=title,
        ladder_type=ladder_type,
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
            'ladder_type': queue_entry.ladder_type,
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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def leave_matchmaking_queue(request, title_slug):
    """
    Remove the user from the matchmaking queue for a specific title.
    """
    import logging
    logger = logging.getLogger(__name__)

    title = get_object_or_404(Title, slug=title_slug)

    ladder_type = request.query_params.get('ladder_type', Game.LADDER_TYPE_RAPID)
    if ladder_type not in dict(Game.LADDER_TYPE_CHOICES):
        return Response(
            {'error': 'Invalid ladder type'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Find the user's active queue entry for this title
    queue_entry = MatchmakingQueue.objects.filter(
        user=request.user,
        deck__title=title,
        ladder_type=ladder_type,
        status=MatchmakingQueue.STATUS_QUEUED
    ).first()

    if not queue_entry:
        return Response(
            {'error': 'You are not currently in the queue for this title'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Cancel the queue entry
    queue_entry.status = MatchmakingQueue.STATUS_CANCELLED
    queue_entry.save(update_fields=['status'])

    logger.info(f"User {request.user.display_name} left matchmaking queue for {title.name}")

    return Response({
        'message': 'Successfully left matchmaking queue',
        'queue_entry_id': queue_entry.id
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_friendly_challenge(request):
    """
    Create a friend vs friend challenge (unrated). Requires:
    - title_slug
    - challengee_user_id
    - challenger_deck_id
    """
    from apps.authentication.models import Friendship
    from apps.gameplay.models import FriendlyChallenge
    import logging
    logger = logging.getLogger(__name__)

    title_slug = request.data.get('title_slug')
    challengee_user_id = request.data.get('challengee_user_id')
    challenger_deck_id = request.data.get('challenger_deck_id')

    if not (title_slug and challengee_user_id and challenger_deck_id):
        return Response({'error': 'title_slug, challengee_user_id, and challenger_deck_id are required'}, status=status.HTTP_400_BAD_REQUEST)

    title = get_object_or_404(Title, slug=title_slug)
    challengee = get_object_or_404(request.user.__class__, id=challengee_user_id)
    challenger_deck = get_object_or_404(Deck, id=challenger_deck_id, user=request.user, title=title)

    # Cannot challenge self
    if challengee.id == request.user.id:
        return Response({'error': 'Cannot challenge yourself'}, status=status.HTTP_400_BAD_REQUEST)

    # Validate they are friends (accepted)
    is_friend = Friendship.objects.filter(
        user=request.user, friend=challengee, status=Friendship.STATUS_ACCEPTED
    ).exists()
    if not is_friend:
        return Response({'error': 'You can only challenge accepted friends'}, status=status.HTTP_403_FORBIDDEN)

    # If there is already a pending challenge from challenger to challengee for this title, return it
    existing = FriendlyChallenge.objects.filter(
        challenger=request.user, challengee=challengee, title=title, status=FriendlyChallenge.STATUS_PENDING
    ).first()
    if existing:
        return Response({
            'id': existing.id,
            'status': existing.status,
            'title': {'id': title.id, 'name': title.name, 'slug': title.slug},
            'challenger': {'id': request.user.id, 'display_name': request.user.display_name},
            'challengee': {'id': challengee.id, 'display_name': challengee.display_name},
            'challenger_deck': {'id': challenger_deck.id, 'name': challenger_deck.name, 'hero': challenger_deck.hero.name},
        }, status=status.HTTP_200_OK)

    challenge = FriendlyChallenge.objects.create(
        challenger=request.user,
        challengee=challengee,
        title=title,
        challenger_deck=challenger_deck,
        status=FriendlyChallenge.STATUS_PENDING
    )

    return Response({
        'id': challenge.id,
        'status': challenge.status,
        'title': {'id': title.id, 'name': title.name, 'slug': title.slug},
        'challenger': {'id': request.user.id, 'display_name': request.user.display_name},
        'challengee': {'id': challengee.id, 'display_name': challengee.display_name},
        'challenger_deck': {'id': challenger_deck.id, 'name': challenger_deck.name, 'hero': challenger_deck.hero.name},
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_pending_friendly_challenges(request, title_slug):
    """
    List pending incoming and outgoing challenges for the current user and title.
    """
    from apps.gameplay.models import FriendlyChallenge
    title = get_object_or_404(Title, slug=title_slug)

    incoming = FriendlyChallenge.objects.select_related('challenger', 'challenger_deck').filter(
        challengee=request.user, title=title, status=FriendlyChallenge.STATUS_PENDING
    )
    outgoing = FriendlyChallenge.objects.select_related('challengee', 'challenger_deck').filter(
        challenger=request.user, title=title, status=FriendlyChallenge.STATUS_PENDING
    )

    incoming_payload = [{
        'id': c.id,
        'status': c.status,
        'challenger': {'id': c.challenger.id, 'display_name': c.challenger.display_name},
        'challengee': {'id': c.challengee.id, 'display_name': c.challengee.display_name},
        'challenger_deck': {'id': c.challenger_deck.id, 'name': c.challenger_deck.name, 'hero': c.challenger_deck.hero.name},
        'title': {'id': c.title.id, 'name': c.title.name, 'slug': c.title.slug},
    } for c in incoming]

    outgoing_payload = [{
        'id': c.id,
        'status': c.status,
        'challenger': {'id': c.challenger.id, 'display_name': c.challenger.display_name},
        'challengee': {'id': c.challengee.id, 'display_name': c.challengee.display_name},
        'challenger_deck': {'id': c.challenger_deck.id, 'name': c.challenger_deck.name, 'hero': c.challenger_deck.hero.name},
        'title': {'id': c.title.id, 'name': c.title.name, 'slug': c.title.slug},
    } for c in outgoing]

    return Response({'incoming': incoming_payload, 'outgoing': outgoing_payload})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accept_friendly_challenge(request, challenge_id):
    """
    Accept a friendly challenge. Requires:
    - challengee_deck_id
    Creates an unrated Game and returns its id.
    """
    from apps.gameplay.models import FriendlyChallenge
    challenge = get_object_or_404(FriendlyChallenge, id=challenge_id)

    if challenge.challengee != request.user:
        return Response({'error': 'Only the challengee can accept this challenge'}, status=status.HTTP_403_FORBIDDEN)

    if challenge.status != FriendlyChallenge.STATUS_PENDING:
        return Response({'error': 'Challenge is not pending'}, status=status.HTTP_400_BAD_REQUEST)

    challengee_deck_id = request.data.get('challengee_deck_id')
    if not challengee_deck_id:
        return Response({'error': 'challengee_deck_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    # Validate deck ownership and title
    challengee_deck = get_object_or_404(Deck, id=challengee_deck_id, user=request.user, title=challenge.title)

    # Create the game
    game = GameService.create_game(challenge.challenger_deck, challengee_deck, randomize_starting_player=True)
    game.type = Game.GAME_TYPE_FRIENDLY
    game.save(update_fields=['type'])

    # Update time_per_turn in game state (friendly games have no time limit)
    _update_game_time_per_turn(game)

    # Link and update challenge
    challenge.challengee_deck = challengee_deck
    challenge.game = game
    challenge.status = FriendlyChallenge.STATUS_ACCEPTED
    challenge.save(update_fields=['challengee_deck', 'game', 'status'])

    # Kick off first step
    step.delay(game.id)

    return Response({'game_id': game.id}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def decline_friendly_challenge(request, challenge_id):
    """
    Decline a friendly challenge. Only the challengee can decline.
    """
    from apps.gameplay.models import FriendlyChallenge
    challenge = get_object_or_404(FriendlyChallenge, id=challenge_id)

    if challenge.challengee != request.user:
        return Response({'error': 'Only the challengee can decline this challenge'}, status=status.HTTP_403_FORBIDDEN)

    if challenge.status != FriendlyChallenge.STATUS_PENDING:
        return Response({'error': 'Challenge is not pending'}, status=status.HTTP_400_BAD_REQUEST)

    challenge.status = FriendlyChallenge.STATUS_CANCELLED
    challenge.save(update_fields=['status'])

    return Response({'success': True, 'message': 'Challenge declined'}, status=status.HTTP_200_OK)
