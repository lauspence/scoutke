from django.db import models
from django.conf import settings
from django.utils.timesince import timesince
from django.utils.timezone import now

class Post(models.Model):
    CATEGORY_GENERAL = "general"
    CATEGORY_TALENT = "talent"
    CATEGORY_MATCH = "match"
    CATEGORY_NEWS = "news"

    CATEGORY_CHOICES = (
        (CATEGORY_GENERAL, "Football talk"),
        (CATEGORY_TALENT, "Talent spotted"),
        (CATEGORY_MATCH, "Match update"),
        (CATEGORY_NEWS, "Local football news"),
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posts"
    )
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default=CATEGORY_GENERAL,
    )
    content = models.TextField(blank=True)
    prospect_name = models.CharField(max_length=150, blank=True)
    location = models.CharField(max_length=150, blank=True)
    image = models.ImageField(upload_to="posts/images/", blank=True, null=True)
    video = models.FileField(upload_to="posts/videos/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    likes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="liked_posts",
        blank=True
    )

    # Track reposts.
    original_post = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reposts"
    )

    def total_likes(self):
        return self.likes.count()

    @property
    def time_since(self):
        delta = now() - self.created_at
        if delta.total_seconds() < 60:
            return "just now"
        return f"{timesince(self.created_at, now())} ago"

    def is_repost(self):
        return self.original_post is not None

    def __str__(self):
        if self.is_repost():
            return f"Repost by {self.author.username} of {self.original_post.author.username}"
        return f"{self.author.username} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ['-created_at']


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.author.username} on {self.post.id}"


class TalentSpot(models.Model):
    STATUS_NEW = "new"
    STATUS_COMMUNITY_CONFIRMED = "community_confirmed"
    STATUS_SCOUT_VERIFIED = "scout_verified"
    STATUS_LINKED = "linked"
    STATUS_ARCHIVED = "archived"

    STATUS_CHOICES = (
        (STATUS_NEW, "New lead"),
        (STATUS_COMMUNITY_CONFIRMED, "Community confirmed"),
        (STATUS_SCOUT_VERIFIED, "Scout verified"),
        (STATUS_LINKED, "Linked to player"),
        (STATUS_ARCHIVED, "Archived"),
    )

    POSITION_CHOICES = (
        ("unknown", "Unknown"),
        ("Forward", "Forward"),
        ("Midfielder", "Midfielder"),
        ("Defender", "Defender"),
        ("Goalkeeper", "Goalkeeper"),
    )

    spotted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="talent_spots",
    )
    source_post = models.OneToOneField(
        Post,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="talent_spot",
    )
    linked_player = models.ForeignKey(
        "players.PlayerProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="talent_spots",
    )
    confirmations = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="confirmed_talent_spots",
        blank=True,
    )
    prospect_name = models.CharField(max_length=150)
    position = models.CharField(max_length=50, choices=POSITION_CHOICES, default="unknown")
    age_estimate = models.PositiveIntegerField(blank=True, null=True)
    team_or_school = models.CharField(max_length=150, blank=True)
    location = models.CharField(max_length=150)
    event_name = models.CharField(max_length=150, blank=True)
    notes = models.TextField()
    evidence_image = models.ImageField(upload_to="talent_spots/images/", blank=True, null=True)
    evidence_video = models.FileField(upload_to="talent_spots/videos/", blank=True, null=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_NEW)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def confirmation_count(self):
        return self.confirmations.count()

    def refresh_status(self):
        if self.linked_player_id:
            self.status = self.STATUS_LINKED
        elif self.status not in (self.STATUS_SCOUT_VERIFIED, self.STATUS_ARCHIVED):
            if self.confirmation_count() >= 3:
                self.status = self.STATUS_COMMUNITY_CONFIRMED
            else:
                self.status = self.STATUS_NEW
        self.save(update_fields=["status", "updated_at"])

    def __str__(self):
        return f"{self.prospect_name} spotted at {self.location}"

    class Meta:
        ordering = ["-created_at"]


class ScoutReport(models.Model):
    RECOMMENDATION_MONITOR = "monitor"
    RECOMMENDATION_TRIAL = "trial"
    RECOMMENDATION_SIGN = "sign"
    RECOMMENDATION_PASS = "pass"

    RECOMMENDATION_CHOICES = (
        (RECOMMENDATION_MONITOR, "Keep monitoring"),
        (RECOMMENDATION_TRIAL, "Invite for trial"),
        (RECOMMENDATION_SIGN, "Strong signing prospect"),
        (RECOMMENDATION_PASS, "Not recommended now"),
    )

    talent_spot = models.ForeignKey(
        TalentSpot,
        on_delete=models.CASCADE,
        related_name="scout_reports",
    )
    scout = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="scout_reports",
    )
    technical = models.PositiveSmallIntegerField(default=5)
    physical = models.PositiveSmallIntegerField(default=5)
    tactical = models.PositiveSmallIntegerField(default=5)
    mentality = models.PositiveSmallIntegerField(default=5)
    potential = models.PositiveSmallIntegerField(default=5)
    summary = models.TextField()
    recommendation = models.CharField(
        max_length=20,
        choices=RECOMMENDATION_CHOICES,
        default=RECOMMENDATION_MONITOR,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def average_score(self):
        return round(
            (self.technical + self.physical + self.tactical + self.mentality + self.potential) / 5,
            1,
        )

    def __str__(self):
        return f"{self.scout.username} report on {self.talent_spot.prospect_name}"

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("talent_spot", "scout")


class ClubShortlist(models.Model):
    STATUS_WATCHING = "watching"
    STATUS_CONTACTED = "contacted"
    STATUS_TRIAL = "trial"
    STATUS_SIGNED = "signed"
    STATUS_REJECTED = "rejected"

    STATUS_CHOICES = (
        (STATUS_WATCHING, "Watching"),
        (STATUS_CONTACTED, "Contacted"),
        (STATUS_TRIAL, "Trial"),
        (STATUS_SIGNED, "Signed"),
        (STATUS_REJECTED, "Rejected"),
    )

    club = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="club_shortlist",
    )
    talent_spot = models.ForeignKey(
        TalentSpot,
        on_delete=models.CASCADE,
        related_name="club_shortlists",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_WATCHING)
    private_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.club.username} - {self.talent_spot.prospect_name}"

    class Meta:
        ordering = ["-updated_at"]
        unique_together = ("club", "talent_spot")


class TalentSpotClaim(models.Model):
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"

    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    )

    talent_spot = models.ForeignKey(
        TalentSpot,
        on_delete=models.CASCADE,
        related_name="claims",
    )
    player = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="talent_spot_claims",
    )
    player_profile = models.ForeignKey(
        "players.PlayerProfile",
        on_delete=models.CASCADE,
        related_name="talent_spot_claims",
    )
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="reviewed_talent_spot_claims",
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.player.username} claim for {self.talent_spot.prospect_name}"

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("talent_spot", "player")


class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="sent_notifications",
        blank=True,
        null=True,
    )
    message = models.CharField(max_length=255)
    target_url = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.recipient.username}: {self.message}"

    class Meta:
        ordering = ["-created_at"]


class ContactRequest(models.Model):
    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"
    STATUS_DECLINED = "declined"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_DECLINED, "Declined"),
        (STATUS_CANCELLED, "Cancelled"),
    )

    club = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_contact_requests",
    )
    player = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_contact_requests",
    )
    player_profile = models.ForeignKey(
        "players.PlayerProfile",
        on_delete=models.CASCADE,
        related_name="contact_requests",
    )
    talent_spot = models.ForeignKey(
        TalentSpot,
        on_delete=models.SET_NULL,
        related_name="contact_requests",
        blank=True,
        null=True,
    )
    shortlist_entry = models.ForeignKey(
        ClubShortlist,
        on_delete=models.SET_NULL,
        related_name="contact_requests",
        blank=True,
        null=True,
    )
    message = models.TextField()
    proposed_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.club.username} request to {self.player.username}"

    class Meta:
        ordering = ["-created_at"]


class Opportunity(models.Model):
    TYPE_TRIAL = "trial"
    TYPE_OPEN_DAY = "open_day"
    TYPE_SCHOLARSHIP = "scholarship"
    TYPE_TOURNAMENT = "tournament"
    TYPE_ACADEMY = "academy"

    TYPE_CHOICES = (
        (TYPE_TRIAL, "Trial"),
        (TYPE_OPEN_DAY, "Open day"),
        (TYPE_SCHOLARSHIP, "Scholarship"),
        (TYPE_TOURNAMENT, "Tournament"),
        (TYPE_ACADEMY, "Academy intake"),
    )

    publisher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="opportunities",
    )
    title = models.CharField(max_length=180)
    opportunity_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default=TYPE_TRIAL)
    location = models.CharField(max_length=150)
    region = models.CharField(max_length=120, blank=True)
    deadline = models.DateField(blank=True, null=True)
    event_date = models.DateField(blank=True, null=True)
    age_min = models.PositiveSmallIntegerField(blank=True, null=True)
    age_max = models.PositiveSmallIntegerField(blank=True, null=True)
    positions = models.CharField(max_length=180, blank=True)
    description = models.TextField()
    requirements = models.TextField(blank=True)
    contact_instructions = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    saved_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="saved_opportunities",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_open(self):
        return self.is_active and (not self.deadline or self.deadline >= now().date())

    def __str__(self):
        return self.title

    class Meta:
        ordering = ["-created_at"]


class OpportunityApplication(models.Model):
    STATUS_SUBMITTED = "submitted"
    STATUS_REVIEWING = "reviewing"
    STATUS_SHORTLISTED = "shortlisted"
    STATUS_DECLINED = "declined"
    STATUS_WITHDRAWN = "withdrawn"

    STATUS_CHOICES = (
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_REVIEWING, "Reviewing"),
        (STATUS_SHORTLISTED, "Shortlisted"),
        (STATUS_DECLINED, "Declined"),
        (STATUS_WITHDRAWN, "Withdrawn"),
    )

    opportunity = models.ForeignKey(
        Opportunity,
        on_delete=models.CASCADE,
        related_name="applications",
    )
    player = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="opportunity_applications",
    )
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SUBMITTED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.player.username} -> {self.opportunity.title}"

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("opportunity", "player")


class ContentReport(models.Model):
    REASON_SPAM = "spam"
    REASON_ABUSE = "abuse"
    REASON_FALSE_INFO = "false_info"
    REASON_SAFETY = "safety"
    REASON_OTHER = "other"

    REASON_CHOICES = (
        (REASON_SPAM, "Spam or scam"),
        (REASON_ABUSE, "Harassment or abuse"),
        (REASON_FALSE_INFO, "False or misleading information"),
        (REASON_SAFETY, "Player safety concern"),
        (REASON_OTHER, "Other"),
    )

    STATUS_OPEN = "open"
    STATUS_REVIEWING = "reviewing"
    STATUS_RESOLVED = "resolved"
    STATUS_DISMISSED = "dismissed"

    STATUS_CHOICES = (
        (STATUS_OPEN, "Open"),
        (STATUS_REVIEWING, "Reviewing"),
        (STATUS_RESOLVED, "Resolved"),
        (STATUS_DISMISSED, "Dismissed"),
    )

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="content_reports",
    )
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="reports", blank=True, null=True)
    talent_spot = models.ForeignKey(TalentSpot, on_delete=models.CASCADE, related_name="reports", blank=True, null=True)
    reason = models.CharField(max_length=30, choices=REASON_CHOICES)
    details = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="reviewed_content_reports",
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(post__isnull=False, talent_spot__isnull=True)
                    | models.Q(post__isnull=True, talent_spot__isnull=False)
                ),
                name="content_report_exactly_one_target",
            )
        ]

    @property
    def target_label(self):
        if self.post_id:
            return f"Post #{self.post_id}"
        return f"Talent spot #{self.talent_spot_id}"

    def __str__(self):
        return f"{self.reporter.username} reported {self.target_label}"
