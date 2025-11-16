from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('collection', '0001_initial'),
        ('builder', '0001_initial'),
        ('gameplay', '0006_matchmakingqueue'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='is_friendly',
            field=models.BooleanField(default=False, help_text='Friend vs Friend games are unrated'),
        ),
        migrations.CreateModel(
            name='FriendlyChallenge',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('status', models.CharField(choices=[('pending', 'pending'), ('accepted', 'accepted'), ('cancelled', 'cancelled'), ('expired', 'expired')], default='pending', max_length=20)),
                ('challenger', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='challenges_sent', to=settings.AUTH_USER_MODEL)),
                ('challengee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='challenges_received', to=settings.AUTH_USER_MODEL)),
                ('title', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='friendly_challenges', to='builder.title')),
                ('challenger_deck', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='as_challenger_in_challenges', to='collection.deck')),
                ('challengee_deck', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='as_challengee_in_challenges', to='collection.deck')),
                ('game', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='friendly_challenge', to='gameplay.game')),
            ],
            options={
                'db_table': 'gameplay_friendly_challenge',
            },
        ),
        migrations.AddIndex(
            model_name='friendlychallenge',
            index=models.Index(fields=['status', 'title'], name='gameplay_fr_status__6a03a4_idx'),
        ),
        migrations.AddIndex(
            model_name='friendlychallenge',
            index=models.Index(fields=['challenger', 'challengee', 'status'], name='gameplay_fr_challen_1de358_idx'),
        ),
        migrations.AddConstraint(
            model_name='friendlychallenge',
            constraint=models.CheckConstraint(check=models.Q(('challenger', models.F('challengee')), _negated=True), name='friendly_challenge_no_self'),
        ),
    ]
