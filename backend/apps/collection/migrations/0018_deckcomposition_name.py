from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("collection", "0017_starterdeckprovisioning"),
    ]

    operations = [
        migrations.AddField(
            model_name="deckcomposition",
            name="name",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
    ]
