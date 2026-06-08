from django.contrib import admin
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

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("author", "created_at", "total_likes")
    list_filter = ("created_at", "author")
    search_fields = ("author__username", "content")

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("post", "author", "created_at")
    search_fields = ("author__username", "content")


@admin.register(TalentSpot)
class TalentSpotAdmin(admin.ModelAdmin):
    list_display = ("prospect_name", "position", "location", "status", "spotted_by", "created_at")
    list_filter = ("status", "position", "created_at")
    search_fields = ("prospect_name", "location", "team_or_school", "event_name", "notes")
    autocomplete_fields = ("spotted_by", "linked_player", "source_post")


@admin.register(ScoutReport)
class ScoutReportAdmin(admin.ModelAdmin):
    list_display = ("talent_spot", "scout", "recommendation", "average_score", "created_at")
    list_filter = ("recommendation", "created_at")
    search_fields = ("talent_spot__prospect_name", "scout__username", "summary")
    autocomplete_fields = ("talent_spot", "scout")


@admin.register(ClubShortlist)
class ClubShortlistAdmin(admin.ModelAdmin):
    list_display = ("club", "talent_spot", "status", "updated_at")
    list_filter = ("status", "updated_at")
    search_fields = ("club__username", "talent_spot__prospect_name", "private_notes")
    autocomplete_fields = ("club", "talent_spot")


@admin.register(TalentSpotClaim)
class TalentSpotClaimAdmin(admin.ModelAdmin):
    list_display = ("talent_spot", "player", "status", "created_at", "reviewed_by")
    list_filter = ("status", "created_at")
    search_fields = ("talent_spot__prospect_name", "player__username", "message")
    autocomplete_fields = ("talent_spot", "player", "player_profile", "reviewed_by")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient", "message", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("recipient__username", "actor__username", "message")
    autocomplete_fields = ("recipient", "actor")


@admin.register(ContactRequest)
class ContactRequestAdmin(admin.ModelAdmin):
    list_display = ("club", "player", "status", "proposed_date", "created_at")
    list_filter = ("status", "created_at", "proposed_date")
    search_fields = ("club__username", "player__username", "message")
    autocomplete_fields = ("club", "player", "player_profile", "talent_spot", "shortlist_entry")


@admin.register(ContentReport)
class ContentReportAdmin(admin.ModelAdmin):
    list_display = ("target_label", "reporter", "reason", "status", "created_at", "reviewed_by")
    list_filter = ("status", "reason", "created_at")
    search_fields = ("reporter__username", "details", "post__content", "talent_spot__prospect_name")
    autocomplete_fields = ("reporter", "post", "talent_spot", "reviewed_by")


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = ("title", "publisher", "opportunity_type", "location", "deadline", "is_active", "saved_count")
    list_filter = ("opportunity_type", "is_active", "deadline")
    search_fields = ("title", "publisher__username", "location", "region", "positions")
    autocomplete_fields = ("publisher",)

    def saved_count(self, obj):
        return obj.saved_by.count()


@admin.register(OpportunityApplication)
class OpportunityApplicationAdmin(admin.ModelAdmin):
    list_display = ("opportunity", "player", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("opportunity__title", "player__username", "message")
    autocomplete_fields = ("opportunity", "player")
