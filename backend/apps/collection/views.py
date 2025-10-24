from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Count

from apps.builder.models import Title, CardTemplate, HeroTemplate
from apps.builder.schemas import TitleConfig
from .models import Deck, DeckCard



@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def deck_list_by_title(request, title_slug):
    """
    GET: List all decks for a specific title, filtered by the current user.
    POST: Create a new deck for a specific title.
    """
    # Get the title (latest version) or return 404
    title = get_object_or_404(Title, slug=title_slug, is_latest=True)

    if request.method == 'GET':
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

    elif request.method == 'POST':
        # Create a new deck
        # Get required data from request
        name = request.data.get('name', '').strip()
        description = request.data.get('description', '').strip()
        hero_id = request.data.get('hero_id')

        # Validate input
        if not name:
            return Response(
                {'error': 'Name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not hero_id:
            return Response(
                {'error': 'Hero is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get the hero and verify it belongs to this title
        hero = get_object_or_404(HeroTemplate, id=hero_id, title=title, is_latest=True)

        # Check if deck name already exists for this user
        if Deck.objects.filter(user=request.user, name=name).exists():
            return Response(
                {'error': 'A deck with this name already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create the deck
        deck = Deck.objects.create(
            user=request.user,
            name=name,
            description=description,
            hero=hero,
            title=title,
        )

        return Response({
            'id': deck.id,
            'name': deck.name,
            'description': deck.description,
            'hero': {
                'id': hero.id,
                'name': hero.name,
                'slug': hero.slug,
                'health': hero.health,
            },
            'title': {
                'id': title.id,
                'slug': title.slug,
                'name': title.name,
            },
            'cards': [],
            'total_cards': 0,
            'created_at': deck.created_at.isoformat(),
            'updated_at': deck.updated_at.isoformat(),
            'message': f'Deck "{name}" created successfully'
        }, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def deck_detail(request, deck_id):
    """
    GET: Get details for a specific deck.
    PUT: Update an existing deck.
    DELETE: Delete a deck.
    """
    deck = get_object_or_404(Deck, id=deck_id, user=request.user)

    if request.method == 'GET':
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

    elif request.method == 'PUT':
        # Update the deck
        # Get data from request
        name = request.data.get('name', '').strip()
        description = request.data.get('description', '').strip()
        hero_id = request.data.get('hero_id')

        # Validate input
        if not name:
            return Response(
                {'error': 'Name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if deck name already exists for this user (excluding current deck)
        if Deck.objects.filter(user=request.user, name=name).exclude(id=deck.id).exists():
            return Response(
                {'error': 'A deck with this name already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update basic fields
        deck.name = name
        if description is not None:
            deck.description = description

        # Update hero if provided
        if hero_id:
            hero = get_object_or_404(HeroTemplate, id=hero_id, title=deck.hero.title, is_latest=True)
            deck.hero = hero

        deck.save()

        # Get deck cards with counts for response
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
            'message': f'Deck "{deck.name}" updated successfully'
        })

    elif request.method == 'DELETE':
        # Delete the deck
        deck_name = deck.name
        title_slug = deck.hero.title.slug
        deck.delete()

        return Response({
            'message': f'Deck "{deck_name}" deleted successfully',
            'title_slug': title_slug
        }, status=status.HTTP_200_OK)


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

    # Check if card has Unique trait
    has_unique = card.cardtrait_set.filter(trait_slug='unique').exists()
    if has_unique and new_count > 1:
        return Response(
            {'error': f'"{card.name}" has the Unique trait and can only have 1 copy in a deck'},
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
    card_slug = request.data.get('card_slug')
    if not card_slug:
        return Response(
            {'error': 'card_slug is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Get the card and verify it belongs to the same title as the deck's hero
    card = get_object_or_404(CardTemplate, slug=card_slug, is_latest=True)
    if card.title != deck.hero.title:
        return Response(
            {'error': 'Card does not belong to the same title as the deck'},
            status=status.HTTP_400_BAD_REQUEST
        )

    world_config = TitleConfig.model_validate(card.title.config)

    # Get count from request (default to 1)
    count = request.data.get('count', 1)
    try:
        count = int(count)
        if count < 1:
            return Response(
                {'error': 'count must be at least 1'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if count > world_config.deck_card_max_count:
            return Response(
                {'error': 'Cannot have more than %s copies of a card'
                            % world_config.deck_card_max_count},
            )
    except (ValueError, TypeError):
        return Response(
            {'error': 'count must be a valid integer'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check if card has Unique trait
    has_unique = card.cardtrait_set.filter(trait_slug='unique').exists()
    if has_unique and count > 1:
        return Response(
            {'error': f'"{card.name}" has the Unique trait and can only have 1 copy in a deck'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # See if the operation would put the deck over the size limit
    if deck.deck_size + count > world_config.deck_size_limit:
        return Response(
            {'error': 'Deck size would exceed the limit'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check if card is already in deck
    deck_card, created = DeckCard.objects.get_or_create(
        deck=deck,
        card=card,
        defaults={'count': count}
    )

    if not created:
        # Check if adding more would violate Unique trait
        new_total = deck_card.count + count
        if has_unique and new_total > 1:
            return Response(
                {'error': f'"{card.name}" has the Unique trait and can only have 1 copy in a deck'},
                status=status.HTTP_400_BAD_REQUEST
            )
        # Update existing card count
        deck_card.count += count
        deck_card.save()
        message = f'Updated "{card.name}" count to {deck_card.count}'
    else:
        message = f'Added "{card.name}" to deck with count {count}'

    return Response({
        'id': card.id,
        'name': card.name,
        'count': deck_card.count,
        'message': message
    }, status=status.HTTP_200_OK)
