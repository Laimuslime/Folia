from rest_framework import serializers
from .models import Page, PageRevision, PageTag, PageRateVote, File, Category, Notification


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "permissions_default", "rating", "autonumerate"]


class PageTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = PageTag
        fields = ["tag"]


class PageRevisionSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True, default="")

    class Meta:
        model = PageRevision
        fields = [
            "id", "revision_number", "user", "username", "user_string",
            "flag_text", "flag_title", "flag_file", "flag_rename", "flag_new",
            "comments", "date_last_edited",
        ]


class PageFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = ["id", "filename", "mimetype", "size", "description", "date_added", "user_string"]


class PageListSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    category_name = serializers.CharField(source="category.name", read_only=True, default="_default")
    owner_username = serializers.CharField(source="owner_user.username", read_only=True, default="")

    class Meta:
        model = Page
        fields = [
            "id", "unix_name", "title", "category_name", "tags",
            "rate", "blocked", "revision_number",
            "owner_username", "date_created", "date_last_edited",
        ]

    def get_tags(self, obj):
        return list(obj.tags.values_list("tag", flat=True))


class PageDetailSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    category_name = serializers.CharField(source="category.name", read_only=True, default="_default")
    current_source = serializers.SerializerMethodField()
    compiled_html = serializers.SerializerMethodField()
    owner_username = serializers.CharField(source="owner_user.username", read_only=True, default="")
    last_edit_username = serializers.CharField(source="last_edit_user.username", read_only=True, default="")
    breadcrumbs = serializers.SerializerMethodField()
    parent_slug = serializers.SerializerMethodField()

    class Meta:
        model = Page
        fields = [
            "id", "unix_name", "title", "category_name", "tags",
            "rate", "blocked", "revision_number",
            "current_source", "compiled_html",
            "owner_username", "last_edit_username",
            "date_created", "date_last_edited",
            "breadcrumbs", "parent_slug",
        ]

    def get_tags(self, obj):
        return list(obj.tags.values_list("tag", flat=True))

    def get_current_source(self, obj):
        return obj.current_source

    def get_compiled_html(self, obj):
        return obj.compiled_html

    def get_breadcrumbs(self, obj):
        crumbs = []
        current = obj.parent_page
        seen = set()
        while current and current.pk not in seen and len(crumbs) < 10:
            seen.add(current.pk)
            crumbs.insert(0, {"slug": current.unix_name, "title": current.title})
            current = current.parent_page
        return crumbs

    def get_parent_slug(self, obj):
        return obj.parent_page.unix_name if obj.parent_page else None


class PageCreateSerializer(serializers.Serializer):
    slug = serializers.CharField(max_length=256)
    title = serializers.CharField(max_length=256)
    source = serializers.CharField(allow_blank=True)
    category = serializers.CharField(max_length=80, required=False, default="_default")
    tags = serializers.ListField(child=serializers.CharField(max_length=64), required=False, default=list)
    comment = serializers.CharField(max_length=500, required=False, default="", allow_blank=True)


class PageEditSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=256, required=False)
    source = serializers.CharField(required=False, allow_blank=True)
    tags = serializers.ListField(child=serializers.CharField(max_length=64), required=False)
    comment = serializers.CharField(max_length=500, required=False, default="", allow_blank=True)


class PageRenameSerializer(serializers.Serializer):
    new_slug = serializers.CharField(max_length=256)


class PageMoveSerializer(serializers.Serializer):
    new_category = serializers.CharField(max_length=80)


class PageParentSerializer(serializers.Serializer):
    parent_slug = serializers.CharField(max_length=256, allow_blank=True)


class NotificationSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source="actor.username", read_only=True, default="")
    page_slug = serializers.CharField(source="page.unix_name", read_only=True, default="")
    page_title = serializers.CharField(source="page.title", read_only=True, default="")

    class Meta:
        model = Notification
        fields = [
            "id", "type", "actor_username", "page_slug", "page_title",
            "text", "read", "date",
        ]
