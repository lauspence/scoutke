# players/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.http import JsonResponse, HttpResponseBadRequest
from django.db.models import Count, F, Q
from accounts.models import UserSettings
from accounts.onboarding import onboarding_context
from posts.forms import *
from posts.models import ContactRequest, TalentSpot, TalentSpotClaim
from posts.selectors import create_talent_spot_from_post, posts_for_user, recommended_opportunities_for_player
from .models import *
from .forms import *

User = get_user_model()

# -------------------------
# Player dashboard (your existing)
# -------------------------
@login_required
def player_dashboard(request):
    # Ensure player has a profile
    try:
        player_profile = request.user.player_profile
    except PlayerProfile.DoesNotExist:
        player_profile = PlayerProfile.objects.create(user=request.user)

    # Post form (existing)
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            create_talent_spot_from_post(post)
            messages.success(request, "Post created successfully.")
            return redirect("dashboard")
    else:
        form = PostForm()

    # Following/followers & feed
    following_users = request.user.following.all()

    posts = posts_for_user(request.user)

    # Suggestions & trending
    scouts_following = request.user.followers.filter(role='scout')[:5]
    trending_players = User.objects.filter(role='player').annotate(
        post_count=Count('posts', distinct=True),
        followers_count=Count('followers', distinct=True),
    ).order_by('-post_count', '-followers_count')[:5]

    profile_next_steps = []
    if not player_profile.full_name:
        profile_next_steps.append("Add your full name")
    if not player_profile.position:
        profile_next_steps.append("Choose your position")
    if not player_profile.current_club:
        profile_next_steps.append("Add your current club or school")
    if not player_profile.highlight_video:
        profile_next_steps.append("Add a highlight video link")
    if not player_profile.bio:
        profile_next_steps.append("Write a short football bio")

    contact_requests = ContactRequest.objects.filter(player=request.user).select_related("club", "talent_spot")[:3]
    player_claims = TalentSpotClaim.objects.filter(player=request.user).select_related("talent_spot")[:3]
    linked_spots = TalentSpot.objects.filter(linked_player=player_profile).select_related("spotted_by")[:3]
    recommended_opportunities = recommended_opportunities_for_player(player_profile, limit=3)
    scout_profile_views = player_profile.profile_views.filter(viewer__role="scout").select_related("viewer")[:5]
    club_profile_views = player_profile.profile_views.filter(viewer__role="club").select_related("viewer")[:5]
    recent_profile_views = player_profile.profile_views.select_related("viewer")[:5]

    recommended_users = User.objects.exclude(id__in=following_users).exclude(id=request.user.id)
    recommended_users = recommended_users.annotate(followers_count=Count('followers')).order_by('-followers_count')[:5]

    # Search
    search_query = request.GET.get('q', '').strip()
    search_results = None
    if search_query:
        search_results = User.objects.filter(
            Q(username__icontains=search_query) |
            Q(role__icontains=search_query)
        ).exclude(id=request.user.id)

    context = {
        "form": form,
        "posts": posts,
        "comment_form": CommentForm(),
        "player_profile": player_profile,
        "scouts_following": scouts_following,
        "trending_players": trending_players,
        "recommended_users": recommended_users,
        "search_query": search_query,
        "search_results": search_results,
        "profile_completion": player_profile.completion_percent,
        "talent_score": player_profile.talent_score,
        "profile_next_steps": profile_next_steps[:4],
        "contact_requests": contact_requests,
        "player_claims": player_claims,
        "linked_spots": linked_spots,
        "recommended_opportunities": recommended_opportunities,
        "scout_profile_views": scout_profile_views,
        "club_profile_views": club_profile_views,
        "recent_profile_views": recent_profile_views,
        "profile_view_count": player_profile.profile_views.count(),
        "onboarding": onboarding_context(request.user),
    }

    return render(request, "players/dashboard.html", context)



# -------------------------
# Profile view (scouts/clubs/fans land here)
# -------------------------
@login_required
def view_profile(request, user_id):
    """
    Show a player's full profile in tabs: Overview / Media / Posts / Stats.
    Stats tab is visible only to scouts/clubs or to the profile owner.
    """
    import re
    from django.db.models import Q

    profile_user = get_object_or_404(User, id=user_id)
    profile = getattr(profile_user, "player_profile", None)
    profile_settings, _ = UserSettings.objects.get_or_create(user=profile_user)

    if request.user != profile_user:
        if profile_settings.profile_visibility == UserSettings.PROFILE_SCOUTS_CLUBS:
            if getattr(request.user, "role", None) not in ("scout", "club") and not request.user.is_staff:
                messages.info(request, "This profile is visible to scouts and clubs only.")
                return redirect("feed")

    if (
        profile
        and request.user != profile_user
        and getattr(request.user, "role", None) in ("scout", "club")
    ):
        profile_view, created = ProfileView.objects.get_or_create(
            player=profile,
            viewer=request.user,
        )
        if not created:
            profile_view.view_count = F("view_count") + 1
            profile_view.save(update_fields=["view_count", "last_viewed_at"])

    # Who can see detailed stats?
    show_stats = (
        request.user == profile_user
        or (profile_settings.show_stats and getattr(request.user, "role", None) in ("scout", "club"))
    )

    # Posts and media
    posts = Post.objects.filter(author=profile_user).order_by("-created_at")
    media_posts = posts.filter(Q(image__isnull=False) | Q(video__isnull=False))

    # Comment form used for post comments on profile posts
    comment_form = CommentForm()

    # --- Compute highlight embed info (do this in Python, not template) ---
    embed_link = None
    video_type = None  # 'youtube', 'file', 'link', or None
    if profile and profile.highlight_video:
        url = profile.highlight_video.strip()
        # detect youtube patterns (watch?v=, youtu.be, embed/)
        m = re.search(r'(?:v=|v/|embed/|youtu\.be/)([A-Za-z0-9_-]{6,})', url)
        if m:
            vid = m.group(1)
            embed_link = f"https://www.youtube.com/embed/{vid}"
            video_type = "youtube"
        else:
            lower = url.lower()
            if lower.endswith(".mp4") or lower.endswith(".webm") or lower.endswith(".ogg"):
                video_type = "file"
            else:
                video_type = "link"

    context = {
        "profile_user": profile_user,
        "profile": profile,
        "show_stats": show_stats,
        "posts": posts,
        "media_posts": media_posts,
        "comment_form": comment_form,
        "embed_link": embed_link,
        "video_type": video_type,
        "talent_score": profile.talent_score if profile else 0,
        "profile_view_count": profile.profile_views.count() if profile else 0,
        "recent_profile_views": profile.profile_views.select_related("viewer")[:5] if profile else [],
        "show_email": profile_settings.show_email or request.user == profile_user,
    }
    return render(request, "players/view_profile.html", context)


def scout_card(request, user_id):
    profile_user = get_object_or_404(User, id=user_id, role="player")
    profile = getattr(profile_user, "player_profile", None)
    profile_settings, _ = UserSettings.objects.get_or_create(user=profile_user)

    if profile_settings.profile_visibility == UserSettings.PROFILE_SCOUTS_CLUBS:
        if not request.user.is_authenticated or (
            getattr(request.user, "role", None) not in ("scout", "club") and not request.user.is_staff and request.user != profile_user
        ):
            messages.info(request, "This scout card is visible to scouts and clubs only.")
            return redirect("feed")

    public_url = request.build_absolute_uri()
    stats = {
        "matches": profile.matches_played if profile else 0,
        "goals": profile.goals if profile else 0,
        "assists": profile.assists if profile else 0,
        "followers": profile_user.followers.count(),
    }

    return render(request, "players/scout_card.html", {
        "profile_user": profile_user,
        "profile": profile,
        "public_url": public_url,
        "stats": stats,
        "talent_score": profile.talent_score if profile else 0,
        "profile_completion": profile.completion_percent if profile else 0,
    })



# -------------------------
# Follow / unfollow toggle (AJAX-friendly)
# -------------------------
@login_required
def follow_user(request, user_id):
    """
    Toggle follow/unfollow via POST (AJAX). Returns JSON:
    { "action": "followed"|"unfollowed", "followers_count": int }
    """
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    target_user = get_object_or_404(User, id=user_id)
    current_user = request.user

    if target_user == current_user:
        return JsonResponse({"error": "You cannot follow yourself."}, status=400)

    if current_user in target_user.followers.all():
        target_user.followers.remove(current_user)
        action = "unfollowed"
    else:
        target_user.followers.add(current_user)
        action = "followed"

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            "action": action,
            "followers_count": target_user.followers.count()
        })

    return redirect(request.META.get("HTTP_REFERER", "dashboard"))


# -------------------------
# Followers / Following lists (existing)
# -------------------------
@login_required
def followers_list(request, user_id):
    user = get_object_or_404(User, id=user_id)
    followers = user.followers.all()
    return render(request, 'players/followers_list.html', {'user': user, 'followers': followers})

@login_required
def following_list(request, user_id):
    user = get_object_or_404(User, id=user_id)
    following = user.following.all()
    return render(request, 'players/following_list.html', {'user': user, 'following': following})



@login_required
def update_profile(request):
    """
    Create or update a player's profile.
    Includes debug output to help trace why saving might fail.
    """
    # Ensure profile exists
    profile, created = PlayerProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = PlayerProfileForm(request.POST, request.FILES, instance=profile)

        if form.is_valid():
            saved_profile = form.save(commit=False)
            saved_profile.user = request.user
            saved_profile.save()
            if saved_profile.profile_picture:
                request.user.profile_picture = saved_profile.profile_picture
                request.user.save(update_fields=["profile_picture"])
            elif request.POST.get("profile_picture-clear"):
                request.user.profile_picture = None
                request.user.save(update_fields=["profile_picture"])
            messages.success(request, "Profile saved successfully.")

            return redirect("view_profile", user_id=request.user.id)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = PlayerProfileForm(instance=profile)

    return render(request, "players/update_profile.html", {"form": form, "profile": profile})
