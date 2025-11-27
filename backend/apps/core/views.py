from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import PermissionDenied

from apps.collection.models import Deck
from apps.builder.models import Title, CardTemplate, HeroTemplate
from apps.builder.serializers import TitleSerializer
from apps.gameplay.models import Game
from apps.gameplay.schemas import GameSummary, GameList
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

    games = Game.objects.filter(
        side_a__title=title,
    ).filter(
        Q(side_a__user=request.user) | Q(side_b__user=request.user)
    ).exclude(
        status=Game.GAME_STATUS_ENDED
    ).order_by('-created_at')

    game_summaries = []

    for game in games:

        if game.side_a.user == request.user:
            user_side = 'side_a'
            opposing_deck = game.side_b
        else:
            user_side = 'side_b'
            opposing_deck = game.side_a

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
            type="pve" if opposing_deck.is_ai_deck else "pvp",
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
