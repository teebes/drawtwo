from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

# Create a router for ViewSets (if needed later)
router = DefaultRouter()

# URL patterns for the builder app
urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),

    # Add custom URL patterns here as needed
    # Example:
    # path('projects/', views.ProjectListView.as_view(), name='project-list'),
]