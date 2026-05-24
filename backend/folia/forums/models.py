from django.db import models
from django.conf import settings


class ForumSettings(models.Model):
    site = models.OneToOneField("sites.Site", on_delete=models.CASCADE, primary_key=True, related_name="forum_settings")
    permissions = models.CharField(max_length=200, blank=True)
    per_page_discussion = models.BooleanField(default=False)
    max_nest_level = models.IntegerField(default=10)

    class Meta:
        db_table = "forum_settings"


class ForumGroup(models.Model):
    name = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    sort_index = models.IntegerField(default=0)
    site = models.ForeignKey("sites.Site", on_delete=models.CASCADE, related_name="forum_groups")
    visible = models.BooleanField(default=True)

    class Meta:
        db_table = "forum_group"
        ordering = ["sort_index"]

    def __str__(self):
        return self.name


class ForumCategory(models.Model):
    group = models.ForeignKey(ForumGroup, on_delete=models.CASCADE, related_name="categories")
    site = models.ForeignKey("sites.Site", on_delete=models.CASCADE, related_name="forum_categories")
    name = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    number_posts = models.IntegerField(default=0)
    number_threads = models.IntegerField(default=0)
    last_post = models.ForeignKey("ForumPost", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    permissions_default = models.BooleanField(default=True)
    permissions = models.CharField(max_length=200, blank=True)
    max_nest_level = models.IntegerField(null=True, blank=True)
    sort_index = models.IntegerField(default=0)
    per_page_discussion = models.BooleanField(default=False)

    class Meta:
        db_table = "forum_category"
        ordering = ["sort_index"]

    def __str__(self):
        return self.name


class ForumThread(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    user_string = models.CharField(max_length=80, blank=True)
    category = models.ForeignKey(ForumCategory, on_delete=models.CASCADE, related_name="threads")
    title = models.CharField(max_length=256)
    description = models.CharField(max_length=1000, blank=True)
    number_posts = models.IntegerField(default=1)
    date_started = models.DateTimeField(auto_now_add=True)
    site = models.ForeignKey("sites.Site", on_delete=models.CASCADE, related_name="forum_threads")
    last_post = models.ForeignKey("ForumPost", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    page = models.ForeignKey("wiki.Page", on_delete=models.SET_NULL, null=True, blank=True, related_name="discussion_threads")
    sticky = models.BooleanField(default=False)
    blocked = models.BooleanField(default=False)

    class Meta:
        db_table = "forum_thread"
        ordering = ["-sticky", "-date_started"]

    def __str__(self):
        return self.title


class ForumPost(models.Model):
    thread = models.ForeignKey(ForumThread, on_delete=models.CASCADE, related_name="posts")
    parent = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="replies")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    user_string = models.CharField(max_length=80, blank=True)
    title = models.CharField(max_length=256, blank=True)
    text = models.TextField()
    date_posted = models.DateTimeField(auto_now_add=True)
    site = models.ForeignKey("sites.Site", on_delete=models.CASCADE, related_name="forum_posts")
    revision_number = models.IntegerField(default=0)
    date_last_edited = models.DateTimeField(null=True, blank=True)
    edited_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="edited_forum_posts")
    edited_user_string = models.CharField(max_length=80, blank=True)

    class Meta:
        db_table = "forum_post"
        ordering = ["date_posted"]

    def __str__(self):
        return f"Post by {self.user_string or self.user} in {self.thread}"


class ForumPostRevision(models.Model):
    post = models.ForeignKey(ForumPost, on_delete=models.CASCADE, related_name="revisions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    user_string = models.CharField(max_length=80, blank=True)
    text = models.TextField()
    title = models.CharField(max_length=256, blank=True)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "forum_post_revision"
        ordering = ["-date"]


class WatchedForumThread(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    thread = models.ForeignKey(ForumThread, on_delete=models.CASCADE, related_name="watchers")

    class Meta:
        db_table = "watched_forum_thread"
        unique_together = ["user", "thread"]
