from rest_framework import serializers
from .models import ForumGroup, ForumCategory, ForumThread, ForumPost


class ForumPostSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True, default="")

    class Meta:
        model = ForumPost
        fields = [
            "id", "thread", "parent", "user", "username", "user_string",
            "title", "text", "date_posted", "revision_number",
            "date_last_edited", "edited_user_string",
        ]
        read_only_fields = ["id", "user", "username", "date_posted", "revision_number", "date_last_edited"]


class ForumCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ForumCategory
        fields = ["id", "group", "name", "description", "number_posts", "number_threads", "sort_index", "per_page_discussion"]


class ForumGroupSerializer(serializers.ModelSerializer):
    categories = ForumCategorySerializer(many=True, read_only=True)

    class Meta:
        model = ForumGroup
        fields = ["id", "name", "description", "sort_index", "visible", "categories"]


class ForumThreadSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True, default="")

    class Meta:
        model = ForumThread
        fields = [
            "id", "category", "title", "description", "user", "username", "user_string",
            "number_posts", "date_started", "sticky", "blocked", "page",
        ]
        read_only_fields = ["id", "user", "username", "number_posts", "date_started"]


class ForumThreadDetailSerializer(ForumThreadSerializer):
    posts = ForumPostSerializer(many=True, read_only=True)

    class Meta(ForumThreadSerializer.Meta):
        fields = ForumThreadSerializer.Meta.fields + ["posts"]
