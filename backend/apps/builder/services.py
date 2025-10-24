import yaml

from django.contrib.auth import get_user_model
from pydantic import TypeAdapter

from apps.builder import models as builder_models
from apps.builder.models import Title, CardTemplate
from apps.builder.schemas import Resource, Card, Hero, Deck
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

    def ingest_yaml(self, yaml_data: str):
        resource_data = yaml.safe_load(yaml_data)

        if isinstance(resource_data, list):
            # resources = []
            # for resource in resource_data:
            #     print(resource)
            #     resources.append(TypeAdapter(Resource).validate_python(resource))
            resources = [
                TypeAdapter(Resource).validate_python(resource)
                for resource in resource_data
            ]
        else:
            resources = [
                Resource.model_validate(resource_data)
            ]

        for resource in resources:
            self.ingest(resource)


    def ingest(self, resource: Resource):
        resource_map = {
            Card: self.ingest_card,
            Hero: self.ingest_hero,
            Deck: self.ingest_deck
        }
        for resource_type, handler in resource_map.items():
            if isinstance(resource, resource_type):
                handler(resource)
                break

    def get_default_ai_player(self):
        return builder_models.AIPlayer.objects.get_or_create(
            name="Default",
            difficulty="medium"
        )[0]

    # Handlers

    def ingest_card(self, resource: Card):
        versions = CardTemplate.objects.filter(
            title=self.title,
            slug=resource.slug,
            is_latest=True)

        if versions.exists():
            card_template = versions.first()
        else:
            card_template = CardTemplate.objects.create(
                title=self.title,
                slug=resource.slug)

        card_template.card_type = resource.card_type
        card_template.name = resource.name
        card_template.description = resource.description
        card_template.cost = resource.cost
        card_template.attack = resource.attack
        card_template.health = resource.health

        if resource.traits:
            from apps.builder.trait_definitions import validate_trait_slug
            for trait_data in resource.traits:
                if not validate_trait_slug(trait_data.type):
                    raise ValueError(f"Unknown trait type: '{trait_data.type}'")
                card_template.add_trait(trait_data.type, data=trait_data.model_dump())

        card_template.save()

    def ingest_hero(self, resource: Hero):
        versions = builder_models.HeroTemplate.objects.filter(
            title=self.title,
            slug=resource.slug,
            is_latest=True)

        if versions.exists():
            hero_template = versions.first()
        else:
            hero_template = builder_models.HeroTemplate.objects.create(
                title=self.title,
                slug=resource.slug,
                health=resource.health)

        hero_template.name = resource.name
        hero_template.description = resource.description
        hero_template.health = resource.health
        hero_template.hero_power = resource.hero_power.model_dump()
        hero_template.save()

    def ingest_deck(self, resource: Deck):
        hero = builder_models.HeroTemplate.objects.get(
            title=self.title,
            slug=resource.hero,
            is_latest=True)

        deck = collection_models.Deck.objects.get_or_create(
            ai_player=self.get_default_ai_player(),
            title=self.title,
            name=resource.name,
            hero=hero)[0]

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



IngestionService = TitleService