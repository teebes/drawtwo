"""Provision title-specific starter decks for newly created users."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from functools import lru_cache
from pathlib import Path

import yaml
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.builder.models import HeroTemplate, Title
from apps.collection.compositions import (
    ensure_deck_revision,
    parse_composition_code,
    resolve_composition_code,
)
from apps.collection.models import (
    Deck,
    DeckCard,
    StarterDeckProgram,
    StarterDeckProvisioning,
    UserTitleDeckPreference,
)
from apps.collection.validation import validate_deck_for_play

STARTER_DECK_MANIFEST_DIR = Path(__file__).with_name("starter_deck_manifests")
STARTER_DECK_RETRY_BACKOFF = timedelta(seconds=30)
logger = logging.getLogger(__name__)


class StarterDeckProvisioningError(ValueError):
    """A configured starter deck cannot be safely provisioned."""


@dataclass(frozen=True)
class StarterDeckDefinition:
    title_slug: str
    name: str
    description: str
    hero_slug: str
    composition_code: str


def _required_string(value, *, field: str, path: Path) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StarterDeckProvisioningError(
            f'{path}: "{field}" must be a non-empty string'
        )
    return value.strip()


def _load_starter_deck_definition(path: Path) -> StarterDeckDefinition:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise StarterDeckProvisioningError(f"{path}: manifest must be a mapping")
    if payload.get("version") != 1:
        raise StarterDeckProvisioningError(
            f'{path}: unsupported manifest version {payload.get("version")!r}'
        )

    deck = payload.get("deck")
    if not isinstance(deck, dict):
        raise StarterDeckProvisioningError(
            f'{path}: manifest must contain a "deck" mapping'
        )

    title_slug = _required_string(deck.get("title"), field="deck.title", path=path)
    name = _required_string(deck.get("name"), field="deck.name", path=path)
    hero_slug = _required_string(deck.get("hero"), field="deck.hero", path=path)
    composition_code = _required_string(
        deck.get("composition"), field="deck.composition", path=path
    )
    description = deck.get("description", "")
    if not isinstance(description, str):
        raise StarterDeckProvisioningError(
            f'{path}: "deck.description" must be a string'
        )
    if len(name) > Deck._meta.get_field("name").max_length:
        raise StarterDeckProvisioningError(
            f'{path}: "deck.name" exceeds the model limit'
        )

    try:
        parse_composition_code(composition_code)
    except ValueError as exc:
        raise StarterDeckProvisioningError(
            f'{path}: invalid "deck.composition": {exc}'
        ) from exc

    return StarterDeckDefinition(
        title_slug=title_slug,
        name=name,
        description=description,
        hero_slug=hero_slug,
        composition_code=composition_code,
    )


@lru_cache(maxsize=1)
def load_starter_deck_definitions() -> tuple[StarterDeckDefinition, ...]:
    """Load and validate all versioned starter-deck manifests."""

    definitions = tuple(
        _load_starter_deck_definition(path)
        for path in sorted(STARTER_DECK_MANIFEST_DIR.glob("*.yaml"))
    )
    if not definitions:
        raise StarterDeckProvisioningError(
            f"No starter-deck manifests found in {STARTER_DECK_MANIFEST_DIR}"
        )
    title_slugs = [definition.title_slug for definition in definitions]
    if len(title_slugs) != len(set(title_slugs)):
        raise StarterDeckProvisioningError(
            "Only one starter-deck manifest may be configured per title"
        )
    return definitions


@transaction.atomic
def provision_starter_deck_for_user(
    user,
    definition: StarterDeckDefinition,
    provisioning: StarterDeckProvisioning,
) -> tuple[Deck | None, bool]:
    """Create one user's independent starter-deck copy, idempotently."""

    user_model = get_user_model()
    locked_user = (
        user_model.objects.select_for_update().only("pk", "deleted_at").get(pk=user.pk)
    )
    locked_provisioning = StarterDeckProvisioning.objects.select_for_update().get(
        pk=provisioning.pk,
        user=user,
    )
    if locked_provisioning.completed_at is not None:
        return locked_provisioning.deck, False
    if locked_user.deleted_at is not None:
        now = timezone.now()
        locked_provisioning.last_attempted_at = now
        locked_provisioning.last_dispatched_at = None
        locked_provisioning.completed_at = now
        locked_provisioning.last_error = "Account deleted before provisioning"
        locked_provisioning.save(
            update_fields=[
                "last_attempted_at",
                "last_dispatched_at",
                "completed_at",
                "last_error",
                "updated_at",
            ]
        )
        return None, False

    title = Title.objects.filter(
        slug=definition.title_slug,
        is_latest=True,
        status=Title.STATUS_PUBLISHED,
    ).first()
    if title is None:
        return None, False

    if Deck.objects.active().filter(user=user, name=definition.name).exists():
        raise StarterDeckProvisioningError(
            f'User {user.pk} already has an active deck named "{definition.name}"'
        )

    try:
        hero = HeroTemplate.objects.get(
            title=title,
            slug=definition.hero_slug,
            is_latest=True,
        )
        composition = resolve_composition_code(
            title,
            definition.composition_code,
        )
    except (HeroTemplate.DoesNotExist, ValueError) as exc:
        raise StarterDeckProvisioningError(
            f'Cannot resolve starter deck for title "{title.slug}": {exc}'
        ) from exc

    retired_slugs = sorted(
        card.slug for card in composition.cards if not card.is_latest
    )
    if retired_slugs:
        raise StarterDeckProvisioningError(
            f'Starter deck for title "{title.slug}" references retired card(s): '
            f'{", ".join(retired_slugs)}'
        )

    deck = Deck.objects.create(
        user=user,
        title=title,
        name=definition.name,
        description=definition.description,
        hero=hero,
    )
    cards_by_slug = {card.slug: card for card in composition.cards}
    DeckCard.objects.bulk_create(
        [
            DeckCard(
                deck=deck,
                card=cards_by_slug[slug],
                count=count,
            )
            for slug, count in composition.card_counts.items()
        ]
    )
    ensure_deck_revision(deck, source="create")

    validation_error = validate_deck_for_play(deck)
    if validation_error:
        raise StarterDeckProvisioningError(
            f'Invalid starter deck for title "{title.slug}": {validation_error}'
        )

    preference, _ = UserTitleDeckPreference.objects.get_or_create(
        user=user,
        title=title,
        defaults={"last_used_deck": deck},
    )
    if preference.last_used_deck_id is None:
        preference.last_used_deck = deck
        preference.save(update_fields=["last_used_deck", "updated_at"])

    now = timezone.now()
    locked_provisioning.deck = deck
    locked_provisioning.last_attempted_at = now
    locked_provisioning.last_dispatched_at = None
    locked_provisioning.completed_at = now
    locked_provisioning.last_error = ""
    locked_provisioning.save(
        update_fields=[
            "deck",
            "last_attempted_at",
            "last_dispatched_at",
            "completed_at",
            "last_error",
            "updated_at",
        ]
    )

    return deck, True


def provision_starter_decks_for_user(
    user,
    *,
    respect_backoff: bool = False,
) -> list[Deck]:
    """Promise and attempt every configured starter deck for a new user."""

    definitions = load_starter_deck_definitions()
    program_cutoffs = dict(
        StarterDeckProgram.objects.filter(
            title_slug__in=[definition.title_slug for definition in definitions]
        ).values_list("title_slug", "eligible_after")
    )
    missing_programs = sorted(
        definition.title_slug
        for definition in definitions
        if definition.title_slug not in program_cutoffs
    )
    if missing_programs:
        logger.error(
            "Starter-deck program cutoff is missing for title(s): %s",
            ", ".join(missing_programs),
        )
    definitions = tuple(
        definition
        for definition in definitions
        if definition.title_slug in program_cutoffs
        and user.created_at > program_cutoffs[definition.title_slug]
    )
    if not definitions:
        return []
    for definition in definitions:
        StarterDeckProvisioning.objects.get_or_create(
            user=user,
            title_slug=definition.title_slug,
        )
    return retry_pending_starter_decks_for_user(
        user,
        definitions=definitions,
        respect_backoff=respect_backoff,
    )


@transaction.atomic
def _claim_pending_provisioning(
    provisioning: StarterDeckProvisioning,
    *,
    respect_backoff: bool,
) -> StarterDeckProvisioning | None:
    """Serialize retries and claim one pending grant before doing any work."""

    locked = StarterDeckProvisioning.objects.select_for_update().get(
        pk=provisioning.pk,
    )
    if locked.completed_at is not None:
        return None

    now = timezone.now()
    if (
        respect_backoff
        and locked.last_attempted_at is not None
        and locked.last_attempted_at > now - STARTER_DECK_RETRY_BACKOFF
    ):
        return None

    locked.last_attempted_at = now
    locked.last_dispatched_at = None
    locked.save(
        update_fields=[
            "last_attempted_at",
            "last_dispatched_at",
            "updated_at",
        ]
    )
    return locked


def _record_failure(
    provisioning: StarterDeckProvisioning,
    *,
    error: str,
) -> None:
    now = timezone.now()
    updates = {
        "last_error": error,
        "updated_at": now,
    }
    StarterDeckProvisioning.objects.filter(
        pk=provisioning.pk,
        completed_at__isnull=True,
    ).update(**updates)


def retry_pending_starter_decks_for_user(
    user,
    *,
    definitions: tuple[StarterDeckDefinition, ...] | None = None,
    respect_backoff: bool = False,
) -> list[Deck]:
    """Retry only starter decks promised to this user at account creation."""

    if definitions is None:
        definitions = load_starter_deck_definitions()
    definitions_by_title = {
        definition.title_slug: definition for definition in definitions
    }

    pending = StarterDeckProvisioning.objects.filter(
        user=user,
        completed_at__isnull=True,
    )
    if respect_backoff:
        retry_before = timezone.now() - STARTER_DECK_RETRY_BACKOFF
        pending = pending.filter(
            Q(last_attempted_at__isnull=True) | Q(last_attempted_at__lte=retry_before)
        )

    provisioned = []
    for provisioning in pending.order_by("title_slug"):
        provisioning = _claim_pending_provisioning(
            provisioning,
            respect_backoff=respect_backoff,
        )
        if provisioning is None:
            continue

        definition = definitions_by_title.get(provisioning.title_slug)
        if definition is None:
            _record_failure(
                provisioning,
                error="Starter-deck manifest is unavailable",
            )
            continue

        try:
            deck, created = provision_starter_deck_for_user(
                user,
                definition,
                provisioning,
            )
        except Exception as exc:
            _record_failure(provisioning, error=str(exc))
            logger.exception(
                "Could not provision %s starter deck for user %s",
                provisioning.title_slug,
                user.pk,
            )
            continue

        if deck is None:
            _record_failure(
                provisioning,
                error="The latest published title is unavailable",
            )
            continue

        if created:
            provisioned.append(deck)

    return provisioned
