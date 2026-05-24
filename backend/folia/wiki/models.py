from django.db import models
from django.conf import settings


class Category(models.Model):
    site = models.ForeignKey("sites.Site", on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=80)

    theme_default = models.BooleanField(default=True)
    theme_id = models.IntegerField(null=True, blank=True)
    theme_external_url = models.CharField(max_length=512, blank=True)

    permissions_default = models.BooleanField(default=True)
    permissions = models.CharField(max_length=200, blank=True)

    license_default = models.BooleanField(default=True)
    license_id = models.IntegerField(null=True, blank=True)
    license_other = models.CharField(max_length=350, blank=True)

    nav_default = models.BooleanField(default=True)
    top_bar_page_name = models.CharField(max_length=128, blank=True)
    side_bar_page_name = models.CharField(max_length=128, blank=True)

    template_id = models.IntegerField(null=True, blank=True)
    category_template_id = models.IntegerField(null=True, blank=True)

    per_page_discussion = models.BooleanField(null=True, blank=True)
    per_page_discussion_default = models.BooleanField(default=True)

    rating = models.CharField(max_length=10, blank=True)
    autonumerate = models.BooleanField(default=False)
    page_title_template = models.CharField(max_length=256, blank=True)

    enable_pingback_out = models.BooleanField(default=True)
    enable_pingback_in = models.BooleanField(default=False)

    class Meta:
        db_table = "category"
        unique_together = ["site", "name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return f"{self.site.slug}:{self.name}"


class CategoryTemplate(models.Model):
    source = models.TextField(blank=True)

    class Meta:
        db_table = "category_template"


class Page(models.Model):
    site = models.ForeignKey("sites.Site", on_delete=models.CASCADE, related_name="pages")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="pages")
    parent_page = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="children")
    revision_number = models.IntegerField(default=0)
    title = models.CharField(max_length=256)
    unix_name = models.CharField(max_length=256)
    date_created = models.DateTimeField(auto_now_add=True)
    date_last_edited = models.DateTimeField(auto_now=True)
    last_edit_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="last_edited_pages")
    owner_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="owned_pages")
    thread = models.ForeignKey("forums.ForumThread", on_delete=models.SET_NULL, null=True, blank=True, related_name="discussed_page")
    blocked = models.BooleanField(default=False)
    rate = models.IntegerField(default=0)

    class Meta:
        db_table = "page"
        unique_together = ["site", "unix_name"]

    def __str__(self):
        return f"{self.site.slug}:{self.unix_name}"

    @property
    def full_name(self):
        if self.category and self.category.name != "_default":
            return f"{self.category.name}:{self.unix_name}"
        return self.unix_name

    @property
    def current_source(self):
        src = self.sources.order_by("-source_id").first()
        return src.text if src else ""

    @property
    def compiled_html(self):
        compiled = PageCompiled.objects.filter(page=self).first()
        return compiled.text if compiled else ""


class PageSource(models.Model):
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="sources", null=True, blank=True)
    text = models.TextField(blank=True)

    class Meta:
        db_table = "page_source"


class PageMetadata(models.Model):
    parent_page = models.ForeignKey(Page, on_delete=models.SET_NULL, null=True, blank=True, related_name="metadata_refs")
    title = models.CharField(max_length=256, blank=True)
    unix_name = models.CharField(max_length=80, blank=True)
    owner_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = "page_metadata"


class PageRevision(models.Model):
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="revisions")
    source = models.ForeignKey(PageSource, on_delete=models.SET_NULL, null=True, blank=True)
    metadata = models.ForeignKey(PageMetadata, on_delete=models.SET_NULL, null=True, blank=True)
    flags = models.CharField(max_length=100, blank=True)
    flag_text = models.BooleanField(default=False)
    flag_title = models.BooleanField(default=False)
    flag_file = models.BooleanField(default=False)
    flag_rename = models.BooleanField(default=False)
    flag_meta = models.BooleanField(default=False)
    flag_new = models.BooleanField(default=False)
    flag_new_site = models.BooleanField(default=False)
    since_full_source = models.IntegerField(default=0)
    diff_source = models.BooleanField(default=False)
    revision_number = models.IntegerField(default=0)
    date_last_edited = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    user_string = models.CharField(max_length=80, blank=True)
    comments = models.TextField(blank=True)
    site = models.ForeignKey("sites.Site", on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        db_table = "page_revision"
        ordering = ["-revision_number"]

    def __str__(self):
        return f"{self.page} rev.{self.revision_number}"


class PageCompiled(models.Model):
    page = models.OneToOneField(Page, on_delete=models.CASCADE, primary_key=True, related_name="compiled")
    text = models.TextField(blank=True)
    date_compiled = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "page_compiled"


class PageTag(models.Model):
    site = models.ForeignKey("sites.Site", on_delete=models.CASCADE, related_name="page_tags")
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="tags")
    tag = models.CharField(max_length=64)

    class Meta:
        db_table = "page_tag"
        unique_together = ["page", "tag"]

    def __str__(self):
        return self.tag


class PageRateVote(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="votes")
    rate = models.IntegerField(default=1)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "page_rate_vote"
        unique_together = ["user", "page"]


class PageLink(models.Model):
    from_page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="outgoing_links")
    to_page = models.ForeignKey(Page, on_delete=models.SET_NULL, null=True, blank=True, related_name="incoming_links")
    to_page_name = models.CharField(max_length=256)
    site = models.ForeignKey("sites.Site", on_delete=models.CASCADE)

    class Meta:
        db_table = "page_link"


class PageExternalLink(models.Model):
    site = models.ForeignKey("sites.Site", on_delete=models.CASCADE)
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="external_links")
    to_url = models.CharField(max_length=512)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "page_external_link"


class PageInclusion(models.Model):
    including_page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="inclusions_out")
    included_page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="inclusions_in")
    site = models.ForeignKey("sites.Site", on_delete=models.CASCADE)

    class Meta:
        db_table = "page_inclusion"
        unique_together = ["including_page", "included_page"]


class PageEditLock(models.Model):
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="edit_locks", null=True, blank=True)
    mode = models.CharField(max_length=10, default="page")
    section_id = models.IntegerField(null=True, blank=True)
    range_start = models.IntegerField(null=True, blank=True)
    range_end = models.IntegerField(null=True, blank=True)
    page_unix_name = models.CharField(max_length=100, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    user_string = models.CharField(max_length=80, blank=True)
    session_id = models.CharField(max_length=60, blank=True)
    date_started = models.DateTimeField(auto_now_add=True)
    date_last_accessed = models.DateTimeField(auto_now=True)
    secret = models.CharField(max_length=100, blank=True)
    site = models.ForeignKey("sites.Site", on_delete=models.CASCADE)

    class Meta:
        db_table = "page_edit_lock"


class File(models.Model):
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="files")
    site = models.ForeignKey("sites.Site", on_delete=models.CASCADE, related_name="files")
    filename = models.CharField(max_length=100)
    mimetype = models.CharField(max_length=100, blank=True)
    description = models.CharField(max_length=200, blank=True)
    description_short = models.CharField(max_length=200, blank=True)
    comment = models.CharField(max_length=400, blank=True)
    size = models.IntegerField(default=0)
    date_added = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    user_string = models.CharField(max_length=80, blank=True)
    has_resized = models.BooleanField(default=False)

    class Meta:
        db_table = "file"
        unique_together = ["page", "filename"]

    def __str__(self):
        return self.filename


class LogEvent(models.Model):
    date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    user_string = models.CharField(max_length=80, blank=True)
    site = models.ForeignKey("sites.Site", on_delete=models.CASCADE, related_name="log_events")
    page = models.ForeignKey(Page, on_delete=models.SET_NULL, null=True, blank=True)
    revision = models.ForeignKey(PageRevision, on_delete=models.SET_NULL, null=True, blank=True)
    thread = models.ForeignKey("forums.ForumThread", on_delete=models.SET_NULL, null=True, blank=True)
    type = models.CharField(max_length=256, blank=True)
    text = models.TextField(blank=True)
    extra = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "log_event"
        ordering = ["-date"]


class WatchedPage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="watchers")

    class Meta:
        db_table = "watched_page"
        unique_together = ["user", "page"]


class PageRedirect(models.Model):
    site = models.ForeignKey("sites.Site", on_delete=models.CASCADE, related_name="page_redirects")
    from_unix_name = models.CharField(max_length=256)
    to_unix_name = models.CharField(max_length=256)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "page_redirect"
        unique_together = ["site", "from_unix_name"]

    def __str__(self):
        return f"{self.from_unix_name} -> {self.to_unix_name}"


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField(max_length=50)
    page = models.ForeignKey(Page, on_delete=models.CASCADE, null=True, blank=True)
    thread = models.ForeignKey("forums.ForumThread", on_delete=models.CASCADE, null=True, blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    text = models.CharField(max_length=500, blank=True)
    read = models.BooleanField(default=False)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notification"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.type} -> {self.user}"
