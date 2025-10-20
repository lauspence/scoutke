# players/models.py
from django.db import models
from django.conf import settings

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

    def __str__(self):
        return f"{self.user.username} - {self.position}"
