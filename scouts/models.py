from django.db import models
from django.conf import settings   # ✅ instead of importing User directly

class PlayerPost(models.Model):
    player_name = models.CharField(max_length=100)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    # Use AUTH_USER_MODEL instead of auth.User
    reposts = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="reposted_posts", blank=True)

    def repost_count(self):
        return self.reposts.count()

    def __str__(self):
        return f"{self.player_name} - {self.description[:20]}"
