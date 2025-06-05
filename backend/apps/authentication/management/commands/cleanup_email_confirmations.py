from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from allauth.account.models import EmailConfirmation


class Command(BaseCommand):
    help = 'Clean up old email confirmations (older than specified days)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Delete confirmations older than this many days (default: 7)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']

        # Calculate cutoff date
        cutoff_date = timezone.now() - timedelta(days=days)

        # Find old confirmations
        old_confirmations = EmailConfirmation.objects.filter(
            created__lt=cutoff_date
        )

        count = old_confirmations.count()

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN: Would delete {count} email confirmations older than {days} days'
                )
            )
            # Show some examples
            for conf in old_confirmations[:5]:
                self.stdout.write(f'  - {conf.email_address.email}: {conf.created}')
            if count > 5:
                self.stdout.write(f'  ... and {count - 5} more')
        else:
            deleted_count, _ = old_confirmations.delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully deleted {deleted_count} old email confirmations'
                )
            )