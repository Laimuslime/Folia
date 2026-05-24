from django.db import models
from django.conf import settings


class Site(models.Model):
    unix_name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=256)
    subtitle = models.CharField(max_length=256, blank=True)
    description = models.TextField(blank=True)
    language = models.CharField(max_length=10, default="en")
    date_created = models.DateTimeField(auto_now_add=True)
    custom_domain = models.CharField(max_length=60, blank=True, null=True, unique=True)
    visible = models.BooleanField(default=True)
    private = models.BooleanField(default=False)
    suspended = models.BooleanField(default=False)
    default_page = models.CharField(max_length=80, default="start")

    class Meta:
        db_table = "site"

    def __str__(self):
        return self.name


class SiteSettings(models.Model):
    site = models.OneToOneField(Site, on_delete=models.CASCADE, primary_key=True, related_name="settings_obj")

    allow_membership_by_apply = models.BooleanField(default=True)
    allow_membership_by_password = models.BooleanField(default=False)
    membership_password = models.CharField(max_length=80, blank=True)

    file_storage_size = models.BigIntegerField(default=314572800)  # 300MB
    max_upload_file_size = models.IntegerField(default=10485760)  # 10MB
    max_private_members = models.IntegerField(default=50)
    max_private_viewers = models.IntegerField(default=20)

    ssl_mode = models.CharField(max_length=20, blank=True)
    openid_enabled = models.BooleanField(default=False)

    # Navigation
    top_bar_page_name = models.CharField(max_length=128, default="nav:top")
    side_bar_page_name = models.CharField(max_length=128, default="nav:side")

    # Forum
    forum_enabled = models.BooleanField(default=True)
    per_page_discussion = models.BooleanField(default=False)
    max_nest_level = models.IntegerField(default=10)

    # Appearance
    theme_id = models.IntegerField(null=True, blank=True)
    custom_css = models.TextField(blank=True)

    class Meta:
        db_table = "site_settings"


class Member(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships")
    date_joined = models.DateTimeField(auto_now_add=True)
    allow_newsletter = models.BooleanField(default=True)

    class Meta:
        db_table = "member"
        unique_together = ["site", "user"]

    def __str__(self):
        return f"{self.user.username} @ {self.site.slug}"


class Admin(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="admins")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="admin_sites")
    founder = models.BooleanField(default=False)

    class Meta:
        db_table = "admin"
        unique_together = ["site", "user"]


class Moderator(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="moderators")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="moderator_sites")
    permissions = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = "moderator"
        unique_together = ["site", "user"]


class MemberApplication(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="applications")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="site_applications")
    text = models.TextField(blank=True)
    status = models.CharField(max_length=20, default="pending", choices=[
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
    ])
    reply = models.TextField(blank=True)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "member_application"


class MemberInvitation(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="invitations")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="site_invitations")
    by_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="sent_invitations")
    body = models.TextField(blank=True)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "member_invitation"


class SiteBackup(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="backups")
    status = models.CharField(max_length=50, default="pending")
    date = models.DateTimeField(auto_now_add=True)
    rand = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = "site_backup"


class SiteTag(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="site_tags")
    tag = models.CharField(max_length=64)

    class Meta:
        db_table = "site_tag"
        unique_together = ["site", "tag"]


class DomainRedirect(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="domain_redirects")
    url = models.CharField(max_length=80)

    class Meta:
        db_table = "domain_redirect"


class UserBlock(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="user_blocks")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="site_blocks")
    reason = models.TextField(blank=True)
    date_blocked = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_block"
        unique_together = ["site", "user"]


class PlatformBan(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="platform_ban")
    reason = models.TextField(blank=True)
    banned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="bans_issued")
    date_banned = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "platform_ban"


class License(models.Model):
    name = models.CharField(max_length=100)
    url = models.CharField(max_length=256, blank=True)
    text = models.TextField(blank=True)
    sort = models.IntegerField(default=0)

    class Meta:
        db_table = "license"
        ordering = ["sort"]

    def __str__(self):
        return self.name


class Theme(models.Model):
    name = models.CharField(max_length=100)
    unix_name = models.CharField(max_length=100, unique=True)
    abstract = models.BooleanField(default=False)
    extends_theme = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True)
    style = models.TextField(blank=True)
    custom = models.BooleanField(default=False)
    site = models.ForeignKey(Site, on_delete=models.CASCADE, null=True, blank=True, related_name="custom_themes")

    class Meta:
        db_table = "theme"

    def __str__(self):
        return self.name
