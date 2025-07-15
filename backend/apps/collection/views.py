from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Count

from apps.builder.models import Title, CardTemplate
from .models import Deck, DeckCard


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def deck_list_by_title(request, title_slug):
    """
    List all decks for a specific title, filtered by the current user.
    Decks are ordered by updated_at (most recent first).
    """
    # Get the title (latest version) or return 404
    title = get_object_or_404(Title, slug=title_slug, is_latest=True)

    # Get decks for this title, filtering by user and ordering by updated_at
    decks = Deck.objects.filter(
        user=request.user,
        hero__title=title
    ).select_related('hero').annotate(
        card_count=Count('deckcard')
    ).order_by('-updated_at')

    # Serialize the deck data
    deck_data = []
    for deck in decks:
        deck_data.append({
            'id': deck.id,
            'name': deck.name,
            'description': deck.description,
            'hero': {
                'id': deck.hero.id,
                'name': deck.hero.name,
                'slug': deck.hero.slug,
            },
            'card_count': deck.card_count,
            'created_at': deck.created_at.isoformat(),
            'updated_at': deck.updated_at.isoformat(),
        })

    return Response({
        'title': {
            'id': title.id,
            'slug': title.slug,
            'name': title.name,
        },
        'decks': deck_data,
        'count': len(deck_data)
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def deck_detail(request, deck_id):
    """
    Get details for a specific deck.
    """
    deck = get_object_or_404(Deck, id=deck_id, user=request.user)

    # Get deck cards with counts
    deck_cards = deck.deckcard_set.select_related('card').order_by('card__name')

    card_data = []
    for deck_card in deck_cards:
        card_data.append({
            'id': deck_card.card.id,
            'name': deck_card.card.name,
            'slug': deck_card.card.slug,
            'cost': deck_card.card.cost,
            'card_type': deck_card.card.card_type,
            'attack': deck_card.card.attack,
            'health': deck_card.card.health,
            'count': deck_card.count,
        })

    return Response({
        'id': deck.id,
        'name': deck.name,
        'description': deck.description,
        'title': {
            'id': deck.hero.title.id,
            'slug': deck.hero.title.slug,
            'name': deck.hero.title.name,
        },
        'hero': {
            'id': deck.hero.id,
            'name': deck.hero.name,
            'slug': deck.hero.slug,
            'health': deck.hero.health,
        },
        'cards': card_data,
        'total_cards': sum(card['count'] for card in card_data),
        'created_at': deck.created_at.isoformat(),
        'updated_at': deck.updated_at.isoformat(),
    })


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_deck_card(request, deck_id, card_id):
    """
    Update the count of a specific card in a deck.
    """
    deck = get_object_or_404(Deck, id=deck_id, user=request.user)
    card = get_object_or_404(CardTemplate, id=card_id)

    # Get the deck card relationship
    deck_card = get_object_or_404(DeckCard, deck=deck, card=card)

    # Get the new count from request data
    new_count = request.data.get('count')
    if new_count is None:
        return Response(
            {'error': 'count is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Validate count
    try:
        new_count = int(new_count)
        if new_count < 1 or new_count > 10:
            return Response(
                {'error': 'count must be between 1 and 10'},
                status=status.HTTP_400_BAD_REQUEST
            )
    except (ValueError, TypeError):
        return Response(
            {'error': 'count must be a valid integer'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Update the count
    deck_card.count = new_count
    deck_card.save()

    return Response({
        'id': card.id,
        'count': deck_card.count,
        'message': f'Card count updated to {new_count}'
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_deck_card(request, deck_id, card_id):
    """
    Remove a card from a deck.
    """
    deck = get_object_or_404(Deck, id=deck_id, user=request.user)
    card = get_object_or_404(CardTemplate, id=card_id)

    # Get the deck card relationship
    deck_card = get_object_or_404(DeckCard, deck=deck, card=card)

    # Delete the deck card
    deck_card.delete()

    return Response({
        'message': f'Card "{card.name}" removed from deck'
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_deck_card(request, deck_id):
    """
    Add a card to a deck or update its count if it already exists.
    """

    deck = get_object_or_404(Deck, id=deck_id, user=request.user)

    # Get card_id from request data
    card_id = request.data.get('card_id')
    if not card_id:
        return Response(
            {'error': 'card_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Get the card and verify it belongs to the same title as the deck's hero
    card = get_object_or_404(CardTemplate, id=card_id)
    if card.title != deck.hero.title:
        return Response(
            {'error': 'Card does not belong to the same title as the deck'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Get count from request (default to 1)
    count = request.data.get('count', 1)
    try:
        count = int(count)
        if count < 1 or count > 10:
            return Response(
                {'error': 'count must be between 1 and 10'},
                status=status.HTTP_400_BAD_REQUEST
            )
    except (ValueError, TypeError):
        return Response(
            {'error': 'count must be a valid integer'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check if card is already in deck
    deck_card, created = DeckCard.objects.get_or_create(
        deck=deck,
        card=card,
        defaults={'count': count}
    )

    if not created:
        # Update existing card count
        deck_card.count += count
        deck_card.save()
        message = f'Updated "{card.name}" count to {count}'
    else:
        message = f'Added "{card.name}" to deck with count {count}'

    return Response({
        'id': card.id,
        'name': card.name,
        'count': deck_card.count,
        'message': message
    }, status=status.HTTP_200_OK)
