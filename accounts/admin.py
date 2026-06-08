from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, UserSettings, VerificationRequest


class CustomUserAdmin(UserAdmin):
    # Fields to display in the admin list
    list_display = ('username', 'email', 'role', 'verification_status', 'is_staff', 'is_active')
    list_filter = ('role', 'verification_status', 'is_staff', 'is_active')

    # Fields to show when editing/creating a user
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('role', 'bio', 'profile_picture', 'verification_status', 'verified_at')}),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('role', 'bio', 'profile_picture')}),
    )


admin.site.register(User, CustomUserAdmin)


@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    list_display = ("user", "profile_visibility", "default_feed", "layout_density", "updated_at")
    list_filter = ("profile_visibility", "default_feed", "layout_density")
    search_fields = ("user__username", "user__email")


@admin.register(VerificationRequest)
class VerificationRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "organization_name", "status", "reviewed_by", "created_at", "reviewed_at")
    list_filter = ("status", "created_at")
    search_fields = ("user__username", "user__email", "organization_name", "role_context")
    readonly_fields = ("created_at", "updated_at", "reviewed_at")
