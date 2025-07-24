from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.collection.models import Deck
from apps.builder.models import Title, CardTemplate, HeroTemplate
from apps.builder.serializers import TitleSerializer
from apps.gameplay.models import Game
from apps.gameplay.schemas import GameSummary, GameList
from .schemas import Hero, Deck as DeckSchema
from .serializers import serialize_cards_with_traits, serialize_decks

def health_check(request):
    """Simple health check endpoint"""
    return JsonResponse({"status": "healthy"})

@api_view(['GET'])
def titles(request):
    titles = Title.objects.order_by('-published_at')
    serializer = TitleSerializer(titles, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def title_by_slug(request, slug):
    """Get the latest version of a title by its slug."""
    title = get_object_or_404(Title, slug=slug, is_latest=True)
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
    # Get the title (latest version) or return 404
    title = get_object_or_404(Title, slug=slug, is_latest=True)

    # Build the queryset with filtering and ordering
    cards_queryset = (CardTemplate.objects
                     .filter(title=title, is_latest=True)
                     .order_by('cost', 'card_type', 'attack', 'health', 'name'))

    # Use the helper function to serialize with efficient prefetching
    card_data = serialize_cards_with_traits(cards_queryset)

    return Response(card_data)


@api_view(['GET'])
@permission_classes([AllowAny])
def title_heroes(request, slug):
    """Get all heroes for a title."""
    title = get_object_or_404(Title, slug=slug, is_latest=True)
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

    # Get the title (latest version) or return 404
    title = get_object_or_404(Title, slug=slug, is_latest=True)

    games = Game.objects.filter(
        side_a__title=title,
    ).filter(
        Q(side_a__user=request.user) | Q(side_b__user=request.user)
    ).order_by('-created_at')

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
@permission_classes([AllowAny])
def title_decks(request, slug):
    """Get all decks for a title."""
    title = get_object_or_404(Title, slug=slug, is_latest=True)
    decks = Deck.objects.filter(
        user=request.user,
        title=title
    )
    return Response(serialize_decks(decks))


@api_view(['GET'])
@permission_classes([AllowAny])
def title_pve(request, slug):
    """Get all PvE / Scenario decks for a title."""
    title = get_object_or_404(Title, slug=slug, is_latest=True)
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
