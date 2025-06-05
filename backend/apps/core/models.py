"""
Core base models for the DrawTwo project.

This module provides abstract base models that can be inherited by other models
throughout the project to provide common functionality.

Usage Examples:

1. Simple timestamped model:
    ```python
    from apps.core.models import TimestampedModel

    class Post(TimestampedModel):
        title = models.CharField(max_length=200)
        content = models.TextField()

        # Automatically gets created_at and updated_at fields
    ```

2. Full-featured model with UUID and soft delete:
    ```python
    from apps.core.models import BaseModel

    class Article(BaseModel):
        title = models.CharField(max_length=200)
        content = models.TextField()

        # Automatically gets:
        # - UUID primary key (id)
        # - created_at, updated_at timestamps
        # - is_active boolean for soft delete
    ```

3. Advanced soft delete model:
    ```python
    from apps.core.models import SoftDeleteModel

    class Comment(SoftDeleteModel):
        text = models.TextField()
        post = models.ForeignKey(Post, on_delete=models.CASCADE)

        # Usage:
        # comment.delete()  # Soft delete (sets is_active=False, deleted_at=timestamp)
        # comment.restore()  # Restore soft-deleted object
        # comment.hard_delete()  # Actually delete from database
        #
        # Comment.objects.all()  # Only active comments
        # Comment.objects.with_deleted()  # All comments including deleted
        # Comment.objects.deleted_only()  # Only deleted comments
    ```

Available base models:
- TimestampedModel: Basic timestamps (created_at, updated_at)
- BaseModel: UUID primary key + timestamps + is_active flag
- SoftDeleteModel: Full soft delete functionality with custom manager
"""

import uuid
from django.db import models
from django.utils import timezone


class TimestampedModel(models.Model):
    """
    Abstract base model that provides created_at and updated_at fields.
    Inherit from this for basic timestamp tracking.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BaseModel(TimestampedModel):
    """
    Enhanced abstract base model with UUID primary key, timestamps, and soft delete.
    Inherit from this for full-featured models.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    is_active = models.BooleanField(default=True, help_text="Soft delete flag")

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet):
    """Custom QuerySet that excludes soft-deleted objects by default."""

    def active(self):
        """Return only active (non-deleted) objects."""
        return self.filter(is_active=True)

    def deleted(self):
        """Return only soft-deleted objects."""
        return self.filter(is_active=False)

    def with_deleted(self):
        """Return all objects including soft-deleted ones."""
        return self


class SoftDeleteManager(models.Manager):
    """Custom Manager that excludes soft-deleted objects by default."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).active()

    def with_deleted(self):
        """Return all objects including soft-deleted ones."""
        return SoftDeleteQuerySet(self.model, using=self._db)

    def deleted_only(self):
        """Return only soft-deleted objects."""
        return SoftDeleteQuerySet(self.model, using=self._db).deleted()


class SoftDeleteModel(BaseModel):
    """
    Enhanced base model with soft delete functionality.
    Objects are not actually deleted, just marked as inactive.
    """
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()  # Access to all objects including deleted

    def delete(self, using=None, keep_parents=False):
        """Soft delete: mark as inactive and set deleted_at timestamp."""
        self.is_active = False
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_active', 'deleted_at'])

    def hard_delete(self, using=None, keep_parents=False):
        """Actually delete the object from the database."""
        super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        """Restore a soft-deleted object."""
        self.is_active = True
        self.deleted_at = None
        self.save(update_fields=['is_active', 'deleted_at'])

    class Meta:
        abstract = True
