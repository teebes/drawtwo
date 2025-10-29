# Generated manually for trait refactor

from django.db import migrations, models
import django.db.models.deletion
import apps.core.models


def migrate_cardtrait_data(apps, schema_editor):
    """Copy trait FK data to trait_slug field"""
    CardTrait = apps.get_model('builder', 'CardTrait')
    Trait = apps.get_model('builder', 'Trait')

    for card_trait in CardTrait.objects.all().select_related('trait'):
        card_trait.trait_slug = card_trait.trait.slug
        card_trait.save(update_fields=['trait_slug'])


def reverse_migrate_cardtrait_data(apps, schema_editor):
    """Reverse migration - populate trait FK from trait_slug"""
    CardTrait = apps.get_model('builder', 'CardTrait')
    Trait = apps.get_model('builder', 'Trait')

    for card_trait in CardTrait.objects.all():
        # Find the trait with matching slug for this card's title
        try:
            trait = Trait.objects.get(slug=card_trait.trait_slug, title=card_trait.card.title)
            card_trait.trait = trait
            card_trait.save(update_fields=['trait'])
        except Trait.DoesNotExist:
            # Skip if trait doesn't exist (shouldn't happen in proper reverse)
            pass


class Migration(migrations.Migration):

    dependencies = [
        ('builder', '0009_alter_trait_name'),
    ]

    operations = [
        # Step 1: Create TraitOverride model
        migrations.CreateModel(
            name='TraitOverride',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('slug', models.SlugField(choices=[('armor', 'armor'), ('battlecry', 'battlecry'), ('charge', 'charge'), ('cleave', 'cleave'), ('deathrattle', 'deathrattle'), ('inspire', 'inspire'), ('lifesteal', 'lifesteal'), ('ranged', 'ranged'), ('taunt', 'taunt'), ('unique', 'unique')])),
                ('name', models.CharField(max_length=40)),
                ('description', models.TextField(blank=True)),
                ('title', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='builder.title')),
            ],
            options={
                'verbose_name': 'Trait Override',
                'verbose_name_plural': 'Trait Overrides',
            },
        ),

        # Step 2: Add index for TraitOverride
        migrations.AddIndex(
            model_name='traitoverride',
            index=models.Index(fields=['title', 'slug'], name='trait_override_title_slug_idx'),
        ),

        # Step 3: Add unique constraint for TraitOverride
        migrations.AlterUniqueTogether(
            name='traitoverride',
            unique_together={('title', 'slug')},
        ),

        # Step 4: Add trait_slug field to CardTrait (nullable for now)
        migrations.AddField(
            model_name='cardtrait',
            name='trait_slug',
            field=models.SlugField(null=True, blank=True, choices=[('armor', 'armor'), ('battlecry', 'battlecry'), ('charge', 'charge'), ('cleave', 'cleave'), ('deathrattle', 'deathrattle'), ('inspire', 'inspire'), ('lifesteal', 'lifesteal'), ('ranged', 'ranged'), ('taunt', 'taunt'), ('unique', 'unique')]),
        ),

        # Step 5: Migrate data from trait FK to trait_slug
        migrations.RunPython(migrate_cardtrait_data, reverse_migrate_cardtrait_data),

        # Step 6: Make trait_slug non-nullable
        migrations.AlterField(
            model_name='cardtrait',
            name='trait_slug',
            field=models.SlugField(choices=[('armor', 'armor'), ('battlecry', 'battlecry'), ('charge', 'charge'), ('cleave', 'cleave'), ('deathrattle', 'deathrattle'), ('inspire', 'inspire'), ('lifesteal', 'lifesteal'), ('ranged', 'ranged'), ('taunt', 'taunt'), ('unique', 'unique')]),
        ),

        # Step 7: Remove old unique_together constraint (includes trait FK)
        migrations.AlterUniqueTogether(
            name='cardtrait',
            unique_together=set(),
        ),

        # Step 8: Remove old index on trait FK
        migrations.RemoveIndex(
            model_name='cardtrait',
            name='cardtrait_trait_idx',
        ),

        # Step 9: Remove trait FK field
        migrations.RemoveField(
            model_name='cardtrait',
            name='trait',
        ),

        # Step 10: Add new unique constraint on card + trait_slug
        migrations.AlterUniqueTogether(
            name='cardtrait',
            unique_together={('card', 'trait_slug')},
        ),

        # Step 11: Add new index on trait_slug
        migrations.AddIndex(
            model_name='cardtrait',
            index=models.Index(fields=['trait_slug'], name='cardtrait_trait_slug_idx'),
        ),

        # Step 12: Remove CardTemplate.traits M2M field (no DB change needed, just model change)
    ]
