from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

# Create a router for ViewSets (if needed later)
router = DefaultRouter()

# URL patterns for the builder app
urlpatterns = [
    # Include router URLs
    path("", include(router.urls)),
    # Title endpoints
    path("titles/<slug:slug>/", views.title_by_slug, name="title-by-slug"),
    path("titles/<slug:title_slug>/config/", views.title_config, name="title-config"),
    path(
        "titles/<slug:title_slug>/content/",
        views.title_content_config,
        name="title-content-config",
    ),
    path(
        "titles/<slug:title_slug>/config/yaml/",
        views.title_config_yaml,
        name="title-config-yaml",
    ),
    # Card endpoints
    path("titles/<slug:title_slug>/cards/", views.create_card, name="card-create"),
    path(
        "titles/<slug:title_slug>/cards/<slug:card_slug>/",
        views.card_detail,
        name="card-detail",
    ),
    path(
        "titles/<slug:title_slug>/cards/<slug:card_slug>/yaml/",
        views.card_yaml,
        name="card-yaml",
    ),
    # Hero endpoints
    path(
        "titles/<slug:title_slug>/heroes/<slug:hero_slug>/yaml/",
        views.hero_yaml,
        name="hero-yaml",
    ),
    # YAML ingestion endpoint
    path("titles/<slug:title_slug>/ingest/", views.ingest_yaml, name="ingest-yaml"),
]
