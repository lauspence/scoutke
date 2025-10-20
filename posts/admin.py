from django.contrib import admin
from .models import Post, Comment

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("author", "created_at", "total_likes")
    list_filter = ("created_at", "author")
    search_fields = ("author__username", "content")

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("post", "author", "created_at")
    search_fields = ("author__username", "content")
