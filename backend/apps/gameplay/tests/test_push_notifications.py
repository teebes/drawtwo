from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from django.test import TestCase
from rest_framework.test import APIClient

from apps.authentication.models import User
from apps.builder.models import CardTemplate, HeroTemplate, Title
from apps.collection.models import Deck, DeckCard
from apps.gameplay.models import (
    FriendlyChallenge,
    Game,
    MatchmakingQueue,
    PushDevice,
    PushNotificationEvent,
)
from apps.gameplay.push import APNsClient, enqueue_friend_challenge_notification
from apps.gameplay.services import GameService


class PushDeviceRegistrationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="push@example.com", username="push")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_register_push_device_upserts_token_for_user(self):
        response = self.client.post(
            "/api/gameplay/push/devices/",
            {
                "token": "AA BB",
                "platform": "ios",
                "bundle_id": "com.example.app",
                "environment": "sandbox",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        device = PushDevice.objects.get()
        self.assertEqual(device.user, self.user)
        self.assertEqual(device.token, "aabb")
        self.assertEqual(device.bundle_id, "com.example.app")
        self.assertEqual(device.environment, "sandbox")
        self.assertTrue(device.is_active)

    def test_deactivate_current_push_device(self):
        PushDevice.objects.create(
            user=self.user,
            token="aabb",
            bundle_id="com.example.app",
            environment="sandbox",
        )

        response = self.client.post(
            "/api/gameplay/push/devices/current/deactivate/",
            {
                "token": "AA BB",
                "bundle_id": "com.example.app",
                "environment": "sandbox",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["deactivated"], 1)
        self.assertFalse(PushDevice.objects.get().is_active)


class APNsClientTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="apns@example.com", username="apns")
        self.device = PushDevice.objects.create(
            user=self.user,
            token="aabb",
            bundle_id="com.example.app",
            environment=PushDevice.ENVIRONMENT_SANDBOX,
        )

    @patch("apps.gameplay.push._apns_auth_token", return_value="token")
    def test_send_alert_includes_badge_count(self, _auth_token):
        http_client_cls = MagicMock()
        http_client = http_client_cls.return_value.__enter__.return_value
        http_client.post.return_value = Mock(status_code=200)

        with patch.dict(
            "sys.modules", {"httpx": SimpleNamespace(Client=http_client_cls)}
        ):
            APNsClient().send_alert(
                device=self.device,
                title="Your turn",
                body="Your turn against Opponent.",
                data={"notification_type": PushNotificationEvent.TYPE_TURN_READY},
                badge_count=3,
            )

        payload = http_client.post.call_args.kwargs["json"]
        self.assertEqual(payload["aps"]["badge"], 3)


class PushNotificationTriggerTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(
            email="player-a@example.com", username="player_a"
        )
        self.user_b = User.objects.create_user(
            email="player-b@example.com", username="player_b"
        )
        self.title = Title.objects.create(
            slug="push-title",
            author=self.user_a,
            config={"min_cards_in_deck": 4},
        )
        self.hero_a = HeroTemplate.objects.create(
            title=self.title,
            slug="hero-a",
            name="Hero A",
            health=30,
        )
        self.hero_b = HeroTemplate.objects.create(
            title=self.title,
            slug="hero-b",
            name="Hero B",
            health=30,
        )
        self.deck_a = Deck.objects.create(
            title=self.title,
            user=self.user_a,
            name="Deck A",
            hero=self.hero_a,
        )
        self.deck_b = Deck.objects.create(
            title=self.title,
            user=self.user_b,
            name="Deck B",
            hero=self.hero_b,
        )
        for index in range(4):
            card = CardTemplate.objects.create(
                title=self.title,
                slug=f"push-card-{index}",
                name=f"Push Card {index}",
                cost=1,
            )
            DeckCard.objects.create(deck=self.deck_a, card=card)
            DeckCard.objects.create(deck=self.deck_b, card=card)

    def test_turn_ready_push_event_created_when_main_turn_starts(self):
        game = GameService.create_game(
            self.deck_a,
            self.deck_b,
            randomize_starting_player=False,
        )
        game.type = Game.GAME_TYPE_FRIENDLY
        game.save(update_fields=["type"])

        GameService.step(game.id)
        GameService.process_command(
            game.id, {"type": "cmd_mulligan", "card_ids": []}, "side_a"
        )
        GameService.process_command(
            game.id, {"type": "cmd_mulligan", "card_ids": []}, "side_b"
        )
        GameService.step(game.id)

        event = PushNotificationEvent.objects.get(
            notification_type=PushNotificationEvent.TYPE_TURN_READY
        )
        self.assertEqual(event.user, self.user_a)
        self.assertEqual(event.data["game_id"], game.id)

    @patch("apps.gameplay.push.is_user_live_in_game", return_value=True)
    def test_turn_ready_push_event_skipped_when_player_is_live_in_game(
        self, is_user_live_in_game
    ):
        game = GameService.create_game(
            self.deck_a,
            self.deck_b,
            randomize_starting_player=False,
        )
        game.type = Game.GAME_TYPE_FRIENDLY
        game.save(update_fields=["type"])

        GameService.step(game.id)
        GameService.process_command(
            game.id, {"type": "cmd_mulligan", "card_ids": []}, "side_a"
        )
        GameService.process_command(
            game.id, {"type": "cmd_mulligan", "card_ids": []}, "side_b"
        )
        GameService.step(game.id)

        self.assertFalse(
            PushNotificationEvent.objects.filter(
                notification_type=PushNotificationEvent.TYPE_TURN_READY
            ).exists()
        )
        is_user_live_in_game.assert_called_once_with(
            game_id=game.id,
            user_id=self.user_a.id,
            side="side_a",
        )

    def test_friend_challenge_push_event_created(self):
        challenge = FriendlyChallenge.objects.create(
            challenger=self.user_a,
            challengee=self.user_b,
            title=self.title,
            challenger_deck=self.deck_a,
            status=FriendlyChallenge.STATUS_PENDING,
        )

        enqueue_friend_challenge_notification(challenge)

        event = PushNotificationEvent.objects.get(
            notification_type=PushNotificationEvent.TYPE_FRIEND_CHALLENGE
        )
        self.assertEqual(event.user, self.user_b)
        self.assertEqual(event.data["challenge_id"], challenge.id)

    def test_matchmaking_push_events_created_when_ladder_match_starts(self):
        MatchmakingQueue.objects.create(
            user=self.user_a,
            deck=self.deck_a,
            elo_rating=1200,
            status=MatchmakingQueue.STATUS_QUEUED,
            ladder_type=Game.LADDER_TYPE_RAPID,
        )
        MatchmakingQueue.objects.create(
            user=self.user_b,
            deck=self.deck_b,
            elo_rating=1205,
            status=MatchmakingQueue.STATUS_QUEUED,
            ladder_type=Game.LADDER_TYPE_RAPID,
        )

        GameService.process_matchmaking(self.title.id, Game.LADDER_TYPE_RAPID)

        match_events = PushNotificationEvent.objects.filter(
            notification_type=PushNotificationEvent.TYPE_MATCH_STARTED
        )
        self.assertEqual(match_events.count(), 2)
        self.assertSetEqual(
            set(match_events.values_list("user_id", flat=True)),
            {self.user_a.id, self.user_b.id},
        )
