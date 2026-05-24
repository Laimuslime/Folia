from rest_framework import serializers
from .models import Site, SiteSettings, Member, Admin, MemberApplication, Theme, License, UserBlock


class SiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSettings
        exclude = ["site"]


class SiteSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Site
        fields = [
            "id", "unix_name", "slug", "name", "subtitle", "description",
            "language", "private", "visible", "default_page", "custom_domain",
            "date_created", "member_count",
        ]
        read_only_fields = ["id", "date_created"]

    def get_member_count(self, obj):
        return obj.members.count()


class SiteCreateSerializer(serializers.Serializer):
    slug = serializers.SlugField(max_length=80)
    name = serializers.CharField(max_length=256)
    subtitle = serializers.CharField(max_length=256, required=False, default="")
    description = serializers.CharField(required=False, default="")
    language = serializers.CharField(max_length=10, required=False, default="en")
    private = serializers.BooleanField(required=False, default=False)


class MemberSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    role = serializers.SerializerMethodField()

    class Meta:
        model = Member
        fields = ["id", "user", "username", "date_joined", "role"]

    def get_role(self, obj):
        if Admin.objects.filter(site=obj.site, user=obj.user).exists():
            return "admin"
        from .models import Moderator
        if Moderator.objects.filter(site=obj.site, user=obj.user).exists():
            return "moderator"
        return "member"


class AdminSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Admin
        fields = ["id", "user", "username", "founder"]


class MemberApplicationSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = MemberApplication
        fields = ["id", "user", "username", "text", "status", "reply", "date"]


class ThemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Theme
        fields = ["id", "name", "unix_name", "abstract", "custom"]


class LicenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = License
        fields = ["id", "name", "url"]


class UserBlockSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = UserBlock
        fields = ["id", "user", "username", "reason", "date_blocked"]
