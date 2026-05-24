from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import (
    Page, PageSource, PageRevision, PageCompiled, PageTag,
    PageRateVote, PageLink, PageEditLock, File, Category, LogEvent,
    WatchedPage, PageRedirect, Notification,
)
from .serializers import (
    PageListSerializer, PageDetailSerializer, PageCreateSerializer,
    PageEditSerializer, PageRevisionSerializer, PageFileSerializer,
    CategorySerializer, PageRenameSerializer, PageMoveSerializer,
    PageParentSerializer, NotificationSerializer,
)
from .parser import render_wikidot_markup, extract_wiki_links
from .permissions import (
    can_view_page, can_edit_page, can_create_page,
    can_delete_page, can_rate_page, can_attach_file,
    can_rename_page, check_permission, get_user_role,
)
from .search import index_page


class PageViewSet(viewsets.ViewSet):
    def _get_site(self, request):
        site = getattr(request, "current_site", None)
        if not site:
            from folia.sites.models import Site
            site_slug = request.query_params.get("site") or request.data.get("site")
            if site_slug:
                site = get_object_or_404(Site, slug=site_slug)
        return site

    def list(self, request):
        site = self._get_site(request)
        if not site:
            return Response({"detail": "需要站点上下文。"}, status=status.HTTP_400_BAD_REQUEST)

        pages = Page.objects.filter(site=site).select_related("category", "owner_user").prefetch_related("tags")

        tag = request.query_params.get("tag")
        if tag:
            pages = pages.filter(tags__tag=tag)

        category = request.query_params.get("category")
        if category:
            pages = pages.filter(category__name=category)

        order = request.query_params.get("order", "-date_last_edited")
        valid_orders = {"title", "-title", "date_last_edited", "-date_last_edited", "date_created", "-date_created", "unix_name", "-unix_name", "rate", "-rate"}
        if order not in valid_orders:
            order = "-date_last_edited"
        pages = pages.order_by(order)

        serializer = PageListSerializer(pages[:200], many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        site = self._get_site(request)
        if not site:
            return Response({"detail": "需要站点上下文。"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            page = Page.objects.get(site=site, unix_name=pk)
        except Page.DoesNotExist:
            redirect = PageRedirect.objects.filter(site=site, from_unix_name=pk).first()
            if redirect:
                return Response({"redirect": redirect.to_unix_name}, status=status.HTTP_301_MOVED_PERMANENTLY)
            return Response({"detail": "未找到。"}, status=status.HTTP_404_NOT_FOUND)

        if not can_view_page(request.user, site, page):
            return Response({"detail": "你没有权限查看此页面。"}, status=status.HTTP_403_FORBIDDEN)
        serializer = PageDetailSerializer(page)
        return Response(serializer.data)

    @transaction.atomic
    def create(self, request):
        site = self._get_site(request)
        if not site:
            return Response({"detail": "需要站点上下文。"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = PageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # 获取或创建分类
        cat_name = data.get("category", "_default")
        category, _ = Category.objects.get_or_create(site=site, name=cat_name)

        if not can_create_page(request.user, site, category):
            return Response({"detail": "你没有权限在此分类创建页面。"}, status=status.HTTP_403_FORBIDDEN)

        # 创建页面源码
        source_obj = PageSource.objects.create(text=data["source"])

        # 编译
        compiled_html = render_wikidot_markup(data["source"], site)

        # 创建页面
        page = Page.objects.create(
            site=site,
            category=category,
            title=data["title"],
            unix_name=data["slug"],
            owner_user=request.user,
            last_edit_user=request.user,
            revision_number=0,
        )

        # 创建编译结果
        PageCompiled.objects.create(page=page, text=compiled_html)

        # 创建修订记录
        PageRevision.objects.create(
            page=page,
            source=source_obj,
            revision_number=0,
            user=request.user,
            user_string=request.user.username,
            flag_new=True,
            comments=data.get("comment", ""),
            site=site,
        )

        # 标签
        for tag_name in data.get("tags", []):
            PageTag.objects.create(site=site, page=page, tag=tag_name.strip().lower())

        # 日志
        LogEvent.objects.create(
            site=site, user=request.user, page=page,
            type="new_page", text=f"新建页面：{page.unix_name}",
        )

        index_page(page)
        return Response(PageDetailSerializer(page).data, status=status.HTTP_201_CREATED)

    @transaction.atomic
    def update(self, request, pk=None):
        site = self._get_site(request)
        if not site:
            return Response({"detail": "需要站点上下文。"}, status=status.HTTP_400_BAD_REQUEST)

        page = get_object_or_404(Page, site=site, unix_name=pk)

        if not can_edit_page(request.user, site, page):
            return Response({"detail": "你没有权限编辑此页面。"}, status=status.HTTP_403_FORBIDDEN)

        serializer = PageEditSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        current_source = page.current_source
        new_source = data.get("source", current_source)
        new_title = data.get("title", page.title)

        # 创建新源码
        source_obj = PageSource.objects.create(page=page, text=new_source)

        # 编译
        compiled_html = render_wikidot_markup(new_source, site)
        PageCompiled.objects.update_or_create(page=page, defaults={"text": compiled_html})

        # 判断修改标记
        flag_text = new_source != current_source
        flag_title = new_title != page.title

        # 创建修订记录
        page.revision_number += 1
        PageRevision.objects.create(
            page=page,
            source=source_obj,
            revision_number=page.revision_number,
            user=request.user,
            user_string=request.user.username,
            flag_text=flag_text,
            flag_title=flag_title,
            comments=data.get("comment", ""),
            site=site,
        )

        page.title = new_title
        page.last_edit_user = request.user
        page.date_last_edited = timezone.now()
        page.save()

        # 更新标签
        if "tags" in data:
            page.tags.all().delete()
            for tag_name in data["tags"]:
                PageTag.objects.create(site=site, page=page, tag=tag_name.strip().lower())

        # 日志
        LogEvent.objects.create(
            site=site, user=request.user, page=page,
            type="edit_page", text=f"编辑：{page.unix_name}",
        )

        # 更新页面链接
        self._update_page_links(page, new_source, site)

        # 通知监视者
        self._notify_watchers(page, request.user, "page_edit", f"编辑了 {page.title}")

        index_page(page)
        return Response(PageDetailSerializer(page).data)

    def destroy(self, request, pk=None):
        site = self._get_site(request)
        if not site:
            return Response({"detail": "需要站点上下文。"}, status=status.HTTP_400_BAD_REQUEST)

        page = get_object_or_404(Page, site=site, unix_name=pk)

        if not can_delete_page(request.user, site, page):
            return Response({"detail": "你没有权限删除此页面。"}, status=status.HTTP_403_FORBIDDEN)

        LogEvent.objects.create(
            site=site, user=request.user,
            type="delete_page", text=f"删除：{page.unix_name}",
        )

        page.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"])
    def revisions(self, request, pk=None):
        site = self._get_site(request)
        page = get_object_or_404(Page, site=site, unix_name=pk)
        revisions = page.revisions.select_related("user")
        serializer = PageRevisionSerializer(revisions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="revisions/(?P<rev_num>[0-9]+)")
    def revision_detail(self, request, pk=None, rev_num=None):
        site = self._get_site(request)
        page = get_object_or_404(Page, site=site, unix_name=pk)
        revision = get_object_or_404(PageRevision, page=page, revision_number=rev_num)
        data = PageRevisionSerializer(revision).data
        data["source"] = revision.source.text if revision.source else ""
        return Response(data)

    @action(detail=True, methods=["post", "delete"])
    def vote(self, request, pk=None):
        site = self._get_site(request)
        page = get_object_or_404(Page, site=site, unix_name=pk)

        if not can_rate_page(request.user, site, page):
            return Response({"detail": "你没有权限评分此页面。"}, status=status.HTTP_403_FORBIDDEN)

        if request.method == "DELETE":
            PageRateVote.objects.filter(page=page, user=request.user).delete()
        else:
            value = request.data.get("value", 1)
            if value == 0:
                PageRateVote.objects.filter(page=page, user=request.user).delete()
            else:
                PageRateVote.objects.update_or_create(
                    page=page, user=request.user,
                    defaults={"rate": value},
                )

        agg = page.votes.aggregate(total=Sum("rate"))
        page.rate = agg["total"] or 0
        page.save(update_fields=["rate"])

        return Response({"rating": page.rate})

    @action(detail=True, methods=["get", "post"])
    def files(self, request, pk=None):
        site = self._get_site(request)
        page = get_object_or_404(Page, site=site, unix_name=pk)

        if request.method == "GET":
            files = page.files.all()
            return Response(PageFileSerializer(files, many=True).data)

        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"detail": "未上传文件。"}, status=status.HTTP_400_BAD_REQUEST)

        if not can_attach_file(request.user, site, page):
            return Response({"detail": "你没有权限上传附件。"}, status=status.HTTP_403_FORBIDDEN)

        import os
        safe_name = os.path.basename(uploaded.name).strip()
        if not safe_name:
            return Response({"detail": "文件名无效。"}, status=status.HTTP_400_BAD_REQUEST)

        from django.core.files.storage import default_storage
        path = f"sites/{site.slug}/{page.unix_name}/{safe_name}"
        default_storage.save(path, uploaded)

        file_obj = File.objects.create(
            page=page, site=site,
            filename=safe_name,
            mimetype=uploaded.content_type or "application/octet-stream",
            size=uploaded.size,
            user=request.user,
            user_string=request.user.username,
        )
        return Response(PageFileSerializer(file_obj).data, status=status.HTTP_201_CREATED)

    # --- Rename ---
    @action(detail=True, methods=["post"])
    @transaction.atomic
    def rename(self, request, pk=None):
        site = self._get_site(request)
        page = get_object_or_404(Page, site=site, unix_name=pk)

        if not can_rename_page(request.user, site, page):
            return Response({"detail": "没有权限重命名。"}, status=status.HTTP_403_FORBIDDEN)

        serializer = PageRenameSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_slug = serializer.validated_data["new_slug"].strip().lower()

        if Page.objects.filter(site=site, unix_name=new_slug).exists():
            return Response({"detail": "该地址已被其他页面使用。"}, status=status.HTTP_409_CONFLICT)

        old_slug = page.unix_name
        page.unix_name = new_slug
        page.revision_number += 1
        page.last_edit_user = request.user
        page.save()

        PageSource.objects.create(page=page, text=page.current_source)
        PageRevision.objects.create(
            page=page, revision_number=page.revision_number,
            user=request.user, user_string=request.user.username,
            flag_rename=True, comments=f"从 {old_slug} 重命名",
            site=site,
        )

        PageRedirect.objects.update_or_create(
            site=site, from_unix_name=old_slug,
            defaults={"to_unix_name": new_slug},
        )

        PageLink.objects.filter(site=site, to_page_name=old_slug).update(to_page_name=new_slug)

        LogEvent.objects.create(
            site=site, user=request.user, page=page,
            type="rename_page", text=f"重命名：{old_slug} -> {new_slug}",
        )

        index_page(page)
        return Response(PageDetailSerializer(page).data)

    # --- Move ---
    @action(detail=True, methods=["post"])
    @transaction.atomic
    def move(self, request, pk=None):
        site = self._get_site(request)
        page = get_object_or_404(Page, site=site, unix_name=pk)

        if not check_permission(request.user, site, page.category, "move"):
            return Response({"detail": "没有权限移动。"}, status=status.HTTP_403_FORBIDDEN)

        serializer = PageMoveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_cat_name = serializer.validated_data["new_category"]

        new_category, _ = Category.objects.get_or_create(site=site, name=new_cat_name)
        old_cat = page.category.name if page.category else "_default"
        page.category = new_category
        page.revision_number += 1
        page.last_edit_user = request.user
        page.save()

        PageRevision.objects.create(
            page=page, revision_number=page.revision_number,
            user=request.user, user_string=request.user.username,
            flag_meta=True, comments=f"从 {old_cat} 移动到 {new_cat_name}",
            site=site,
        )

        LogEvent.objects.create(
            site=site, user=request.user, page=page,
            type="move_page", text=f"移动：{old_cat} -> {new_cat_name}",
        )

        return Response(PageDetailSerializer(page).data)

    # --- Block/Unblock (admin lock) ---
    @action(detail=True, methods=["post", "delete"])
    def block(self, request, pk=None):
        site = self._get_site(request)
        page = get_object_or_404(Page, site=site, unix_name=pk)

        role = get_user_role(request.user, site)
        if role not in ("moderator", "admin"):
            return Response({"detail": "只有版主/管理员可以锁定页面。"}, status=status.HTTP_403_FORBIDDEN)

        if request.method == "POST":
            page.blocked = True
            page.save(update_fields=["blocked"])
            LogEvent.objects.create(site=site, user=request.user, page=page, type="lock_page")
        else:
            page.blocked = False
            page.save(update_fields=["blocked"])
            LogEvent.objects.create(site=site, user=request.user, page=page, type="unlock_page")

        return Response({"blocked": page.blocked})

    # --- Watch/Unwatch ---
    @action(detail=True, methods=["get", "post", "delete"])
    def watch(self, request, pk=None):
        site = self._get_site(request)
        page = get_object_or_404(Page, site=site, unix_name=pk)

        if request.method == "GET":
            watching = WatchedPage.objects.filter(user=request.user, page=page).exists()
            return Response({"watching": watching})

        if request.method == "POST":
            WatchedPage.objects.get_or_create(user=request.user, page=page)
            return Response({"watching": True})

        WatchedPage.objects.filter(user=request.user, page=page).delete()
        return Response({"watching": False})

    # --- Backlinks ---
    @action(detail=True, methods=["get"])
    def backlinks(self, request, pk=None):
        site = self._get_site(request)
        page = get_object_or_404(Page, site=site, unix_name=pk)

        links = PageLink.objects.filter(site=site, to_page_name=page.unix_name).select_related("from_page")
        result = [
            {"slug": link.from_page.unix_name, "title": link.from_page.title}
            for link in links if link.from_page
        ]
        return Response(result)

    # --- Parent ---
    @action(detail=True, methods=["post", "delete"])
    @transaction.atomic
    def parent(self, request, pk=None):
        site = self._get_site(request)
        page = get_object_or_404(Page, site=site, unix_name=pk)

        if not can_edit_page(request.user, site, page):
            return Response({"detail": "没有权限。"}, status=status.HTTP_403_FORBIDDEN)

        if request.method == "DELETE":
            page.parent_page = None
            page.save(update_fields=["parent_page"])
            return Response({"parent_slug": None})

        serializer = PageParentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        parent_slug = serializer.validated_data["parent_slug"]

        if not parent_slug:
            page.parent_page = None
        else:
            parent = get_object_or_404(Page, site=site, unix_name=parent_slug)
            if parent.pk == page.pk:
                return Response({"detail": "页面不能设为自身的父页面。"}, status=status.HTTP_400_BAD_REQUEST)
            page.parent_page = parent

        page.save(update_fields=["parent_page"])
        return Response({"parent_slug": page.parent_page.unix_name if page.parent_page else None})

    # --- Helper methods ---
    def _update_page_links(self, page, source, site):
        PageLink.objects.filter(from_page=page).delete()
        targets = extract_wiki_links(source)
        for target in targets:
            to_page = Page.objects.filter(site=site, unix_name=target).first()
            PageLink.objects.create(
                from_page=page, to_page=to_page,
                to_page_name=target, site=site,
            )

    def _notify_watchers(self, page, actor, notif_type, text):
        watchers = WatchedPage.objects.filter(page=page).exclude(user=actor).select_related("user")
        notifications = [
            Notification(user=w.user, type=notif_type, page=page, actor=actor, text=text)
            for w in watchers
        ]
        Notification.objects.bulk_create(notifications)

    @action(detail=True, methods=["post"])
    def lock(self, request, pk=None):
        site = self._get_site(request)
        page = get_object_or_404(Page, site=site, unix_name=pk)

        PageEditLock.objects.filter(page=page, date_last_accessed__lt=timezone.now() - timezone.timedelta(minutes=15)).delete()

        existing = PageEditLock.objects.filter(page=page).exclude(user=request.user).first()
        if existing:
            return Response({"detail": f"页面正在被 {existing.user_string} 编辑。"}, status=status.HTTP_409_CONFLICT)

        lock, _ = PageEditLock.objects.update_or_create(
            page=page, user=request.user,
            defaults={"site": site, "user_string": request.user.username},
        )
        return Response({"lock_id": lock.pk, "secret": lock.secret})

    @action(detail=True, methods=["delete"])
    def unlock(self, request, pk=None):
        site = self._get_site(request)
        page = get_object_or_404(Page, site=site, unix_name=pk)
        PageEditLock.objects.filter(page=page, user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer

    def get_queryset(self):
        site = getattr(self.request, "current_site", None)
        if site:
            return Category.objects.filter(site=site)
        return Category.objects.none()


class NotificationViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        notifications = Notification.objects.filter(user=request.user)[:50]
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def count(self, request):
        unread = Notification.objects.filter(user=request.user, read=False).count()
        return Response({"unread": unread})

    @action(detail=False, methods=["post"])
    def read(self, request):
        ids = request.data.get("ids")
        if ids:
            Notification.objects.filter(user=request.user, id__in=ids).update(read=True)
        else:
            Notification.objects.filter(user=request.user, read=False).update(read=True)
        return Response({"status": "ok"})
