from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from players.models import PlayerProfile
from .models import Notification, Opportunity, OpportunityApplication, Post, TalentSpot
from .selectors import recommended_opportunities_for_player


class OpportunityFlowTests(TestCase):
    def test_fetch_new_posts_returns_full_interactive_markup(self):
        user = User.objects.create_user(
            username="live-feed-user",
            email="live-feed@example.com",
            password="pass12345",
            role="fan",
        )
        post = Post.objects.create(
            author=user,
            category=Post.CATEGORY_MATCH,
            content="Late winner at a Nairobi school final.",
            location="Nairobi",
        )

        self.client.force_login(user)
        response = self.client.get(reverse("fetch_new_posts"), {"last_post_id": 0})
        html = response.json()["html"]

        self.assertIn("Late winner at a Nairobi school final.", html)
        self.assertIn('class="comment-form"', html)
        self.assertIn(reverse("report_post", args=[post.id]), html)
        self.assertIn("No comments yet.", html)

    def test_talent_spots_filter_by_confirmations_media_and_location(self):
        reporter = User.objects.create_user(
            username="spot-reporter",
            email="spot-reporter@example.com",
            password="pass12345",
            role="fan",
        )
        confirmers = [
            User.objects.create_user(
                username=f"confirmer-{index}",
                email=f"confirmer-{index}@example.com",
                password="pass12345",
                role="fan",
            )
            for index in range(3)
        ]
        strong_spot = TalentSpot.objects.create(
            spotted_by=reporter,
            prospect_name="Confirmed winger",
            position="Forward",
            location="Kasarani, Nairobi",
            team_or_school="Local Academy",
            event_name="County finals",
            notes="Fast wide player with strong delivery.",
            evidence_image="talent_spots/images/winger.jpg",
        )
        strong_spot.confirmations.add(*confirmers)
        TalentSpot.objects.create(
            spotted_by=reporter,
            prospect_name="Unconfirmed keeper",
            position="Goalkeeper",
            location="Mombasa",
            notes="Needs another look.",
        )

        response = self.client.get(reverse("talent_spots"), {
            "location": "Nairobi",
            "min_confirmations": "3",
            "has_media": "1",
            "sort": "confirmed",
        })

        self.assertContains(response, "Confirmed winger")
        self.assertContains(response, "1 talent spot found")
        self.assertContains(response, "Evidence media attached")
        self.assertNotContains(response, "Unconfirmed keeper")

    def test_opportunities_filter_by_region_age_deadline_and_sort(self):
        club = User.objects.create_user(
            username="filter-club",
            email="filter-club@example.com",
            password="pass12345",
            role="club",
        )
        today = timezone.now().date()
        matching = Opportunity.objects.create(
            publisher=club,
            title="Nairobi U17 academy intake",
            opportunity_type=Opportunity.TYPE_ACADEMY,
            location="Kasarani",
            region="Nairobi",
            deadline=today + timedelta(days=5),
            event_date=today + timedelta(days=10),
            age_min=15,
            age_max=17,
            positions="Forwards",
            description="Academy intake for Nairobi forwards.",
        )
        Opportunity.objects.create(
            publisher=club,
            title="Coast senior open day",
            opportunity_type=Opportunity.TYPE_OPEN_DAY,
            location="Mombasa",
            region="Mombasa",
            deadline=today + timedelta(days=20),
            age_min=19,
            age_max=23,
            positions="Goalkeepers",
            description="Senior open day.",
        )

        response = self.client.get(reverse("opportunities"), {
            "region": "Nairobi",
            "age": "16",
            "deadline": "7",
            "sort": "deadline",
            "status": "open",
        })

        self.assertContains(response, matching.title)
        self.assertContains(response, "1 opportunity found")
        self.assertContains(response, "Ages 15 - 17")
        self.assertNotContains(response, "Coast senior open day")

    def test_notifications_page_filters_unread_all_and_read_items(self):
        user = User.objects.create_user(
            username="notify-user",
            email="notify@example.com",
            password="pass12345",
            role="fan",
        )
        actor = User.objects.create_user(
            username="notify-actor",
            email="notify-actor@example.com",
            password="pass12345",
            role="scout",
        )
        unread_notification = Notification.objects.create(
            recipient=user,
            actor=actor,
            message="Unread scouting update",
            target_url=reverse("feed"),
        )
        Notification.objects.create(
            recipient=user,
            actor=actor,
            message="Read shortlist update",
            target_url=reverse("feed"),
            is_read=True,
        )

        self.client.force_login(user)
        response = self.client.get(reverse("notifications"))
        self.assertContains(response, "Unread scouting update")
        self.assertNotContains(response, "Read shortlist update")
        self.assertContains(response, "Unread")
        self.assertContains(response, reverse("open_notification", args=[unread_notification.id]))

        response = self.client.get(reverse("notifications"), {"status": "all"})
        self.assertContains(response, "Unread scouting update")
        self.assertContains(response, "Read shortlist update")

        response = self.client.get(reverse("notifications"), {"status": "read"})
        main_content = response.content.decode().split("<main", 1)[1]
        self.assertNotIn("Unread scouting update", main_content)
        self.assertContains(response, "Read shortlist update")

        response = self.client.post(reverse("mark_notification_read", args=[unread_notification.id]))
        self.assertRedirects(response, reverse("notifications"))
        unread_notification.refresh_from_db()
        self.assertTrue(unread_notification.is_read)

        response = self.client.get(reverse("notifications"))
        self.assertContains(response, "You are all caught up.")
        self.assertNotContains(response, "Unread scouting update")

    def test_club_publishes_and_player_applies_to_opportunity(self):
        club = User.objects.create_user(
            username="club-test",
            email="club@example.com",
            password="pass12345",
            role="club",
        )
        player = User.objects.create_user(
            username="player-test",
            email="player@example.com",
            password="pass12345",
            role="player",
        )
        PlayerProfile.objects.create(
            user=player,
            age=16,
            region="Nairobi",
            position="Forward",
            matches_played=5,
        )
        deadline = timezone.now().date() + timedelta(days=7)

        self.client.force_login(club)
        response = self.client.post(reverse("create_opportunity"), {
            "title": "U17 Nairobi trial day",
            "opportunity_type": Opportunity.TYPE_TRIAL,
            "location": "Kasarani",
            "region": "Nairobi",
            "deadline": deadline.isoformat(),
            "event_date": deadline.isoformat(),
            "age_min": 15,
            "age_max": 17,
            "positions": "Wingers and strikers",
            "description": "Open trial for promising youth players.",
            "requirements": "Bring boots and guardian consent.",
            "contact_instructions": "Staff will contact shortlisted players.",
            "is_active": "on",
        })

        opportunity = Opportunity.objects.get(title="U17 Nairobi trial day")
        self.assertRedirects(response, reverse("opportunity_detail", args=[opportunity.id]))
        self.assertEqual(opportunity.publisher, club)

        response = self.client.post(reverse("edit_opportunity", args=[opportunity.id]), {
            "title": "U17 Nairobi elite trial day",
            "opportunity_type": Opportunity.TYPE_TRIAL,
            "location": "Kasarani",
            "region": "Nairobi",
            "deadline": deadline.isoformat(),
            "event_date": deadline.isoformat(),
            "age_min": 15,
            "age_max": 17,
            "positions": "Forwards and wingers",
            "description": "Updated trial details.",
            "requirements": "Bring boots and guardian consent.",
            "contact_instructions": "Staff will contact shortlisted players.",
            "is_active": "on",
        })
        self.assertRedirects(response, reverse("opportunity_detail", args=[opportunity.id]))
        opportunity.refresh_from_db()
        self.assertEqual(opportunity.title, "U17 Nairobi elite trial day")
        self.assertEqual(opportunity.positions, "Forwards and wingers")

        response = self.client.post(reverse("toggle_opportunity_active", args=[opportunity.id]))
        self.assertRedirects(response, reverse("opportunity_detail", args=[opportunity.id]))
        opportunity.refresh_from_db()
        self.assertFalse(opportunity.is_active)
        response = self.client.post(reverse("toggle_opportunity_active", args=[opportunity.id]))
        self.assertRedirects(response, reverse("opportunity_detail", args=[opportunity.id]))
        opportunity.refresh_from_db()
        self.assertTrue(opportunity.is_active)

        other_club = User.objects.create_user(
            username="other-club",
            email="other-club@example.com",
            password="pass12345",
            role="club",
        )
        self.client.force_login(other_club)
        response = self.client.post(reverse("toggle_opportunity_active", args=[opportunity.id]))
        self.assertRedirects(response, reverse("opportunity_detail", args=[opportunity.id]))
        opportunity.refresh_from_db()
        self.assertTrue(opportunity.is_active)

        self.client.force_login(club)
        board_response = self.client.get(reverse("opportunities"))
        detail_response = self.client.get(reverse("opportunity_detail", args=[opportunity.id]))
        self.assertContains(board_response, "U17 Nairobi elite trial day")
        self.assertContains(detail_response, "Updated trial details.")

        self.client.force_login(player)
        response = self.client.post(reverse("apply_opportunity", args=[opportunity.id]), {
            "message": "I play striker in Nairobi and can attend the trial.",
        })

        self.assertRedirects(response, reverse("opportunity_detail", args=[opportunity.id]))
        application = OpportunityApplication.objects.get(opportunity=opportunity, player=player)
        self.assertEqual(application.status, OpportunityApplication.STATUS_SUBMITTED)

        response = self.client.post(reverse("toggle_save_opportunity", args=[opportunity.id]))
        self.assertRedirects(response, reverse("opportunity_detail", args=[opportunity.id]))
        self.assertTrue(opportunity.saved_by.filter(id=player.id).exists())

        tracker_response = self.client.get(reverse("my_opportunity_applications"))
        self.assertContains(tracker_response, "U17 Nairobi elite trial day")
        saved_response = self.client.get(reverse("saved_opportunities"))
        self.assertContains(saved_response, "U17 Nairobi elite trial day")

        self.client.post(reverse("toggle_save_opportunity", args=[opportunity.id]))
        self.assertFalse(opportunity.saved_by.filter(id=player.id).exists())

        response = self.client.post(reverse("withdraw_opportunity_application", args=[application.id]))
        self.assertRedirects(response, reverse("my_opportunity_applications"))
        application.refresh_from_db()
        self.assertEqual(application.status, OpportunityApplication.STATUS_WITHDRAWN)
        withdrawn_response = self.client.get(reverse("my_opportunity_applications"), {"status": "withdrawn"})
        self.assertContains(withdrawn_response, "Withdrawn")

        self.client.force_login(club)
        response = self.client.post(reverse("update_opportunity_application", args=[application.id, "shortlist"]))
        self.assertRedirects(response, reverse("opportunity_detail", args=[opportunity.id]))
        application.refresh_from_db()
        self.assertEqual(application.status, OpportunityApplication.STATUS_WITHDRAWN)

        self.client.force_login(player)
        response = self.client.post(reverse("apply_opportunity", args=[opportunity.id]), {
            "message": "I am available again for the trial.",
        })
        self.assertRedirects(response, reverse("opportunity_detail", args=[opportunity.id]))
        application.refresh_from_db()
        self.assertEqual(application.status, OpportunityApplication.STATUS_SUBMITTED)

        self.client.force_login(club)
        manager_response = self.client.get(reverse("manage_opportunities"))
        self.assertContains(manager_response, "U17 Nairobi elite trial day")
        self.assertContains(manager_response, "Opportunity Alerts")
        self.assertContains(manager_response, "player-test applied for U17 Nairobi elite trial day.")
        publisher_notification = Notification.objects.filter(
            recipient=club,
            target_url=reverse("opportunity_detail", args=[opportunity.id]),
            is_read=False,
        ).first()
        self.assertIsNotNone(publisher_notification)
        self.assertContains(manager_response, reverse("open_notification", args=[publisher_notification.id]))
        response = self.client.get(reverse("open_notification", args=[publisher_notification.id]))
        self.assertRedirects(response, reverse("opportunity_detail", args=[opportunity.id]))
        publisher_notification.refresh_from_db()
        self.assertTrue(publisher_notification.is_read)
        applicant_response = self.client.get(reverse("opportunity_detail", args=[opportunity.id]))
        self.assertContains(applicant_response, "Talent")
        self.assertContains(applicant_response, "Forward")
        self.assertContains(applicant_response, reverse("view_profile", args=[player.id]))
        self.assertContains(applicant_response, reverse("scout_card", args=[player.id]))
        self.assertContains(applicant_response, "Submitted")
        response = self.client.post(reverse("update_opportunity_application", args=[application.id, "shortlist"]))

        self.assertRedirects(response, reverse("opportunity_detail", args=[opportunity.id]))
        application.refresh_from_db()
        self.assertEqual(application.status, OpportunityApplication.STATUS_SHORTLISTED)

        self.client.force_login(player)
        tracker_response = self.client.get(reverse("my_opportunity_applications"))
        self.assertContains(tracker_response, "Recent Application Updates")
        self.assertContains(tracker_response, "Your application for U17 Nairobi elite trial day is now shortlisted.")
        player_notification = Notification.objects.filter(
            recipient=player,
            target_url=reverse("opportunity_detail", args=[opportunity.id]),
            is_read=False,
        ).first()
        self.assertIsNotNone(player_notification)
        self.assertContains(tracker_response, reverse("open_notification", args=[player_notification.id]))

        self.client.force_login(club)
        shortlisted_response = self.client.get(
            reverse("opportunity_detail", args=[opportunity.id]),
            {"application_status": "shortlisted"},
        )
        self.assertContains(shortlisted_response, "Shortlisted")
        self.assertContains(shortlisted_response, "player-test")
        declined_response = self.client.get(
            reverse("opportunity_detail", args=[opportunity.id]),
            {"application_status": "declined"},
        )
        declined_main_content = declined_response.content.decode().split("<main", 1)[1]
        self.assertContains(declined_response, "No applications in this status yet.")
        self.assertNotIn("player-test", declined_main_content)

    def test_recommended_opportunities_rank_player_fit_and_exclude_applied(self):
        club = User.objects.create_user(
            username="fit-club",
            email="fit-club@example.com",
            password="pass12345",
            role="club",
            verification_status=User.VERIFICATION_VERIFIED,
        )
        player = User.objects.create_user(
            username="fit-player",
            email="fit-player@example.com",
            password="pass12345",
            role="player",
        )
        profile = PlayerProfile.objects.create(
            user=player,
            age=16,
            region="Nairobi",
            position="Forward",
        )
        deadline = timezone.now().date() + timedelta(days=7)
        good_fit = Opportunity.objects.create(
            publisher=club,
            title="Forward trial in Nairobi",
            opportunity_type=Opportunity.TYPE_TRIAL,
            location="Kasarani",
            region="Nairobi",
            deadline=deadline,
            age_min=15,
            age_max=17,
            positions="Forward",
            description="Best match",
        )
        applied_fit = Opportunity.objects.create(
            publisher=club,
            title="Already applied opportunity",
            opportunity_type=Opportunity.TYPE_TRIAL,
            location="Nairobi",
            region="Nairobi",
            deadline=deadline,
            age_min=15,
            age_max=17,
            positions="Forward",
            description="Should be hidden",
        )
        Opportunity.objects.create(
            publisher=club,
            title="Distant goalkeeper intake",
            opportunity_type=Opportunity.TYPE_ACADEMY,
            location="Mombasa",
            region="Mombasa",
            deadline=deadline,
            age_min=20,
            age_max=23,
            positions="Goalkeeper",
            description="Poor fit",
        )
        OpportunityApplication.objects.create(
            opportunity=applied_fit,
            player=player,
            message="I already applied.",
        )

        recommendations = recommended_opportunities_for_player(profile)

        self.assertEqual(recommendations[0], good_fit)
        self.assertNotIn(applied_fit, recommendations)
        self.assertIn("Position fit", recommendations[0].match_reasons)

    def test_opportunity_board_for_you_mode_ranks_matches_and_hides_applied(self):
        club = User.objects.create_user(
            username="board-club",
            email="board-club@example.com",
            password="pass12345",
            role="club",
            verification_status=User.VERIFICATION_VERIFIED,
        )
        player = User.objects.create_user(
            username="board-player",
            email="board-player@example.com",
            password="pass12345",
            role="player",
        )
        PlayerProfile.objects.create(
            user=player,
            age=16,
            region="Nairobi",
            position="Forward",
        )
        deadline = timezone.now().date() + timedelta(days=7)
        good_fit = Opportunity.objects.create(
            publisher=club,
            title="Best Nairobi forward trial",
            opportunity_type=Opportunity.TYPE_TRIAL,
            location="Kasarani",
            region="Nairobi",
            deadline=deadline,
            age_min=15,
            age_max=17,
            positions="Forward",
            description="Best board match",
        )
        poor_fit = Opportunity.objects.create(
            publisher=club,
            title="Older goalkeeper intake",
            opportunity_type=Opportunity.TYPE_ACADEMY,
            location="Mombasa",
            region="Mombasa",
            deadline=deadline,
            age_min=20,
            age_max=23,
            positions="Goalkeeper",
            description="Lower board match",
        )
        applied = Opportunity.objects.create(
            publisher=club,
            title="Applied Nairobi forward trial",
            opportunity_type=Opportunity.TYPE_TRIAL,
            location="Nairobi",
            region="Nairobi",
            deadline=deadline,
            age_min=15,
            age_max=17,
            positions="Forward",
            description="Already applied",
        )
        OpportunityApplication.objects.create(opportunity=applied, player=player, message="Already in.")

        self.client.force_login(player)
        response = self.client.get(reverse("opportunities"), {"mode": "for_you"})
        content = response.content.decode()

        self.assertContains(response, "For You")
        self.assertContains(response, "Position fit")
        self.assertContains(response, good_fit.title)
        self.assertContains(response, poor_fit.title)
        self.assertNotContains(response, applied.title)
        self.assertLess(content.index(good_fit.title), content.index(poor_fit.title))
