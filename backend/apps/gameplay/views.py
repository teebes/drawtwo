from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import Game
from .schemas import GameState


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def game_detail(request, game_id):
    game = get_object_or_404(Game, id=game_id)
    return Response(GameState.model_validate(game.state).model_dump())