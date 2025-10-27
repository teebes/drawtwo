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
    path('titles/<slug:title_slug>/opponents/', views.opponent_decks_by_title, name='opponent-decks-by-title'),
    path('decks/<int:deck_id>/', views.deck_detail, name='deck-detail'),

    # Deck card endpoints
    path('decks/<int:deck_id>/cards/<int:card_id>/', views.update_deck_card, name='update-deck-card'),
    path('decks/<int:deck_id>/cards/<int:card_id>/delete/', views.delete_deck_card, name='delete-deck-card'),
    path('decks/<int:deck_id>/cards/add/', views.add_deck_card, name='add-deck-card'),
]