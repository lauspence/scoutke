from django.db import models
from django.conf import settings
from django.utils.timesince import timesince
from django.utils.timezone import now

class Post(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="posts"
    )
    content = models.TextField(blank=True)
    image = models.ImageField(upload_to="posts/images/", blank=True, null=True)
    video = models.FileField(upload_to="posts/videos/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    likes = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        related_name="liked_posts", 
        blank=True
    )

    # ✅ NEW FIELD: track reposts
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
