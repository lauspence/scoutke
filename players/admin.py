# players/admin.py
from django.contrib import admin
from .models import PlayerProfile, ProfileView

@admin.register(PlayerProfile)
class PlayerProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user", "full_name", "position", "current_club", "region", "updated_at"
    )
    list_filter = ("position", "region", "current_club")
    search_fields = ("user__username", "full_name", "current_club")
    readonly_fields = ("updated_at",)
    fieldsets = (
        ("Basic Info", {
            "fields": ("user", "full_name", "age", "nationality", "region")
        }),
        ("Physical Attributes", {
            "fields": ("height_cm", "weight_kg", "preferred_foot")
        }),
        ("Football Details", {
            "fields": ("position", "current_club", "jersey_number")
        }),
        ("Performance Stats", {
            "fields": ("matches_played", "goals", "assists", "yellow_cards", "red_cards")
        }),
        ("Media", {
            "fields": ("profile_picture", "highlight_video")
        }),
        ("Bio & Metadata", {
            "fields": ("bio", "updated_at")
        }),
    )


@admin.register(ProfileView)
class ProfileViewAdmin(admin.ModelAdmin):
    list_display = ("player", "viewer", "view_count", "last_viewed_at")
    list_filter = ("last_viewed_at", "viewer__role")
    search_fields = ("player__user__username", "viewer__username")
    readonly_fields = ("first_viewed_at", "last_viewed_at")
