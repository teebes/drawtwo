import yaml
from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from pydantic import ValidationError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.collection.models import Deck, DeckCard
from apps.collection.validation import get_title_config, validate_card_for_deck

from .models import CardTemplate, CardTrait, HeroTemplate, Title
from .schemas import Card, Hero, TitleConfig
from .serializers import CardTemplateSerializer, HeroTemplateSerializer, TitleSerializer
from .services import TitleService

User = get_user_model()

AI_DECK_STRATEGIES = {"rush", "control", "combo", "aggressive", "defensive", "smart"}
AI_DECK_DRAW_MODES = {"shuffle", "ordered"}


def _title_config_from_data(config_data) -> TitleConfig:
    config_data = config_data or {}
    return TitleConfig(
        deck_size_limit=config_data.get("deck_size_limit", 30),
        min_cards_in_deck=config_data.get("min_cards_in_deck", 10),
        deck_card_max_count=config_data.get("deck_card_max_count", 9),
        hand_start_size=config_data.get("hand_start_size", 3),
        side_b_compensation=config_data.get("side_b_compensation"),
        death_retaliation=config_data.get("death_retaliation", False),
        ranked_time_per_turn=config_data.get("ranked_time_per_turn", 60),
    )


def _validate_title_config(config: TitleConfig) -> str | None:
    if config.deck_size_limit < 1:
        return "Deck size limit must be at least 1."
    if config.min_cards_in_deck < 0:
        return "Minimum cards in deck cannot be negative."
    if config.min_cards_in_deck > config.deck_size_limit:
        return "Minimum cards in deck cannot exceed the deck size limit."
    if config.deck_card_max_count < 1:
        return "Maximum copies of a card must be at least 1."
    if config.hand_start_size < 0:
        return "Starting hand size cannot be negative."
    if config.hand_start_size > config.deck_size_limit:
        return "Starting hand size cannot exceed the deck size limit."
    if config.ranked_time_per_turn < 0:
        return "Ranked time per turn cannot be negative."
    return None


def _ai_deck_queryset(title):
    return (
        Deck.objects.filter(
            title=title,
            ai_player__isnull=False,
            archived_at__isnull=True,
        )
        .exclude(ai_player__name="Intro Scenario", name__startswith="Intro ")
        .select_related("ai_player", "hero")
        .order_by("created_at", "id")
    )


def _deck_config_payload(title):
    config = get_title_config(title)
    return {
        "deck_size_limit": config.deck_size_limit,
        "min_cards_in_deck": config.min_cards_in_deck,
        "deck_card_max_count": config.deck_card_max_count,
        "hand_start_size": config.hand_start_size,
    }


def _default_ai_starting_hand_size(title) -> int:
    return get_title_config(title).hand_start_size


def _card_hero_slugs(card) -> list[str]:
    heroes = sorted(card.allowed_heroes.all(), key=lambda hero: hero.name)
    return [hero.slug for hero in heroes]


def _ai_deck_card_payload(deck_card):
    card = deck_card.card
    return {
        "deck_card_id": deck_card.id,
        "card_id": card.id,
        "card_slug": card.slug,
        "name": card.name,
        "card_type": card.card_type,
        "cost": card.cost,
        "attack": card.attack,
        "health": card.health,
        "count": deck_card.count,
        "is_collectible": card.is_collectible,
        "hero_slugs": _card_hero_slugs(card),
    }


def _serialize_ai_deck(deck):
    deck_cards = (
        deck.deckcard_set.select_related("card", "card__faction")
        .prefetch_related("card__allowed_heroes", "card__cardtrait_set")
        .order_by("card__cost", "card__name", "card__id")
    )
    script = deck.script or {}
    draw_mode = script.get("draw_mode", "shuffle")
    if draw_mode not in AI_DECK_DRAW_MODES:
        draw_mode = "shuffle"
    return {
        "id": deck.id,
        "name": deck.name,
        "description": deck.description,
        "is_pve_opponent": deck.is_pve_opponent,
        "strategy": script.get("strategy", "rush"),
        "draw_mode": draw_mode,
        "starting_hand_size": script.get(
            "starting_hand_size", _default_ai_starting_hand_size(deck.title)
        ),
        "draw_order": (
            _normalize_draw_order(script.get("draw_order", []))
            if draw_mode == "ordered"
            else []
        ),
        "ai_player": {
            "id": deck.ai_player.id,
            "name": deck.ai_player.name,
        },
        "hero": {
            "id": deck.hero.id,
            "slug": deck.hero.slug,
            "name": deck.hero.name,
            "health": deck.hero.health,
        },
        "card_count": deck.deck_size,
        "cards": [_ai_deck_card_payload(deck_card) for deck_card in deck_cards],
        "created_at": deck.created_at,
        "updated_at": deck.updated_at,
    }


def _parse_bool(value, default=False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _strategy_from_payload(payload, current: str = "rush") -> str:
    strategy = payload.get("strategy", current) or "rush"
    if strategy not in AI_DECK_STRATEGIES:
        raise ValueError(f'Unknown AI strategy "{strategy}".')
    return strategy


def _draw_mode_from_payload(payload, current: str = "shuffle") -> str:
    draw_mode = payload.get("draw_mode", current) or "shuffle"
    if draw_mode not in AI_DECK_DRAW_MODES:
        raise ValueError(f'Unknown AI deck draw mode "{draw_mode}".')
    return draw_mode


def _starting_hand_size_from_payload(title, payload, current=None) -> int:
    default = _default_ai_starting_hand_size(title) if current is None else current
    raw_value = payload.get("starting_hand_size", default)
    try:
        size = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError("starting_hand_size must be a number.") from exc
    if size < 0:
        raise ValueError("starting_hand_size cannot be negative.")
    return size


def _normalize_draw_order(raw_order) -> list[int]:
    if raw_order in (None, ""):
        return []
    if not isinstance(raw_order, list):
        raise ValueError("draw_order must be a list.")

    draw_order = []
    for item in raw_order:
        raw_card_id = item.get("card_id") if isinstance(item, dict) else item
        try:
            card_id = int(raw_card_id)
        except (TypeError, ValueError) as exc:
            raise ValueError("Each draw_order entry needs a card_id.") from exc
        draw_order.append(card_id)
    return draw_order


def _expanded_card_ids_from_counts(card_counts) -> list[int]:
    draw_order = []
    for card, count in card_counts:
        draw_order.extend([card.id] * count)
    return draw_order


def _hero_from_payload(title, payload, current=None):
    hero_id = payload.get("hero_id")
    if hero_id in (None, ""):
        if current is not None:
            return current
        raise ValueError("Hero is required.")
    return HeroTemplate.objects.get(id=hero_id, title=title, is_latest=True)


def _cards_payload_from_request(payload):
    if "cards" not in payload:
        return None
    cards = payload.get("cards")
    if not isinstance(cards, list):
        raise ValueError("cards must be a list.")
    return cards


def _validated_ai_deck_cards(deck, cards_payload):
    if cards_payload is None:
        deck_cards = (
            DeckCard.objects.filter(deck=deck)
            .select_related("card")
            .prefetch_related("card__allowed_heroes", "card__cardtrait_set")
        )
        card_counts = [(deck_card.card, deck_card.count) for deck_card in deck_cards]
    else:
        seen_card_ids = set()
        card_counts = []
        requested_ids = []
        normalized_items = []

        for item in cards_payload:
            if not isinstance(item, dict):
                raise ValueError("Each card entry must be an object.")
            card_id = item.get("card_id")
            count = item.get("count")
            try:
                card_id = int(card_id)
                count = int(count)
            except (TypeError, ValueError) as exc:
                raise ValueError("Each card entry needs card_id and count.") from exc
            if card_id in seen_card_ids:
                raise ValueError("Duplicate card entries are not allowed.")
            seen_card_ids.add(card_id)
            requested_ids.append(card_id)
            normalized_items.append((card_id, count))

        cards_by_id = {
            card.id: card
            for card in CardTemplate.objects.filter(
                title=deck.title,
                id__in=requested_ids,
                is_latest=True,
            ).prefetch_related("allowed_heroes", "cardtrait_set")
        }
        missing_ids = sorted(set(requested_ids) - set(cards_by_id))
        if missing_ids:
            raise ValueError(f"Card(s) not found: {', '.join(map(str, missing_ids))}")

        card_counts = [
            (cards_by_id[card_id], count) for card_id, count in normalized_items
        ]

    for card, count in card_counts:
        if count < 1:
            raise ValueError("Card counts must be at least 1.")

        card_error = validate_card_for_deck(deck, card)
        if card_error:
            raise ValueError(card_error)

    return card_counts


def _validated_ai_deck_draw_order(deck, draw_order):
    if not draw_order:
        return []

    cards_by_id = {
        card.id: card
        for card in CardTemplate.objects.filter(
            title=deck.title,
            id__in=set(draw_order),
            is_latest=True,
        ).prefetch_related("allowed_heroes", "cardtrait_set")
    }
    missing_ids = sorted(set(draw_order) - set(cards_by_id))
    if missing_ids:
        raise ValueError(f"Card(s) not found: {', '.join(map(str, missing_ids))}")

    counts_by_card_id = {}
    for card_id in draw_order:
        card = cards_by_id[card_id]
        card_error = validate_card_for_deck(deck, card)
        if card_error:
            raise ValueError(card_error)
        counts_by_card_id[card_id] = counts_by_card_id.get(card_id, 0) + 1

    return [
        (cards_by_id[card_id], count) for card_id, count in counts_by_card_id.items()
    ]


def _ai_deck_script_and_cards_from_payload(
    title,
    deck,
    payload,
    current_script=None,
    current_cards_payload=None,
):
    current_script = dict(current_script or {})
    strategy = _strategy_from_payload(
        payload, current=current_script.get("strategy", "rush")
    )
    draw_mode = _draw_mode_from_payload(
        payload, current=current_script.get("draw_mode", "shuffle")
    )
    starting_hand_size = _starting_hand_size_from_payload(
        title,
        payload,
        current=current_script.get(
            "starting_hand_size", _default_ai_starting_hand_size(title)
        ),
    )

    script = {
        "strategy": strategy,
        "draw_mode": draw_mode,
        "starting_hand_size": starting_hand_size,
    }

    if draw_mode == "ordered":
        if "draw_order" in payload:
            draw_order = _normalize_draw_order(payload.get("draw_order"))
            card_counts = _validated_ai_deck_draw_order(deck, draw_order)
        elif (
            current_cards_payload is None
            and current_script.get("draw_order") is not None
        ):
            draw_order = _normalize_draw_order(current_script.get("draw_order"))
            card_counts = _validated_ai_deck_draw_order(deck, draw_order)
        else:
            card_counts = _validated_ai_deck_cards(deck, current_cards_payload)
            draw_order = _expanded_card_ids_from_counts(card_counts)

        if starting_hand_size > len(draw_order):
            raise ValueError("starting_hand_size cannot exceed the ordered deck size.")
        script["draw_order"] = draw_order
        return script, card_counts

    card_counts = _validated_ai_deck_cards(deck, current_cards_payload)
    return script, card_counts


def _replace_ai_deck_cards(deck, card_counts):
    seen_card_ids = set()
    for card, count in card_counts:
        DeckCard.objects.update_or_create(
            deck=deck,
            card=card,
            defaults={"count": count},
        )
        seen_card_ids.add(card.id)

    DeckCard.objects.filter(deck=deck).exclude(card_id__in=seen_card_ids).delete()


def _assert_ai_deck_name_available(ai_player, name: str, deck_id=None) -> None:
    existing = Deck.objects.filter(
        ai_player=ai_player,
        name=name,
        archived_at__isnull=True,
    )
    if deck_id is not None:
        existing = existing.exclude(id=deck_id)
    if existing.exists():
        raise ValueError("An active AI deck with this name already exists.")


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


@api_view(["GET"])
@permission_classes([AllowAny])
def title_by_slug(request, slug):
    """Get the latest version of a title by its slug."""
    title = get_title_or_403(slug, request.user)

    serializer = TitleSerializer(title)
    data = serializer.data

    # Add edit permission info if user is authenticated
    if request.user and request.user.is_authenticated:
        data["can_edit"] = title.can_be_edited_by(request.user)
    else:
        data["can_edit"] = False

    return Response(data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_card(request, title_slug):
    """Create a new card for a title."""
    # Get the title (latest version) or return 404
    title = get_object_or_404(Title, slug=title_slug, is_latest=True)

    # Check if user has permission to edit this title
    if not title.can_be_edited_by(request.user):
        return Response(
            {"error": "You do not have permission to edit this title"},
            status=status.HTTP_403_FORBIDDEN,
        )

    yaml_data = request.data.get("yaml_definition")
    if not yaml_data:
        return Response(
            {"error": "yaml_definition is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    # Get and validate slug
    slug = request.data.get("slug", "").strip()
    if not slug:
        return Response(
            {"error": "slug is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    # Validate slug format
    import re

    if not re.match(r"^[a-z0-9\-_]+$", slug):
        return Response(
            {
                "error": (
                    "Slug can only contain lowercase letters, numbers, hyphens, "
                    "and underscores"
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(slug) < 2:
        return Response(
            {"error": "Slug must be at least 2 characters long"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(slug) > 50:
        return Response(
            {"error": "Slug must be no more than 50 characters long"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Check if slug already exists in this title
    if CardTemplate.objects.filter(title=title, slug=slug).exists():
        return Response(
            {"error": f'A card with slug "{slug}" already exists in this title'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        with transaction.atomic():
            # Create new card using YAML data and specified slug
            serializer = CardTemplateSerializer()
            new_card = serializer.create_from_yaml(title, yaml_data, slug=slug)

            response_serializer = CardTemplateSerializer(new_card)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def card_detail(request, title_slug, card_slug):
    """Get or update a specific card by title and card slug."""
    # Get the title (latest version) or return 404
    title = get_object_or_404(Title, slug=title_slug, is_latest=True)

    # Check if user has permission to edit this title
    if not title.can_be_edited_by(request.user):
        return Response(
            {"error": "You do not have permission to edit this title"},
            status=status.HTTP_403_FORBIDDEN,
        )

    # Get the card (latest version) or return 404
    card = get_object_or_404(CardTemplate, title=title, slug=card_slug, is_latest=True)

    if request.method == "GET":
        serializer = CardTemplateSerializer(card)
        return Response(serializer.data)

    elif request.method == "PUT":
        yaml_data = request.data.get("yaml_definition")
        bump_version = request.data.get("bump_version", False)

        if not yaml_data:
            return Response(
                {"error": "yaml_definition is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                if bump_version:
                    # Create new version using the version bump logic
                    updated_card = bump_card_version(card, yaml_data)
                else:
                    # Update the existing card in place
                    serializer = CardTemplateSerializer()
                    updated_card = serializer.update_from_yaml(card, yaml_data)

                serializer = CardTemplateSerializer(updated_card)
                return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "DELETE":
        try:
            with transaction.atomic():
                # Soft delete by setting is_latest=False
                card.is_latest = False
                card.save(update_fields=["is_latest"])

                return Response(
                    {"message": f'Card "{card.name}" has been deleted'},
                    status=status.HTTP_200_OK,
                )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def card_yaml(request, title_slug, card_slug):
    """
    Get a card's YAML representation in the ingestion format.

    Returns the card as YAML that can be copied and used with the ingestion endpoint.
    """
    # Get the title (latest version) or return 404
    title = get_object_or_404(Title, slug=title_slug, is_latest=True)

    # Check if user has permission to view this title
    if not title.can_be_viewed_by(request.user):
        return Response(
            {"error": "You do not have permission to view this title"},
            status=status.HTTP_403_FORBIDDEN,
        )

    # Get the card (latest version) or return 404
    card = get_object_or_404(CardTemplate, title=title, slug=card_slug, is_latest=True)

    # Convert CardTemplate to Card schema format
    card_schema = card_template_to_schema(card)

    # Serialize to YAML (exclude None values and use the schema's dict representation)
    yaml_content = yaml.dump(
        card_schema.model_dump(exclude_none=True, exclude_defaults=False),
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )

    return Response(
        {
            "yaml": yaml_content,
            "card": {"slug": card.slug, "name": card.name, "card_type": card.card_type},
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def hero_yaml(request, title_slug, hero_slug):
    """
    Get a hero's YAML representation in the ingestion format.

    Returns the hero as YAML that can be copied and used with the ingestion endpoint.
    """
    title = get_object_or_404(Title, slug=title_slug, is_latest=True)

    if not title.can_be_viewed_by(request.user):
        return Response(
            {"error": "You do not have permission to view this title"},
            status=status.HTTP_403_FORBIDDEN,
        )

    hero = get_object_or_404(HeroTemplate, title=title, slug=hero_slug, is_latest=True)
    hero_schema = hero_template_to_schema(hero)

    yaml_content = yaml.dump(
        hero_schema.model_dump(exclude_none=True, exclude_defaults=False),
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )

    return Response(
        {
            "yaml": yaml_content,
            "hero": {"slug": hero.slug, "name": hero.name},
        },
        status=status.HTTP_200_OK,
    )


def card_template_to_schema(card: CardTemplate) -> Card:
    """
    Convert a CardTemplate database model to the Card Pydantic schema.

    This ensures the output matches exactly what the ingestion endpoint expects.
    """
    # Build traits list from CardTrait relations
    traits = []
    for card_trait in card.cardtrait_set.all():
        # The trait data contains the full trait definition including type and actions
        trait_data = {"type": card_trait.trait_slug}
        if card_trait.data:
            # Merge in additional trait data (actions, etc.)
            # But exclude 'type' from data since we set it explicitly
            for key, value in card_trait.data.items():
                if key != "type":
                    trait_data[key] = value
        traits.append(trait_data)

    # Build the Card schema
    return Card(
        slug=card.slug,
        card_type=card.card_type,
        name=card.name,
        description=card.description or "",
        cost=card.cost or 0,
        attack=card.attack or 0,
        health=card.health or 0,
        traits=traits,
        faction=card.faction.slug if card.faction else None,
        spec=card.spec or {},
        tags=list(card.tags.values_list("slug", flat=True).order_by("slug")),
        art_url=card.art_url if hasattr(card, "art_url") and card.art_url else None,
        is_collectible=card.is_collectible,
        hero_slugs=list(card.allowed_heroes.values_list("slug", flat=True)),
    )


def hero_template_to_schema(hero: HeroTemplate) -> Hero:
    """
    Convert a HeroTemplate database model to the Hero Pydantic schema.

    This ensures the output matches the ingestion endpoint's expected format.
    """
    return Hero(
        slug=hero.slug,
        name=hero.name,
        description=hero.description or "",
        health=hero.health,
        hero_power=hero.hero_power or {},
        faction=hero.faction.slug if hero.faction else None,
        spec=hero.spec or {},
    )


def bump_card_version(card: CardTemplate, yaml_data: str) -> CardTemplate:
    """Create a new version of a card with updated data from YAML."""
    # Lock the current latest row
    prev = CardTemplate.objects.select_for_update().get(
        title=card.title, slug=card.slug, is_latest=True
    )

    # Mark it no longer latest
    prev.is_latest = False
    prev.save(update_fields=["is_latest"])

    # Create new version with copied data
    new_card = CardTemplate.objects.create(
        title=prev.title,
        slug=prev.slug,
        name=prev.name,
        description=prev.description,
        version=prev.version + 1,
        is_latest=True,
        card_type=prev.card_type,
        cost=prev.cost,
        attack=prev.attack,
        health=prev.health,
        spec=prev.spec,
        faction=prev.faction,
        is_collectible=prev.is_collectible,
    )

    # Copy tags
    new_card.tags.set(prev.tags.all())

    # Copy traits
    for card_trait in prev.cardtrait_set.all():
        CardTrait.objects.create(
            card=new_card, trait_slug=card_trait.trait_slug, data=card_trait.data
        )

    # Update with YAML data
    serializer = CardTemplateSerializer()
    updated_card = serializer.update_from_yaml(new_card, yaml_data)

    return updated_card


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ingest_yaml(request, title_slug):
    """
    Ingest YAML manifest to create/update cards and heroes.

    Accepts a YAML string containing one or more resource definitions.
    Returns a list of created/updated resources with their types and IDs.
    """
    # Get the title (latest version) or return 404
    title = get_object_or_404(Title, slug=title_slug, is_latest=True)

    # Check if user has permission to edit this title
    if not title.can_be_edited_by(request.user):
        return Response(
            {"error": "You do not have permission to edit this title"},
            status=status.HTTP_403_FORBIDDEN,
        )

    yaml_content = request.data.get("yaml_content")
    if not yaml_content:
        return Response(
            {"error": "yaml_content is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        with transaction.atomic():
            service = TitleService(title)
            ingested_resources = service.ingest_yaml(yaml_content)

            # Convert IngestedResource Pydantic models to dictionaries for JSON response
            results = [res.model_dump() for res in ingested_resources]

            return Response(
                {
                    "success": True,
                    "message": f"Successfully processed {len(results)} resource(s)",
                    "resources": results,
                },
                status=status.HTTP_200_OK,
            )

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated])
def title_config(request, title_slug):
    """
    Read or update a title's game configuration.
    """
    title = get_object_or_404(Title, slug=title_slug, is_latest=True)

    if not title.can_be_edited_by(request.user):
        return Response(
            {"error": "You do not have permission to edit this title"},
            status=status.HTTP_403_FORBIDDEN,
        )

    if request.method == "GET":
        title_config = _title_config_from_data(title.config)
        return Response(
            {
                "title": {"slug": title.slug, "name": title.name},
                "config": title_config.model_dump(exclude={"type"}),
            },
            status=status.HTTP_200_OK,
        )

    config_payload = request.data.get("config", request.data)
    if not isinstance(config_payload, dict):
        return Response(
            {"error": "config must be an object"}, status=status.HTTP_400_BAD_REQUEST
        )

    if config_payload.get("side_b_compensation") == "":
        config_payload = {**config_payload, "side_b_compensation": None}

    try:
        updated_config = TitleConfig.model_validate(
            {
                **_title_config_from_data(title.config).model_dump(),
                **config_payload,
            }
        )
    except ValidationError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    validation_error = _validate_title_config(updated_config)
    if validation_error:
        return Response({"error": validation_error}, status=status.HTTP_400_BAD_REQUEST)

    title.config = updated_config.model_dump(exclude={"type"}, exclude_none=True)
    title.save(update_fields=["config"])

    return Response(
        {
            "title": {"slug": title.slug, "name": title.name},
            "config": updated_config.model_dump(exclude={"type"}),
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def title_content_config(request, title_slug):
    """
    Read builder-facing hero and card configuration for a title.
    """
    title = get_object_or_404(Title, slug=title_slug, is_latest=True)

    if not title.can_be_edited_by(request.user):
        return Response(
            {"error": "You do not have permission to edit this title"},
            status=status.HTTP_403_FORBIDDEN,
        )

    heroes = (
        HeroTemplate.objects.filter(title=title, is_latest=True)
        .select_related("title", "faction")
        .order_by("name")
    )
    cards = (
        CardTemplate.objects.filter(title=title, is_latest=True)
        .select_related("title", "faction")
        .prefetch_related("cardtrait_set", "allowed_heroes")
        .order_by("cost", "card_type", "attack", "health", "name")
    )

    return Response(
        {
            "title": {"slug": title.slug, "name": title.name},
            "heroes": HeroTemplateSerializer(heroes, many=True).data,
            "cards": CardTemplateSerializer(cards, many=True).data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def title_ai_decks(request, title_slug):
    """List or create editable AI decks for a title."""
    title = get_object_or_404(Title, slug=title_slug, is_latest=True)

    if not title.can_be_edited_by(request.user):
        return Response(
            {"error": "You do not have permission to edit this title"},
            status=status.HTTP_403_FORBIDDEN,
        )

    if request.method == "GET":
        decks = _ai_deck_queryset(title)
        return Response(
            {
                "title": {"slug": title.slug, "name": title.name},
                "config": _deck_config_payload(title),
                "decks": [_serialize_ai_deck(deck) for deck in decks],
            },
            status=status.HTTP_200_OK,
        )

    try:
        with transaction.atomic():
            name = (request.data.get("name") or "").strip()
            if not name:
                raise ValueError("Name is required.")

            ai_player = TitleService(title).get_default_ai_player()
            _assert_ai_deck_name_available(ai_player, name)
            hero = _hero_from_payload(title, request.data)

            deck = Deck(
                ai_player=ai_player,
                title=title,
                name=name,
                description=(request.data.get("description") or "").strip(),
                hero=hero,
                is_pve_opponent=_parse_bool(
                    request.data.get("is_pve_opponent"), default=False
                ),
            )
            script, card_counts = _ai_deck_script_and_cards_from_payload(
                title,
                deck,
                request.data,
                current_cards_payload=_cards_payload_from_request(request.data) or [],
            )
            deck.script = script
            deck.save()
            _replace_ai_deck_cards(deck, card_counts)

            return Response(_serialize_ai_deck(deck), status=status.HTTP_201_CREATED)
    except Exception as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def title_ai_deck_detail(request, title_slug, deck_id):
    """Read, update, or archive an editable AI deck for a title."""
    title = get_object_or_404(Title, slug=title_slug, is_latest=True)

    if not title.can_be_edited_by(request.user):
        return Response(
            {"error": "You do not have permission to edit this title"},
            status=status.HTTP_403_FORBIDDEN,
        )

    deck = get_object_or_404(_ai_deck_queryset(title), id=deck_id)

    if request.method == "GET":
        return Response(_serialize_ai_deck(deck), status=status.HTTP_200_OK)

    if request.method == "DELETE":
        deck.archive()
        return Response(status=status.HTTP_204_NO_CONTENT)

    try:
        with transaction.atomic():
            if "name" in request.data:
                deck.name = (request.data.get("name") or "").strip()
                if not deck.name:
                    raise ValueError("Name is required.")
                _assert_ai_deck_name_available(
                    deck.ai_player, deck.name, deck_id=deck.id
                )

            if "description" in request.data:
                deck.description = (request.data.get("description") or "").strip()

            if "hero_id" in request.data:
                deck.hero = _hero_from_payload(title, request.data, current=deck.hero)

            if "is_pve_opponent" in request.data:
                deck.is_pve_opponent = _parse_bool(request.data.get("is_pve_opponent"))

            cards_payload = _cards_payload_from_request(request.data)
            script, card_counts = _ai_deck_script_and_cards_from_payload(
                title,
                deck,
                request.data,
                current_script=deck.script or {},
                current_cards_payload=cards_payload,
            )
            deck.script = script

            deck.save(
                update_fields=[
                    "name",
                    "description",
                    "hero",
                    "is_pve_opponent",
                    "script",
                    "updated_at",
                ]
            )
            if (
                cards_payload is not None
                or "draw_order" in request.data
                or "draw_mode" in request.data
            ):
                _replace_ai_deck_cards(deck, card_counts)

            return Response(_serialize_ai_deck(deck), status=status.HTTP_200_OK)
    except Exception as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def title_snapshot(request, title_slug):
    """
    Export or import a full title snapshot manifest.

    Snapshot YAML is intentionally slug-based so it can move between
    environments where database IDs differ.
    """
    title = get_object_or_404(Title, slug=title_slug, is_latest=True)

    if not title.can_be_edited_by(request.user):
        return Response(
            {"error": "You do not have permission to edit this title"},
            status=status.HTTP_403_FORBIDDEN,
        )

    service = TitleService(title)

    if request.method == "GET":
        return Response(
            {
                "yaml": service.export_snapshot_yaml(),
                "title": {"slug": title.slug, "name": title.name},
                "counts": service.export_snapshot_counts(),
            },
            status=status.HTTP_200_OK,
        )

    yaml_content = request.data.get("yaml_content")
    if not yaml_content:
        return Response(
            {"error": "yaml_content is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    replace_missing = bool(
        request.data.get("replace_missing", request.data.get("replace", False))
    )

    try:
        with transaction.atomic():
            ingested_resources, removed_resources = service.import_snapshot_yaml(
                yaml_content, replace_missing=replace_missing
            )
            results = [res.model_dump() for res in ingested_resources]

            return Response(
                {
                    "success": True,
                    "message": f"Successfully processed {len(results)} resource(s)",
                    "resources": results,
                    "removed": removed_resources,
                    "replace_missing": replace_missing,
                },
                status=status.HTTP_200_OK,
            )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def title_config_yaml(request, title_slug):
    """
    Get a title's configuration YAML representation in the ingestion format.

    Returns the title config as YAML that can be copied and used with the ingestion
    endpoint.
    """
    # Get the title (latest version) or return 404
    title = get_object_or_404(Title, slug=title_slug, is_latest=True)

    # Check if user has permission to view this title
    if not title.can_be_viewed_by(request.user):
        return Response(
            {"error": "You do not have permission to view this title"},
            status=status.HTTP_403_FORBIDDEN,
        )

    title_config = _title_config_from_data(title.config)

    # Serialize to YAML (exclude None values and use the schema's dict representation)
    yaml_content = yaml.dump(
        title_config.model_dump(exclude_none=True, exclude_defaults=False),
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )

    return Response(
        {"yaml": yaml_content, "title": {"slug": title.slug, "name": title.name}},
        status=status.HTTP_200_OK,
    )
