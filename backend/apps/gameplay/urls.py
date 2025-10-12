from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

# Create a router for ViewSets (if needed later)
router = DefaultRouter()

# URL patterns for the collection app
urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),

    # Game endpoints
    path('games/<int:game_id>/', views.game_detail, name='game-detail'),
    path('games/<int:game_id>/queue/', views.game_queue, name='game-queue'),
    path('games/<int:game_id>/advance/', views.advance_game, name='game-advance'),
    path('games/', views.current_games, name='current-games'),
    path('games/new/', views.create_game, name='game-create'),

]