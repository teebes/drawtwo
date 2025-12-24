from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, IntervalSchedule
import json


class Command(BaseCommand):
    help = 'Set up the periodic task to check for expired turns'

    def handle(self, *args, **options):
        # Create or get the interval schedule (every 5 seconds)
        schedule, created = IntervalSchedule.objects.get_or_create(
            every=5,
            period=IntervalSchedule.SECONDS,
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Created interval schedule: every 5 seconds'))
        else:
            self.stdout.write('Using existing interval schedule: every 5 seconds')

        # Create or update the periodic task
        task, created = PeriodicTask.objects.get_or_create(
            name='Check expired turns',
            defaults={
                'task': 'apps.gameplay.tasks.check_expired_turns',
                'interval': schedule,
                'enabled': True,
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS('Created periodic task: Check expired turns'))
        else:
            # Update existing task to ensure it's enabled and using correct schedule
            task.interval = schedule
            task.enabled = True
            task.task = 'apps.gameplay.tasks.check_expired_turns'
            task.save()
            self.stdout.write(self.style.SUCCESS('Updated periodic task: Check expired turns'))

        self.stdout.write(self.style.SUCCESS(
            f'Periodic task is {"enabled" if task.enabled else "disabled"}. '
            f'It will run every {schedule.every} {schedule.period}.'
        ))
