from django.contrib import admin
from .models import Site, SiteSettings, Member, Admin, Moderator, MemberApplication, Theme, License


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ["slug", "name", "private", "visible", "date_created"]
    search_fields = ["slug", "name"]


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ["site", "forum_enabled", "per_page_discussion"]


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ["user", "site", "date_joined"]
    list_filter = ["site"]


@admin.register(Admin)
class AdminAdmin(admin.ModelAdmin):
    list_display = ["user", "site", "founder"]
    list_filter = ["site"]


@admin.register(Moderator)
class ModeratorAdmin(admin.ModelAdmin):
    list_display = ["user", "site"]
    list_filter = ["site"]


@admin.register(MemberApplication)
class MemberApplicationAdmin(admin.ModelAdmin):
    list_display = ["user", "site", "status", "date"]
    list_filter = ["site", "status"]


@admin.register(Theme)
class ThemeAdmin(admin.ModelAdmin):
    list_display = ["name", "unix_name", "custom", "site"]


@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    list_display = ["name", "sort"]
