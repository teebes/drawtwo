from typing import List, Sequence

import yaml
from django.contrib.auth import get_user_model
from pydantic import TypeAdapter

from apps.builder import models as builder_models
from apps.builder.models import CardTemplate, Title
from apps.builder.schemas import (
    Card,
    Deck,
    FactionResource,
    Hero,
    IngestedResource,
    Resource,
    TagResource,
    TitleConfig,
    TitleMetadata,
    TraitOverrideResource,
)
from apps.builder.trait_definitions import validate_trait_slug
from apps.collection import models as collection_models

User = get_user_model()


class TitleService:
    RESOURCE_IMPORT_ORDER = {
        "title": 0,
        "config": 1,
        "faction": 2,
        "tag": 3,
        "trait_override": 4,
        "hero": 5,
        "card": 6,
        "deck": 7,
    }

    @classmethod
    def create_title(cls, author: User, slug: str, name: str):
        title = Title.objects.create(name=name, slug=slug, author=author)
        service = cls(title)
        # No longer need to create trait rows - using trait_definitions.py
        return service

    def __init__(self, title: Title):
        self.title = title

    def ingest_yaml(self, yaml_data: str) -> List[IngestedResource]:
        """
        Ingest YAML data and create/update resources.

        Returns a list of IngestedResource objects describing what was created
        or updated.
        """
        resources = self.parse_yaml_resources(yaml_data)
        return self.ingest_resources(resources)

    def import_snapshot_yaml(
        self, yaml_data: str, replace_missing: bool = False
    ) -> tuple[List[IngestedResource], list[dict]]:
        resources = [
            resource
            for resource in self.parse_yaml_resources(yaml_data)
            if not isinstance(resource, Deck)
        ]
        if replace_missing and not any(
            isinstance(resource, TitleMetadata) for resource in resources
        ):
            raise ValueError("Replace imports require a full title snapshot.")

        ingested = self.ingest_resources(resources)
        removed = self.replace_missing_resources(resources) if replace_missing else []
        return ingested, removed

    def parse_yaml_resources(self, yaml_data: str) -> List[Resource]:
        resource_data = yaml.safe_load(yaml_data)
        if resource_data is None:
            raise ValueError("YAML content is empty.")

        if (
            isinstance(resource_data, dict)
            and resource_data.get("type") == "title_snapshot"
        ):
            resource_data = self._resources_from_snapshot_mapping(resource_data)
        elif not isinstance(resource_data, list):
            resource_data = [resource_data]

        if not isinstance(resource_data, list):
            raise ValueError("YAML content must be a resource or a list of resources.")

        resource_adapter = TypeAdapter(Resource)
        resources: List[Resource] = []
        for resource in resource_data:
            if not isinstance(resource, dict):
                raise ValueError("Each YAML resource must be an object.")
            resources.append(resource_adapter.validate_python(resource))

        return resources

    def ingest_resources(self, resources: Sequence[Resource]) -> List[IngestedResource]:
        ingested: List[IngestedResource] = []
        for resource in sorted(resources, key=self._resource_sort_key):
            result = self.ingest(resource)
            if result:
                ingested.append(result)
        return ingested

    def ingest(self, resource: Resource) -> IngestedResource | None:
        resource_map = {
            Card: self.ingest_card,
            Deck: self.ingest_deck,
            FactionResource: self.ingest_faction,
            Hero: self.ingest_hero,
            TagResource: self.ingest_tag,
            TitleConfig: self.ingest_config,
            TitleMetadata: self.ingest_title,
            TraitOverrideResource: self.ingest_trait_override,
        }
        for resource_type, handler in resource_map.items():
            if isinstance(resource, resource_type):
                return handler(resource)
        return None

    def export_snapshot_yaml(self) -> str:
        resource_payload = [
            resource.model_dump(exclude_none=True, exclude_defaults=False)
            for resource in self.export_snapshot_resources()
        ]
        return yaml.dump(
            resource_payload,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )

    def export_snapshot_counts(self) -> dict:
        resources = self.export_snapshot_resources()
        return {
            "resources": len(resources),
            "cards": sum(isinstance(resource, Card) for resource in resources),
            "heroes": sum(isinstance(resource, Hero) for resource in resources),
        }

    def export_snapshot_resources(self) -> List[Resource]:
        resources: List[Resource] = [
            TitleMetadata(
                slug=self.title.slug,
                name=self.title.name,
                description=self.title.description or "",
            ),
            self._title_config_from_data(self.title.config),
        ]

        resources.extend(
            FactionResource(
                slug=faction.slug,
                name=faction.name,
                description=faction.description or "",
            )
            for faction in builder_models.Faction.objects.filter(
                title=self.title
            ).order_by("slug")
        )
        resources.extend(
            TagResource(
                slug=tag.slug,
                name=tag.name,
                description=tag.description or "",
            )
            for tag in builder_models.Tag.objects.filter(title=self.title).order_by(
                "slug"
            )
        )
        resources.extend(
            TraitOverrideResource(
                slug=trait.slug,
                name=trait.name,
                description=trait.description or "",
            )
            for trait in builder_models.TraitOverride.objects.filter(
                title=self.title
            ).order_by("slug")
        )

        heroes = (
            builder_models.HeroTemplate.objects.filter(title=self.title, is_latest=True)
            .select_related("faction")
            .order_by("slug")
        )
        resources.extend(self.hero_to_resource(hero) for hero in heroes)

        cards = (
            CardTemplate.objects.filter(title=self.title, is_latest=True)
            .select_related("faction")
            .prefetch_related("allowed_heroes", "cardtrait_set", "tags")
            .order_by("slug")
        )
        resources.extend(self.card_to_resource(card) for card in cards)

        return resources

    def get_default_ai_player(self):
        return builder_models.AIPlayer.objects.get_or_create(
            name="Default", difficulty="medium"
        )[0]

    def replace_missing_resources(self, resources: Sequence[Resource]) -> list[dict]:
        resource_slugs = self._resource_slugs(resources)
        removed: list[dict] = []

        for card in CardTemplate.objects.filter(
            title=self.title, is_latest=True
        ).exclude(slug__in=resource_slugs["card"]):
            card.is_latest = False
            card.save(update_fields=["is_latest"])
            removed.append(
                {"resource_type": "card", "slug": card.slug, "name": card.name}
            )

        for hero in builder_models.HeroTemplate.objects.filter(
            title=self.title, is_latest=True
        ).exclude(slug__in=resource_slugs["hero"]):
            hero.is_latest = False
            hero.save(update_fields=["is_latest"])
            removed.append(
                {"resource_type": "hero", "slug": hero.slug, "name": hero.name}
            )

        for trait in builder_models.TraitOverride.objects.filter(
            title=self.title
        ).exclude(slug__in=resource_slugs["trait_override"]):
            removed.append(
                {
                    "resource_type": "trait_override",
                    "slug": trait.slug,
                    "name": trait.name,
                }
            )
            trait.delete()

        self._delete_unreferenced_tag_resources(resource_slugs["tag"], removed)
        self._delete_unreferenced_faction_resources(resource_slugs["faction"], removed)

        return removed

    # Handlers

    def ingest_title(self, resource: TitleMetadata) -> IngestedResource:
        if resource.slug != self.title.slug:
            raise ValueError(
                f'Title snapshot slug "{resource.slug}" does not match '
                f'target title "{self.title.slug}".'
            )

        self.title.name = resource.name
        self.title.description = resource.description or ""
        self.title.save(update_fields=["name", "description"])

        return IngestedResource(
            resource_type="title",
            action="updated",
            id=self.title.id,
            slug=self.title.slug,
            name=self.title.name,
        )

    def ingest_faction(self, resource: FactionResource) -> IngestedResource:
        faction = self._get_resource_by_slug(builder_models.Faction, resource.slug)
        is_new = faction is None
        if is_new:
            faction = builder_models.Faction(title=self.title, slug=resource.slug)

        faction.name = resource.name
        faction.description = resource.description or ""
        faction.save()

        return IngestedResource(
            resource_type="faction",
            action="created" if is_new else "updated",
            id=faction.id,
            slug=faction.slug,
            name=faction.name,
        )

    def ingest_tag(self, resource: TagResource) -> IngestedResource:
        tag = self._get_resource_by_slug(builder_models.Tag, resource.slug)
        is_new = tag is None
        if is_new:
            tag = builder_models.Tag(title=self.title, slug=resource.slug)

        tag.name = resource.name
        tag.description = resource.description or ""
        tag.save()

        return IngestedResource(
            resource_type="tag",
            action="created" if is_new else "updated",
            id=tag.id,
            slug=tag.slug,
            name=tag.name,
        )

    def ingest_trait_override(
        self, resource: TraitOverrideResource
    ) -> IngestedResource:
        if not validate_trait_slug(resource.slug):
            raise ValueError(f"Unknown trait type: '{resource.slug}'")

        trait = self._get_resource_by_slug(builder_models.TraitOverride, resource.slug)
        is_new = trait is None
        if is_new:
            trait = builder_models.TraitOverride(title=self.title, slug=resource.slug)

        trait.name = resource.name
        trait.description = resource.description or ""
        trait.save()

        return IngestedResource(
            resource_type="trait_override",
            action="created" if is_new else "updated",
            id=trait.id,
            slug=trait.slug,
            name=trait.name,
        )

    def ingest_card(self, resource: Card) -> IngestedResource:
        versions = CardTemplate.objects.filter(
            title=self.title, slug=resource.slug, is_latest=True
        )

        is_new = not versions.exists()
        if is_new:
            card_template = CardTemplate.objects.create(
                title=self.title, slug=resource.slug
            )
        else:
            card_template = versions.first()

        card_template.card_type = resource.card_type
        card_template.name = resource.name
        card_template.description = resource.description or ""
        card_template.cost = resource.cost
        card_template.attack = (
            resource.attack
            if resource.card_type == CardTemplate.CARD_TYPE_CREATURE
            else None
        )
        card_template.health = (
            resource.health
            if resource.card_type == CardTemplate.CARD_TYPE_CREATURE
            else None
        )
        card_template.faction = self._faction_for_slug(resource.faction)
        card_template.spec = resource.spec or {}
        card_template.is_collectible = resource.is_collectible
        card_template.save()

        builder_models.CardTrait.objects.filter(card=card_template).delete()
        for trait_data in resource.traits:
            if not validate_trait_slug(trait_data.type):
                raise ValueError(f"Unknown trait type: '{trait_data.type}'")
            card_template.add_trait(
                trait_data.type,
                data=trait_data.model_dump(exclude={"type"}, exclude_none=True),
            )

        self._set_card_tags(card_template, resource.tags)
        self._set_card_allowed_heroes(card_template, resource.hero_slugs)

        return IngestedResource(
            resource_type="card",
            action="created" if is_new else "updated",
            id=card_template.id,
            slug=card_template.slug,
            name=card_template.name,
        )

    def ingest_hero(self, resource: Hero) -> IngestedResource:
        versions = builder_models.HeroTemplate.objects.filter(
            title=self.title, slug=resource.slug, is_latest=True
        )

        is_new = not versions.exists()
        if is_new:
            hero_template = builder_models.HeroTemplate.objects.create(
                title=self.title, slug=resource.slug, health=resource.health
            )
        else:
            hero_template = versions.first()

        hero_template.name = resource.name
        hero_template.description = resource.description
        hero_template.health = resource.health
        hero_template.hero_power = resource.hero_power.model_dump()
        hero_template.faction = self._faction_for_slug(resource.faction)
        hero_template.spec = resource.spec or {}
        hero_template.save()

        return IngestedResource(
            resource_type="hero",
            action="created" if is_new else "updated",
            id=hero_template.id,
            slug=hero_template.slug,
            name=hero_template.name,
        )

    def ingest_deck(self, resource: Deck) -> IngestedResource:
        hero = builder_models.HeroTemplate.objects.get(
            title=self.title, slug=resource.hero, is_latest=True
        )

        deck, is_new = collection_models.Deck.objects.get_or_create(
            ai_player=self.get_default_ai_player(),
            title=self.title,
            name=resource.name,
            hero=hero,
        )

        deck.hero = hero
        deck.save()

        seen_card_ids = set()
        for card_data in resource.cards:
            card_slug = card_data.get("card")
            if not card_slug:
                raise ValueError(f'Deck "{resource.name}" has a card without a slug.')

            card = CardTemplate.objects.get(
                title=self.title, slug=card_slug, is_latest=True
            )
            if not card.is_available_to_hero(hero):
                raise ValueError(
                    f'Card "{card.name}" is not available to hero "{hero.name}"'
                )

            deck_card = collection_models.DeckCard.objects.get_or_create(
                deck=deck, card=card
            )[0]
            deck_card.count = card_data["count"]
            deck_card.save()
            seen_card_ids.add(card.id)

        collection_models.DeckCard.objects.filter(deck=deck).exclude(
            card_id__in=seen_card_ids
        ).delete()

        return IngestedResource(
            resource_type="deck",
            action="created" if is_new else "updated",
            id=deck.id,
            slug="",
            name=deck.name,
        )

    def ingest_config(self, resource: TitleConfig) -> IngestedResource:
        """Update the title's configuration from a TitleConfig resource."""
        current_config = self.title.config or {}
        is_new = not current_config or current_config == {}

        updated_config = current_config.copy()
        updated_config["deck_size_limit"] = resource.deck_size_limit
        updated_config["min_cards_in_deck"] = resource.min_cards_in_deck
        updated_config["deck_card_max_count"] = resource.deck_card_max_count
        updated_config["hand_start_size"] = resource.hand_start_size
        updated_config["death_retaliation"] = resource.death_retaliation
        updated_config["ranked_time_per_turn"] = resource.ranked_time_per_turn

        if resource.side_b_compensation is not None:
            updated_config["side_b_compensation"] = resource.side_b_compensation
        elif "side_b_compensation" in updated_config:
            del updated_config["side_b_compensation"]

        self.title.config = updated_config
        self.title.save(update_fields=["config"])

        return IngestedResource(
            resource_type="config",
            action="created" if is_new else "updated",
            id=self.title.id,
            slug=self.title.slug,
            name=f"{self.title.name} Configuration",
        )

    # Export helpers

    def card_to_resource(self, card: CardTemplate) -> Card:
        traits = []
        for card_trait in sorted(
            card.cardtrait_set.all(), key=lambda trait: trait.trait_slug
        ):
            trait_data = {**(card_trait.data or {}), "type": card_trait.trait_slug}
            traits.append(trait_data)

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
            tags=[tag.slug for tag in card.tags.all().order_by("slug")],
            is_collectible=card.is_collectible,
            hero_slugs=[
                hero.slug for hero in card.allowed_heroes.all().order_by("slug")
            ],
        )

    def hero_to_resource(self, hero: builder_models.HeroTemplate) -> Hero:
        return Hero(
            slug=hero.slug,
            name=hero.name,
            description=hero.description or "",
            health=hero.health,
            hero_power=hero.hero_power or {},
            faction=hero.faction.slug if hero.faction else None,
            spec=hero.spec or {},
        )

    # Internal helpers

    def _title_config_from_data(self, config_data) -> TitleConfig:
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

    def _resource_sort_key(self, resource: Resource) -> int:
        return self.RESOURCE_IMPORT_ORDER.get(resource.type, 99)

    def _get_resource_by_slug(self, model, slug: str):
        return model.objects.filter(title=self.title, slug=slug).order_by("id").first()

    def _faction_for_slug(self, slug: str | None):
        if not slug:
            return None
        faction = self._get_resource_by_slug(builder_models.Faction, slug)
        if not faction:
            raise ValueError(f"Faction '{slug}' not found")
        return faction

    def _set_card_allowed_heroes(
        self, card_template: CardTemplate, hero_slugs: list[str]
    ) -> None:
        if not hero_slugs:
            card_template.allowed_heroes.clear()
            return

        allowed_heroes = list(
            builder_models.HeroTemplate.objects.filter(
                title=self.title,
                slug__in=hero_slugs,
                is_latest=True,
            )
        )
        found_slugs = {hero.slug for hero in allowed_heroes}
        missing_slugs = sorted(set(hero_slugs) - found_slugs)
        if missing_slugs:
            raise ValueError(
                f"Hero(s) not found for this title: {', '.join(missing_slugs)}"
            )
        card_template.allowed_heroes.set(allowed_heroes)

    def _set_card_tags(self, card_template: CardTemplate, tag_slugs: list[str]) -> None:
        if not tag_slugs:
            card_template.tags.clear()
            return

        tags = list(
            builder_models.Tag.objects.filter(title=self.title, slug__in=tag_slugs)
        )
        found_slugs = {tag.slug for tag in tags}
        missing_slugs = sorted(set(tag_slugs) - found_slugs)
        if missing_slugs:
            raise ValueError(
                f"Tag(s) not found for this title: {', '.join(missing_slugs)}"
            )
        card_template.tags.set(tags)

    def _resource_slugs(self, resources: Sequence[Resource]) -> dict[str, set[str]]:
        slugs = {
            "card": set(),
            "faction": set(),
            "hero": set(),
            "tag": set(),
            "trait_override": set(),
        }
        for resource in resources:
            if isinstance(resource, Card):
                slugs["card"].add(resource.slug)
            elif isinstance(resource, FactionResource):
                slugs["faction"].add(resource.slug)
            elif isinstance(resource, Hero):
                slugs["hero"].add(resource.slug)
            elif isinstance(resource, TagResource):
                slugs["tag"].add(resource.slug)
            elif isinstance(resource, TraitOverrideResource):
                slugs["trait_override"].add(resource.slug)
        return slugs

    def _delete_unreferenced_tag_resources(
        self, snapshot_slugs: set[str], removed: list[dict]
    ) -> None:
        for tag in builder_models.Tag.objects.filter(title=self.title).exclude(
            slug__in=snapshot_slugs
        ):
            if tag.cardtemplate_set.exists():
                continue
            removed.append({"resource_type": "tag", "slug": tag.slug, "name": tag.name})
            tag.delete()

    def _delete_unreferenced_faction_resources(
        self, snapshot_slugs: set[str], removed: list[dict]
    ) -> None:
        for faction in builder_models.Faction.objects.filter(title=self.title).exclude(
            slug__in=snapshot_slugs
        ):
            has_cards = CardTemplate.objects.filter(faction=faction).exists()
            has_heroes = builder_models.HeroTemplate.objects.filter(
                faction=faction
            ).exists()
            if has_cards or has_heroes:
                continue
            removed.append(
                {
                    "resource_type": "faction",
                    "slug": faction.slug,
                    "name": faction.name,
                }
            )
            faction.delete()

    def _resources_from_snapshot_mapping(self, snapshot: dict) -> list[dict]:
        resources: list[dict] = []

        title_data = snapshot.get("title") or {}
        if snapshot.get("slug"):
            title_data = {
                "slug": snapshot.get("slug"),
                "name": snapshot.get("name", title_data.get("name", "")),
                "description": snapshot.get(
                    "description", title_data.get("description", "")
                ),
            }
        if title_data:
            resources.append({"type": "title", **title_data})

        if "config" in snapshot:
            resources.append({"type": "config", **(snapshot.get("config") or {})})

        for key, resource_type in (
            ("factions", "faction"),
            ("tags", "tag"),
            ("trait_overrides", "trait_override"),
            ("heroes", "hero"),
            ("cards", "card"),
            ("decks", "deck"),
        ):
            for item in snapshot.get(key, []) or []:
                resources.append({"type": resource_type, **item})

        return resources


IngestionService = TitleService
