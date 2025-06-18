from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_email_task(self, subject, message, recipient_list):
    """
    Send an email asynchronously using Celery.

    Args:
        subject (str): Email subject
        message (str): Email message body
        recipient_list (list): List of recipient email addresses

    Returns:
        dict: Result dictionary with success status and message
    """
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            fail_silently=False,
        )
        logger.info(f"Email sent successfully to {recipient_list}")
        return {
            'success': True,
            'message': f'Email sent to {len(recipient_list)} recipients'
        }
    except Exception as exc:
        logger.error(f"Email sending failed: {exc}")
        # Retry the task with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task
def cleanup_old_data():
    """
    Example periodic task to clean up old data.
    This can be scheduled using django-celery-beat.
    """
    from datetime import datetime, timedelta
    from django.utils import timezone

    # Example: Clean up old sessions
    cutoff_date = timezone.now() - timedelta(days=30)

    logger.info(f"Running cleanup task for data older than {cutoff_date}")

    # Add your cleanup logic here
    # e.g., delete old records, clear caches, etc.

    return f"Cleanup completed at {timezone.now()}"


@shared_task
def process_background_job(job_data):
    """
    Example task for processing background jobs.

    Args:
        job_data (dict): Data to process

    Returns:
        dict: Processing result
    """
    import time

    logger.info(f"Processing background job: {job_data.get('id', 'unknown')}")

    # Simulate some processing time
    time.sleep(2)

    # Add your processing logic here
    result = {
        'job_id': job_data.get('id'),
        'status': 'completed',
        'processed_at': timezone.now().isoformat(),
        'result': 'Job processed successfully'
    }

    logger.info(f"Background job completed: {result}")
    return result