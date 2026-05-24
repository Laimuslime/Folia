from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["username", "email", "display_name", "karma", "is_active", "created_at"]
    search_fields = ["username", "email", "display_name"]
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Folia", {"fields": ("display_name", "bio", "avatar", "karma", "language")}),
    )
