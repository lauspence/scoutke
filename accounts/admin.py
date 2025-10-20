from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


class CustomUserAdmin(UserAdmin):
    # Fields to display in the admin list
    list_display = ('username', 'email', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')

    # Fields to show when editing/creating a user
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('role', 'bio', 'profile_picture')}),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('role', 'bio', 'profile_picture')}),
    )


admin.site.register(User, CustomUserAdmin)
