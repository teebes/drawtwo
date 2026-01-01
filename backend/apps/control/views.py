import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SiteSettings
from .serializers import (
    SiteSettingsSerializer,
    UserManagementSerializer,
    UserStatusUpdateSerializer,
    UserAnalyticsSerializer,
    RecentUsersSerializer,
    MatchmakingQueueEntrySerializer,
)
from apps.gameplay.models import MatchmakingQueue, Game
from apps.gameplay.services import GameService
from apps.builder.models import Title

User = get_user_model()
logger = logging.getLogger(__name__)


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


class MatchmakingQueueAdminView(APIView):
    """View matchmaking queue state for administrators."""

    permission_classes = [IsStaffPermission]

    def get(self, request):
        status_filter = request.query_params.get('status', MatchmakingQueue.STATUS_QUEUED)
        ladder_type = request.query_params.get('ladder_type')
        limit_param = request.query_params.get('limit', 100)
        try:
            limit = max(1, min(int(limit_param), 500))
        except (ValueError, TypeError):
            limit = 100

        queryset = (
            MatchmakingQueue.objects.select_related(
                'user',
                'deck',
                'deck__hero',
                'deck__title',
                'matched_with',
                'matched_with__user',
                'game',
            )
            .order_by('-created_at')
        )

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if ladder_type:
            if ladder_type not in dict(Game.LADDER_TYPE_CHOICES):
                return Response({'error': 'Invalid ladder type'}, status=status.HTTP_400_BAD_REQUEST)
            queryset = queryset.filter(ladder_type=ladder_type)

        entries = queryset[:limit]
        serializer = MatchmakingQueueEntrySerializer(entries, many=True)

        status_counts_qs = MatchmakingQueue.objects
        if ladder_type:
            status_counts_qs = status_counts_qs.filter(ladder_type=ladder_type)
        status_counts = {
            item['status']: item['count']
            for item in status_counts_qs.values('status').annotate(count=Count('id'))
        }

        title_summary_qs = (
            MatchmakingQueue.objects.filter(status=MatchmakingQueue.STATUS_QUEUED)
            .values('deck__title_id', 'deck__title__name', 'deck__title__slug')
            .annotate(queued_count=Count('id'))
            .order_by('-queued_count')
        )
        if ladder_type:
            title_summary_qs = title_summary_qs.filter(ladder_type=ladder_type)
        title_summary = [
            {
                'title_id': row['deck__title_id'],
                'title_name': row['deck__title__name'],
                'title_slug': row['deck__title__slug'],
                'queued_count': row['queued_count'],
            }
            for row in title_summary_qs
        ]

        return Response({
            'entries': serializer.data,
            'summary': {
                'queued': status_counts.get(MatchmakingQueue.STATUS_QUEUED, 0),
                'matched': status_counts.get(MatchmakingQueue.STATUS_MATCHED, 0),
                'cancelled': status_counts.get(MatchmakingQueue.STATUS_CANCELLED, 0),
                'title_summary': title_summary,
            },
            'status_filter': status_filter,
            'ladder_type': ladder_type,
            'limit': limit,
            'refreshed_at': timezone.now(),
        })


class MatchmakingManualRunView(APIView):
    """Trigger a manual matchmaking pass from the control panel."""

    permission_classes = [IsStaffPermission]

    def post(self, request):
        title_id = request.data.get('title_id')
        ladder_type = request.data.get('ladder_type')

        try:
            if title_id:
                try:
                    title = Title.objects.get(id=title_id)
                except Title.DoesNotExist:
                    return Response({'error': 'Title not found'}, status=status.HTTP_404_NOT_FOUND)

                if ladder_type and ladder_type not in dict(Game.LADDER_TYPE_CHOICES):
                    return Response({'error': 'Invalid ladder type'}, status=status.HTTP_400_BAD_REQUEST)

                matches_created = GameService.process_matchmaking(
                    title.id,
                    ladder_type=ladder_type,
                )
                logger.info(
                    "Manual matchmaking run for title %s (%s) created %s matches",
                    title.id,
                    title.name,
                    matches_created,
                )
                return Response({
                    'message': f'Processed matchmaking queue for {title.name}',
                    'processed_titles': 1,
                    'matches_created': matches_created,
                })

            title_queryset = MatchmakingQueue.objects.filter(status=MatchmakingQueue.STATUS_QUEUED)
            if ladder_type:
                if ladder_type not in dict(Game.LADDER_TYPE_CHOICES):
                    return Response({'error': 'Invalid ladder type'}, status=status.HTTP_400_BAD_REQUEST)
                title_queryset = title_queryset.filter(ladder_type=ladder_type)

            title_ids = list(
                title_queryset
                .values_list('deck__title_id', flat=True)
                .distinct()
            )

            if not title_ids:
                return Response({
                    'message': 'No queued players to process',
                    'processed_titles': 0,
                    'matches_created': 0,
                })

            total_matches = 0
            for tid in title_ids:
                total_matches += GameService.process_matchmaking(
                    tid,
                    ladder_type=ladder_type,
                )

            logger.info(
                "Manual matchmaking run for %s titles created %s matches",
                len(title_ids),
                total_matches,
            )

            return Response({
                'message': f'Processed matchmaking for {len(title_ids)} title(s)',
                'processed_titles': len(title_ids),
                'matches_created': total_matches,
            })

        except Exception as exc:
            logger.exception("Manual matchmaking run failed: %s", exc)
            return Response(
                {'error': f'Failed to process matchmaking: {exc}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


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
