from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

# Create a router for ViewSets (if needed later)
router = DefaultRouter()

# URL patterns for the builder app
urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),

    # Title endpoints
    path('titles/<slug:slug>/', views.title_by_slug, name='title-by-slug'),

    # Card endpoints
    path('titles/<slug:title_slug>/cards/', views.create_card, name='card-create'),
    path('titles/<slug:title_slug>/cards/<slug:card_slug>/', views.card_detail, name='card-detail'),
    path('titles/<slug:title_slug>/cards/<slug:card_slug>/yaml/', views.card_yaml, name='card-yaml'),

    # YAML ingestion endpoint
    path('titles/<slug:title_slug>/ingest/', views.ingest_yaml, name='ingest-yaml'),
]