import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("collection", "0015_deck_compositions"),
        ("gameplay", "0028_push_notifications"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="GameLoadout",
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
                    "side",
                    models.CharField(
                        choices=[("side_a", "Side_a"), ("side_b", "Side_b")],
                        max_length=10,
                    ),
                ),
                ("hero_slug", models.SlugField(max_length=255)),
                ("hero_name", models.CharField(max_length=120)),
                ("deck_name", models.CharField(max_length=255)),
                (
                    "composition",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="game_loadouts",
                        to="collection.deckcomposition",
                    ),
                ),
                (
                    "game",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="loadouts",
                        to="gameplay.game",
                    ),
                ),
                (
                    "player",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="game_loadouts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "source_deck",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="game_loadouts",
                        to="collection.deck",
                    ),
                ),
                (
                    "source_revision",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="game_loadouts",
                        to="collection.deckrevision",
                    ),
                ),
            ],
            options={
                "db_table": "gameplay_game_loadout",
                "indexes": [
                    models.Index(
                        fields=["composition", "player"],
                        name="gameplay_gl_comp_player_idx",
                    ),
                    models.Index(
                        fields=["composition", "hero_slug"],
                        name="gameplay_gl_comp_hero_idx",
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("game", "side"),
                        name="gameplay_game_loadout_game_side_unique",
                    ),
                ],
            },
        ),
    ]
