from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from apps.authentication.models import User
from apps.builder.models import HeroTemplate, Title
from apps.collection.models import Deck
from apps.gameplay.models import Game, MatchmakingQueue


class MatchmakingManualRunTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            email="staff@example.com",
            username="staff",
            is_staff=True,
        )
        self.user_a = User.objects.create_user(
            email="a@example.com",
            username="player-a",
        )
        self.user_b = User.objects.create_user(
            email="b@example.com",
            username="player-b",
        )
        self.title = Title.objects.create(
            slug="manual-run-title",
            author=self.staff,
            config={"min_cards_in_deck": 0},
        )
        self.hero = HeroTemplate.objects.create(
            title=self.title,
            slug="hero",
            name="Hero",
            health=30,
        )
        self.deck_a = Deck.objects.create(
            title=self.title,
            user=self.user_a,
            name="Deck A",
            hero=self.hero,
        )
        self.deck_b = Deck.objects.create(
            title=self.title,
            user=self.user_b,
            name="Deck B",
            hero=self.hero,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.staff)

    @patch("apps.control.views.GameService.process_matchmaking", return_value=1)
    def test_title_run_without_ladder_processes_queued_daily_scope(
        self, process_matchmaking
    ):
        MatchmakingQueue.objects.create(
            user=self.user_a,
            deck=self.deck_a,
            elo_rating=1200,
            status=MatchmakingQueue.STATUS_QUEUED,
            ladder_type=Game.LADDER_TYPE_DAILY,
        )
        MatchmakingQueue.objects.create(
            user=self.user_b,
            deck=self.deck_b,
            elo_rating=1210,
            status=MatchmakingQueue.STATUS_QUEUED,
            ladder_type=Game.LADDER_TYPE_DAILY,
        )

        response = self.client.post(
            "/api/control/matchmaking/run/",
            {"title_id": self.title.id},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        process_matchmaking.assert_called_once_with(
            self.title.id,
            ladder_type=Game.LADDER_TYPE_DAILY,
        )
        self.assertEqual(response.data["processed_titles"], 1)
        self.assertEqual(response.data["processed_ladders"], 1)
        self.assertEqual(response.data["matches_created"], 1)
