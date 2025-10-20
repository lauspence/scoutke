# players/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.http import JsonResponse, HttpResponseBadRequest
from django.db.models import Q, Count
from posts.forms import *
from posts.models import Post
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
            messages.success(request, "✅ Post created successfully!")
            return redirect("dashboard")
    else:
        form = PostForm()

    # Following/followers & feed
    following_users = request.user.following.all()

    if request.user.role == 'player':
        posts = Post.objects.filter(
            Q(author=request.user) | Q(author__in=following_users)
        ).order_by('-created_at')
    elif request.user.role == 'scout':
        posts = Post.objects.filter(
            author__role='player',
            author__in=following_users
        ).order_by('-created_at')
    elif request.user.role == 'club':
        posts = Post.objects.filter(
            Q(author__role='player') | Q(author__role='scout')
        ).order_by('-created_at')
    else:
        posts = Post.objects.none()

    # Suggestions & trending
    scouts_following = request.user.followers.filter(role='scout')[:5]
    trending_players = User.objects.filter(role='player').annotate(
        last_post=Count('posts')
    ).order_by('-last_post')[:5]

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
        "player_profile": player_profile,  # ✅ added
        "scouts_following": scouts_following,
        "trending_players": trending_players,
        "recommended_users": recommended_users,
        "search_query": search_query,
        "search_results": search_results,
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

    # Who can see detailed stats?
    show_stats = (request.user == profile_user) or (getattr(request.user, "role", None) in ("scout", "club"))

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
    }
    return render(request, "players/view_profile.html", context)



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

    return JsonResponse({
        "action": action,
        "followers_count": target_user.followers.count()
    })


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
            messages.success(request, "✅ Profile saved successfully.")

            # Debug: confirm what was saved
            print("✅ Profile updated successfully for:", request.user.username)
            print("Cleaned Data:", form.cleaned_data)

            return redirect("view_profile", user_id=request.user.id)
        else:
            # Debugging
            print("❌ Profile update failed for:", request.user.username)
            print("Form errors (JSON):", form.errors.as_json())
            print("Form data received:", request.POST.dict())
            print("Files received:", request.FILES)

            messages.error(request, "❌ Please correct the errors below.")
    else:
        form = PlayerProfileForm(instance=profile)

    return render(request, "players/update_profile.html", {"form": form})