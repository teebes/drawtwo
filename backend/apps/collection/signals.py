"""Collection-related model signals."""

import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.collection.provisioning import provision_starter_decks_for_user
from apps.collection.tasks import provision_starter_decks_for_user_task

logger = logging.getLogger(__name__)
User = get_user_model()


@receiver(post_save, sender=User, dispatch_uid="collection_provision_starter_decks")
def provision_starter_decks_on_user_creation(
    sender,
    instance,
    created,
    raw=False,
    **kwargs,
):
    """Give each newly created account its configured title starter decks."""

    if not created or raw:
        return

    try:
        # Keep provisioning failures inside a savepoint so callers wrapping user
        # creation in transaction.atomic() are still able to commit the account.
        with transaction.atomic():
            provision_starter_decks_for_user(instance)
    except Exception:
        # A content/configuration problem must not make account creation fail.
        logger.exception("Could not provision starter decks for user %s", instance.pk)

    # Queue an idempotent second pass after the account commits. This also repairs
    # the uncommon case where creating the durable promise itself failed.
    transaction.on_commit(
        lambda user_id=instance.pk: provision_starter_decks_for_user_task.apply_async(
            args=[user_id],
            countdown=30,
        ),
        robust=True,
    )
