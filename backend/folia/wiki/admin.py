from django.contrib import admin
from .models import (
    Category, Page, PageSource, PageRevision, PageCompiled,
    PageTag, PageRateVote, File, PageEditLock, LogEvent,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "site", "permissions_default"]
    list_filter = ["site"]


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ["unix_name", "title", "site", "category", "rate", "revision_number", "date_created"]
    search_fields = ["unix_name", "title"]
    list_filter = ["site", "category"]


@admin.register(PageRevision)
class PageRevisionAdmin(admin.ModelAdmin):
    list_display = ["page", "revision_number", "user_string", "flag_text", "flag_title", "flag_new", "date_last_edited"]
    list_filter = ["site"]


@admin.register(PageTag)
class PageTagAdmin(admin.ModelAdmin):
    list_display = ["page", "tag"]
    list_filter = ["site"]


@admin.register(PageRateVote)
class PageRateVoteAdmin(admin.ModelAdmin):
    list_display = ["page", "user", "rate", "date"]


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ["filename", "page", "size", "mimetype", "date_added"]
    list_filter = ["site"]


@admin.register(LogEvent)
class LogEventAdmin(admin.ModelAdmin):
    list_display = ["type", "page", "user", "date", "text"]
    list_filter = ["site", "type"]
