from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class User(AbstractUser):
    ROLE_CHOICES = (
        ('player', 'Player'),
        ('scout', 'Scout'),
        ('club', 'Club'),
        ("fan", "Fan"),
    )
    VERIFICATION_NOT_REQUESTED = "not_requested"
    VERIFICATION_PENDING = "pending"
    VERIFICATION_VERIFIED = "verified"
    VERIFICATION_REJECTED = "rejected"

    VERIFICATION_CHOICES = (
        (VERIFICATION_NOT_REQUESTED, "Not requested"),
        (VERIFICATION_PENDING, "Pending review"),
        (VERIFICATION_VERIFIED, "Verified"),
        (VERIFICATION_REJECTED, "Needs more information"),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_CHOICES,
        default=VERIFICATION_NOT_REQUESTED,
    )
    verified_at = models.DateTimeField(blank=True, null=True)

    followers = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='following',
        blank=True
    )


    # Scouts can bookmark/save players.
    saved_players = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='saved_by',
        blank=True
    )

    def __str__(self):
        return f"{self.username} ({self.role})"

    @property
    def unread_notifications_count(self):
        return self.notifications.filter(is_read=False).count()

    @property
    def recent_unread_notifications(self):
        return self.notifications.filter(is_read=False).select_related("actor")[:5]

    @property
    def is_verified_account(self):
        return self.verification_status == self.VERIFICATION_VERIFIED


class UserSettings(models.Model):
    PROFILE_PUBLIC = "public"
    PROFILE_LOGGED_IN = "logged_in"
    PROFILE_SCOUTS_CLUBS = "scouts_clubs"

    PROFILE_VISIBILITY_CHOICES = (
        (PROFILE_PUBLIC, "Public"),
        (PROFILE_LOGGED_IN, "Logged-in users"),
        (PROFILE_SCOUTS_CLUBS, "Scouts and clubs"),
    )

    FEED_ALL = "all"
    FEED_FOLLOWING = "following"
    FEED_TALENT = "talent"

    DEFAULT_FEED_CHOICES = (
        (FEED_ALL, "All football posts"),
        (FEED_FOLLOWING, "Following only"),
        (FEED_TALENT, "Talent spots"),
    )

    DENSITY_COMFORTABLE = "comfortable"
    DENSITY_COMPACT = "compact"

    LAYOUT_DENSITY_CHOICES = (
        (DENSITY_COMFORTABLE, "Comfortable"),
        (DENSITY_COMPACT, "Compact"),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="settings")
    layout_density = models.CharField(max_length=20, choices=LAYOUT_DENSITY_CHOICES, default=DENSITY_COMFORTABLE)
    notify_in_app = models.BooleanField(default=True)
    notify_email = models.BooleanField(default=False)
    notify_contact = models.BooleanField(default=True)
    notify_reports = models.BooleanField(default=True)
    notify_social = models.BooleanField(default=True)
    profile_visibility = models.CharField(max_length=20, choices=PROFILE_VISIBILITY_CHOICES, default=PROFILE_PUBLIC)
    show_email = models.BooleanField(default=False)
    allow_contact = models.BooleanField(default=True)
    show_stats = models.BooleanField(default=True)
    default_feed = models.CharField(max_length=20, choices=DEFAULT_FEED_CHOICES, default=FEED_ALL)
    autoplay_video = models.BooleanField(default=False)
    show_media = models.BooleanField(default=True)
    compact_cards = models.BooleanField(default=False)
    player_available = models.BooleanField(default=True)
    player_trials = models.BooleanField(default=False)
    scout_regional_alerts = models.BooleanField(default=True)
    scout_shortlist_alerts = models.BooleanField(default=True)
    club_trial_ready = models.BooleanField(default=True)
    club_contact_alerts = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Settings for {self.user.username}"


class VerificationRequest(models.Model):
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"

    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="verification_requests")
    organization_name = models.CharField(max_length=160)
    role_context = models.CharField(max_length=220)
    evidence = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    staff_note = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="reviewed_verification_requests",
    )
    reviewed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} verification ({self.status})"

    def approve(self, reviewer):
        self.status = self.STATUS_APPROVED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
        self.user.verification_status = User.VERIFICATION_VERIFIED
        self.user.verified_at = self.reviewed_at
        self.user.save(update_fields=["verification_status", "verified_at"])

    def reject(self, reviewer):
        self.status = self.STATUS_REJECTED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
        self.user.verification_status = User.VERIFICATION_REJECTED
        self.user.verified_at = None
        self.user.save(update_fields=["verification_status", "verified_at"])
