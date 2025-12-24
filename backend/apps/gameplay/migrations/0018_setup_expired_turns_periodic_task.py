# Generated manually for setting up periodic task

from django.db import migrations


def create_periodic_task(apps, schema_editor):
    """Create the periodic task to check for expired turns"""
    try:
        IntervalSchedule = apps.get_model('django_celery_beat', 'IntervalSchedule')
        PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')

        # Create or get the interval schedule (every 5 seconds)
        # Note: period is a string field, not a constant
        schedule, created = IntervalSchedule.objects.get_or_create(
            every=5,
            period='seconds',
        )

        # Create or update the periodic task
        task, created = PeriodicTask.objects.get_or_create(
            name='Check expired turns',
            defaults={
                'task': 'apps.gameplay.tasks.check_expired_turns',
                'interval': schedule,
                'enabled': True,
            }
        )

        if not created:
            # Update existing task to ensure it's enabled and using correct schedule
            task.interval = schedule
            task.enabled = True
            task.task = 'apps.gameplay.tasks.check_expired_turns'
            task.save()
    except LookupError:
        # django-celery-beat not installed or models not available
        # This is fine - the migration will be skipped
        pass


def remove_periodic_task(apps, schema_editor):
    """Remove the periodic task"""
    try:
        PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')
        PeriodicTask.objects.filter(name='Check expired turns').delete()
    except LookupError:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('gameplay', '0017_refactor_time_control_fields'),
        # Note: django_celery_beat migrations should run before this
        # If django_celery_beat is not installed, this migration will still work
    ]

    operations = [
        migrations.RunPython(create_periodic_task, remove_periodic_task),
    ]
