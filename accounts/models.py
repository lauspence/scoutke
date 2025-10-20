from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ('player', 'Player'),
        ('scout', 'Scout'),
        ('club', 'Club'),
        ("fan", "Fan"),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)

    followers = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='following',
        blank=True
    )

    
    # ✅ Scouts can bookmark/save players
    saved_players = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='saved_by',
        blank=True
    )

    def __str__(self):
        return f"{self.username} ({self.role})"
