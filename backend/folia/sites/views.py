from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Site, SiteSettings, Member, Admin, Moderator, MemberApplication, MemberInvitation, UserBlock, Theme, License
from .serializers import (
    SiteSerializer, SiteCreateSerializer, MemberSerializer,
    AdminSerializer, MemberApplicationSerializer, SiteSettingsSerializer,
    UserBlockSerializer, ThemeSerializer, LicenseSerializer,
)
from .permissions import IsSiteAdmin


class SiteViewSet(viewsets.ModelViewSet):
    queryset = Site.objects.filter(visible=True)
    serializer_class = SiteSerializer
    lookup_field = "slug"

    @action(detail=False, methods=["get"], url_path="check-slug")
    def check_slug(self, request):
        slug = request.query_params.get("slug", "").strip().lower()
        if not slug:
            return Response({"available": False, "detail": "请输入地址。"})
        import re
        if not re.match(r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?$', slug):
            return Response({"available": False, "detail": "只能包含小写字母、数字和连字符。"})
        if len(slug) < 3:
            return Response({"available": False, "detail": "至少 3 个字符。"})
        reserved = {"www", "admin", "api", "static", "media", "new-site", "auth", "account"}
        if slug in reserved:
            return Response({"available": False, "detail": "该地址为系统保留。"})
        exists = Site.objects.filter(slug=slug).exists()
        return Response({"available": not exists, "detail": "该地址已被使用。" if exists else ""})

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def create(self, request):
        serializer = SiteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        owned_count = Admin.objects.filter(user=request.user, founder=True).count()
        if owned_count >= 5:
            return Response({"detail": "每个用户最多创建 5 个站点。"}, status=status.HTTP_400_BAD_REQUEST)

        if Site.objects.filter(slug=data["slug"]).exists():
            return Response({"detail": "该站点地址已被使用。"}, status=status.HTTP_400_BAD_REQUEST)

        site = Site.objects.create(
            unix_name=data["slug"],
            slug=data["slug"],
            name=data["name"],
            subtitle=data.get("subtitle", ""),
            description=data.get("description", ""),
            language=data.get("language", "en"),
            private=data.get("private", False),
        )

        # 创建设置
        SiteSettings.objects.create(site=site)

        # 创建者设为管理员 + 成员
        Admin.objects.create(site=site, user=request.user, founder=True)
        Member.objects.create(site=site, user=request.user)

        # 创建默认页面
        from folia.wiki.models import Page, PageSource, PageCompiled, Category
        default_cat, _ = Category.objects.get_or_create(site=site, name="_default")
        nav_cat, _ = Category.objects.get_or_create(site=site, name="nav")

        # 首页
        start_page = Page.objects.create(
            site=site, category=default_cat, unix_name="start",
            title="欢迎", owner_user=request.user, last_edit_user=request.user,
        )
        start_source = PageSource.objects.create(
            page=start_page,
            text=f"+ 欢迎来到 {data['name']}\n\n这是你的新 Wiki。点击下方的 **编辑** 开始撰写内容。",
        )
        from folia.wiki.parser import render_wikidot_markup
        PageCompiled.objects.create(page=start_page, text=render_wikidot_markup(start_source.text, site))

        # 导航侧栏
        nav_page = Page.objects.create(
            site=site, category=nav_cat, unix_name="side",
            title="侧边导航", owner_user=request.user, last_edit_user=request.user,
        )
        nav_source = PageSource.objects.create(
            page=nav_page,
            text="* [/ 首页]\n* [/system:list-all-pages 所有页面]\n* [/system:recent-changes 最近更改]\n* [/forum:start 论坛]",
        )
        PageCompiled.objects.create(page=nav_page, text=render_wikidot_markup(nav_source.text, site))

        return Response(SiteSerializer(site).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def members(self, request, slug=None):
        site = self.get_object()
        members = site.members.select_related("user").order_by("-date_joined")
        return Response(MemberSerializer(members, many=True).data)

    @action(detail=True, methods=["get"])
    def admins(self, request, slug=None):
        site = self.get_object()
        admins = site.admins.select_related("user")
        return Response(AdminSerializer(admins, many=True).data)

    @action(detail=True, methods=["get", "put"], url_path="settings")
    def site_settings(self, request, slug=None):
        site = self.get_object()
        settings_obj, _ = SiteSettings.objects.get_or_create(site=site)

        if request.method == "GET":
            return Response(SiteSettingsSerializer(settings_obj).data)

        if not IsSiteAdmin().has_permission(request, self):
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = SiteSettingsSerializer(settings_obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def join(self, request, slug=None):
        site = self.get_object()
        user = request.user

        if Member.objects.filter(site=site, user=user).exists():
            return Response({"detail": "你已经是成员了。"}, status=status.HTTP_400_BAD_REQUEST)

        if site.private:
            settings_obj = getattr(site, "settings_obj", None)
            if settings_obj and settings_obj.allow_membership_by_apply:
                MemberApplication.objects.get_or_create(
                    site=site, user=user,
                    defaults={"text": request.data.get("message", "")},
                )
                return Response({"detail": "申请已提交。"}, status=status.HTTP_202_ACCEPTED)
            return Response({"detail": "该站点不接受新成员。"}, status=status.HTTP_403_FORBIDDEN)

        Member.objects.create(site=site, user=user)
        return Response({"detail": "已加入。"}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def leave(self, request, slug=None):
        site = self.get_object()
        Member.objects.filter(site=site, user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get", "post"], url_path="applications")
    def applications(self, request, slug=None):
        site = self.get_object()

        if request.method == "GET":
            apps = site.applications.filter(status="pending").select_related("user")
            return Response(MemberApplicationSerializer(apps, many=True).data)

        # 通过或拒绝
        app_id = request.data.get("application_id")
        decision = request.data.get("decision")
        application = get_object_or_404(MemberApplication, id=app_id, site=site)

        if decision == "accept":
            application.status = "accepted"
            application.save()
            Member.objects.get_or_create(site=site, user=application.user)
        elif decision == "decline":
            application.status = "declined"
            application.reply = request.data.get("reply", "")
            application.save()

        return Response({"detail": f"申请已{decision}。"})

    @action(detail=True, methods=["post"], url_path="members/(?P<user_id>[^/.]+)/remove")
    def remove_member(self, request, slug=None, user_id=None):
        site = self.get_object()
        if not IsSiteAdmin().has_permission(request, self):
            return Response(status=status.HTTP_403_FORBIDDEN)
        Member.objects.filter(site=site, user_id=user_id).delete()
        Moderator.objects.filter(site=site, user_id=user_id).delete()
        Admin.objects.filter(site=site, user_id=user_id, founder=False).delete()
        return Response({"detail": "成员已移除。"})

    @action(detail=True, methods=["post"], url_path="members/(?P<user_id>[^/.]+)/promote")
    def promote_member(self, request, slug=None, user_id=None):
        site = self.get_object()
        if not IsSiteAdmin().has_permission(request, self):
            return Response(status=status.HTTP_403_FORBIDDEN)
        role = request.data.get("role", "moderator")
        if role == "admin":
            Admin.objects.get_or_create(site=site, user_id=user_id)
        else:
            Moderator.objects.get_or_create(site=site, user_id=user_id)
        return Response({"detail": f"已升级为{role}。"})

    @action(detail=True, methods=["post"], url_path="members/(?P<user_id>[^/.]+)/demote")
    def demote_member(self, request, slug=None, user_id=None):
        site = self.get_object()
        if not IsSiteAdmin().has_permission(request, self):
            return Response(status=status.HTTP_403_FORBIDDEN)
        Admin.objects.filter(site=site, user_id=user_id, founder=False).delete()
        Moderator.objects.filter(site=site, user_id=user_id).delete()
        return Response({"detail": "已降级为普通成员。"})

    @action(detail=True, methods=["get", "post"])
    def invitations(self, request, slug=None):
        site = self.get_object()
        if not IsSiteAdmin().has_permission(request, self):
            return Response(status=status.HTTP_403_FORBIDDEN)

        if request.method == "GET":
            invites = site.invitations.select_related("user", "by_user").order_by("-date")
            data = [{"id": i.id, "username": i.user.username, "by": i.by_user.username if i.by_user else "", "date": i.date} for i in invites]
            return Response(data)

        from folia.users.models import User
        username = request.data.get("username", "")
        message = request.data.get("message", "")
        try:
            target_user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({"detail": "用户不存在。"}, status=status.HTTP_404_NOT_FOUND)
        MemberInvitation.objects.create(site=site, user=target_user, by_user=request.user, body=message)
        return Response({"detail": "邀请已发送。"}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post", "delete"])
    def blocks(self, request, slug=None):
        site = self.get_object()
        if not IsSiteAdmin().has_permission(request, self):
            return Response(status=status.HTTP_403_FORBIDDEN)

        if request.method == "GET":
            blocks = site.user_blocks.select_related("user").order_by("-date_blocked")
            return Response(UserBlockSerializer(blocks, many=True).data)

        if request.method == "POST":
            from folia.users.models import User
            user_id = request.data.get("user_id")
            reason = request.data.get("reason", "")
            UserBlock.objects.get_or_create(site=site, user_id=user_id, defaults={"reason": reason})
            return Response({"detail": "用户已封禁。"}, status=status.HTTP_201_CREATED)

        block_id = request.data.get("block_id")
        UserBlock.objects.filter(id=block_id, site=site).delete()
        return Response({"detail": "已解除封禁。"})

    @action(detail=True, methods=["get"])
    def themes(self, request, slug=None):
        themes = Theme.objects.filter(custom=False)
        return Response(ThemeSerializer(themes, many=True).data)

    @action(detail=True, methods=["get"])
    def licenses(self, request, slug=None):
        return Response(LicenseSerializer(License.objects.all(), many=True).data)

    @action(detail=True, methods=["get", "put"], url_path="category-permissions")
    def category_permissions(self, request, slug=None):
        site = self.get_object()
        if not IsSiteAdmin().has_permission(request, self):
            return Response(status=status.HTTP_403_FORBIDDEN)

        from folia.wiki.models import Category

        if request.method == "GET":
            categories = Category.objects.filter(site=site)
            data = []
            for cat in categories:
                perms = {}
                if cat.permissions:
                    for pair in cat.permissions.split(";"):
                        if ":" in pair:
                            k, v = pair.split(":", 1)
                            perms[k] = v
                data.append({"id": cat.id, "name": cat.name, "permissions": perms})
            return Response(data)

        cat_id = request.data.get("category_id")
        perms = request.data.get("permissions", {})
        cat = get_object_or_404(Category, id=cat_id, site=site)
        cat.permissions = ";".join(f"{k}:{v}" for k, v in perms.items() if v)
        cat.save(update_fields=["permissions"])
        return Response({"detail": "权限已更新。"})
