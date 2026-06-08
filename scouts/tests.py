from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from players.models import PlayerProfile


class ScoutSearchTests(TestCase):
    def test_scout_search_filters_by_score_video_and_saved_state(self):
        scout = User.objects.create_user(
            username="search-scout",
            email="search-scout@example.com",
            password="pass12345",
            role="scout",
        )
        strong_player = User.objects.create_user(
            username="strong-player",
            email="strong@example.com",
            password="pass12345",
            role="player",
        )
        weak_player = User.objects.create_user(
            username="weak-player",
            email="weak@example.com",
            password="pass12345",
            role="player",
        )
        PlayerProfile.objects.create(
            user=strong_player,
            full_name="Strong Player",
            age=17,
            nationality="Kenyan",
            region="Nairobi",
            position="Forward",
            current_club="Academy FC",
            height_cm=178,
            weight_kg=68,
            bio="Fast forward with strong movement.",
            highlight_video="https://example.com/highlight.mp4",
        )
        PlayerProfile.objects.create(
            user=weak_player,
            age=16,
            region="Mombasa",
            position="Goalkeeper",
        )
        scout.saved_players.add(strong_player)

        self.client.force_login(scout)
        response = self.client.get(reverse("scout_search"), {
            "min_score": "25",
            "completion": "75",
            "has_video": "1",
        })

        self.assertContains(response, "Strong Player")
        self.assertContains(response, "Saved")
        self.assertContains(response, "1 player found")
        self.assertNotContains(response, "weak-player")
