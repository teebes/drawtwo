from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Game
from .schemas import GameState, GameSummary, GameList


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def game_detail(request, game_id):
    game = get_object_or_404(Game, id=game_id)

    game_data = GameState.model_validate(game.state).model_dump()

    # In addition to the game data, we also have to return who the viewing user
    # is.
    if game.side_a.user == request.user:
        game_data['viewer'] = 'side_a'
    else:
        game_data['viewer'] = 'side_b'

    game_data['is_vs_ai'] = game.is_vs_ai

    return Response(game_data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_games(request):
    games = Game.objects.filter(
        Q(side_a__user=request.user) | Q(side_b__user=request.user)
    ).order_by('-created_at')

    #games = Game.objects.all()

    game_summaries = []

    for game in games:
        if game.side_a.user == request.user:
            game_summaries.append(GameSummary(
                id=game.id,
                name=game.side_b.owner_name,
            ))
        else:
            game_summaries.append(GameSummary(
                id=game.id,
                name=game.side_a.owner_name,
            ))

    return Response(GameList(games=game_summaries).model_dump())