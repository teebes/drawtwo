from django.db.models import Q, Count, Case, When, Value, IntegerField
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import PermissionDenied

from apps.authentication.models import Friendship
from apps.collection.models import Deck
from apps.builder.models import Title, CardTemplate, HeroTemplate
from apps.builder.serializers import TitleSerializer
from apps.gameplay.models import Game, MatchmakingQueue, ELORatingChange, UserTitleRating
from apps.gameplay.schemas import GameSummary, GameList
from apps.gameplay.schemas.game import Notification
from .schemas import Hero, Deck as DeckSchema
from .serializers import serialize_cards_with_traits, serialize_decks


def get_title_or_403(slug, user):
    """
    Get a title by slug and check if the user has permission to view it.

    Raises:
        Http404: If the title doesn't exist
        PermissionDenied: If the user doesn't have permission to view the title

    Returns:
        Title: The title object if user has permission
    """
    title = get_object_or_404(Title, slug=slug, is_latest=True)
    if not title.can_be_viewed_by(user):
        raise PermissionDenied("You do not have permission to view this title.")
    return title

def health_check(request):
    """Simple health check endpoint"""
    return JsonResponse({"status": "healthy"})

@api_view(['GET'])
def titles(request):
    titles = Title.objects.filter(
        status=Title.STATUS_PUBLISHED
    ).order_by('-published_at')
    serializer = TitleSerializer(titles, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def title_by_slug(request, slug):
    """Get the latest version of a title by its slug."""
    title = get_title_or_403(slug, request.user)

    serializer = TitleSerializer(title)
    data = serializer.data

    # Add edit permission info if user is authenticated
    if request.user and request.user.is_authenticated:
        data['can_edit'] = title.can_be_edited_by(request.user)
    else:
        data['can_edit'] = False

    return Response(data)

@api_view(['GET'])
@permission_classes([AllowAny])
def title_cards(request, slug):
    """
    Get all cards for a title, ordered by cost then name.
    Returns data in the Card schema format with efficient trait fetching.
    """
    title = get_title_or_403(slug, request.user)

    # Build the queryset with filtering and ordering
    cards_queryset = (CardTemplate.objects
                     .filter(title=title, is_latest=True)
                     .order_by('cost', 'card_type', 'attack', 'health', 'name'))

    # Use the helper function to serialize with efficient prefetching
    card_data = serialize_cards_with_traits(cards_queryset)

    return Response([card.model_dump() for card in card_data])

@api_view(['GET'])
@permission_classes([AllowAny])
def title_card_detail(request, slug, card_slug):
    """Get a specific card by title and card slug."""
    title = get_title_or_403(slug, request.user)
    card = get_object_or_404(CardTemplate, title=title, slug=card_slug, is_latest=True)
    card_data = serialize_cards_with_traits(
        CardTemplate.objects.filter(pk=card.id))
    return Response(card_data[0].model_dump())

@api_view(['GET'])
@permission_classes([AllowAny])
def title_heroes(request, slug):
    """Get all heroes for a title."""
    title = get_title_or_403(slug, request.user)

    heroes = HeroTemplate.objects.filter(
        title=title, is_latest=True
    ).order_by('name')
    hero_data = [Hero(
        id=hero.id,
        slug=hero.slug,
        name=hero.name,
        health=hero.health,
        hero_power=hero.hero_power,
        spec=hero.spec,
        faction=hero.faction.slug if hero.faction else None
    ).model_dump() for hero in heroes]
    return Response(hero_data)


@api_view(['GET'])
@permission_classes([AllowAny])
def title_games(request, slug):
    """Get all games for a title."""
    title = get_title_or_403(slug, request.user)

    # Use the new manager method with side annotation
    if request.user.is_authenticated:
        games = Game.objects.where_user_is_side(title, request.user).exclude(
            status=Game.GAME_STATUS_ENDED
        ).order_by('-created_at')
    else:
        # For unauthenticated users, just filter by title
        games = Game.objects.for_title(title).exclude(
            status=Game.GAME_STATUS_ENDED
        ).order_by('-created_at')

    game_summaries = []

    for game in games:
        if request.user.is_authenticated:
            # Use the annotated user_side if available
            user_side = getattr(game, 'user_side', None)
            if not user_side:
                # Fallback for unauthenticated or edge cases
                if game.player_a_user == request.user:
                    user_side = 'side_a'
                else:
                    user_side = 'side_b'
        else:
            # For unauthenticated, default to side_a
            user_side = 'side_a'

        opposing_deck = game.side_b if user_side == 'side_a' else game.side_a

        if opposing_deck.is_ai_deck:
            opposing_name = opposing_deck.name
        else:
            opposing_name = opposing_deck.owner_name

        # Determine if it's the user's turn
        game_state = game.game_state
        is_user_turn = game_state.active == user_side

        game_summaries.append(GameSummary(
            id=game.id,
            name=opposing_name,
            type=game.type,
            is_user_turn=is_user_turn,
        ))

    return Response(GameList(games=game_summaries).model_dump())

@api_view(['GET'])
@permission_classes([AllowAny])
def title_decks(request, slug):
    """Get all decks for a title."""
    title = get_title_or_403(slug, request.user)

    decks = Deck.objects.filter(
        user=request.user,
        title=title
    )
    return Response(serialize_decks(decks))


@api_view(['GET'])
@permission_classes([AllowAny])
def title_pve(request, slug):
    """Get all PvE / Scenario decks for a title."""
    title = get_title_or_403(slug, request.user)

    decks = Deck.objects.filter(
        ai_player__isnull=False,
        title=title,
    )
    return Response([
        DeckSchema(
            id=deck.id,
            name=deck.name,
            description=deck.description,
            hero=Hero(
                id=deck.hero.id,
                slug=deck.hero.slug,
                name=deck.hero.name,
                health=deck.hero.health,
                hero_power=deck.hero.hero_power,
                spec=deck.hero.spec,
                faction=deck.hero.faction.slug if deck.hero.faction else None,
            ),
            card_count=deck.deck_size,
            created_at=deck.created_at,
            updated_at=deck.updated_at,
        ).model_dump()
        for deck in decks
    ])

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def title_notifications(request, slug):
    from apps.gameplay.schemas.game import Notification
    from apps.gameplay.models import FriendlyChallenge
    from apps.builder.models import Title

    print(f"list_notifications called with title_slug: {slug}")

    try:
        title = Title.objects.get(slug=slug)
    except Title.DoesNotExist:
        return Response({'error': 'Title not found'}, status=404)

    notifications = []

    # Queued for Ranked Match
    queued_for_ranked_match = MatchmakingQueue.objects.filter(
        user=request.user,
        deck__title=title,
        status=MatchmakingQueue.STATUS_QUEUED
    ).first()
    if queued_for_ranked_match:
        notifications.append(Notification(
            ref_id=queued_for_ranked_match.id,
            type='game_ranked_queued',
            message="You are in the queue for a ranked match."))

    games = Game.objects.where_user_is_side(title, request.user)

    ranked_game = games.filter(
        type=Game.GAME_TYPE_RANKED
    ).order_by('-created_at').first()
    if ranked_game:
        opponent_deck = ranked_game.opponent_deck_for_user(request.user)

        # Game In Progress
        if ranked_game.status == Game.GAME_STATUS_IN_PROGRESS:
            is_player_turn = ranked_game.state['active'] == ranked_game.user_side
            if is_player_turn:
                message = f"Your turn against {opponent_deck.owner_name}."
            else:
                message = f"Waiting for {opponent_deck.owner_name} to take their turn."

        # Game Ended
        elif ranked_game.status == Game.GAME_STATUS_ENDED:
            if opponent_deck == ranked_game.winner:
                message = f"You lost your ranked match against {opponent_deck.owner_name}."
            else:
                message = f"You won your ranked match against {opponent_deck.owner_name}."

        notifications.append(Notification(
            ref_id=ranked_game.id,
            type='game_ranked',
            message=message,
        ))

    # Friendly games where it is the player's turn
    friendly_games = games.filter(
        type=Game.GAME_TYPE_FRIENDLY,
        status=Game.GAME_STATUS_IN_PROGRESS
    ).order_by('-created_at')
    for friendly_game in friendly_games:
        opponent_deck = friendly_game.opponent_deck_for_user(request.user)
        is_player_turn = friendly_game.state['active'] == friendly_game.user_side
        if is_player_turn:
            message = f"Your turn against {opponent_deck.owner_name}."
        else:
            message = f"Waiting for {opponent_deck.owner_name} to take their turn."
        notifications.append(Notification(
            ref_id=friendly_game.id,
            type='game_friendly',
            message=message,
        ))

    # Pending friendly challenges
    pending_challenges = FriendlyChallenge.objects.filter(
        challengee=request.user,
        title=title,
        status=FriendlyChallenge.STATUS_PENDING
    )
    for challenge in pending_challenges:
        challenger = challenge.challenger.display_name
        notifications.append(Notification(
            ref_id=challenge.id,
            type='game_challenge',
            message=f'You have a pending friendly challenge from {challenger}',
        ))

    # Incoming friend requests
    incoming_friend_requests = Friendship.objects.filter(
        friend=request.user,
        status=Friendship.STATUS_PENDING
    )
    for friend_request in incoming_friend_requests:
        notifications.append(Notification(
            ref_id=friend_request.id,
            type='friend_request',
            message=f'You have a pending friend request from {friend_request.user.display_name}',
        ))

    return Response([n.model_dump() for n in notifications])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def title_games_history(request, slug):
    """
    Get paginated game history for a title with stats.
    Returns:
    - stats: ranked game stats (total, wins, losses) and friendly game stats (total only)
    - games: paginated list of games (ended and in-progress) with opponent, outcome, status, and turn indicator
    """
    title = get_title_or_403(slug, request.user)
    user = request.user

    # Get all completed games for stats calculation only
    ended_games = Game.objects.for_title(title).for_user(user).filter(
        status=Game.GAME_STATUS_ENDED
    ).select_related(
        'side_a__user', 'side_b__user', 'side_a__hero', 'side_b__hero',
        'winner', 'player_a_user', 'player_b_user'
    ).prefetch_related('elo_change')

    # Calculate stats using efficient aggregation (only from ended games)
    ranked_games = ended_games.filter(type=Game.GAME_TYPE_RANKED)
    friendly_games = ended_games.filter(type=Game.GAME_TYPE_FRIENDLY)

    def get_ranked_stats(queryset):
        total = queryset.count()
        wins = 0
        losses = 0
        for game in queryset:
            user_deck = game.side_a if game.player_a_user == user else game.side_b
            if game.winner == user_deck:
                wins += 1
            elif game.winner is not None:
                losses += 1
        return {'total': total, 'wins': wins, 'losses': losses}

    ranked_stats = get_ranked_stats(ranked_games)
    friendly_stats = {'total': friendly_games.count()}

    # Get user's current ELO rating for this title
    try:
        user_rating = UserTitleRating.objects.get(user=user, title=title)
        current_rating = user_rating.elo_rating
    except UserTitleRating.DoesNotExist:
        current_rating = 1200  # Default rating if user hasn't played ranked games yet

    # Get all games (ended and in-progress) for the games list
    # Use where_user_is_side to annotate user_side
    all_games = Game.objects.where_user_is_side(title, user).filter(
        status__in=[Game.GAME_STATUS_ENDED, Game.GAME_STATUS_IN_PROGRESS]
    ).select_related(
        'side_a__user', 'side_b__user', 'side_a__hero', 'side_b__hero',
        'winner', 'player_a_user', 'player_b_user'
    ).prefetch_related('elo_change')

    # Paginate games (ordered by creation timestamp, newest first)
    page_number = request.query_params.get('page', 1)
    page_size = request.query_params.get('page_size', 20)
    try:
        page_number = int(page_number)
        page_size = min(int(page_size), 50)  # Cap at 50 per page
    except (TypeError, ValueError):
        page_number = 1
        page_size = 20

    all_games_ordered = all_games.order_by('-created_at')
    paginator = Paginator(all_games_ordered, page_size)
    page = paginator.get_page(page_number)

    games_list = []
    for game in page.object_list:
        # Get annotated user_side
        user_side = getattr(game, 'user_side', None)
        if not user_side:
            # Fallback if annotation didn't work
            if game.player_a_user == user:
                user_side = 'side_a'
            else:
                user_side = 'side_b'

        # Determine user's deck and opponent
        if user_side == 'side_a':
            user_deck = game.side_a
            opponent_deck = game.side_b
            opponent_user = game.player_b_user
        else:
            user_deck = game.side_b
            opponent_deck = game.side_a
            opponent_user = game.player_a_user

        # Determine opponent name
        if opponent_deck.is_ai_deck:
            opponent_name = opponent_deck.name
        elif opponent_user:
            opponent_name = opponent_user.display_name
        else:
            opponent_name = opponent_deck.owner_name

        # Determine outcome (only for ended games)
        outcome = None
        if game.status == Game.GAME_STATUS_ENDED:
            if game.winner == user_deck:
                outcome = 'win'
            elif game.winner == opponent_deck:
                outcome = 'loss'
            else:
                outcome = 'draw'

        # Determine if it's the user's turn (only for in-progress games)
        is_user_turn = None
        if game.status == Game.GAME_STATUS_IN_PROGRESS:
            game_state = game.game_state
            is_user_turn = game_state.active == user_side

        # Get ELO change if available (only for ended ranked games)
        elo_change = None
        if game.status == Game.GAME_STATUS_ENDED and hasattr(game, 'elo_change') and game.elo_change:
            elo_obj = game.elo_change
            if elo_obj.winner == user:
                elo_change = elo_obj.winner_rating_change
            elif elo_obj.loser == user:
                elo_change = elo_obj.loser_rating_change

        games_list.append({
            'id': game.id,
            'type': game.type,
            'status': game.status,
            'opponent_name': opponent_name,
            'opponent_hero': opponent_deck.hero.name if opponent_deck.hero else None,
            'user_hero': user_deck.hero.name if user_deck.hero else None,
            'outcome': outcome,
            'is_user_turn': is_user_turn,
            'elo_change': elo_change,
            'created_at': game.created_at.isoformat(),
        })

    return Response({
        'stats': {
            'ranked': ranked_stats,
            'friendly': friendly_stats,
            'current_rating': current_rating,
        },
        'games': games_list,
        'pagination': {
            'page': page.number,
            'total_pages': paginator.num_pages,
            'total_games': paginator.count,
            'has_next': page.has_next(),
            'has_previous': page.has_previous(),
        }
    })