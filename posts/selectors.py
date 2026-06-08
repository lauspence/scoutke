from django.db.models import Q
from django.utils import timezone

from accounts.models import UserSettings
from .models import Opportunity, OpportunityApplication, Post


def posts_for_user(user):
    """Return the football feed based on a user's saved feed preference."""
    posts = Post.objects.all().select_related("author", "original_post__author").prefetch_related("likes", "comments")

    if not getattr(user, "is_authenticated", False):
        return posts

    settings, _ = UserSettings.objects.get_or_create(user=user)
    if settings.default_feed == UserSettings.FEED_FOLLOWING:
        return posts.filter(Q(author=user) | Q(author__in=user.following.all()))
    if settings.default_feed == UserSettings.FEED_TALENT:
        return posts.filter(category=Post.CATEGORY_TALENT)
    return posts


def repost_post_for_user(user, original):
    """Create a repost if one does not already exist for this user/post pair."""
    return Post.objects.get_or_create(
        author=user,
        original_post=original,
        defaults={"content": f"Repost from {original.author.username}"},
    )


def create_talent_spot_from_post(post):
    """Promote a talent-category post into a structured scouting lead."""
    from .models import TalentSpot

    if post.category != Post.CATEGORY_TALENT or not post.prospect_name or not post.location:
        return None

    spot, _ = TalentSpot.objects.get_or_create(
        source_post=post,
        defaults={
            "spotted_by": post.author,
            "prospect_name": post.prospect_name,
            "location": post.location,
            "notes": post.content or "Talent spotted from the football feed.",
            "evidence_image": post.image,
            "evidence_video": post.video,
        },
    )
    return spot


def rank_opportunities_for_player(player_profile, opportunities, exclude_applied=True, limit=None):
    """Attach match scores/reasons and return opportunities ranked for a player."""
    if not player_profile:
        return []

    user = player_profile.user
    applied_ids = set()
    if exclude_applied:
        applied_ids = set(OpportunityApplication.objects.filter(player=user).values_list("opportunity_id", flat=True))

    ranked = []
    position = (player_profile.position or "").strip().lower()
    region = (player_profile.region or "").strip().lower()
    age = player_profile.age

    for opportunity in opportunities[:80]:
        if opportunity.id in applied_ids:
            continue

        score = 0
        reasons = []

        if age:
            min_ok = opportunity.age_min is None or opportunity.age_min <= age
            max_ok = opportunity.age_max is None or age <= opportunity.age_max
            if min_ok and max_ok:
                score += 35
                reasons.append("Age fit")

        positions = (opportunity.positions or "").lower()
        if position and (not positions or "any" in positions or position in positions):
            score += 30
            reasons.append("Position fit")

        place = f"{opportunity.region} {opportunity.location}".lower()
        if region and region in place:
            score += 20
            reasons.append("Near your region")

        if opportunity.publisher.is_verified_account:
            score += 10
            reasons.append("Verified publisher")

        if opportunity.deadline:
            score += 5
            reasons.append("Has deadline")

        opportunity.match_score = score
        opportunity.match_reasons = reasons[:3] or ["Open opportunity"]
        ranked.append(opportunity)

    ranked.sort(key=lambda item: (item.match_score, item.created_at), reverse=True)
    return ranked[:limit] if limit else ranked


def recommended_opportunities_for_player(player_profile, limit=4):
    """Return open opportunities ranked by how well they fit a player profile."""
    if not player_profile:
        return []

    opportunities = Opportunity.objects.select_related("publisher")
    opportunities = opportunities.filter(is_active=True).filter(Q(deadline__isnull=True) | Q(deadline__gte=timezone.now().date()))
    return rank_opportunities_for_player(player_profile, opportunities, exclude_applied=True, limit=limit)
