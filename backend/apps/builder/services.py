import yaml

from django.contrib.auth import get_user_model

from apps.builder.models import Title, CardTemplate, Trait
from apps.builder.schemas import Resource, Card

User = get_user_model()


class TitleService:

    @classmethod
    def create_title(cls, author: User, slug: str,name: str):
        title = Title.objects.create(name=name, slug=slug, author=author)
        self.assign_traits(title)
        return cls(title)

    def __init__(self, title: Title):
        self.title = title

    def assign_traits(self):
        trait_slugs = list(dict(Trait._meta.get_field('slug').choices).keys())
        for trait_slug in trait_slugs:
            Trait.objects.get_or_create(slug=trait_slug, title=self.title)

    def ingest(self, resource: Resource):

        if isinstance(resource, Card):
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
                for trait_data in resource.traits:
                    try:
                        trait = Trait.objects.get(slug=trait_data.type, title=self.title)
                    except Trait.DoesNotExist:
                        raise ValueError(f"Trait '{trait_data.type}' not found")
                    card_template.add_trait(trait, data=trait_data.model_dump())

            card_template.save()

    def ingest_yaml(self, yaml_data: str):
        resource_data = yaml.safe_load(yaml_data)

        if isinstance(resource_data, list):
            resources = [
                Resource.model_validate(resource)
                for resource in resource_data
            ]
        else:
            resources = [
                Resource.model_validate(resource_data)
            ]

        for resource in resources:
            self.ingest(resource)


IngestionService = TitleService