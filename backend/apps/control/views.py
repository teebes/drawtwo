from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination

from .models import SiteSettings
from .serializers import (
    SiteSettingsSerializer,
    UserManagementSerializer,
    UserStatusUpdateSerializer,
    UserAnalyticsSerializer,
    RecentUsersSerializer
)

User = get_user_model()


class IsStaffPermission(permissions.BasePermission):
    """Custom permission to only allow staff users."""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff


class SiteSettingsView(APIView):
    """API view for managing site settings."""

    permission_classes = [IsStaffPermission]

    def get(self, request):
        """Get current site settings."""
        settings = SiteSettings.get_settings()
        serializer = SiteSettingsSerializer(settings)
        return Response(serializer.data)

    def patch(self, request):
        """Update site settings."""
        settings = SiteSettings.get_settings()
        serializer = SiteSettingsSerializer(settings, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserAnalyticsView(APIView):
    """API view for user analytics and statistics."""

    permission_classes = [IsStaffPermission]

    def get(self, request):
        """Get user analytics data."""
        # Calculate date for last week
        one_week_ago = timezone.now() - timedelta(days=7)

        # Get user counts
        total_users = User.objects.count()
        users_last_week = User.objects.filter(created_at__gte=one_week_ago).count()

        # Get status counts
        status_counts = User.objects.aggregate(
            pending_users=Count('id', filter=Q(status=User.STATUS_PENDING)),
            approved_users=Count('id', filter=Q(status=User.STATUS_APPROVED)),
            suspended_users=Count('id', filter=Q(status=User.STATUS_SUSPENDED)),
            banned_users=Count('id', filter=Q(status=User.STATUS_BANNED)),
        )

        # Get daily signup trend for last 7 days
        recent_signups = []
        for i in range(7):
            date = timezone.now().date() - timedelta(days=i)
            next_date = date + timedelta(days=1)

            count = User.objects.filter(
                created_at__date=date
            ).count()

            recent_signups.append({
                'date': date.isoformat(),
                'count': count
            })

        # Reverse to get chronological order (oldest first)
        recent_signups.reverse()

        analytics_data = {
            'total_users': total_users,
            'users_last_week': users_last_week,
            'recent_signups': recent_signups,
            **status_counts
        }

        serializer = UserAnalyticsSerializer(analytics_data)
        return Response(serializer.data)


class UserManagementPagination(PageNumberPagination):
    """Custom pagination for user management."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class UserManagementView(ListAPIView):
    """API view for user management with filtering and pagination."""

    permission_classes = [IsStaffPermission]
    serializer_class = UserManagementSerializer
    pagination_class = UserManagementPagination

    def get_queryset(self):
        """Get filtered user queryset."""
        queryset = User.objects.all().order_by('-created_at')

        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Search by email or username
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(email__icontains=search) | Q(username__icontains=search)
            )

        return queryset


class UserStatusUpdateView(APIView):
    """API view for updating user status."""

    permission_classes = [IsStaffPermission]

    def patch(self, request, user_id):
        """Update user status."""
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Prevent staff users from changing their own status to non-approved
        if (user == request.user and
            request.data.get('status') != User.STATUS_APPROVED):
            return Response(
                {'error': 'You cannot change your own approval status'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = UserStatusUpdateSerializer(data=request.data)
        if serializer.is_valid():
            user.status = serializer.validated_data['status']
            user.save()

            # Return updated user data
            user_serializer = UserManagementSerializer(user)
            return Response(user_serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RecentUsersView(ListAPIView):
    """API view for recent user signups."""

    permission_classes = [IsStaffPermission]
    serializer_class = RecentUsersSerializer
    pagination_class = None  # No pagination for recent users

    def get_queryset(self):
        """Get the 20 most recent users."""
        return User.objects.all().order_by('-created_at')[:20]


@api_view(['GET'])
@permission_classes([IsStaffPermission])
def control_panel_overview(request):
    """Get overview data for the control panel dashboard."""
    # Get site settings
    settings = SiteSettings.get_settings()

    # Get quick stats
    one_week_ago = timezone.now() - timedelta(days=7)
    total_users = User.objects.count()
    users_last_week = User.objects.filter(created_at__gte=one_week_ago).count()
    pending_users = User.objects.filter(status=User.STATUS_PENDING).count()

    return Response({
        'site_settings': SiteSettingsSerializer(settings).data,
        'quick_stats': {
            'total_users': total_users,
            'users_last_week': users_last_week,
            'pending_users': pending_users,
        }
    })
