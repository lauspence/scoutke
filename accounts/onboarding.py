from django.urls import reverse

from .models import User


def _step(label, description, url, done):
    return {
        "label": label,
        "description": description,
        "url": url,
        "done": done,
    }


def onboarding_context(user):
    if not user.is_authenticated:
        return None

    steps = []

    if user.role == "player":
        from players.models import PlayerProfile

        profile, _ = PlayerProfile.objects.get_or_create(user=user)
        steps = [
            _step(
                "Complete your player profile",
                "Add name, position, region, club or school, and a short football bio.",
                reverse("update_profile"),
                profile.completion_percent >= 70,
            ),
            _step(
                "Add proof of play",
                "Add a highlight link or match stats so scouts can judge your current level.",
                reverse("update_profile"),
                bool(profile.highlight_video or profile.matches_played or profile.goals or profile.assists),
            ),
            _step(
                "Apply for an opportunity",
                "Use matched trials, intakes, and academy calls to start your recruitment trail.",
                reverse("opportunities"),
                user.opportunity_applications.exists(),
            ),
            _step(
                "Share your scout card",
                "Use your public card when contacting coaches, scouts, schools, or clubs.",
                reverse("scout_card", args=[user.id]),
                profile.completion_percent >= 85,
            ),
        ]
    elif user.role == "scout":
        from posts.models import ScoutReport

        verification_started = user.verification_status in (
            User.VERIFICATION_PENDING,
            User.VERIFICATION_VERIFIED,
        )
        steps = [
            _step(
                "Polish your scout profile",
                "Add a photo or bio so players and clubs understand your scouting context.",
                reverse("edit_scout_profile"),
                bool(user.profile_picture or user.bio),
            ),
            _step(
                "Save your first player",
                "Build a watchlist of players you want to monitor.",
                reverse("scout_search"),
                user.saved_players.filter(role="player").exists(),
            ),
            _step(
                "Write a scout report",
                "Turn a community talent spot into a useful scouting signal.",
                reverse("talent_spots"),
                ScoutReport.objects.filter(scout=user).exists(),
            ),
            _step(
                "Request verification",
                "Verification helps players and clubs trust your activity.",
                reverse("request_verification"),
                verification_started,
            ),
        ]
    elif user.role == "club":
        from posts.models import ClubShortlist, ContactRequest, Opportunity

        verification_started = user.verification_status in (
            User.VERIFICATION_PENDING,
            User.VERIFICATION_VERIFIED,
        )
        steps = [
            _step(
                "Build a shortlist",
                "Save prospects from talent spots into your recruitment pipeline.",
                reverse("talent_spots"),
                ClubShortlist.objects.filter(club=user).exists(),
            ),
            _step(
                "Publish an opportunity",
                "Create a trial, intake, scholarship, or academy call.",
                reverse("create_opportunity"),
                Opportunity.objects.filter(publisher=user).exists(),
            ),
            _step(
                "Contact a player",
                "Send a structured contact request from your shortlist.",
                reverse("club_shortlist"),
                ContactRequest.objects.filter(club=user).exists(),
            ),
            _step(
                "Request verification",
                "Verification makes your recruitment calls safer and more credible.",
                reverse("request_verification"),
                verification_started,
            ),
        ]
    else:
        steps = [
            _step(
                "Follow football people",
                "Follow players, scouts, clubs, or fans to shape your feed.",
                reverse("talent_radar"),
                user.following.exists(),
            ),
            _step(
                "Share a post",
                "Post match notes, clips, or local football updates.",
                reverse("feed"),
                user.posts.exists(),
            ),
            _step(
                "Submit a talent spot",
                "Help the community surface promising players from your area.",
                reverse("create_talent_spot"),
                user.talent_spots.exists(),
            ),
        ]

    completed = sum(1 for step in steps if step["done"])
    total = len(steps)
    return {
        "steps": steps,
        "completed": completed,
        "total": total,
        "percent": round((completed / total) * 100) if total else 100,
        "is_complete": completed == total,
    }
