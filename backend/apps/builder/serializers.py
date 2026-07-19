import yaml
from django.contrib.auth import get_user_model
from pydantic import TypeAdapter
from pydantic import ValidationError as PydanticValidationError
from rest_framework import serializers

from apps.builder.models import (
    CardTemplate,
    CardTrait,
    Faction,
    HeroTemplate,
    Title,
)
from apps.builder.schemas import Trait
from apps.builder.trait_definitions import validate_trait_slug
from apps.core.card_assets import get_card_art_url, get_hero_art_url

User = get_user_model()

TRAIT_ADAPTER = TypeAdapter(Trait)


def _parse_and_validate_card_yaml(yaml_data):
    try:
        card_data = yaml.safe_load(yaml_data)
    except yaml.YAMLError as exc:
        raise serializers.ValidationError(f"Invalid YAML: {exc}") from exc

    if not isinstance(card_data, dict):
        raise serializers.ValidationError(
            "Card YAML must define a single card object, not a list."
        )

    traits_data = card_data.get("traits", [])
    if traits_data is None:
        traits_data = []
    if not isinstance(traits_data, list):
        raise serializers.ValidationError("Card traits must be a list.")

    for index, trait_entry in enumerate(traits_data, start=1):
        try:
            TRAIT_ADAPTER.validate_python(trait_entry)
        except PydanticValidationError as exc:
            details = []
            for error in exc.errors(include_url=False):
                location = ".".join(str(part) for part in error["loc"])
                prefix = f"{location}: " if location else ""
                details.append(f'{prefix}{error["msg"]}')
            raise serializers.ValidationError(
                f"Invalid trait #{index}: {'; '.join(details)}"
            ) from exc

    card_data["traits"] = traits_data
    return card_data


class TitleSerializer(serializers.ModelSerializer):
    """Serializer for Title model."""

    author_username = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = Title
        fields = [
            "id",
            "slug",
            "version",
            "is_latest",
            "name",
            "description",
            "author",
            "author_username",
            "status",
            "published_at",
            "created_at",
            "updated_at",
            "art_url",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CardTemplateSerializer(serializers.ModelSerializer):
    """Serializer for CardTemplate model with YAML support."""

    title_slug = serializers.CharField(source="title.slug", read_only=True)
    faction_slug = serializers.CharField(
        source="faction.slug", read_only=True, allow_null=True
    )
    yaml_definition = serializers.SerializerMethodField()

    # Fields for displaying traits with data
    traits_with_data = serializers.SerializerMethodField()

    art_url = serializers.SerializerMethodField()
    hero_slugs = serializers.SerializerMethodField()

    class Meta:
        model = CardTemplate
        fields = [
            "id",
            "slug",
            "name",
            "description",
            "version",
            "is_latest",
            "card_type",
            "cost",
            "attack",
            "health",
            "spec",
            "is_collectible",
            "title_slug",
            "faction_slug",
            "traits_with_data",
            "yaml_definition",
            "hero_slugs",
            "art_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "version", "created_at", "updated_at"]

    def get_art_url(self, obj):
        """Get the art URL for the card."""
        return get_card_art_url(obj.title.slug, obj.slug)

    def get_hero_slugs(self, obj):
        """Get the hero slugs this card is restricted to."""
        heroes = sorted(obj.allowed_heroes.all(), key=lambda hero: hero.name)
        return [hero.slug for hero in heroes]

    def _get_hero_slugs_from_card_data(self, card_data):
        hero_slugs = card_data.get("hero_slugs", [])
        if not hero_slugs:
            hero_slugs = card_data.get("heroes", [])
        if not hero_slugs:
            hero_slugs = card_data.get("hero", [])
        if isinstance(hero_slugs, str):
            hero_slugs = [hero_slugs]
        return [slug for slug in hero_slugs if isinstance(slug, str) and slug.strip()]

    def _set_allowed_heroes_from_card_data(self, instance, card_data):
        hero_slugs = self._get_hero_slugs_from_card_data(card_data)
        if not hero_slugs:
            instance.allowed_heroes.clear()
            return

        heroes = list(
            HeroTemplate.objects.filter(
                title=instance.title,
                slug__in=hero_slugs,
                is_latest=True,
            )
        )
        found_slugs = {hero.slug for hero in heroes}
        missing_slugs = sorted(set(hero_slugs) - found_slugs)
        if missing_slugs:
            raise serializers.ValidationError(
                f"Hero(s) not found for this title: {', '.join(missing_slugs)}"
            )
        instance.allowed_heroes.set(heroes)

    def get_traits_with_data(self, obj):
        """Get traits with their associated data."""
        traits_data = []
        for card_trait in obj.cardtrait_set.all():
            trait_info = card_trait.get_trait_info()
            traits_data.append(
                {
                    "slug": trait_info["slug"],
                    "name": trait_info["name"],
                    "data": card_trait.data,
                }
            )
        return traits_data

    def get_yaml_definition(self, obj):
        """Convert card template to YAML format."""
        # Build the card data structure
        card_data = {
            "name": obj.name,
            "card_type": obj.card_type,
            "cost": obj.cost,
        }

        # Only include description if it's not empty
        if obj.description:
            card_data["description"] = obj.description

        # Add attack/health for creatures
        if obj.card_type == "creature":
            card_data["attack"] = obj.attack
            card_data["health"] = obj.health

        # Add faction if present
        if obj.faction:
            card_data["faction"] = obj.faction.slug

        # Add traits
        traits_list = []
        for card_trait in obj.cardtrait_set.all():
            trait_entry = {"type": card_trait.trait_slug}
            if card_trait.data:
                trait_entry.update(card_trait.data)
            traits_list.append(trait_entry)

        if traits_list:
            card_data["traits"] = traits_list

        # Add spec if present
        if obj.spec:
            card_data["spec"] = obj.spec

        hero_slugs = self.get_hero_slugs(obj)
        if hero_slugs:
            card_data["hero_slugs"] = hero_slugs

        # Add is_collectible if False (True is the default, so we only show False)
        if not obj.is_collectible:
            card_data["is_collectible"] = False

        return yaml.dump(
            card_data, default_flow_style=False, sort_keys=False, width=float("inf")
        )

    def update_from_yaml(self, instance, yaml_data):
        """Update card instance from YAML data."""
        card_data = _parse_and_validate_card_yaml(yaml_data)

        # Update basic fields
        instance.name = card_data.get("name", instance.name)
        instance.description = card_data.get("description", instance.description)
        instance.card_type = card_data.get("card_type", instance.card_type)
        instance.cost = card_data.get("cost", instance.cost)

        # Update attack/health for creatures
        if instance.card_type == "creature":
            instance.attack = card_data.get("attack", instance.attack)
            instance.health = card_data.get("health", instance.health)
        else:
            instance.attack = None
            instance.health = None

        # Update faction
        faction_slug = card_data.get("faction")
        if faction_slug:
            try:
                faction = Faction.objects.get(slug=faction_slug, title=instance.title)
                instance.faction = faction
            except Faction.DoesNotExist:
                raise serializers.ValidationError(f"Faction '{faction_slug}' not found")
        else:
            instance.faction = None

        # Update spec
        instance.spec = card_data.get("spec", {})

        print("updating from yaml with card_data: ", card_data)
        # Update is_collectible when present; otherwise keep the existing value.
        if "is_collectible" in card_data:
            instance.is_collectible = card_data["is_collectible"]

        instance.save()
        self._set_allowed_heroes_from_card_data(instance, card_data)

        # Update traits
        # Clear existing traits
        CardTrait.objects.filter(card=instance).delete()

        # Add new traits
        traits_data = card_data.get("traits", [])
        for trait_entry in traits_data:
            trait_type = trait_entry.get("type")
            if not trait_type:
                continue

            # Validate trait slug
            if not validate_trait_slug(trait_type):
                raise serializers.ValidationError(f"Unknown trait type: '{trait_type}'")

            trait_data = {k: v for k, v in trait_entry.items() if k != "type"}
            CardTrait.objects.create(
                card=instance, trait_slug=trait_type, data=trait_data
            )

        return instance

    def create_from_yaml(self, title, yaml_data, slug=None):
        """Create a new card instance from YAML data."""
        card_data = _parse_and_validate_card_yaml(yaml_data)

        # Required fields
        name = card_data.get("name")
        if not name:
            raise serializers.ValidationError("Card name is required")

        # Use provided slug or generate one from name
        if slug:
            # Use the provided slug (already validated in the view)
            pass
        else:
            # Generate slug from name (simple implementation) - legacy behavior
            import re

            slug = re.sub(r"[^a-zA-Z0-9\-_]", "_", name.lower().replace(" ", "_"))

            # Check if slug already exists in this title
            if CardTemplate.objects.filter(title=title, slug=slug).exists():
                # Find a unique slug by appending a number
                base_slug = slug
                counter = 1
                while CardTemplate.objects.filter(title=title, slug=slug).exists():
                    slug = f"{base_slug}_{counter}"
                    counter += 1

        # Create card instance
        card_type = card_data.get("card_type", "creature")
        cost = card_data.get("cost", 0)

        instance = CardTemplate.objects.create(
            title=title,
            slug=slug,
            name=name,
            description=card_data.get("description", ""),
            card_type=card_type,
            cost=cost,
            attack=card_data.get("attack") if card_type == "creature" else None,
            health=card_data.get("health") if card_type == "creature" else None,
            spec=card_data.get("spec", {}),
            is_collectible=card_data.get("is_collectible", True),
            version=1,
            is_latest=True,
        )
        self._set_allowed_heroes_from_card_data(instance, card_data)

        # Set faction if provided
        faction_slug = card_data.get("faction")
        if faction_slug:
            try:
                faction = Faction.objects.get(slug=faction_slug, title=title)
                instance.faction = faction
                instance.save(update_fields=["faction"])
            except Faction.DoesNotExist:
                raise serializers.ValidationError(f"Faction '{faction_slug}' not found")

        # Add traits
        traits_data = card_data.get("traits", [])
        for trait_entry in traits_data:
            trait_type = trait_entry.get("type")
            if not trait_type:
                continue

            # Validate trait slug
            if not validate_trait_slug(trait_type):
                raise serializers.ValidationError(f"Unknown trait type: '{trait_type}'")

            trait_data = {k: v for k, v in trait_entry.items() if k != "type"}
            CardTrait.objects.create(
                card=instance, trait_slug=trait_type, data=trait_data
            )

        return instance


class HeroTemplateSerializer(serializers.ModelSerializer):
    """Serializer for hero template summaries used by builder tooling."""

    title_slug = serializers.CharField(source="title.slug", read_only=True)
    faction_slug = serializers.CharField(
        source="faction.slug", read_only=True, allow_null=True
    )
    art_url = serializers.SerializerMethodField()

    class Meta:
        model = HeroTemplate
        fields = [
            "id",
            "slug",
            "name",
            "description",
            "version",
            "is_latest",
            "health",
            "hero_power",
            "spec",
            "title_slug",
            "faction_slug",
            "art_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "version", "created_at", "updated_at"]

    def get_art_url(self, obj):
        """Get the art URL for the hero."""
        return get_hero_art_url(obj.title.slug, obj.slug)
