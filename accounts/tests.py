from django.test import TestCase
from django.urls import reverse

from players.models import PlayerProfile
from .onboarding import onboarding_context
from .models import User, VerificationRequest


class VerificationFlowTests(TestCase):
    def test_player_onboarding_tracks_profile_progress(self):
        player = User.objects.create_user(
            username="onboard-player",
            email="onboard@example.com",
            password="pass12345",
            role="player",
        )

        context = onboarding_context(player)

        self.assertEqual(context["total"], 4)
        self.assertFalse(context["is_complete"])
        self.assertEqual(context["completed"], 0)

        profile = PlayerProfile.objects.get(user=player)
        profile.full_name = "Onboard Player"
        profile.age = 17
        profile.region = "Nairobi"
        profile.position = "Forward"
        profile.current_club = "School FC"
        profile.bio = "Quick forward with academy experience."
        profile.highlight_video = "https://example.com/highlight.mp4"
        profile.matches_played = 8
        profile.save()

        context = onboarding_context(player)

        self.assertGreaterEqual(context["completed"], 2)
        self.assertGreater(context["percent"], 0)

    def test_scout_can_request_and_staff_can_approve_verification(self):
        scout = User.objects.create_user(
            username="scout-test",
            email="scout@example.com",
            password="pass12345",
            role="scout",
        )
        staff = User.objects.create_user(
            username="staff-test",
            email="staff@example.com",
            password="pass12345",
            role="fan",
            is_staff=True,
        )

        self.client.force_login(scout)
        response = self.client.post(reverse("request_verification"), {
            "organization_name": "Nairobi Talent Network",
            "role_context": "Regional scout, Nairobi",
            "evidence": "Official listing and public references.",
        })

        self.assertRedirects(response, reverse("settings"))
        scout.refresh_from_db()
        self.assertEqual(scout.verification_status, User.VERIFICATION_PENDING)
        verification = VerificationRequest.objects.get(user=scout)
        self.assertEqual(verification.status, VerificationRequest.STATUS_PENDING)

        self.client.force_login(staff)
        response = self.client.post(reverse("review_verification_request", args=[verification.id, "approve"]))

        self.assertRedirects(response, reverse("verification_queue"))
        scout.refresh_from_db()
        verification.refresh_from_db()
        self.assertTrue(scout.is_verified_account)
        self.assertIsNotNone(scout.verified_at)
        self.assertEqual(verification.status, VerificationRequest.STATUS_APPROVED)
        self.assertEqual(verification.reviewed_by, staff)
