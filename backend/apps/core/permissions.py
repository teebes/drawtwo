from rest_framework import permissions


class CanViewTitle(permissions.BasePermission):
    """
    Custom permission to check if user can view a title.

    - Published titles can be viewed by anyone (including anonymous users)
    - Unpublished titles can only be viewed by the author or builders
    """

    def has_object_permission(self, request, view, obj):
        """
        Check if the user has permission to view the title object.
        obj should be a Title instance.
        """
        return obj.can_be_viewed_by(request.user)
