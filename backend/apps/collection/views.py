from django.db import transaction
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.authentication.models import Friendship
from apps.builder.models import CardTemplate, HeroTemplate, Title
from apps.collection.models import Deck, DeckCard, UserTitleDeckPreference
from apps.collection.validation import get_title_config, validate_deck_card_count
from apps.core.card_assets import get_hero_art_url
from apps.core.serializers import serialize_cards_with_traits, to_card_schema


def _card_not_available_error(card, hero) -> str:
    return (
        f'"{card.name}" is only available to specific heroes and cannot be used '
        f"by {hero.name}"
    )


def _ineligible_deck_cards(deck, hero=None):
    hero = hero or deck.hero
    return (
        deck.deckcard_set.filter(card__allowed_heroes__isnull=False)
        .exclude(card__allowed_heroes=hero)
        .select_related("card")
        .distinct()
    )


def _eligible_cards_for_hero(title, hero):
    return (
        CardTemplate.objects.filter(title=title, is_latest=True, is_collectible=True)
        .filter(Q(allowed_heroes__isnull=True) | Q(allowed_heroes=hero))
        .distinct()
    )


def _archive_deck(deck):
    from apps.gameplay.models import FriendlyChallenge, MatchmakingQueue

    now = timezone.now()
    with transaction.atomic():
        archived_now = deck.archive(when=now)
        MatchmakingQueue.objects.filter(
            deck=deck,
            status=MatchmakingQueue.STATUS_QUEUED,
        ).update(status=MatchmakingQueue.STATUS_CANCELLED, updated_at=now)
        FriendlyChallenge.objects.filter(
            Q(challenger_deck=deck) | Q(challengee_deck=deck),
            status=FriendlyChallenge.STATUS_PENDING,
        ).update(status=FriendlyChallenge.STATUS_CANCELLED, updated_at=now)
        UserTitleDeckPreference.objects.filter(last_used_deck=deck).update(
            last_used_deck=None,
            updated_at=now,
        )

    return archived_now


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def deck_list_by_title(request, title_slug):
    """
    GET: List all decks for a specific title, filtered by the current user.
    POST: Create a new deck for a specific title.
    """
    # Get the title (latest version) or return 404
    title = get_object_or_404(Title, slug=title_slug, is_latest=True)

    if request.method == "GET":
        # Get decks for this title, filtering by user and ordering by updated_at
        decks = (
            Deck.objects.filter(
                user=request.user,
                hero__title=title,
                archived_at__isnull=True,
            )
            .select_related("hero")
            .annotate(card_count=Coalesce(Sum("deckcard__count"), 0))
            .order_by("-updated_at")
        )

        # Serialize the deck data
        deck_data = []
        for deck in decks:
            deck_data.append(
                {
                    "id": deck.id,
                    "name": deck.name,
                    "description": deck.description,
                    "hero": {
                        "id": deck.hero.id,
                        "name": deck.hero.name,
                        "slug": deck.hero.slug,
                        "art_url": get_hero_art_url(title.slug, deck.hero.slug),
                    },
                    "card_count": deck.card_count,
                    "created_at": deck.created_at.isoformat(),
                    "updated_at": deck.updated_at.isoformat(),
                }
            )

        last_used_deck_id = None
        last_used_friend_id = None
        preference = (
            UserTitleDeckPreference.objects.filter(user=request.user, title=title)
            .select_related("last_used_deck")
            .first()
        )
        if preference and preference.last_used_deck_id:
            deck_ids = {deck["id"] for deck in deck_data}
            if preference.last_used_deck_id in deck_ids:
                last_used_deck_id = preference.last_used_deck_id
        if preference and preference.last_used_friend_id:
            is_friend = Friendship.objects.filter(
                user=request.user,
                friend_id=preference.last_used_friend_id,
                status=Friendship.STATUS_ACCEPTED,
            ).exists()
            if is_friend:
                last_used_friend_id = preference.last_used_friend_id

        return Response(
            {
                "title": {
                    "id": title.id,
                    "slug": title.slug,
                    "name": title.name,
                },
                "decks": deck_data,
                "count": len(deck_data),
                "last_used_deck_id": last_used_deck_id,
                "last_used_friend_id": last_used_friend_id,
            }
        )

    elif request.method == "POST":
        # Create a new deck
        # Get required data from request
        name = request.data.get("name", "").strip()
        description = request.data.get("description", "").strip()
        hero_id = request.data.get("hero_id")

        # Validate input
        if not name:
            return Response(
                {"error": "Name is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not hero_id:
            return Response(
                {"error": "Hero is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Get the hero and verify it belongs to this title
        hero = get_object_or_404(HeroTemplate, id=hero_id, title=title, is_latest=True)

        # Check if deck name already exists for this user
        if Deck.objects.filter(
            user=request.user,
            name=name,
            archived_at__isnull=True,
        ).exists():
            return Response(
                {"error": "A deck with this name already exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create the deck
        deck = Deck.objects.create(
            user=request.user,
            name=name,
            description=description,
            hero=hero,
            title=title,
        )

        return Response(
            {
                "id": deck.id,
                "name": deck.name,
                "description": deck.description,
                "hero": {
                    "id": hero.id,
                    "name": hero.name,
                    "slug": hero.slug,
                    "health": hero.health,
                    "art_url": get_hero_art_url(title.slug, hero.slug),
                },
                "title": {
                    "id": title.id,
                    "slug": title.slug,
                    "name": title.name,
                },
                "cards": [],
                "total_cards": 0,
                "created_at": deck.created_at.isoformat(),
                "updated_at": deck.updated_at.isoformat(),
                "message": f'Deck "{name}" created successfully',
            },
            status=status.HTTP_201_CREATED,
        )


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def deck_detail(request, deck_id):
    """
    GET: Get details for a specific deck.
    PUT: Update an existing deck.
    DELETE: Archive a deck.
    """
    deck_queryset = Deck.objects.filter(id=deck_id, user=request.user)
    if request.method != "DELETE":
        deck_queryset = deck_queryset.filter(archived_at__isnull=True)
    deck = get_object_or_404(deck_queryset)

    if request.method == "GET":
        config = get_title_config(deck.title)

        # Get deck cards with counts
        deck_cards = (
            deck.deckcard_set.select_related("card", "card__title", "card__faction")
            .prefetch_related(
                "card__cardtrait_set",
                "card__allowed_heroes",
            )
            .filter(card__is_collectible=True)
            .order_by("card__name")
        )

        card_data = []
        for deck_card in deck_cards:
            # Use schema for consistent serialization including art_url and description
            schema = to_card_schema(deck_card.card)
            data = schema.model_dump()
            data["count"] = deck_card.count
            card_data.append(data)

        # Get all available collectible cards for this title (for "Edit Cards" mode)
        all_cards_queryset = _eligible_cards_for_hero(
            deck.hero.title, deck.hero
        ).order_by("cost", "card_type", "attack", "health", "name")
        all_cards_data = serialize_cards_with_traits(
            all_cards_queryset, skip_invalid=True
        )
        all_cards = [card.model_dump() for card in all_cards_data]

        return Response(
            {
                "id": deck.id,
                "name": deck.name,
                "description": deck.description,
                "title": {
                    "id": deck.hero.title.id,
                    "slug": deck.hero.title.slug,
                    "name": deck.hero.title.name,
                },
                "hero": {
                    "id": deck.hero.id,
                    "name": deck.hero.name,
                    "slug": deck.hero.slug,
                    "health": deck.hero.health,
                    "art_url": get_hero_art_url(deck.hero.title.slug, deck.hero.slug),
                },
                "config": config.model_dump(exclude={"type"}),
                "cards": card_data,
                # All available collectible cards for adding to deck.
                "all_cards": all_cards,
                "total_cards": sum(card["count"] for card in card_data),
                "created_at": deck.created_at.isoformat(),
                "updated_at": deck.updated_at.isoformat(),
            }
        )

    elif request.method == "PUT":
        # Update the deck
        # Get data from request
        name = request.data.get("name", "").strip()
        description = request.data.get("description", "").strip()
        hero_id = request.data.get("hero_id")

        # Validate input
        if not name:
            return Response(
                {"error": "Name is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Check if deck name already exists for this user (excluding current deck)
        name_exists = (
            Deck.objects.filter(user=request.user, name=name)
            .exclude(id=deck.id)
            .filter(archived_at__isnull=True)
            .exists()
        )
        if name_exists:
            return Response(
                {"error": "A deck with this name already exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update basic fields
        deck.name = name
        if description is not None:
            deck.description = description

        # Update hero if provided
        if hero_id:
            hero = get_object_or_404(
                HeroTemplate,
                id=hero_id,
                title=deck.hero.title,
                is_latest=True,
            )
            invalid_cards = _ineligible_deck_cards(deck, hero)
            if invalid_cards.exists():
                invalid_names = ", ".join(
                    deck_card.card.name for deck_card in invalid_cards[:3]
                )
                return Response(
                    {
                        "error": (
                            f'Cannot switch to "{hero.name}" while the deck contains '
                            f"ineligible cards: {invalid_names}"
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            deck.hero = hero

        deck.save()

        # Get deck cards with counts for response
        deck_cards = (
            deck.deckcard_set.select_related("card", "card__title", "card__faction")
            .prefetch_related(
                "card__cardtrait_set",
                "card__allowed_heroes",
            )
            .order_by("card__name")
        )

        card_data = []
        for deck_card in deck_cards:
            schema = to_card_schema(deck_card.card)
            data = schema.model_dump()
            data["count"] = deck_card.count
            card_data.append(data)

        return Response(
            {
                "id": deck.id,
                "name": deck.name,
                "description": deck.description,
                "title": {
                    "id": deck.hero.title.id,
                    "slug": deck.hero.title.slug,
                    "name": deck.hero.title.name,
                },
                "hero": {
                    "id": deck.hero.id,
                    "name": deck.hero.name,
                    "slug": deck.hero.slug,
                    "health": deck.hero.health,
                },
                "cards": card_data,
                "total_cards": sum(card["count"] for card in card_data),
                "created_at": deck.created_at.isoformat(),
                "updated_at": deck.updated_at.isoformat(),
                "message": f'Deck "{deck.name}" updated successfully',
            }
        )

    elif request.method == "DELETE":
        # Archive the deck so historical games can keep their protected references.
        deck_name = deck.name
        title_slug = deck.hero.title.slug
        archived_now = _archive_deck(deck)

        return Response(
            {
                "message": (
                    f'Deck "{deck_name}" archived successfully'
                    if archived_now
                    else f'Deck "{deck_name}" was already archived'
                ),
                "title_slug": title_slug,
            },
            status=status.HTTP_200_OK,
        )


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_deck_card(request, deck_id, card_id):
    """
    Update the count of a specific card in a deck.
    """
    deck = get_object_or_404(
        Deck,
        id=deck_id,
        user=request.user,
        archived_at__isnull=True,
    )
    # Get the deck card relationship
    deck_card = get_object_or_404(
        DeckCard.objects.select_related("card"),
        deck=deck,
        card_id=card_id,
    )
    card = deck_card.card

    # Get the new count from request data
    new_count = request.data.get("count")
    if new_count is None:
        return Response(
            {"error": "count is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    # Validate count
    try:
        new_count = int(new_count)
    except (ValueError, TypeError):
        return Response(
            {"error": "count must be a valid integer"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    validation_error = validate_deck_card_count(
        deck,
        card,
        new_count,
        current_count=deck_card.count,
    )
    if validation_error:
        return Response({"error": validation_error}, status=status.HTTP_400_BAD_REQUEST)

    # Update the count
    deck_card.count = new_count
    deck_card.save()

    return Response(
        {
            "id": card.id,
            "count": deck_card.count,
            "message": f"Card count updated to {new_count}",
        }
    )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_deck_card(request, deck_id, card_id):
    """
    Remove a card from a deck.
    """
    deck = get_object_or_404(
        Deck,
        id=deck_id,
        user=request.user,
        archived_at__isnull=True,
    )
    card = get_object_or_404(CardTemplate, id=card_id)

    # Get the deck card relationship
    deck_card = get_object_or_404(DeckCard, deck=deck, card=card)

    # Delete the deck card
    deck_card.delete()

    return Response(
        {"message": f'Card "{card.name}" removed from deck'}, status=status.HTTP_200_OK
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def opponent_decks_by_title(request, title_slug):
    """
    GET: List all other users' decks for a specific title (for PvP matchmaking).
    Excludes AI decks and the current user's decks.
    """
    # Get the title (latest version) or return 404
    title = get_object_or_404(Title, slug=title_slug, is_latest=True)

    # Get decks for this title from other users (excluding current user and AI)
    decks = (
        Deck.objects.filter(
            hero__title=title,
            user__isnull=False,  # Only human players
            archived_at__isnull=True,
        )
        .exclude(user=request.user)  # Exclude current user
        .select_related("hero", "user")
        .annotate(card_count=Coalesce(Sum("deckcard__count"), 0))
        .order_by("-updated_at")
    )

    # Serialize the deck data
    deck_data = []
    for deck in decks:
        deck_data.append(
            {
                "id": deck.id,
                "name": deck.name,
                "description": deck.description,
                "hero": {
                    "id": deck.hero.id,
                    "name": deck.hero.name,
                    "slug": deck.hero.slug,
                },
                "owner": {
                    "email": deck.user.email,
                },
                "card_count": deck.card_count,
                "created_at": deck.created_at.isoformat(),
                "updated_at": deck.updated_at.isoformat(),
            }
        )

    return Response(
        {
            "title": {
                "id": title.id,
                "slug": title.slug,
                "name": title.name,
            },
            "decks": deck_data,
            "count": len(deck_data),
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_deck_card(request, deck_id):
    """
    Add a card to a deck or update its count if it already exists.
    """

    deck = get_object_or_404(
        Deck,
        id=deck_id,
        user=request.user,
        archived_at__isnull=True,
    )

    # Get card_id from request data
    card_slug = request.data.get("card_slug")
    if not card_slug:
        return Response(
            {"error": "card_slug is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    # Get the card and verify it belongs to the same title as the deck's hero
    card = get_object_or_404(
        CardTemplate,
        slug=card_slug,
        title=deck.hero.title,
        is_latest=True,
    )

    # Check if card is collectible
    if not card.is_collectible:
        error = f'"{card.name}" is not collectible and cannot be added to a deck'
        return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

    if not card.is_available_to_hero(deck.hero):
        return Response(
            {"error": _card_not_available_error(card, deck.hero)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Get count from request (default to 1)
    count = request.data.get("count", 1)
    try:
        count = int(count)
        if count < 1:
            return Response(
                {"error": "count must be at least 1"},
                status=status.HTTP_400_BAD_REQUEST,
            )
    except (ValueError, TypeError):
        return Response(
            {"error": "count must be a valid integer"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    deck_card = DeckCard.objects.filter(deck=deck, card=card).first()
    current_count = deck_card.count if deck_card else 0
    new_total = current_count + count
    validation_error = validate_deck_card_count(
        deck,
        card,
        new_total,
        current_count=current_count,
    )
    if validation_error:
        return Response({"error": validation_error}, status=status.HTTP_400_BAD_REQUEST)

    if deck_card:
        # Update existing card count
        deck_card.count = new_total
        deck_card.save()
        message = f'Updated "{card.name}" count to {deck_card.count}'
    else:
        deck_card = DeckCard.objects.create(deck=deck, card=card, count=count)
        message = f'Added "{card.name}" to deck with count {count}'

    return Response(
        {
            "id": card.id,
            "name": card.name,
            "count": deck_card.count,
            "message": message,
        },
        status=status.HTTP_200_OK,
    )
