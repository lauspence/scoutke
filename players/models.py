from django.db import models
from django.conf import settings
from django.db.models import Avg

class PlayerProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="player_profile"
    )

    # ---- Choices ----
    REGION_CHOICES = [
        ("Nairobi", "Nairobi"),
        ("Mombasa", "Mombasa"),
        ("Kisumu", "Kisumu"),
        # Add more as needed
    ]

    POSITION_CHOICES = [
        ("Forward", "Forward"),
        ("Midfielder", "Midfielder"),
        ("Defender", "Defender"),
        ("Goalkeeper", "Goalkeeper"),
    ]

    # Basic info
    full_name = models.CharField(max_length=150, blank=True, null=True)
    age = models.PositiveIntegerField(blank=True, null=True)
    nationality = models.CharField(max_length=100, blank=True, null=True)
    region = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        choices=REGION_CHOICES,
        help_text="Region/Province"
    )

    # Physical attributes
    height_cm = models.PositiveIntegerField(blank=True, null=True, help_text="Height in cm")
    weight_kg = models.PositiveIntegerField(blank=True, null=True, help_text="Weight in kg")
    preferred_foot = models.CharField(
        max_length=10,
        choices=[("right", "Right"), ("left", "Left"), ("both", "Both")],
        default="right"
    )

    # Football details
    position = models.CharField(
        max_length=50,
        choices=POSITION_CHOICES,
        help_text="E.g., Striker, Midfielder, Defender, Goalkeeper"
    )
    current_club = models.CharField(max_length=100, blank=True, null=True)
    jersey_number = models.CharField(max_length=10, blank=True, null=True)

    # Performance stats
    matches_played = models.PositiveIntegerField(default=0)
    goals = models.PositiveIntegerField(default=0)
    assists = models.PositiveIntegerField(default=0)
    yellow_cards = models.PositiveIntegerField(default=0)
    red_cards = models.PositiveIntegerField(default=0)

    # Media
    profile_picture = models.ImageField(upload_to="players/profile_pics/", blank=True, null=True)
    highlight_video = models.URLField(blank=True, null=True, help_text="YouTube/Vimeo link to highlights")

    # Metadata
    bio = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def completion_percent(self):
        fields = [
            self.full_name,
            self.age,
            self.nationality,
            self.region,
            self.position,
            self.current_club,
            self.height_cm,
            self.weight_kg,
            self.bio,
            self.highlight_video,
        ]
        return round((sum(1 for value in fields if value) / len(fields)) * 100)

    @property
    def talent_score(self):
        from posts.models import ContactRequest, ScoutReport, TalentSpot

        score = 0
        score += min(30, round(self.completion_percent * 0.3))
        if self.profile_picture or self.user.profile_picture:
            score += 8
        if self.highlight_video:
            score += 12

        score += min(10, self.user.posts.count() * 2)
        score += min(10, self.user.followers.count() * 2)

        linked_spots = TalentSpot.objects.filter(linked_player=self)
        score += min(12, linked_spots.count() * 4)
        if linked_spots.filter(status=TalentSpot.STATUS_SCOUT_VERIFIED).exists():
            score += 8
        if linked_spots.filter(status=TalentSpot.STATUS_COMMUNITY_CONFIRMED).exists():
            score += 5

        reports = ScoutReport.objects.filter(talent_spot__linked_player=self)
        report_average = reports.aggregate(avg=Avg("potential"))["avg"] or 0
        score += min(10, round(report_average))

        if ContactRequest.objects.filter(player_profile=self).exists():
            score += 5

        return min(100, score)

    def __str__(self):
        return f"{self.user.username} - {self.position}"


class ProfileView(models.Model):
    player = models.ForeignKey(
        PlayerProfile,
        on_delete=models.CASCADE,
        related_name="profile_views",
    )
    viewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile_views_made",
    )
    view_count = models.PositiveIntegerField(default=1)
    first_viewed_at = models.DateTimeField(auto_now_add=True)
    last_viewed_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_viewed_at"]
        unique_together = ("player", "viewer")

    def __str__(self):
        return f"{self.viewer} viewed {self.player}"
