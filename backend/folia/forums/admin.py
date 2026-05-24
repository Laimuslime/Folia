from django.contrib import admin
from .models import ForumGroup, ForumCategory, ForumThread, ForumPost


@admin.register(ForumGroup)
class ForumGroupAdmin(admin.ModelAdmin):
    list_display = ["name", "site", "sort_index", "visible"]
    list_filter = ["site"]


@admin.register(ForumCategory)
class ForumCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "group", "number_threads", "number_posts"]
    list_filter = ["group__site"]


@admin.register(ForumThread)
class ForumThreadAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "user_string", "number_posts", "date_started", "sticky"]
    list_filter = ["site", "sticky", "blocked"]


@admin.register(ForumPost)
class ForumPostAdmin(admin.ModelAdmin):
    list_display = ["thread", "user_string", "date_posted", "revision_number"]
    list_filter = ["site"]
