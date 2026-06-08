from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from accounts.models import UserSettings
from posts.models import Opportunity, Post, TalentSpot
from .models import PlayerProfile


class PlayerDashboardTests(TestCase):
    def test_dashboard_talent_post_creates_talent_spot(self):
        player = User.objects.create_user(
            username="spot-player",
            email="spot-player@example.com",
            password="pass12345",
            role="player",
        )
        PlayerProfile.objects.create(user=player, age=17, region="Nairobi", position="Forward")

        self.client.force_login(player)
        response = self.client.post(reverse("dashboard"), {
            "category": Post.CATEGORY_TALENT,
            "prospect_name": "Nairobi winger",
            "location": "Kasarani",
            "content": "Quick winger with strong one-on-one ability.",
        })

        self.assertRedirects(response, reverse("dashboard"))
        spot = TalentSpot.objects.get(prospect_name="Nairobi winger")
        self.assertEqual(spot.spotted_by, player)
        self.assertEqual(spot.location, "Kasarani")

    def test_dashboard_shows_recommended_opportunities(self):
        club = User.objects.create_user(
            username="dashboard-club",
            email="dashboard-club@example.com",
            password="pass12345",
            role="club",
            verification_status=User.VERIFICATION_VERIFIED,
        )
        player = User.objects.create_user(
            username="dashboard-player",
            email="dashboard-player@example.com",
            password="pass12345",
            role="player",
        )
        PlayerProfile.objects.create(
            user=player,
            age=16,
            region="Nairobi",
            position="Forward",
        )
        Opportunity.objects.create(
            publisher=club,
            title="Nairobi forward trial",
            opportunity_type=Opportunity.TYPE_TRIAL,
            location="Kasarani",
            region="Nairobi",
            deadline=timezone.now().date() + timedelta(days=5),
            age_min=15,
            age_max=17,
            positions="Forward",
            description="A strong dashboard match.",
        )

        self.client.force_login(player)
        response = self.client.get(reverse("dashboard"))

        self.assertContains(response, "Nairobi forward trial")
        self.assertContains(response, "Position fit")

    def test_scout_card_renders_public_player_snapshot(self):
        player = User.objects.create_user(
            username="card-player",
            email="card-player@example.com",
            password="pass12345",
            role="player",
        )
        PlayerProfile.objects.create(
            user=player,
            full_name="Card Player",
            age=18,
            region="Nairobi",
            position="Forward",
            current_club="City Academy",
            matches_played=12,
            goals=8,
            assists=3,
        )

        response = self.client.get(reverse("scout_card", args=[player.id]))

        self.assertContains(response, "Card Player")
        self.assertContains(response, "Talent Score")
        self.assertContains(response, "City Academy")

    def test_private_scout_card_requires_scout_or_club(self):
        player = User.objects.create_user(
            username="private-card-player",
            email="private-card-player@example.com",
            password="pass12345",
            role="player",
        )
        PlayerProfile.objects.create(user=player, age=18, region="Nairobi", position="Forward")
        UserSettings.objects.create(
            user=player,
            profile_visibility=UserSettings.PROFILE_SCOUTS_CLUBS,
        )
        fan = User.objects.create_user(
            username="fan-card",
            email="fan-card@example.com",
            password="pass12345",
            role="fan",
        )
        scout = User.objects.create_user(
            username="scout-card",
            email="scout-card@example.com",
            password="pass12345",
            role="scout",
        )

        self.client.force_login(fan)
        fan_response = self.client.get(reverse("scout_card", args=[player.id]))
        self.assertRedirects(fan_response, reverse("feed"))

        self.client.force_login(scout)
        scout_response = self.client.get(reverse("scout_card", args=[player.id]))
        self.assertContains(scout_response, "private-card-player")
