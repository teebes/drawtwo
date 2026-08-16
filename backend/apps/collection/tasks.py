"""Background recovery for starter-deck provisioning."""

import logging
from datetime import datetime, timedelta

from celery import shared_task
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Exists, F, OuterRef, Q
from django.utils import timezone

from apps.collection.models import StarterDeckProgram, StarterDeckProvisioning
from apps.collection.provisioning import (
    STARTER_DECK_RETRY_BACKOFF,
    load_starter_deck_definitions,
    provision_starter_decks_for_user,
)

STARTER_DECK_DISPATCH_LEASE = timedelta(minutes=5)
logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, ignore_result=True)
def provision_starter_decks_for_user_task(self, user_id: int) -> int:
    """Retry a new account's pending starter decks outside request handling."""

    user_model = get_user_model()
    try:
        user = user_model.objects.get(pk=user_id, deleted_at__isnull=True)
    except user_model.DoesNotExist:
        return 0

    try:
        provisioned = provision_starter_decks_for_user(
            user,
            respect_backoff=True,
        )
    except Exception as exc:
        raise self.retry(
            exc=exc,
            countdown=int(STARTER_DECK_RETRY_BACKOFF.total_seconds()),
        )

    return len(provisioned)


@transaction.atomic
def _reserve_due_provisionings(
    title_slugs: list[str],
    *,
    batch_size: int,
) -> tuple[datetime, list[tuple[int, tuple[int, ...]]]]:
    """Lease due rows so concurrent or repeated sweeps do not duplicate work."""

    now = timezone.now()
    retry_before = now - STARTER_DECK_RETRY_BACKOFF
    lease_before = now - STARTER_DECK_DISPATCH_LEASE
    due_rows = list(
        StarterDeckProvisioning.objects.select_for_update(
            of=("self",),
            skip_locked=True,
        )
        .filter(
            title_slug__in=title_slugs,
            completed_at__isnull=True,
            user__deleted_at__isnull=True,
        )
        .filter(
            Q(last_attempted_at__isnull=True) | Q(last_attempted_at__lte=retry_before)
        )
        .filter(
            Q(last_dispatched_at__isnull=True) | Q(last_dispatched_at__lte=lease_before)
        )
        .order_by(F("last_attempted_at").asc(nulls_first=True), "pk")
        .values_list("pk", "user_id")[:batch_size]
    )
    if not due_rows:
        return now, []

    row_ids_by_user: dict[int, list[int]] = {}
    for row_id, user_id in due_rows:
        row_ids_by_user.setdefault(user_id, []).append(row_id)
    StarterDeckProvisioning.objects.filter(
        pk__in=[row_id for row_id, _ in due_rows]
    ).update(last_dispatched_at=now, updated_at=now)

    reservations = [
        (user_id, tuple(row_ids)) for user_id, row_ids in row_ids_by_user.items()
    ]
    return now, reservations


@shared_task(ignore_result=True)
def reconcile_starter_deck_provisionings(batch_size: int = 250) -> int:
    """Repair missing promises and dispatch a bounded batch of due retries."""

    definitions = load_starter_deck_definitions()
    title_slugs = [definition.title_slug for definition in definitions]
    user_model = get_user_model()
    program_cutoffs = dict(
        StarterDeckProgram.objects.filter(title_slug__in=title_slugs).values_list(
            "title_slug",
            "eligible_after",
        )
    )
    active_title_slugs = [
        title_slug for title_slug in title_slugs if title_slug in program_cutoffs
    ]

    for title_slug in title_slugs:
        eligible_after = program_cutoffs.get(title_slug)
        if eligible_after is None:
            logger.error(
                "Cannot reconcile starter deck without a program cutoff: %s",
                title_slug,
            )
            continue
        promise = StarterDeckProvisioning.objects.filter(
            user_id=OuterRef("pk"),
            title_slug=title_slug,
        )
        missing_user_ids = list(
            user_model.objects.filter(
                created_at__gt=eligible_after,
                deleted_at__isnull=True,
            )
            .annotate(_has_starter_promise=Exists(promise))
            .filter(_has_starter_promise=False)
            .order_by("pk")
            .values_list("pk", flat=True)[:batch_size]
        )
        StarterDeckProvisioning.objects.bulk_create(
            [
                StarterDeckProvisioning(
                    user_id=user_id,
                    title_slug=title_slug,
                )
                for user_id in missing_user_ids
            ],
            ignore_conflicts=True,
        )

    dispatched_at, reservations = _reserve_due_provisionings(
        active_title_slugs,
        batch_size=batch_size,
    )

    dispatched = 0
    for user_id, row_ids in reservations:
        try:
            provision_starter_decks_for_user_task.delay(user_id)
        except Exception:
            now = timezone.now()
            StarterDeckProvisioning.objects.filter(
                pk__in=row_ids,
                completed_at__isnull=True,
                last_dispatched_at=dispatched_at,
            ).update(last_dispatched_at=None, updated_at=now)
            raise
        dispatched += 1
    return dispatched
