from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

# Create a router for ViewSets (if needed later)
router = DefaultRouter()

# URL patterns for the collection app
urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),

    # Deck endpoints
    path('titles/<slug:title_slug>/decks/', views.deck_list_by_title, name='deck-list-by-title'),
    path('decks/<int:deck_id>/', views.deck_detail, name='deck-detail'),
]