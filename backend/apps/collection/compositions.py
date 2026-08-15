"""Canonical, hero-independent deck composition identities and revisions."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Iterable, Mapping
from urllib.parse import quote

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from apps.builder.models import CardTemplate, Title
from apps.collection.models import Deck, DeckComposition, DeckRevision

COMPOSITION_CODE_VERSION = 1
COMPOSITION_CODE_PREFIX = f"dt{COMPOSITION_CODE_VERSION}"
COMPOSITION_DIGEST_NAMESPACE = f"drawtwo:deck-composition:v{COMPOSITION_CODE_VERSION}"
MAX_COMPOSITION_TOTAL_CARDS = 2_147_483_647
CARD_SLUG_RE = re.compile(r"[-a-zA-Z0-9_]+\Z")
COUNT_RE = re.compile(r"[1-9][0-9]*\Z")


class CompositionCodeError(ValueError):
    """Raised when a portable deck code is invalid for its title."""


@dataclass(frozen=True)
class ResolvedComposition:
    composition: DeckComposition | None
    code: str
    digest: str
    manifest: list[dict[str, str | int]]
    total_cards: int
    card_counts: dict[str, int]
    cards: tuple[CardTemplate, ...]


def canonicalize_card_counts(
    card_counts: Mapping[str, int] | Iterable[tuple[str, int]],
) -> dict[str, int]:
    """Coalesce counts and return a slug-sorted, validated mapping."""

    items = card_counts.items() if isinstance(card_counts, Mapping) else card_counts
    totals: dict[str, int] = {}
    for slug, count in items:
        if not isinstance(slug, str) or not CARD_SLUG_RE.fullmatch(slug):
            raise CompositionCodeError(f'Invalid card slug "{slug}"')
        if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
            raise CompositionCodeError(
                f'Card "{slug}" must have a positive integer count'
            )
        combined_count = totals.get(slug, 0) + count
        if combined_count > MAX_COMPOSITION_TOTAL_CARDS:
            raise CompositionCodeError(f'Card "{slug}" count is too large')
        totals[slug] = combined_count

    if sum(totals.values()) > MAX_COMPOSITION_TOTAL_CARDS:
        raise CompositionCodeError("Deck contains too many cards")

    return dict(sorted(totals.items()))


def encode_composition_code(
    card_counts: Mapping[str, int] | Iterable[tuple[str, int]],
) -> str:
    """Encode a card multiset as a canonical, URL-safe one-line code."""

    canonical = canonicalize_card_counts(card_counts)
    if not canonical:
        return COMPOSITION_CODE_PREFIX
    entries = ".".join(f"{slug}~{count}" for slug, count in canonical.items())
    return f"{COMPOSITION_CODE_PREFIX}.{entries}"


def parse_composition_code(code: str) -> dict[str, int]:
    """Parse a code, rejecting noncanonical aliases and ambiguous input."""

    if not isinstance(code, str):
        raise CompositionCodeError("Deck code must be a string")
    if code == COMPOSITION_CODE_PREFIX:
        return {}
    prefix = f"{COMPOSITION_CODE_PREFIX}."
    if not code.startswith(prefix):
        raise CompositionCodeError(
            f'Deck code must be "{COMPOSITION_CODE_PREFIX}" or start with '
            f'"{prefix}"'
        )

    entries = code[len(prefix) :].split(".")
    if not entries or any(not entry for entry in entries):
        raise CompositionCodeError("Deck code contains an empty card entry")

    card_counts: dict[str, int] = {}
    previous_slug: str | None = None
    for entry in entries:
        if entry.count("~") != 1:
            raise CompositionCodeError(f'Invalid card entry "{entry}"')
        slug, raw_count = entry.split("~", 1)
        if not CARD_SLUG_RE.fullmatch(slug):
            raise CompositionCodeError(f'Invalid card slug "{slug}"')
        if not COUNT_RE.fullmatch(raw_count):
            raise CompositionCodeError(
                f'Card "{slug}" must have an explicit positive count'
            )
        if len(raw_count) > 10:
            raise CompositionCodeError(f'Card "{slug}" count is too large')
        count = int(raw_count)
        if count > MAX_COMPOSITION_TOTAL_CARDS:
            raise CompositionCodeError(f'Card "{slug}" count is too large')
        if previous_slug is not None and slug <= previous_slug:
            raise CompositionCodeError("Card entries must be unique and sorted by slug")
        card_counts[slug] = count
        previous_slug = slug

    if sum(card_counts.values()) > MAX_COMPOSITION_TOTAL_CARDS:
        raise CompositionCodeError("Deck contains too many cards")

    # Keep one canonicality assertion here so future grammar changes cannot
    # accidentally introduce multiple portable strings for one composition.
    if encode_composition_code(card_counts) != code:
        raise CompositionCodeError("Deck code is not canonical")
    return card_counts


def composition_digest(title: Title, code: str) -> str:
    material = f"{COMPOSITION_DIGEST_NAMESPACE}\0{title.slug}\0{code}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _manifest_for(card_counts: Mapping[str, int]) -> list[dict[str, str | int]]:
    return [
        {"slug": slug, "count": count} for slug, count in sorted(card_counts.items())
    ]


def _cards_for_title(
    title: Title, card_counts: Mapping[str, int]
) -> tuple[CardTemplate, ...]:
    """Resolve stable slugs, preferring latest but retaining retired cards."""

    if not card_counts:
        return ()

    candidates = CardTemplate.objects.filter(
        title=title, slug__in=card_counts
    ).order_by("slug", "-is_latest", "-version", "-id")
    cards_by_slug: dict[str, CardTemplate] = {}
    for card in candidates:
        cards_by_slug.setdefault(card.slug, card)

    missing = sorted(set(card_counts) - set(cards_by_slug))
    if missing:
        label = ", ".join(missing)
        raise CompositionCodeError(f"Unknown card slug(s) for {title.slug}: {label}")
    return tuple(cards_by_slug[slug] for slug in sorted(card_counts))


def resolve_composition_code(
    title: Title,
    code: str,
    *,
    create: bool = False,
) -> ResolvedComposition:
    """Resolve a portable code without writing unless explicitly requested."""

    card_counts = parse_composition_code(code)
    cards = _cards_for_title(title, card_counts)
    digest = composition_digest(title, code)
    manifest = _manifest_for(card_counts)
    total_cards = sum(card_counts.values())

    if create:
        composition, _ = get_or_create_composition(title, card_counts)
    else:
        composition = DeckComposition.objects.filter(
            title=title,
            version=COMPOSITION_CODE_VERSION,
            digest=digest,
        ).first()
        if composition is not None:
            _assert_composition_matches(composition, code, manifest, total_cards)

    return ResolvedComposition(
        composition=composition,
        code=code,
        digest=digest,
        manifest=manifest,
        total_cards=total_cards,
        card_counts=card_counts,
        cards=cards,
    )


def _assert_composition_matches(
    composition: DeckComposition,
    code: str,
    manifest: list[dict[str, str | int]],
    total_cards: int,
) -> None:
    if (
        composition.code != code
        or composition.manifest != manifest
        or composition.total_cards != total_cards
    ):
        raise CompositionCodeError(
            "Deck composition digest collision or inconsistent stored manifest"
        )


def get_or_create_composition(
    title: Title,
    card_counts: Mapping[str, int] | Iterable[tuple[str, int]],
) -> tuple[DeckComposition, bool]:
    """Deduplicate a canonical composition within a title."""

    canonical = canonicalize_card_counts(card_counts)
    # Validate that portable compositions cannot silently contain foreign or
    # misspelled slugs. Current DeckCard rows already satisfy this in practice.
    _cards_for_title(title, canonical)
    code = encode_composition_code(canonical)
    digest = composition_digest(title, code)
    manifest = _manifest_for(canonical)
    total_cards = sum(canonical.values())

    composition, created = DeckComposition.objects.get_or_create(
        title=title,
        version=COMPOSITION_CODE_VERSION,
        digest=digest,
        defaults={
            "code": code,
            "manifest": manifest,
            "total_cards": total_cards,
        },
    )
    _assert_composition_matches(composition, code, manifest, total_cards)
    return composition, created


def _deck_card_counts(deck: Deck) -> dict[str, int]:
    return canonicalize_card_counts(
        deck.deckcard_set.select_related("card").values_list("card__slug", "count")
    )


@transaction.atomic
def ensure_deck_revision(
    deck: Deck,
    *,
    source: str = DeckRevision.SOURCE_EDIT,
) -> tuple[DeckRevision, bool]:
    """Make the deck's current immutable revision match its live state."""

    if source not in dict(DeckRevision.SOURCE_CHOICES):
        raise ValueError(f'Unknown deck revision source "{source}"')

    locked_deck = (
        Deck.objects.select_for_update().select_related("title", "hero").get(pk=deck.pk)
    )
    current = (
        DeckRevision.objects.select_related("composition")
        .filter(pk=locked_deck.current_revision_id)
        .first()
    )
    composition, _ = get_or_create_composition(
        locked_deck.title,
        _deck_card_counts(locked_deck),
    )
    if (
        current is not None
        and current.composition_id == composition.id
        and current.hero_slug == locked_deck.hero.slug
    ):
        deck.current_revision = current
        deck.current_revision_id = current.id
        return current, False

    next_sequence = (
        locked_deck.revisions.aggregate(max_sequence=Max("sequence"))["max_sequence"]
        or 0
    ) + 1
    revision = DeckRevision.objects.create(
        deck=locked_deck,
        sequence=next_sequence,
        composition=composition,
        hero_slug=locked_deck.hero.slug,
        hero_name=locked_deck.hero.name,
        source=source,
    )
    now = timezone.now()
    Deck.objects.filter(pk=locked_deck.pk).update(
        current_revision=revision,
        updated_at=now,
    )
    deck.current_revision = revision
    deck.current_revision_id = revision.id
    deck.updated_at = now
    return revision, True


def serialize_deck_composition(
    deck: Deck,
    revision: DeckRevision | None = None,
) -> dict | None:
    """Serialize current identity plus whether it occurred before this revision."""

    revision = revision or deck.current_revision
    if revision is None:
        return None
    composition = revision.composition
    other_occurrences = composition.revisions.exclude(pk=revision.pk).count()
    occurrence_count = other_occurrences + 1
    previously_seen = other_occurrences > 0
    return {
        "id": composition.id,
        "version": composition.version,
        "code": composition.code,
        "digest": composition.digest,
        "manifest": composition.manifest,
        "total_cards": composition.total_cards,
        "url": (
            f"/{quote(deck.title.slug, safe='')}/compositions/"
            f"{quote(composition.code, safe='')}"
        ),
        "is_existing": previously_seen,
        "previously_seen": previously_seen,
        "occurrence_count": occurrence_count,
        "revision": {
            "id": revision.id,
            "sequence": revision.sequence,
            "hero_slug": revision.hero_slug,
            "hero_name": revision.hero_name,
            "source": revision.source,
            "created_at": revision.created_at.isoformat(),
        },
    }


def serialize_resolved_composition(resolved: ResolvedComposition, title: Title) -> dict:
    composition = resolved.composition
    occurrence_count = composition.revisions.count() if composition else 0
    cards_by_slug = {card.slug: card for card in resolved.cards}
    return {
        "id": composition.id if composition else None,
        "version": COMPOSITION_CODE_VERSION,
        "code": resolved.code,
        "digest": resolved.digest,
        "manifest": resolved.manifest,
        "total_cards": resolved.total_cards,
        "url": (
            f"/{quote(title.slug, safe='')}/compositions/"
            f"{quote(resolved.code, safe='')}"
        ),
        "is_existing": composition is not None and occurrence_count > 0,
        "previously_seen": composition is not None and occurrence_count > 0,
        "occurrence_count": occurrence_count,
        "cards": [
            {
                "slug": slug,
                "name": cards_by_slug[slug].name,
                "count": count,
            }
            for slug, count in resolved.card_counts.items()
        ],
    }
