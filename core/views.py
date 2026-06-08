from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import redirect, render

from accounts.onboarding import onboarding_context
from posts.forms import CommentForm, PostForm
from posts.models import ClubShortlist, ContactRequest, Post, ScoutReport, TalentSpot
from posts.selectors import create_talent_spot_from_post, posts_for_user
from players.models import PlayerProfile

def home(request):
    if request.user.is_authenticated:
        if request.user.role == "player":
            return redirect("dashboard")
        if request.user.role == "scout":
            return redirect("scout_dashboard")
        if request.user.role == "club":
            return redirect("club_dashboard")
        return redirect("feed")

    recent_posts = (
        Post.objects.select_related("author")
        .filter(original_post__isnull=True)
        .order_by("-created_at")[:6]
    )
    return render(request, "core/home.html", {"recent_posts": recent_posts})


def talent_radar(request):
    active_spots = TalentSpot.objects.exclude(status=TalentSpot.STATUS_ARCHIVED)
    regional_counts = (
        active_spots.values("location")
        .annotate(total=Count("id"))
        .order_by("-total", "location")[:8]
    )
    position_counts = (
        active_spots.values("position")
        .annotate(total=Count("id"))
        .order_by("-total", "position")
    )
    spotlight_spots = (
        active_spots.select_related("spotted_by", "linked_player", "linked_player__user")
        .order_by("-updated_at")[:6]
    )
    verified_count = active_spots.filter(status=TalentSpot.STATUS_SCOUT_VERIFIED).count()
    community_count = active_spots.filter(status=TalentSpot.STATUS_COMMUNITY_CONFIRMED).count()
    top_profiles = sorted(
        PlayerProfile.objects.select_related("user").all(),
        key=lambda profile: profile.talent_score,
        reverse=True,
    )[:6]

    return render(request, "core/talent_radar.html", {
        "regional_counts": regional_counts,
        "position_counts": position_counts,
        "spotlight_spots": spotlight_spots,
        "total_spots": active_spots.count(),
        "verified_count": verified_count,
        "community_count": community_count,
        "top_profiles": top_profiles,
    })


@login_required
def club_dashboard(request):
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            create_talent_spot_from_post(post)
            return redirect("club_dashboard")
    else:
        form = PostForm()

    shortlist_entries = ClubShortlist.objects.filter(club=request.user).select_related(
        "talent_spot",
        "talent_spot__linked_player",
        "talent_spot__linked_player__user",
    )
    contact_requests = ContactRequest.objects.filter(club=request.user).select_related(
        "player",
        "talent_spot",
    )
    scout_reports = ScoutReport.objects.select_related("scout", "talent_spot")[:5]

    return render(request, 'core/club_dashboard.html', {
        "form": form,
        "posts": posts_for_user(request.user),
        "comment_form": CommentForm(),
        "talent_spots": TalentSpot.objects.exclude(status=TalentSpot.STATUS_ARCHIVED).select_related("spotted_by")[:6],
        "shortlist_entries": shortlist_entries[:5],
        "contact_requests": contact_requests[:5],
        "scout_reports": scout_reports,
        "active_leads_count": TalentSpot.objects.exclude(status=TalentSpot.STATUS_ARCHIVED).count(),
        "shortlist_count": shortlist_entries.count(),
        "pending_contacts_count": contact_requests.filter(status=ContactRequest.STATUS_PENDING).count(),
        "trial_count": shortlist_entries.filter(status=ClubShortlist.STATUS_TRIAL).count(),
        "onboarding": onboarding_context(request.user),
    })
