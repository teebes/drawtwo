import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


def create_archetype_starter_program(apps, schema_editor):
    program_model = apps.get_model("collection", "StarterDeckProgram")
    program_model.objects.create(
        title_slug="archetype",
        eligible_after=timezone.now(),
    )


class Migration(migrations.Migration):

    dependencies = [
        ("collection", "0016_deck_composition_favorites"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="StarterDeckProgram",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title_slug", models.SlugField(max_length=255, unique=True)),
                ("eligible_after", models.DateTimeField()),
            ],
        ),
        migrations.CreateModel(
            name="StarterDeckProvisioning",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "title_slug",
                    models.SlugField(max_length=255),
                ),
                (
                    "deck",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="collection.deck",
                    ),
                ),
                (
                    "last_attempted_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "last_dispatched_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "completed_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                ("last_error", models.TextField(blank=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="starter_deck_provisionings",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["user", "completed_at"],
                        name="starter_deck_user_pending_idx",
                    ),
                    models.Index(
                        condition=models.Q(("completed_at__isnull", True)),
                        fields=[
                            "title_slug",
                            "last_attempted_at",
                            "last_dispatched_at",
                        ],
                        name="starter_deck_pending_due_idx",
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("user", "title_slug"),
                        name="starter_deck_provisioning_u_user_title",
                    )
                ],
            },
        ),
        migrations.RunPython(
            create_archetype_starter_program,
            migrations.RunPython.noop,
        ),
    ]
