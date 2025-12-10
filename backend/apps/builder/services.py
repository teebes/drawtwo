import yaml
from typing import List

from django.contrib.auth import get_user_model
from pydantic import TypeAdapter

from apps.builder import models as builder_models
from apps.builder.models import Title, CardTemplate
from apps.builder.schemas import Resource, Card, Hero, Deck, TitleConfig, IngestedResource
from apps.collection import models as collection_models

User = get_user_model()


class TitleService:

    @classmethod
    def create_title(cls, author: User, slug: str,name: str):
        title = Title.objects.create(name=name, slug=slug, author=author)
        service = cls(title)
        # No longer need to create trait rows - using trait_definitions.py
        return service

    def __init__(self, title: Title):
        self.title = title

    def ingest_yaml(self, yaml_data: str) -> List[IngestedResource]:
        """
        Ingest YAML data and create/update resources.

        Returns a list of IngestedResource objects describing what was created or updated.
        """
        resource_data = yaml.safe_load(yaml_data)

        # Handle both single resource and list of resources
        if isinstance(resource_data, list):
            resources = [
                TypeAdapter(Resource).validate_python(resource)
                for resource in resource_data
            ]
        else:
            # Single resource - wrap in list for consistent processing
            resources = [
                TypeAdapter(Resource).validate_python(resource_data)
            ]

        ingested: List[IngestedResource] = []
        for resource in resources:
            result = self.ingest(resource)
            if result:
                ingested.append(result)

        return ingested


    def ingest(self, resource: Resource) -> IngestedResource | None:
        resource_map = {
            Card: self.ingest_card,
            Hero: self.ingest_hero,
            Deck: self.ingest_deck,
            TitleConfig: self.ingest_config
        }
        for resource_type, handler in resource_map.items():
            if isinstance(resource, resource_type):
                return handler(resource)
        return None

    def get_default_ai_player(self):
        return builder_models.AIPlayer.objects.get_or_create(
            name="Default",
            difficulty="medium"
        )[0]

    # Handlers

    def ingest_card(self, resource: Card) -> IngestedResource:
        versions = CardTemplate.objects.filter(
            title=self.title,
            slug=resource.slug,
            is_latest=True)

        is_new = not versions.exists()
        if is_new:
            card_template = CardTemplate.objects.create(
                title=self.title,
                slug=resource.slug)
        else:
            card_template = versions.first()

        card_template.card_type = resource.card_type
        card_template.name = resource.name
        card_template.description = resource.description or ''
        card_template.cost = resource.cost
        card_template.attack = resource.attack
        card_template.health = resource.health
        card_template.is_collectible = resource.is_collectible

        if resource.traits:
            from apps.builder.trait_definitions import validate_trait_slug
            for trait_data in resource.traits:
                if not validate_trait_slug(trait_data.type):
                    raise ValueError(f"Unknown trait type: '{trait_data.type}'")
                card_template.add_trait(trait_data.type, data=trait_data.model_dump())

        card_template.save()

        return IngestedResource(
            resource_type='card',
            action='created' if is_new else 'updated',
            id=card_template.id,
            slug=card_template.slug,
            name=card_template.name
        )

    def ingest_hero(self, resource: Hero) -> IngestedResource:
        versions = builder_models.HeroTemplate.objects.filter(
            title=self.title,
            slug=resource.slug,
            is_latest=True)

        is_new = not versions.exists()
        if is_new:
            hero_template = builder_models.HeroTemplate.objects.create(
                title=self.title,
                slug=resource.slug,
                health=resource.health)
        else:
            hero_template = versions.first()

        hero_template.name = resource.name
        hero_template.description = resource.description
        hero_template.health = resource.health
        hero_template.hero_power = resource.hero_power.model_dump()
        hero_template.save()

        return IngestedResource(
            resource_type='hero',
            action='created' if is_new else 'updated',
            id=hero_template.id,
            slug=hero_template.slug,
            name=hero_template.name
        )

    def ingest_deck(self, resource: Deck) -> IngestedResource:
        hero = builder_models.HeroTemplate.objects.get(
            title=self.title,
            slug=resource.hero,
            is_latest=True)

        deck, is_new = collection_models.Deck.objects.get_or_create(
            ai_player=self.get_default_ai_player(),
            title=self.title,
            name=resource.name,
            hero=hero)

        for card_data in resource.cards:
            card = CardTemplate.objects.get(
                title=self.title,
                slug=card_data['card'],
                is_latest=True)

            deck_card = collection_models.DeckCard.objects.get_or_create(
                deck=deck,
                card=card)[0]
            deck_card.count = card_data['count']
            deck_card.save()

        return IngestedResource(
            resource_type='deck',
            action='created' if is_new else 'updated',
            id=deck.id,
            slug='',  # Decks don't have slugs, use empty string
            name=deck.name
        )

    def ingest_config(self, resource: TitleConfig) -> IngestedResource:
        """Update the title's configuration from a TitleConfig resource."""
        # Get current config or initialize empty dict
        current_config = self.title.config or {}

        # Determine if this is an update (config exists) or creation (first time setting config)
        is_new = not current_config or current_config == {}

        # Update config with values from TitleConfig schema
        # Only update fields that are explicitly set (non-None for optional fields)
        updated_config = current_config.copy()
        updated_config['deck_size_limit'] = resource.deck_size_limit
        updated_config['deck_card_max_count'] = resource.deck_card_max_count
        updated_config['hand_start_size'] = resource.hand_start_size
        updated_config['death_retaliation'] = resource.death_retaliation

        # Only include side_b_compensation if it's not None
        if resource.side_b_compensation is not None:
            updated_config['side_b_compensation'] = resource.side_b_compensation
        elif 'side_b_compensation' in updated_config:
            # Remove it if it was set to None
            del updated_config['side_b_compensation']

        # Save updated config
        self.title.config = updated_config
        self.title.save(update_fields=['config'])

        return IngestedResource(
            resource_type='config',
            action='created' if is_new else 'updated',
            id=self.title.id,
            slug=self.title.slug,
            name=f'{self.title.name} Configuration'
        )



IngestionService = TitleService