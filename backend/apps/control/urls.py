from django.urls import path
from . import views

app_name = 'control'

urlpatterns = [
    # Control panel overview
    path('overview/', views.control_panel_overview, name='overview'),

    # System status (health checks + metrics)
    path('system-status/', views.system_status, name='system_status'),

    # Matchmaking queue admin
    path('matchmaking/queue/', views.MatchmakingQueueAdminView.as_view(), name='matchmaking_queue'),
    path('matchmaking/run/', views.MatchmakingManualRunView.as_view(), name='matchmaking_run'),

    # Site settings
    path('settings/', views.SiteSettingsView.as_view(), name='site_settings'),

    # User analytics
    path('analytics/', views.UserAnalyticsView.as_view(), name='user_analytics'),

    # User management
    path('users/', views.UserManagementView.as_view(), name='user_management'),
    path('users/<int:user_id>/status/', views.UserStatusUpdateView.as_view(), name='user_status_update'),
    path('users/recent/', views.RecentUsersView.as_view(), name='recent_users'),
]