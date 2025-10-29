from rest_framework import serializers
from django.contrib.auth import get_user_model
import yaml
from .models import Title, CardTemplate, Faction, Tag, CardTrait
from .trait_definitions import get_trait_info, validate_trait_slug


User = get_user_model()


class TitleSerializer(serializers.ModelSerializer):
    """Serializer for Title model."""
    author_username = serializers.CharField(source='author.username', read_only=True)

    class Meta:
        model = Title
        fields = ['id', 'slug', 'version', 'is_latest', 'name', 'description',
                 'author', 'author_username', 'status', 'published_at',
                 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class CardTemplateSerializer(serializers.ModelSerializer):
    """Serializer for CardTemplate model with YAML support."""
    title_slug = serializers.CharField(source='title.slug', read_only=True)
    faction_slug = serializers.CharField(source='faction.slug', read_only=True, allow_null=True)
    yaml_definition = serializers.SerializerMethodField()

    # Fields for displaying traits with data
    traits_with_data = serializers.SerializerMethodField()

    class Meta:
        model = CardTemplate
        fields = ['id', 'slug', 'name', 'description', 'version', 'is_latest',
                 'card_type', 'cost', 'attack', 'health', 'spec',
                 'title_slug', 'faction_slug', 'traits_with_data', 'yaml_definition',
                 'created_at', 'updated_at']
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']

    def get_traits_with_data(self, obj):
        """Get traits with their associated data."""
        traits_data = []
        for card_trait in obj.cardtrait_set.all():
            trait_info = card_trait.get_trait_info()
            traits_data.append({
                'slug': trait_info['slug'],
                'name': trait_info['name'],
                'data': card_trait.data
            })
        return traits_data

    def get_yaml_definition(self, obj):
        """Convert card template to YAML format."""
        # Build the card data structure
        card_data = {
            'name': obj.name,
            'description': obj.description,
            'card_type': obj.card_type,
            'cost': obj.cost,
        }

        # Add attack/health for creatures
        if obj.card_type == 'creature':
            card_data['attack'] = obj.attack
            card_data['health'] = obj.health

        # Add faction if present
        if obj.faction:
            card_data['faction'] = obj.faction.slug

        # Add traits
        traits_list = []
        for card_trait in obj.cardtrait_set.all():
            trait_entry = {'type': card_trait.trait_slug}
            if card_trait.data:
                trait_entry.update(card_trait.data)
            traits_list.append(trait_entry)

        if traits_list:
            card_data['traits'] = traits_list

        # Add spec if present
        if obj.spec:
            card_data['spec'] = obj.spec

        return yaml.dump(
            card_data,
            default_flow_style=False,
            sort_keys=False,
            width=float("inf"))

    def update_from_yaml(self, instance, yaml_data):
        """Update card instance from YAML data."""
        try:
            card_data = yaml.safe_load(yaml_data)
        except yaml.YAMLError as e:
            raise serializers.ValidationError(f"Invalid YAML: {e}")

        # Update basic fields
        instance.name = card_data.get('name', instance.name)
        instance.description = card_data.get('description', instance.description)
        instance.card_type = card_data.get('card_type', instance.card_type)
        instance.cost = card_data.get('cost', instance.cost)

        # Update attack/health for creatures
        if instance.card_type == 'creature':
            instance.attack = card_data.get('attack', instance.attack)
            instance.health = card_data.get('health', instance.health)
        else:
            instance.attack = None
            instance.health = None

        # Update faction
        faction_slug = card_data.get('faction')
        if faction_slug:
            try:
                faction = Faction.objects.get(slug=faction_slug, title=instance.title)
                instance.faction = faction
            except Faction.DoesNotExist:
                raise serializers.ValidationError(f"Faction '{faction_slug}' not found")
        else:
            instance.faction = None

        # Update spec
        instance.spec = card_data.get('spec', {})

        instance.save()

        # Update traits
        # Clear existing traits
        CardTrait.objects.filter(card=instance).delete()

        # Add new traits
        traits_data = card_data.get('traits', [])
        for trait_entry in traits_data:
            trait_type = trait_entry.get('type')
            if not trait_type:
                continue

            # Validate trait slug
            if not validate_trait_slug(trait_type):
                raise serializers.ValidationError(f"Unknown trait type: '{trait_type}'")

            trait_data = {k: v for k, v in trait_entry.items() if k != 'type'}
            CardTrait.objects.create(
                card=instance,
                trait_slug=trait_type,
                data=trait_data
            )

        return instance

    def create_from_yaml(self, title, yaml_data, slug=None):
        """Create a new card instance from YAML data."""
        try:
            card_data = yaml.safe_load(yaml_data)
        except yaml.YAMLError as e:
            raise serializers.ValidationError(f"Invalid YAML: {e}")

        # Required fields
        name = card_data.get('name')
        if not name:
            raise serializers.ValidationError("Card name is required")

        # Use provided slug or generate one from name
        if slug:
            # Use the provided slug (already validated in the view)
            pass
        else:
            # Generate slug from name (simple implementation) - legacy behavior
            import re
            slug = re.sub(r'[^a-zA-Z0-9\-_]', '_', name.lower().replace(' ', '_'))

            # Check if slug already exists in this title
            if CardTemplate.objects.filter(title=title, slug=slug).exists():
                # Find a unique slug by appending a number
                base_slug = slug
                counter = 1
                while CardTemplate.objects.filter(title=title, slug=slug).exists():
                    slug = f"{base_slug}_{counter}"
                    counter += 1

        # Create card instance
        card_type = card_data.get('card_type', 'creature')
        cost = card_data.get('cost', 0)

        instance = CardTemplate.objects.create(
            title=title,
            slug=slug,
            name=name,
            description=card_data.get('description', ''),
            card_type=card_type,
            cost=cost,
            attack=card_data.get('attack') if card_type == 'creature' else None,
            health=card_data.get('health') if card_type == 'creature' else None,
            spec=card_data.get('spec', {}),
            version=1,
            is_latest=True
        )

        # Set faction if provided
        faction_slug = card_data.get('faction')
        if faction_slug:
            try:
                faction = Faction.objects.get(slug=faction_slug, title=title)
                instance.faction = faction
                instance.save(update_fields=['faction'])
            except Faction.DoesNotExist:
                raise serializers.ValidationError(f"Faction '{faction_slug}' not found")

        # Add traits
        traits_data = card_data.get('traits', [])
        for trait_entry in traits_data:
            trait_type = trait_entry.get('type')
            if not trait_type:
                continue

            # Validate trait slug
            if not validate_trait_slug(trait_type):
                raise serializers.ValidationError(f"Unknown trait type: '{trait_type}'")

            trait_data = {k: v for k, v in trait_entry.items() if k != 'type'}
            CardTrait.objects.create(
                card=instance,
                trait_slug=trait_type,
                data=trait_data
            )

        return instance