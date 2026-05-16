import hashlib
import json
from typing import Any

from apps.builder.models import CardTemplate, HeroTemplate, Title
from apps.builder.trait_definitions import TRAIT_DEFINITIONS

RULESET_ENGINE_VERSION = "drawtwo-gameplay-v1"


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def compute_ruleset_id(title: Title) -> str:
    """
    Compute a content/rules compatibility id for model datasets and checkpoints.

    This intentionally includes the title config, latest hero/card templates,
    card trait payloads, and the current engine compatibility version. When any
    of those change, future games and training exports get a different id.
    """
    heroes = []
    for hero in (
        HeroTemplate.objects.filter(title=title, is_latest=True)
        .order_by("slug", "version")
        .values("slug", "version", "name", "description", "health", "hero_power")
    ):
        heroes.append(hero)

    cards = []
    for card in (
        CardTemplate.objects.filter(title=title, is_latest=True)
        .prefetch_related("cardtrait_set", "allowed_heroes")
        .order_by("slug", "version")
    ):
        cards.append(
            {
                "slug": card.slug,
                "version": card.version,
                "name": card.name,
                "description": card.description,
                "card_type": card.card_type,
                "cost": card.cost,
                "attack": card.attack,
                "health": card.health,
                "is_collectible": card.is_collectible,
                "allowed_heroes": sorted(
                    card.allowed_heroes.values_list("slug", flat=True)
                ),
                "traits": sorted(
                    [
                        {"slug": trait.trait_slug, "data": trait.data}
                        for trait in card.cardtrait_set.all()
                    ],
                    key=lambda item: item["slug"],
                ),
            }
        )

    payload = {
        "engine": RULESET_ENGINE_VERSION,
        "title": {
            "slug": title.slug,
            "version": title.version,
            "config": title.config or {},
        },
        "heroes": heroes,
        "cards": cards,
        "trait_definitions": TRAIT_DEFINITIONS,
    }
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()
