from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserSettings
from accounts.onboarding import onboarding_context
from .forms import (
    ClubShortlistForm,
    CommentForm,
    ContactRequestForm,
    ContentReportForm,
    OpportunityApplicationForm,
    OpportunityForm,
    PostForm,
    ScoutReportForm,
    TalentSpotClaimForm,
    TalentSpotForm,
)
from .models import (
    ClubShortlist,
    Comment,
    ContactRequest,
    ContentReport,
    Notification,
    Opportunity,
    OpportunityApplication,
    Post,
    ScoutReport,
    TalentSpot,
    TalentSpotClaim,
)
from .selectors import create_talent_spot_from_post, posts_for_user, rank_opportunities_for_player, repost_post_for_user


def notify_user(recipient, message, actor=None, target_url="", category="general"):
    if recipient and recipient != actor:
        settings, _ = UserSettings.objects.get_or_create(user=recipient)
        if not settings.notify_in_app:
            return
        if category == "social" and not settings.notify_social:
            return
        if category == "contact" and not settings.notify_contact:
            return
        if category == "reports" and not settings.notify_reports:
            return
        Notification.objects.create(
            recipient=recipient,
            actor=actor,
            message=message,
            target_url=target_url,
        )


def feed(request):
    """Role-aware feed with dynamic liking/commenting."""
    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect("login")
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            create_talent_spot_from_post(post)
            messages.success(request, "Post created successfully.")
            return redirect("feed")
    else:
        form = PostForm()

    context = {
        "form": form,
        "posts": posts_for_user(request.user),
        "comment_form": CommentForm(),
        "onboarding": onboarding_context(request.user) if request.user.is_authenticated else None,
    }
    return render(request, "posts/feed_page.html", context)


@login_required
def like_post(request, post_id):
    """AJAX: toggle like/unlike."""
    post = get_object_or_404(Post, id=post_id)
    user = request.user

    if user in post.likes.all():
        post.likes.remove(user)
        liked = False
    else:
        post.likes.add(user)
        liked = True
        notify_user(
            post.author,
            f"{user.username} liked your post.",
            actor=user,
            target_url=reverse("feed") + f"#post-{post.id}",
            category="social",
        )

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            "liked": liked,
            "total_likes": post.total_likes(),
            "likes": post.total_likes(),
        })

    return redirect(request.META.get("HTTP_REFERER", "feed"))


@login_required
def add_comment(request, post_id):
    """AJAX: add a comment to a post."""
    if request.method == "POST":
        post = get_object_or_404(Post, id=post_id)
        content = request.POST.get("content", "").strip()
        if content:
            comment = Comment.objects.create(post=post, author=request.user, content=content)
            notify_user(
                post.author,
                f"{request.user.username} commented on your post.",
                actor=request.user,
                target_url=reverse("feed") + f"#post-{post.id}",
                category="social",
            )
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({
                    "author": comment.author.username,
                    "content": comment.content,
                    "total_comments": post.comments.count(),
                })
            return redirect(request.META.get("HTTP_REFERER", "feed"))

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"error": "Invalid request"}, status=400)
    return redirect(request.META.get("HTTP_REFERER", "feed"))


@login_required
def repost_post(request, post_id):
    """Create a repost once per user/post."""
    original = get_object_or_404(Post, id=post_id)
    _, created = repost_post_for_user(request.user, original)

    if created:
        messages.success(request, "Post successfully reposted.")
    else:
        messages.info(request, "You already reposted this post.")

    return redirect("scout_dashboard" if request.user.role == "scout" else "feed")


def fetch_new_posts(request):
    """AJAX: return new posts since the most recent visible post ID."""
    try:
        last_post_id = int(request.GET.get("last_post_id", 0))
    except (TypeError, ValueError):
        last_post_id = 0
    new_posts = posts_for_user(request.user).filter(id__gt=last_post_id).order_by("-created_at")
    html = render_to_string(
        "posts/partials/post_list.html",
        {
            "posts": new_posts,
            "comment_form": CommentForm(),
            "show_empty": False,
        },
        request=request,
    )
    return JsonResponse({"html": html})


def talent_spots(request):
    """Browse structured community scouting leads."""
    spots = TalentSpot.objects.select_related(
        "spotted_by",
        "linked_player__user",
    ).annotate(confirmations_count=Count("confirmations", distinct=True))

    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "active")
    position = request.GET.get("position", "any")
    location = request.GET.get("location", "").strip()
    min_confirmations = request.GET.get("min_confirmations", "")
    has_media = request.GET.get("has_media") == "1"
    sort = request.GET.get("sort", "recent")

    if query:
        spots = spots.filter(
            Q(prospect_name__icontains=query) |
            Q(location__icontains=query) |
            Q(team_or_school__icontains=query) |
            Q(event_name__icontains=query)
        )
    if position and position != "any":
        spots = spots.filter(position=position)
    if location:
        spots = spots.filter(location__icontains=location)
    if status == "active":
        spots = spots.exclude(status=TalentSpot.STATUS_ARCHIVED)
    elif status and status != "any":
        spots = spots.filter(status=status)
    if min_confirmations:
        try:
            confirmation_floor = int(min_confirmations)
        except ValueError:
            confirmation_floor = None
        if confirmation_floor is not None:
            spots = spots.filter(confirmations_count__gte=confirmation_floor)
    if has_media:
        spots = spots.filter(Q(evidence_image__isnull=False) | Q(evidence_video__isnull=False))

    sort_options = {
        "recent": "-created_at",
        "updated": "-updated_at",
        "confirmed": "-confirmations_count",
        "name": "prospect_name",
    }
    if sort not in sort_options:
        sort = "recent"
    spots = spots.order_by(sort_options[sort])

    result_count = spots.count()

    return render(request, "posts/talent_spots.html", {
        "spots": spots,
        "query": query,
        "status": status,
        "position": position,
        "location": location,
        "min_confirmations": min_confirmations,
        "has_media": has_media,
        "sort": sort,
        "result_count": result_count,
        "status_choices": TalentSpot.STATUS_CHOICES,
        "position_choices": TalentSpot.POSITION_CHOICES,
    })


@login_required
def report_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.method == "POST":
        form = ContentReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            report.post = post
            report.save()
            messages.success(request, "Thanks. Your report was sent to moderators.")
            return redirect(request.META.get("HTTP_REFERER", "feed"))
    else:
        form = ContentReportForm()

    return render(request, "posts/content_report_form.html", {
        "form": form,
        "target_type": "post",
        "target_label": post.author.username,
        "cancel_url": request.META.get("HTTP_REFERER", reverse("feed")),
    })


@login_required
def report_talent_spot(request, spot_id):
    spot = get_object_or_404(TalentSpot, id=spot_id)
    if request.method == "POST":
        form = ContentReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            report.talent_spot = spot
            report.save()
            messages.success(request, "Thanks. Your report was sent to moderators.")
            return redirect("talent_spot_detail", spot_id=spot.id)
    else:
        form = ContentReportForm()

    return render(request, "posts/content_report_form.html", {
        "form": form,
        "target_type": "talent spot",
        "target_label": spot.prospect_name,
        "cancel_url": reverse("talent_spot_detail", args=[spot.id]),
    })


@login_required
def moderation_queue(request):
    if not request.user.is_staff:
        messages.error(request, "Only staff can access the moderation queue.")
        return redirect("feed")

    status = request.GET.get("status", ContentReport.STATUS_OPEN)
    reports = ContentReport.objects.select_related(
        "reporter",
        "post",
        "post__author",
        "talent_spot",
        "talent_spot__spotted_by",
        "reviewed_by",
    )
    if status != "all":
        reports = reports.filter(status=status)

    return render(request, "posts/moderation_queue.html", {
        "reports": reports,
        "status": status,
        "status_choices": ContentReport.STATUS_CHOICES,
    })


@login_required
def review_content_report(request, report_id, action):
    if not request.user.is_staff:
        messages.error(request, "Only staff can review reports.")
        return redirect("feed")

    report = get_object_or_404(ContentReport, id=report_id)
    if action == "reviewing":
        report.status = ContentReport.STATUS_REVIEWING
        message = "Report marked as reviewing."
    elif action == "resolve":
        report.status = ContentReport.STATUS_RESOLVED
        message = "Report marked as resolved."
    elif action == "dismiss":
        report.status = ContentReport.STATUS_DISMISSED
        message = "Report dismissed."
    else:
        messages.error(request, "Unknown report action.")
        return redirect("moderation_queue")

    report.reviewed_by = request.user
    report.save(update_fields=["status", "reviewed_by", "updated_at"])
    messages.success(request, message)
    return redirect(request.META.get("HTTP_REFERER", "moderation_queue"))


@login_required
def create_talent_spot(request):
    """Submit a structured lead from a match, school game, or local tournament."""
    if request.method == "POST":
        form = TalentSpotForm(request.POST, request.FILES)
        if form.is_valid():
            spot = form.save(commit=False)
            spot.spotted_by = request.user
            spot.save()
            messages.success(request, "Talent spot submitted.")
            return redirect("talent_spot_detail", spot_id=spot.id)
    else:
        form = TalentSpotForm()

    return render(request, "posts/talent_spot_form.html", {"form": form})


def talent_spot_detail(request, spot_id):
    spot = get_object_or_404(
        TalentSpot.objects.select_related("spotted_by", "linked_player__user", "source_post"),
        id=spot_id,
    )
    related_spots = TalentSpot.objects.filter(
        Q(prospect_name__iexact=spot.prospect_name) | Q(location__iexact=spot.location)
    ).exclude(id=spot.id)[:4]
    scout_reports = spot.scout_reports.select_related("scout")[:5]
    claims = spot.claims.select_related("player", "player_profile").all()
    user_claim = None
    if request.user.is_authenticated:
        user_claim = claims.filter(player=request.user).first()
    club_shortlist_entry = None
    existing_contact_request = None
    if request.user.is_authenticated and request.user.role == "club":
        club_shortlist_entry = ClubShortlist.objects.filter(
            club=request.user,
            talent_spot=spot,
        ).first()
        if spot.linked_player:
            existing_contact_request = ContactRequest.objects.filter(
                club=request.user,
                player_profile=spot.linked_player,
                talent_spot=spot,
            ).first()
    can_verify_spot = (
        request.user.is_authenticated and (
            request.user.role in ("scout", "club") or request.user.is_staff
        )
    )

    return render(request, "posts/talent_spot_detail.html", {
        "spot": spot,
        "related_spots": related_spots,
        "scout_reports": scout_reports,
        "claims": claims,
        "user_claim": user_claim,
        "club_shortlist_entry": club_shortlist_entry,
        "existing_contact_request": existing_contact_request,
        "can_verify_spot": can_verify_spot,
    })


@login_required
def confirm_talent_spot(request, spot_id):
    spot = get_object_or_404(TalentSpot, id=spot_id)

    if request.user == spot.spotted_by:
        messages.info(request, "You already submitted this spot.")
        return redirect("talent_spot_detail", spot_id=spot.id)

    if request.user in spot.confirmations.all():
        spot.confirmations.remove(request.user)
        messages.info(request, "Confirmation removed.")
    else:
        spot.confirmations.add(request.user)
        notify_user(
            spot.spotted_by,
            f"{request.user.username} confirmed your talent spot for {spot.prospect_name}.",
            actor=request.user,
            target_url=reverse("talent_spot_detail", args=[spot.id]),
            category="reports",
        )
        messages.success(request, "Talent spot confirmed.")

    spot.refresh_status()
    return redirect("talent_spot_detail", spot_id=spot.id)


@login_required
def verify_talent_spot(request, spot_id):
    spot = get_object_or_404(TalentSpot, id=spot_id)

    if request.user.role not in ("scout", "club") and not request.user.is_staff:
        messages.error(request, "Only scouts, clubs, and admins can verify a talent spot.")
        return redirect("talent_spot_detail", spot_id=spot.id)

    spot.status = TalentSpot.STATUS_SCOUT_VERIFIED
    spot.save(update_fields=["status", "updated_at"])
    notify_user(
        spot.spotted_by,
        f"{spot.prospect_name} was marked scout verified.",
        actor=request.user,
        target_url=reverse("talent_spot_detail", args=[spot.id]),
        category="reports",
    )
    messages.success(request, "Talent spot marked as scout verified.")
    return redirect("talent_spot_detail", spot_id=spot.id)


@login_required
def create_scout_report(request, spot_id):
    """Create or update the current scout's report for a talent spot."""
    spot = get_object_or_404(TalentSpot, id=spot_id)
    if request.user.role != "scout" and not request.user.is_staff:
        messages.error(request, "Only scouts can write scout reports.")
        return redirect("talent_spot_detail", spot_id=spot.id)

    report = ScoutReport.objects.filter(talent_spot=spot, scout=request.user).first()
    if request.method == "POST":
        form = ScoutReportForm(request.POST, instance=report)
        if form.is_valid():
            report = form.save(commit=False)
            report.talent_spot = spot
            report.scout = request.user
            report.save()
            if spot.status not in (TalentSpot.STATUS_LINKED, TalentSpot.STATUS_ARCHIVED):
                spot.status = TalentSpot.STATUS_SCOUT_VERIFIED
                spot.save(update_fields=["status", "updated_at"])
            notify_user(
                spot.spotted_by,
                f"{request.user.username} wrote a scout report for {spot.prospect_name}.",
                actor=request.user,
                target_url=reverse("talent_spot_detail", args=[spot.id]),
                category="reports",
            )
            messages.success(request, "Scout report saved.")
            return redirect("talent_spot_detail", spot_id=spot.id)
    else:
        form = ScoutReportForm(instance=report)

    return render(request, "posts/scout_report_form.html", {
        "form": form,
        "spot": spot,
        "report": report,
    })


@login_required
def add_to_shortlist(request, spot_id):
    """Add a talent spot to a club shortlist."""
    spot = get_object_or_404(TalentSpot, id=spot_id)
    if request.user.role != "club" and not request.user.is_staff:
        messages.error(request, "Only clubs can shortlist prospects.")
        return redirect("talent_spot_detail", spot_id=spot.id)

    _, created = ClubShortlist.objects.get_or_create(club=request.user, talent_spot=spot)
    if created:
        notify_user(
            spot.spotted_by,
            f"{request.user.username} shortlisted {spot.prospect_name}.",
            actor=request.user,
            target_url=reverse("talent_spot_detail", args=[spot.id]),
            category="contact",
        )
    messages.success(request, "Prospect added to your club shortlist.")
    return redirect("club_shortlist")


@login_required
def claim_talent_spot(request, spot_id):
    spot = get_object_or_404(TalentSpot, id=spot_id)
    if request.user.role != "player":
        messages.error(request, "Only player accounts can claim a talent spot.")
        return redirect("talent_spot_detail", spot_id=spot.id)

    player_profile = getattr(request.user, "player_profile", None)
    if player_profile is None:
        messages.info(request, "Create your player profile before claiming a spot.")
        return redirect("update_profile")

    existing_claim = TalentSpotClaim.objects.filter(talent_spot=spot, player=request.user).first()
    if request.method == "POST":
        form = TalentSpotClaimForm(request.POST, instance=existing_claim)
        if form.is_valid():
            claim = form.save(commit=False)
            claim.talent_spot = spot
            claim.player = request.user
            claim.player_profile = player_profile
            claim.status = TalentSpotClaim.STATUS_PENDING
            claim.reviewed_by = None
            claim.reviewed_at = None
            claim.save()
            notify_user(
                spot.spotted_by,
                f"{request.user.username} claimed your talent spot for {spot.prospect_name}.",
                actor=request.user,
                target_url=reverse("talent_spot_detail", args=[spot.id]),
                category="reports",
            )
            messages.success(request, "Claim submitted for review.")
            return redirect("talent_spot_detail", spot_id=spot.id)
    else:
        form = TalentSpotClaimForm(instance=existing_claim)

    return render(request, "posts/talent_spot_claim_form.html", {
        "form": form,
        "spot": spot,
        "existing_claim": existing_claim,
    })


@login_required
def review_talent_spot_claim(request, claim_id, action):
    claim = get_object_or_404(TalentSpotClaim.objects.select_related("talent_spot", "player"), id=claim_id)
    if request.user.role != "scout" and not request.user.is_staff:
        messages.error(request, "Only scouts and admins can review claims.")
        return redirect("talent_spot_detail", spot_id=claim.talent_spot.id)

    if action == "approve":
        claim.status = TalentSpotClaim.STATUS_APPROVED
        claim.talent_spot.linked_player = claim.player_profile
        claim.talent_spot.status = TalentSpot.STATUS_LINKED
        claim.talent_spot.save(update_fields=["linked_player", "status", "updated_at"])
        message = "Claim approved and linked to player profile."
        notification = f"Your claim for {claim.talent_spot.prospect_name} was approved."
    elif action == "reject":
        claim.status = TalentSpotClaim.STATUS_REJECTED
        message = "Claim rejected."
        notification = f"Your claim for {claim.talent_spot.prospect_name} was rejected."
    else:
        messages.error(request, "Unknown claim action.")
        return redirect("talent_spot_detail", spot_id=claim.talent_spot.id)

    claim.reviewed_by = request.user
    claim.reviewed_at = timezone.now()
    claim.save(update_fields=["status", "reviewed_by", "reviewed_at"])
    notify_user(
        claim.player,
        notification,
        actor=request.user,
        target_url=reverse("talent_spot_detail", args=[claim.talent_spot.id]),
        category="reports",
    )
    messages.success(request, message)
    return redirect("talent_spot_detail", spot_id=claim.talent_spot.id)


@login_required
def notifications(request):
    status = request.GET.get("status", "unread")
    if status not in ("unread", "read", "all"):
        status = "unread"

    base_notifications = request.user.notifications.select_related("actor")
    unread_count = base_notifications.filter(is_read=False).count()
    total_count = base_notifications.count()

    user_notifications = base_notifications
    if status == "unread":
        user_notifications = user_notifications.filter(is_read=False)
    elif status == "read":
        user_notifications = user_notifications.filter(is_read=True)

    return render(request, "posts/notifications.html", {
        "notifications": user_notifications[:50],
        "status": status,
        "unread_count": unread_count,
        "total_count": total_count,
    })


@login_required
def open_notification(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])
    return redirect(notification.target_url or "notifications")


@login_required
def mark_notifications_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect("notifications")


@login_required
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    if request.method == "POST" and not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])
    return redirect(request.META.get("HTTP_REFERER", "notifications"))


@login_required
def club_shortlist(request):
    """Manage a club's recruitment pipeline."""
    if request.user.role != "club" and not request.user.is_staff:
        messages.error(request, "Only club accounts can access the club shortlist.")
        return redirect("talent_spots")

    entries = ClubShortlist.objects.filter(club=request.user).select_related(
        "talent_spot",
        "talent_spot__spotted_by",
    )
    return render(request, "posts/club_shortlist.html", {
        "entries": entries,
        "status_choices": ClubShortlist.STATUS_CHOICES,
    })


@login_required
def update_shortlist_entry(request, entry_id):
    entry = get_object_or_404(ClubShortlist, id=entry_id, club=request.user)

    if request.method == "POST":
        form = ClubShortlistForm(request.POST, instance=entry)
        if form.is_valid():
            form.save()
            messages.success(request, "Shortlist updated.")

    return redirect("club_shortlist")


@login_required
def create_contact_request(request, spot_id):
    spot = get_object_or_404(TalentSpot.objects.select_related("linked_player__user"), id=spot_id)
    if request.user.role != "club" and not request.user.is_staff:
        messages.error(request, "Only clubs can contact players.")
        return redirect("talent_spot_detail", spot_id=spot.id)
    if not spot.linked_player:
        messages.info(request, "This spot must be linked to a player profile before contact.")
        return redirect("talent_spot_detail", spot_id=spot.id)
    player_settings, _ = UserSettings.objects.get_or_create(user=spot.linked_player.user)
    if not player_settings.allow_contact:
        messages.info(request, "This player is not accepting club contact requests right now.")
        return redirect("talent_spot_detail", spot_id=spot.id)

    shortlist_entry, _ = ClubShortlist.objects.get_or_create(club=request.user, talent_spot=spot)
    existing_request = ContactRequest.objects.filter(
        club=request.user,
        player_profile=spot.linked_player,
        talent_spot=spot,
        status=ContactRequest.STATUS_PENDING,
    ).first()

    if request.method == "POST":
        form = ContactRequestForm(request.POST, instance=existing_request)
        if form.is_valid():
            contact_request = form.save(commit=False)
            contact_request.club = request.user
            contact_request.player = spot.linked_player.user
            contact_request.player_profile = spot.linked_player
            contact_request.talent_spot = spot
            contact_request.shortlist_entry = shortlist_entry
            contact_request.status = ContactRequest.STATUS_PENDING
            contact_request.save()
            shortlist_entry.status = ClubShortlist.STATUS_CONTACTED
            shortlist_entry.save(update_fields=["status", "updated_at"])
            notify_user(
                contact_request.player,
                f"{request.user.username} sent you a contact request.",
                actor=request.user,
                target_url=reverse("contact_requests"),
                category="contact",
            )
            messages.success(request, "Contact request sent.")
            return redirect("club_shortlist")
    else:
        form = ContactRequestForm(instance=existing_request)

    return render(request, "posts/contact_request_form.html", {
        "form": form,
        "spot": spot,
        "existing_request": existing_request,
    })


@login_required
def contact_requests(request):
    if request.user.role == "club":
        requests = ContactRequest.objects.filter(club=request.user).select_related("player", "talent_spot")
    elif request.user.role == "player":
        requests = ContactRequest.objects.filter(player=request.user).select_related("club", "talent_spot")
    else:
        requests = ContactRequest.objects.none()

    return render(request, "posts/contact_requests.html", {"contact_requests": requests})


@login_required
def respond_contact_request(request, request_id, action):
    contact_request = get_object_or_404(ContactRequest, id=request_id, player=request.user)
    if contact_request.status != ContactRequest.STATUS_PENDING:
        messages.info(request, "This request has already been handled.")
        return redirect("contact_requests")

    if action == "accept":
        contact_request.status = ContactRequest.STATUS_ACCEPTED
        message = "Contact request accepted."
        notification = f"{request.user.username} accepted your contact request."
    elif action == "decline":
        contact_request.status = ContactRequest.STATUS_DECLINED
        message = "Contact request declined."
        notification = f"{request.user.username} declined your contact request."
    else:
        messages.error(request, "Unknown request action.")
        return redirect("contact_requests")

    contact_request.save(update_fields=["status", "updated_at"])
    notify_user(
        contact_request.club,
        notification,
        actor=request.user,
        target_url=reverse("contact_requests"),
        category="contact",
    )
    messages.success(request, message)
    return redirect("contact_requests")


@login_required
def cancel_contact_request(request, request_id):
    contact_request = get_object_or_404(ContactRequest, id=request_id, club=request.user)
    if contact_request.status == ContactRequest.STATUS_PENDING:
        contact_request.status = ContactRequest.STATUS_CANCELLED
        contact_request.save(update_fields=["status", "updated_at"])
        notify_user(
            contact_request.player,
            f"{request.user.username} cancelled a contact request.",
            actor=request.user,
            target_url=reverse("contact_requests"),
            category="contact",
        )
        messages.success(request, "Contact request cancelled.")
    return redirect("contact_requests")


def opportunities(request):
    opportunities_qs = Opportunity.objects.select_related("publisher").annotate(
        application_count=Count("applications", distinct=True),
        save_count=Count("saved_by", distinct=True),
    )
    query = request.GET.get("q", "").strip()
    opportunity_type = request.GET.get("type", "any")
    status = request.GET.get("status", "open")
    region = request.GET.get("region", "").strip()
    location = request.GET.get("location", "").strip()
    player_age = request.GET.get("age", "").strip()
    deadline_window = request.GET.get("deadline", "any")
    sort = request.GET.get("sort", "recent")
    default_mode = "for_you" if request.user.is_authenticated and request.user.role == "player" else "all"
    mode = request.GET.get("mode", default_mode)

    if query:
        opportunities_qs = opportunities_qs.filter(
            Q(title__icontains=query)
            | Q(location__icontains=query)
            | Q(region__icontains=query)
            | Q(positions__icontains=query)
            | Q(description__icontains=query)
        )
    if opportunity_type and opportunity_type != "any":
        opportunities_qs = opportunities_qs.filter(opportunity_type=opportunity_type)
    if region:
        opportunities_qs = opportunities_qs.filter(region__icontains=region)
    if location:
        opportunities_qs = opportunities_qs.filter(location__icontains=location)
    if player_age:
        try:
            age_value = int(player_age)
        except ValueError:
            age_value = None
        if age_value is not None:
            opportunities_qs = opportunities_qs.filter(
                Q(age_min__isnull=True) | Q(age_min__lte=age_value),
                Q(age_max__isnull=True) | Q(age_max__gte=age_value),
            )
    if status == "open":
        today = timezone.now().date()
        opportunities_qs = opportunities_qs.filter(is_active=True).filter(
            Q(deadline__isnull=True) | Q(deadline__gte=today)
        )
    elif status == "closed":
        today = timezone.now().date()
        opportunities_qs = opportunities_qs.filter(Q(is_active=False) | Q(deadline__lt=today))
    if deadline_window != "any":
        today = timezone.now().date()
        if deadline_window == "7":
            opportunities_qs = opportunities_qs.filter(deadline__isnull=False, deadline__lte=today + timedelta(days=7), deadline__gte=today)
        elif deadline_window == "30":
            opportunities_qs = opportunities_qs.filter(deadline__isnull=False, deadline__lte=today + timedelta(days=30), deadline__gte=today)
        elif deadline_window == "none":
            opportunities_qs = opportunities_qs.filter(deadline__isnull=True)

    saved_opportunity_ids = set()
    applied_opportunity_ids = set()
    if request.user.is_authenticated:
        saved_opportunity_ids = set(request.user.saved_opportunities.values_list("id", flat=True))
        if request.user.role == "player":
            applied_opportunity_ids = set(
                OpportunityApplication.objects.filter(player=request.user).values_list("opportunity_id", flat=True)
            )

    player_profile = getattr(request.user, "player_profile", None) if request.user.is_authenticated else None
    if mode == "for_you" and player_profile:
        opportunities_qs = rank_opportunities_for_player(player_profile, opportunities_qs, exclude_applied=True)
    else:
        sort_options = {
            "recent": "-created_at",
            "deadline": "deadline",
            "event": "event_date",
            "popular": "-application_count",
            "saved": "-save_count",
            "title": "title",
        }
        if sort not in sort_options:
            sort = "recent"
        opportunities_qs = opportunities_qs.order_by(sort_options[sort])

    result_count = len(opportunities_qs) if isinstance(opportunities_qs, list) else opportunities_qs.count()

    return render(request, "posts/opportunities.html", {
        "opportunities": opportunities_qs,
        "query": query,
        "opportunity_type": opportunity_type,
        "status": status,
        "region": region,
        "location": location,
        "player_age": player_age,
        "deadline_window": deadline_window,
        "sort": sort,
        "result_count": result_count,
        "mode": mode,
        "saved_opportunity_ids": saved_opportunity_ids,
        "applied_opportunity_ids": applied_opportunity_ids,
        "type_choices": Opportunity.TYPE_CHOICES,
    })


@login_required
def create_opportunity(request):
    if request.user.role not in ("club", "scout") and not request.user.is_staff:
        messages.error(request, "Only clubs, scouts, and staff can publish opportunities.")
        return redirect("opportunities")

    if request.method == "POST":
        form = OpportunityForm(request.POST)
        if form.is_valid():
            opportunity = form.save(commit=False)
            opportunity.publisher = request.user
            opportunity.save()
            messages.success(request, "Opportunity published.")
            return redirect("opportunity_detail", opportunity_id=opportunity.id)
        messages.error(request, "Please fix the highlighted opportunity details.")
    else:
        form = OpportunityForm()

    return render(request, "posts/opportunity_form.html", {
        "form": form,
        "page_title": "Publish Opportunity",
        "page_description": "Create a clear call for trials, intakes, scholarships, or tournament opportunities.",
        "submit_label": "Publish opportunity",
    })


@login_required
def edit_opportunity(request, opportunity_id):
    opportunity = get_object_or_404(Opportunity, id=opportunity_id)
    if request.user != opportunity.publisher and not request.user.is_staff:
        messages.error(request, "Only the publisher can edit this opportunity.")
        return redirect("opportunity_detail", opportunity_id=opportunity.id)

    if request.method == "POST":
        form = OpportunityForm(request.POST, instance=opportunity)
        if form.is_valid():
            form.save()
            messages.success(request, "Opportunity updated.")
            return redirect("opportunity_detail", opportunity_id=opportunity.id)
        messages.error(request, "Please fix the highlighted opportunity details.")
    else:
        form = OpportunityForm(instance=opportunity)

    return render(request, "posts/opportunity_form.html", {
        "form": form,
        "opportunity": opportunity,
        "page_title": "Edit Opportunity",
        "page_description": "Update dates, eligibility, requirements, visibility, and recruitment instructions.",
        "submit_label": "Save changes",
    })


@login_required
def toggle_opportunity_active(request, opportunity_id):
    opportunity = get_object_or_404(Opportunity, id=opportunity_id)
    if request.user != opportunity.publisher and not request.user.is_staff:
        messages.error(request, "Only the publisher can change this opportunity status.")
        return redirect("opportunity_detail", opportunity_id=opportunity.id)
    if request.method != "POST":
        return redirect("opportunity_detail", opportunity_id=opportunity.id)

    opportunity.is_active = not opportunity.is_active
    opportunity.save(update_fields=["is_active", "updated_at"])
    messages.success(request, "Opportunity reopened." if opportunity.is_active else "Opportunity closed.")
    return redirect(request.META.get("HTTP_REFERER", reverse("opportunity_detail", args=[opportunity.id])))


def opportunity_detail(request, opportunity_id):
    opportunity = get_object_or_404(
        Opportunity.objects.select_related("publisher").annotate(
            application_count=Count("applications", distinct=True),
            save_count=Count("saved_by", distinct=True),
        ),
        id=opportunity_id,
    )
    user_application = None
    applications = OpportunityApplication.objects.none()
    can_manage = False
    is_saved = False
    application_status = request.GET.get("application_status", "all")
    application_status_cards = []

    if request.user.is_authenticated:
        user_application = OpportunityApplication.objects.filter(
            opportunity=opportunity,
            player=request.user,
        ).first()
        is_saved = opportunity.saved_by.filter(id=request.user.id).exists()
        can_manage = request.user == opportunity.publisher or request.user.is_staff
        if can_manage:
            base_applications = opportunity.applications.select_related("player", "player__player_profile")
            total_applications = base_applications.count()
            application_status_cards = [{
                "value": "all",
                "label": "All",
                "count": total_applications,
            }]
            for value, label in OpportunityApplication.STATUS_CHOICES:
                application_status_cards.append({
                    "value": value,
                    "label": label,
                    "count": base_applications.filter(status=value).count(),
                })

            applications = base_applications
            if application_status in dict(OpportunityApplication.STATUS_CHOICES):
                applications = applications.filter(status=application_status)
            else:
                application_status = "all"

    return render(request, "posts/opportunity_detail.html", {
        "opportunity": opportunity,
        "user_application": user_application,
        "applications": applications,
        "can_manage": can_manage,
        "is_saved": is_saved,
        "application_status": application_status,
        "application_status_cards": application_status_cards,
    })


@login_required
def my_opportunity_applications(request):
    if request.user.role != "player":
        messages.error(request, "Only player accounts have opportunity applications.")
        return redirect("opportunities")

    applications = OpportunityApplication.objects.filter(player=request.user).select_related(
        "opportunity",
        "opportunity__publisher",
    )
    status = request.GET.get("status", "all")
    if status in dict(OpportunityApplication.STATUS_CHOICES):
        applications = applications.filter(status=status)

    application_updates = request.user.notifications.filter(
        target_url__contains=reverse("opportunities"),
    ).select_related("actor")[:5]

    return render(request, "posts/my_opportunity_applications.html", {
        "applications": applications,
        "status": status,
        "status_choices": OpportunityApplication.STATUS_CHOICES,
        "application_updates": application_updates,
    })


@login_required
def manage_opportunities(request):
    if request.user.role not in ("club", "scout") and not request.user.is_staff:
        messages.error(request, "Only clubs, scouts, and staff can manage opportunities.")
        return redirect("opportunities")

    opportunities_qs = Opportunity.objects.filter(publisher=request.user).annotate(
        application_count=Count("applications", distinct=True),
        shortlisted_count=Count(
            "applications",
            filter=Q(applications__status=OpportunityApplication.STATUS_SHORTLISTED),
            distinct=True,
        ),
    )
    if request.user.is_staff and request.GET.get("scope") == "all":
        opportunities_qs = Opportunity.objects.select_related("publisher").annotate(
            application_count=Count("applications", distinct=True),
            shortlisted_count=Count(
                "applications",
                filter=Q(applications__status=OpportunityApplication.STATUS_SHORTLISTED),
                distinct=True,
            ),
        )

    opportunity_alerts_qs = request.user.notifications.filter(
        target_url__contains=reverse("opportunities"),
    ).select_related("actor")
    unread_opportunity_alerts = opportunity_alerts_qs.filter(is_read=False).count()
    opportunity_alerts = opportunity_alerts_qs[:5]

    return render(request, "posts/manage_opportunities.html", {
        "opportunities": opportunities_qs,
        "scope": request.GET.get("scope", "mine"),
        "opportunity_alerts": opportunity_alerts,
        "unread_opportunity_alerts": unread_opportunity_alerts,
    })


@login_required
def saved_opportunities(request):
    opportunities_qs = request.user.saved_opportunities.select_related("publisher").annotate(
        application_count=Count("applications", distinct=True),
        save_count=Count("saved_by", distinct=True),
    )
    return render(request, "posts/saved_opportunities.html", {"opportunities": opportunities_qs})


@login_required
def toggle_save_opportunity(request, opportunity_id):
    if request.method != "POST":
        return redirect("opportunity_detail", opportunity_id=opportunity_id)

    opportunity = get_object_or_404(Opportunity, id=opportunity_id)
    if request.user in opportunity.saved_by.all():
        opportunity.saved_by.remove(request.user)
        messages.info(request, "Opportunity removed from saved list.")
    else:
        opportunity.saved_by.add(request.user)
        messages.success(request, "Opportunity saved.")

    return redirect(request.META.get("HTTP_REFERER", reverse("opportunity_detail", args=[opportunity.id])))


@login_required
def apply_opportunity(request, opportunity_id):
    opportunity = get_object_or_404(Opportunity, id=opportunity_id)
    if request.user.role != "player":
        messages.error(request, "Only player accounts can apply for opportunities.")
        return redirect("opportunity_detail", opportunity_id=opportunity.id)
    if not opportunity.is_open:
        messages.info(request, "This opportunity is no longer accepting applications.")
        return redirect("opportunity_detail", opportunity_id=opportunity.id)

    existing = OpportunityApplication.objects.filter(opportunity=opportunity, player=request.user).first()
    if request.method == "POST":
        form = OpportunityApplicationForm(request.POST, instance=existing)
        if form.is_valid():
            application = form.save(commit=False)
            application.opportunity = opportunity
            application.player = request.user
            application.status = OpportunityApplication.STATUS_SUBMITTED
            application.save()
            notify_user(
                opportunity.publisher,
                f"{request.user.username} applied for {opportunity.title}.",
                actor=request.user,
                target_url=reverse("opportunity_detail", args=[opportunity.id]),
                category="contact",
            )
            messages.success(request, "Application sent.")
            return redirect("opportunity_detail", opportunity_id=opportunity.id)
        messages.error(request, "Please fix the highlighted application details.")
    else:
        form = OpportunityApplicationForm(instance=existing)

    return render(request, "posts/opportunity_apply.html", {
        "form": form,
        "opportunity": opportunity,
        "existing": existing,
    })


@login_required
def withdraw_opportunity_application(request, application_id):
    application = get_object_or_404(
        OpportunityApplication.objects.select_related("opportunity", "opportunity__publisher", "player"),
        id=application_id,
        player=request.user,
    )
    if request.method != "POST":
        return redirect("opportunity_detail", opportunity_id=application.opportunity.id)

    if application.status == OpportunityApplication.STATUS_WITHDRAWN:
        messages.info(request, "This application is already withdrawn.")
        return redirect("my_opportunity_applications")

    application.status = OpportunityApplication.STATUS_WITHDRAWN
    application.save(update_fields=["status", "updated_at"])
    notify_user(
        application.opportunity.publisher,
        f"{request.user.username} withdrew their application for {application.opportunity.title}.",
        actor=request.user,
        target_url=reverse("opportunity_detail", args=[application.opportunity.id]),
        category="contact",
    )
    messages.success(request, "Application withdrawn.")
    return redirect("my_opportunity_applications")


@login_required
def update_opportunity_application(request, application_id, action):
    application = get_object_or_404(
        OpportunityApplication.objects.select_related("opportunity", "player"),
        id=application_id,
    )
    if request.user != application.opportunity.publisher and not request.user.is_staff:
        messages.error(request, "Only the publisher can manage these applications.")
        return redirect("opportunity_detail", opportunity_id=application.opportunity.id)
    if request.method != "POST":
        return redirect("opportunity_detail", opportunity_id=application.opportunity.id)
    if application.status == OpportunityApplication.STATUS_WITHDRAWN:
        messages.info(request, "Withdrawn applications cannot be updated by the publisher.")
        return redirect("opportunity_detail", opportunity_id=application.opportunity.id)

    status_map = {
        "review": OpportunityApplication.STATUS_REVIEWING,
        "shortlist": OpportunityApplication.STATUS_SHORTLISTED,
        "decline": OpportunityApplication.STATUS_DECLINED,
    }
    next_status = status_map.get(action)
    if not next_status:
        messages.error(request, "Unknown application action.")
        return redirect("opportunity_detail", opportunity_id=application.opportunity.id)

    application.status = next_status
    application.save(update_fields=["status", "updated_at"])
    notify_user(
        application.player,
        f"Your application for {application.opportunity.title} is now {application.get_status_display().lower()}.",
        actor=request.user,
        target_url=reverse("opportunity_detail", args=[application.opportunity.id]),
        category="contact",
    )
    messages.success(request, "Application updated.")
    return redirect("opportunity_detail", opportunity_id=application.opportunity.id)
