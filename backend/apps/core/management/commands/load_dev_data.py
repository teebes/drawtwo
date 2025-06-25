import os
import json
import yaml
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from django.conf import settings

User = get_user_model()


class Command(BaseCommand):
    help = 'Load development data for testing and development'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Clear existing dev data before loading',
        )
        parser.add_argument(
            '--users',
            action='store_true',
            help='Load only user data',
        )
        parser.add_argument(
            '--cards',
            action='store_true',
            help='Load only card data',
        )
        parser.add_argument(
            '--builder',
            action='store_true',
            help='Load only builder data',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Load all development data (default)',
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('This command can only be run in DEBUG mode')

        # Default to loading all if no specific options provided
        load_all = options['all'] or not any([
            options['users'],
            options['cards'],
            options['builder']
        ])

        try:
            with transaction.atomic():
                if options['reset']:
                    self.stdout.write(
                        self.style.WARNING('Clearing existing dev data...')
                    )
                    self.clear_dev_data()

                if options['users'] or load_all:
                    self.load_users()

                if options['cards'] or load_all:
                    self.load_cards()

                if options['builder'] or load_all:
                    self.load_builder_data()

                self.stdout.write(
                    self.style.SUCCESS('Successfully loaded development data!')
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error loading dev data: {str(e)}')
            )
            raise

    def clear_dev_data(self):
        """Clear existing development data"""
        # Remove users with dev email domains
        dev_users = User.objects.filter(
            email__in=[
                'admin@devdata.local',
                'staff@devdata.local',
                'user@devdata.local',
                'player1@devdata.local',
                'player2@devdata.local'
            ]
        )
        count = dev_users.count()
        dev_users.delete()
        self.stdout.write(f'Deleted {count} dev users')

        # TODO: Add clearing for other dev data when those models exist
        # Example:
        # Card.objects.filter(created_by__email__endswith='@devdata.local').delete()

    def load_users(self):
        """Load development users"""
        self.stdout.write('Loading development users...')

        dev_users = [
            {
                'email': 'admin@devdata.local',
                'username': 'admin',
                'is_staff': True,
                'is_superuser': True,
                'is_email_verified': True,
            },
            {
                'email': 'staff@devdata.local',
                'username': 'staff',
                'is_staff': True,
                'is_superuser': False,
                'is_email_verified': True,
            },
            {
                'email': 'user@devdata.local',
                'username': 'testuser',
                'is_staff': False,
                'is_superuser': False,
                'is_email_verified': True,
            },
            {
                'email': 'player1@devdata.local',
                'username': 'player1',
                'is_staff': False,
                'is_superuser': False,
                'is_email_verified': True,
            },
            {
                'email': 'player2@devdata.local',
                'username': 'player2',
                'is_staff': False,
                'is_superuser': False,
                'is_email_verified': False,  # Test unverified user
            }
        ]

        created_count = 0
        for user_data in dev_users:
            user, created = User.objects.get_or_create(
                email=user_data['email'],
                defaults=user_data
            )

            if created:
                # Set unusable password for passwordless auth
                user.set_unusable_password()
                user.save()
                created_count += 1
                self.stdout.write(f'  Created user: {user.email}')
            else:
                self.stdout.write(f'  User already exists: {user.email}')

        self.stdout.write(
            self.style.SUCCESS(f'Loaded {created_count} new users')
        )

    def load_cards(self):
        """Load development cards"""
        self.stdout.write('Loading development cards...')

        # TODO: Implement when Card model exists
        # This is a placeholder showing the pattern

        # Example structure:
        # dev_cards = [
        #     {
        #         'name': 'Lightning Bolt',
        #         'cost': 1,
        #         'type': 'spell',
        #         'rarity': 'common',
        #         'description': 'Deal 3 damage to any target.',
        #     },
        #     # ... more cards
        # ]

        # created_count = 0
        # for card_data in dev_cards:
        #     card, created = Card.objects.get_or_create(
        #         name=card_data['name'],
        #         defaults=card_data
        #     )
        #     if created:
        #         created_count += 1
        #         self.stdout.write(f'  Created card: {card.name}')
        #     else:
        #         self.stdout.write(f'  Card already exists: {card.name}')

        self.stdout.write(
            self.style.WARNING('Card loading not implemented yet (no Card model)')
        )

    def load_builder_data(self):
        from apps.builder.models import (
            Title, HeroTemplate, CardTemplate,
            Faction, Trait, CardTrait)

        self.stdout.write('Loading builder data...')

        # Try to load from YAML first, then JSON as fallback
        builder_data_list = (
            self.load_from_file('builder_data.yaml') or
            self.load_from_file('builder_data.yml') or
            self.load_from_file('builder_data.json')
        )

        if not builder_data_list:
            self.stdout.write(
                self.style.WARNING('No builder data found (tried .yaml, .yml, and .json formats)')
            )
            return

        created_count = 0
        for item in builder_data_list:
            try:
                if item['model'] == 'auth.user':
                    item_data = item.copy()
                    item_data.pop('model')
                    password = item_data.pop('password')

                    user, created = User.objects.get_or_create(
                        email=item_data['email'],
                        defaults=item_data)
                    if created:
                        if password:
                            user.set_password(password)
                            user.save()
                        created_count += 1
                        self.stdout.write(f'  Created user: {user.email}')
                    else:
                        self.stdout.write(f'  User already exists: {user.email}')

                elif item['model'] == 'builder.title':
                    item_data = item.copy()
                    item_data.pop('model')

                    title, created = Title.objects.get_or_create(
                        slug=item_data['slug'],
                        version=item_data['version'],
                        defaults=item_data
                    )
                    if created:
                        created_count += 1
                        self.stdout.write(f'  Created title: {title.name}')
                    else:
                        self.stdout.write(f'  Title already exists: {title.name}')

                elif item['model'] == 'builder.herotemplate':
                    item_data = item.copy()
                    item_data.pop('model')

                    hero_template, created = HeroTemplate.objects.get_or_create(
                        title_id=item_data['title_id'],
                        slug=item_data['slug'],
                        version=item_data['version'],
                        defaults=item_data
                    )
                    if created:
                        created_count += 1
                        self.stdout.write(f'  Created hero template: {hero_template.name}')
                    else:
                        self.stdout.write(f'  Hero template already exists: {hero_template.name}')

                elif item['model'] == 'builder.cardtemplate':
                    print('CARD TEMPLATE')
                    item_data = item.copy()
                    item_data.pop('model')

                    # Handle faction field - convert faction slug to Faction object
                    faction_slug = item_data.pop('faction', None)
                    if faction_slug:
                        try:
                            faction = Faction.objects.get(
                                title_id=item_data['title_id'],
                                slug=faction_slug
                            )
                            item_data['faction'] = faction
                        except Faction.DoesNotExist:
                            self.stdout.write(f'  ❌ Warning: Faction {faction_slug} not found for card {item_data.get("slug", "unknown")}')
                            # Continue without faction

                    card_template, created = CardTemplate.objects.get_or_create(
                        title_id=item_data['title_id'],
                        slug=item_data['slug'],
                        version=item_data['version'],
                        defaults=item_data
                    )
                    if created:
                        created_count += 1
                        self.stdout.write(f'  Created card template: {card_template.name}')
                    else:
                        self.stdout.write(f'  Card template already exists: {card_template.name}')
                elif item['model'] == 'builder.faction':
                    item_data = item.copy()
                    item_data.pop('model')

                    faction, created = Faction.objects.get_or_create(
                        title_id=item_data['title_id'],
                        slug=item_data['slug'],
                        defaults=item_data)
                    if created:
                        created_count += 1
                        self.stdout.write(f'  Created faction: {faction.name}')
                    else:
                        self.stdout.write(f'  Faction already exists: {faction.name}')

                elif item['model'] == 'builder.trait':
                    item_data = item.copy()
                    item_data.pop('model')

                    trait, created = Trait.objects.get_or_create(
                        title_id=item_data['title_id'],
                        slug=item_data['slug'],
                        defaults=item_data)
                    if created:
                        created_count += 1
                        self.stdout.write(f'  Created trait: {trait.name}')
                    else:
                        self.stdout.write(f'  Trait already exists: {trait.name}')
                elif item['model'] == 'builder.cardtemplate_trait':
                    item_data = item.copy()
                    item_data.pop('model')
                    title_id = item_data.pop('title_id')

                    # Extract trait_data (unified data field)
                    trait_data = item_data.pop('trait_data', {})

                    trait = Trait.objects.get(
                        title_id=title_id,
                        slug=item_data['trait'],
                    )

                    card_template = CardTemplate.objects.get(
                        title_id=title_id,
                        slug=item_data['card_template'],
                    )

                    # Check if CardTrait relationship already exists
                    card_trait, created = CardTrait.objects.get_or_create(
                        card=card_template,
                        trait=trait,
                        defaults={'data': trait_data}
                    )

                    if created:
                        created_count += 1
                        if trait_data:
                            self.stdout.write(f'  Added trait: {trait.name} to card template: {card_template.name} with data: {trait_data}')
                        else:
                            self.stdout.write(f'  Added trait: {trait.name} to card template: {card_template.name}')
                    else:
                        self.stdout.write(f'  Trait relationship already exists: {trait.name} on {card_template.name}')
                else:
                    self.stdout.write(f'  Skipping unknown model: {item.get("model", "unknown")}')
            except Exception as e:
                self.stdout.write(f'  ❌ Error processing item: {str(e)}')

        self.stdout.write(
            self.style.SUCCESS(f'Loaded {created_count} new builder items')
        )

    def load_from_file(self, filename):
        """Helper method to load data from JSON or YAML files in dev_data directory"""
        dev_data_path = os.path.join(settings.BASE_DIR, 'dev_data', filename)

        if not os.path.exists(dev_data_path):
            self.stdout.write(
                self.style.WARNING(f'❌ Dev data file not found: {dev_data_path}')
            )
            return []

        try:
            with open(dev_data_path, 'r') as f:
                # Determine file format based on extension
                _, ext = os.path.splitext(filename.lower())

                if ext in ['.yaml', '.yml']:
                    return yaml.safe_load(f) or []
                elif ext == '.json':
                    return json.load(f)
                else:
                    # Try to parse as JSON first, then YAML
                    content = f.read()
                    f.seek(0)
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        try:
                            return yaml.safe_load(content) or []
                        except yaml.YAMLError:
                            raise ValueError(f"Could not parse {filename} as JSON or YAML")

        except (json.JSONDecodeError, yaml.YAMLError) as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error parsing {filename}: {str(e)}')
            )
            return []
        except (IOError, ValueError) as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error reading {filename}: {str(e)}')
            )
            return []
