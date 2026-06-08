from itertools import chain

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from accounts.onboarding import onboarding_context
from accounts.models import User
from players.models import PlayerProfile
from posts.models import Comment, Post, ScoutReport, TalentSpot
from posts.selectors import repost_post_for_user
from .forms import ScoutProfileForm


@login_required
def scout_dashboard(request):
    user = request.user
    following_players = user.following.filter(role="player")

    player_posts = Post.objects.filter(
        author__in=following_players,
        original_post__isnull=True,
    ).select_related("author")
    scout_reposts = Post.objects.filter(
        author=user,
        original_post__isnull=False,
    ).select_related("author", "original_post__author")

    highlights = sorted(
        chain(player_posts, scout_reposts),
        key=lambda post: post.created_at,
        reverse=True,
    )

    recommended = (
        User.objects.filter(role="player")
        .select_related("player_profile")
        .exclude(id__in=following_players)
        .order_by("-date_joined")[:6]
    )
    media_posts = Post.objects.filter(author=user).filter(
        models.Q(video__isnull=False) | models.Q(image__isnull=False)
    )
    recent_spots = TalentSpot.objects.exclude(
        status=TalentSpot.STATUS_ARCHIVED
    ).select_related("spotted_by")[:5]
    saved_count = user.saved_players.filter(role="player").count()
    reports_count = ScoutReport.objects.filter(scout=user).count()
    verified_count = TalentSpot.objects.filter(status=TalentSpot.STATUS_SCOUT_VERIFIED).count()
    recent_reports = ScoutReport.objects.filter(scout=user).select_related("talent_spot")[:4]

    return render(request, "scouts/dashboard.html", {
        "highlights": highlights,
        "recommended": recommended,
        "media_posts": media_posts,
        "reposts": scout_reposts,
        "recent_spots": recent_spots,
        "saved_count": saved_count,
        "reports_count": reports_count,
        "verified_count": verified_count,
        "recent_reports": recent_reports,
        "onboarding": onboarding_context(user),
    })


@login_required
def scout_search(request):
    """Browse/search players with filters."""
    profiles = PlayerProfile.objects.select_related("user").all()

    query = request.GET.get("q", "").strip()
    position = request.GET.get("position", "any")
    region = request.GET.get("region", "any")
    min_age = request.GET.get("min_age")
    max_age = request.GET.get("max_age")
    min_score = request.GET.get("min_score")
    completion = request.GET.get("completion", "any")
    has_video = request.GET.get("has_video") == "1"
    sort = request.GET.get("sort", "talent")

    if query:
        profiles = profiles.filter(
            models.Q(user__username__icontains=query) |
            models.Q(full_name__icontains=query) |
            models.Q(current_club__icontains=query) |
            models.Q(nationality__icontains=query) |
            models.Q(region__icontains=query)
        )
    if position and position != "any":
        profiles = profiles.filter(position__iexact=position)
    if region and region != "any":
        profiles = profiles.filter(region__iexact=region)
    if min_age:
        profiles = profiles.filter(age__gte=min_age)
    if max_age:
        profiles = profiles.filter(age__lte=max_age)
    if has_video:
        profiles = profiles.exclude(highlight_video__isnull=True).exclude(highlight_video="")

    profiles = list(profiles)
    if min_score:
        try:
            score_floor = int(min_score)
        except ValueError:
            score_floor = None
        if score_floor is not None:
            profiles = [profile for profile in profiles if profile.talent_score >= score_floor]
    if completion != "any":
        try:
            completion_floor = int(completion)
        except ValueError:
            completion_floor = None
        if completion_floor is not None:
            profiles = [profile for profile in profiles if profile.completion_percent >= completion_floor]

    sorters = {
        "talent": lambda profile: (profile.talent_score, profile.completion_percent, profile.updated_at),
        "completion": lambda profile: (profile.completion_percent, profile.talent_score, profile.updated_at),
        "newest": lambda profile: (profile.updated_at, profile.talent_score),
        "age_young": lambda profile: (-(profile.age or 999), profile.talent_score),
        "age_old": lambda profile: (profile.age or 0, profile.talent_score),
    }
    if sort not in sorters:
        sort = "talent"
    profiles = sorted(profiles, key=sorters[sort], reverse=True)

    saved_player_ids = set(request.user.saved_players.filter(role="player").values_list("id", flat=True))

    return render(request, "scouts/search.html", {
        "players": profiles,
        "query": query,
        "position": position,
        "region": region,
        "min_age": min_age,
        "max_age": max_age,
        "min_score": min_score,
        "completion": completion,
        "has_video": has_video,
        "sort": sort,
        "result_count": len(profiles),
        "position_choices": PlayerProfile.POSITION_CHOICES,
        "region_choices": PlayerProfile.REGION_CHOICES,
        "saved_player_ids": saved_player_ids,
    })


@login_required
def saved_players(request):
    """List saved players."""
    saved = request.user.saved_players.filter(role="player").select_related("player_profile")
    return render(request, "scouts/saved_players.html", {"players": saved})


@login_required
def save_player(request, player_id):
    """Save a player to the scout's list."""
    player = get_object_or_404(User, id=player_id, role="player")
    request.user.saved_players.add(player)
    messages.success(request, f"{player.username} added to your saved players.")
    return redirect("saved_players")


@login_required
def unsave_player(request, player_id):
    """Remove a player from the scout's saved list."""
    player = get_object_or_404(User, id=player_id, role="player")
    request.user.saved_players.remove(player)
    messages.success(request, f"{player.username} removed from your saved players.")
    return redirect("saved_players")


@login_required
def scout_insights(request):
    """Top/trending players."""
    top_players = (
        User.objects.filter(role="player")
        .annotate(
            follower_count=models.Count("followers", distinct=True),
            post_count=models.Count("posts", distinct=True),
        )
        .order_by("-follower_count", "-post_count")[:5]
    )
    return render(request, "scouts/insights.html", {"top_players": top_players})


@login_required
def repost_post(request, post_id):
    """Scout reposts a player's post once."""
    original = get_object_or_404(Post, id=post_id)
    _, created = repost_post_for_user(request.user, original)

    if created:
        messages.success(request, "Post successfully reposted.")
    else:
        messages.info(request, "You already reposted this post.")

    return redirect("scout_dashboard")


@login_required
def like_post(request, post_id):
    """Toggle like/unlike for a post."""
    post = get_object_or_404(Post, id=post_id)
    user = request.user

    if user in post.likes.all():
        post.likes.remove(user)
        liked = False
    else:
        post.likes.add(user)
        liked = True

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"liked": liked, "like_count": post.total_likes()})

    return redirect("scout_dashboard")


@login_required
def add_comment(request, post_id):
    """Add a new comment to a post."""
    post = get_object_or_404(Post, id=post_id)
    content = request.POST.get("content", "").strip()

    if content:
        Comment.objects.create(post=post, author=request.user, content=content)

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            "comment_count": post.comments.count(),
            "latest_comment": {
                "author": request.user.username,
                "content": content,
            },
        })

    return redirect("scout_dashboard")


@login_required
def edit_scout_profile(request):
    scout = request.user

    if request.method == "POST":
        form = ScoutProfileForm(request.POST, request.FILES, instance=scout)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("edit_scout_profile")
    else:
        form = ScoutProfileForm(instance=scout)

    media_posts = Post.objects.filter(author=scout).filter(
        models.Q(video__isnull=False) | models.Q(image__isnull=False)
    )
    reposts = Post.objects.filter(author=scout, original_post__isnull=False)

    return render(request, "scouts/edit_profile.html", {
        "form": form,
        "media_posts": media_posts,
        "reposts": reposts,
    })


@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id, author=request.user)
    post.delete()
    messages.success(request, "Post deleted successfully.")
    return redirect("scout_dashboard")
