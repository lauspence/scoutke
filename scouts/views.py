from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import models
from itertools import chain
from players.models import PlayerProfile
from posts.models import Post,Comment
from accounts.models import User
from .forms import ScoutProfileForm


@login_required
def scout_dashboard(request):
    user = request.user

    # --- FEED LOGIC ---

    # Player posts from followed players (exclude reposts)
    following_players = user.following.filter(role="player")
    player_posts = Post.objects.filter(
        author__in=following_players,
        original_post__isnull=True
    )

    # Reposts created by scout
    scout_reposts = Post.objects.filter(
        author=user,
        original_post__isnull=False
    )

    # Combine into Highlights feed (recent first)
    highlights = sorted(
        chain(player_posts, scout_reposts),
        key=lambda x: x.created_at,
        reverse=True
    )

    # --- EXTRA SECTIONS FOR DASHBOARD ---

    # Recommended players (not already followed)
    recommended = (
        User.objects.filter(role="player")
        .select_related("player_profile")
        .exclude(id__in=following_players)
        .order_by("-date_joined")[:6]
    )

    # Media tab (scout’s uploaded videos/images)
    media_posts = Post.objects.filter(author=user).filter(
        models.Q(video__isnull=False) | models.Q(image__isnull=False)
    )

    # Reposts tab (scout’s repost history)
    reposts = scout_reposts

    context = {
        "highlights": highlights,
        "recommended": recommended,
        "media_posts": media_posts,
        "reposts": reposts,
    }
    return render(request, "scouts/dashboard.html", context)


# --- QUICK ACTIONS ---

@login_required
def scout_search(request):
    """Browse/Search players with filters"""
    profiles = PlayerProfile.objects.select_related("user").all()

    # --- Filters ---
    query = request.GET.get("q", "").strip()
    position = request.GET.get("position", "any")
    region = request.GET.get("region", "any")
    min_age = request.GET.get("min_age")
    max_age = request.GET.get("max_age")

    if query:
        profiles = profiles.filter(user__username__icontains=query)

    if position and position != "any":
        profiles = profiles.filter(position__iexact=position)

    if region and region != "any":
        profiles = profiles.filter(nationality__iexact=region)  # assuming nationality ~ region

    if min_age:
        profiles = profiles.filter(age__gte=min_age)

    if max_age:
        profiles = profiles.filter(age__lte=max_age)

    context = {
        "players": profiles,  # queryset of PlayerProfile
        "query": query,
        "position": position,
        "region": region,
        "min_age": min_age,
        "max_age": max_age,
    }
    return render(request, "scouts/search.html", context)


@login_required
def saved_players(request):
    """List of saved players"""
    saved = request.user.saved_players.all()
    return render(request, "scouts/saved_players.html", {"players": saved})


@login_required
def save_player(request, player_id):
    """Save a player to scout’s list"""
    player = get_object_or_404(User, id=player_id, role="player")
    request.user.saved_players.add(player)
    messages.success(request, f"{player.username} added to your saved players.")
    return redirect("saved_players")


@login_required
def scout_insights(request):
    """Top/trending players"""
    top_players = (
        User.objects.filter(role="player")
        .annotate(follower_count=models.Count("followers"))
        .order_by("-follower_count")[:5]
    )
    return render(request, "scouts/insights.html", {"top_players": top_players})


# --- REPOST FEATURE ---

@login_required
def repost_post(request, post_id):
    """Scout reposts a player’s post"""
    original = get_object_or_404(Post, id=post_id)

    # prevent duplicate reposts
    if Post.objects.filter(author=request.user, original_post=original).exists():
        messages.info(request, "You already reposted this post.")
        return redirect("scout_dashboard")

    # create the repost entry
    repost = Post.objects.create(
        author=request.user,
        original_post=original,
        content=f"🔁 Repost from {original.author.username}",
    )

    # increment the original post's repost count
    original.repost_count = (original.repost_count or 0) + 1
    original.save(update_fields=["repost_count"])

    messages.success(request, "Post successfully reposted.")
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
            }
        })

    return redirect("scout_dashboard")

# --- EDIT PROFILE ---

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

    # Tabs: Media + Reposts for profile page
    media_posts = Post.objects.filter(author=scout).filter(
        models.Q(video__isnull=False) | models.Q(image__isnull=False)
    )
    reposts = Post.objects.filter(author=scout, original_post__isnull=False)

    context = {
        "form": form,
        "media_posts": media_posts,
        "reposts": reposts,
    }
    return render(request, "scouts/edit_profile.html", context)

@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id, author=request.user)
    post.delete()
    messages.success(request, "Post deleted successfully.")
    return redirect("scout_dashboard")




