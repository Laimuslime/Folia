"""
AJAX Module Connector — equivalent to Wikidot's ajax-module-connector.php.

Handles dynamic module loading from the frontend. Wikidot's frontend uses this
endpoint to load modules like Rate, ListPages (pagination), Edit, History, etc.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models import Page, PageRateVote, PageRevision, PageSource, PageCompiled, PageTag, LogEvent, Category
from .parser import render_wikidot_markup
from .modules import ModuleRegistry
from folia.sites.models import Site


class AjaxModuleConnectorView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        module_name = request.data.get("moduleName", "")
        call_type = request.data.get("callType", "module")
        site = getattr(request, "current_site", None)

        if not site:
            site_slug = request.data.get("site")
            if site_slug:
                site = Site.objects.filter(slug=site_slug).first()

        if not site:
            return Response({"status": "error", "message": "No site context"}, status=400)

        handler = self._get_handler(module_name)
        if handler:
            return handler(request, site)

        # Generic module rendering
        params = {k: v for k, v in request.data.items() if k not in ("moduleName", "callType", "site")}
        context = {"site": site, "page": None, "user": request.user if request.user.is_authenticated else None}

        page_slug = request.data.get("pageId") or request.data.get("page_unix_name")
        if page_slug:
            context["page"] = Page.objects.filter(site=site, unix_name=page_slug).first()

        html = ModuleRegistry.render(module_name, params, context)
        return Response({"status": "ok", "body": html})

    def _get_handler(self, module_name):
        handlers = {
            "Empty": self._handle_empty,
            "edit/PageEditModule": self._handle_page_edit,
            "history/PageRevisionListModule": self._handle_revisions,
            "history/PageSourceModule": self._handle_source,
            "history/PageDiffModule": self._handle_diff,
            "pagerate/WhoRatedPageModule": self._handle_who_rated,
            "pagetags/PageTagsModule": self._handle_tags,
            "viewsource/ViewSourceModule": self._handle_source,
            "list/ListPagesModule": self._handle_listpages,
            "forum/ForumStartModule": self._handle_forum_start,
            "forum/ForumViewCategoryModule": self._handle_forum_category,
            "forum/ForumViewThreadModule": self._handle_forum_thread,
            "forum/ForumNewThreadModule": self._handle_forum_new_thread,
            "forum/ForumNewPostFormModule": self._handle_forum_new_post,
        }
        return handlers.get(module_name)

    def _handle_empty(self, request, site):
        source = request.data.get("source")
        if source and request.data.get("render"):
            html = render_wikidot_markup(source, site)
            return Response({"status": "ok", "body": html})
        return Response({"status": "ok", "body": ""})

    def _handle_page_edit(self, request, site):
        page_slug = request.data.get("page_unix_name", "")
        page = Page.objects.filter(site=site, unix_name=page_slug).first()

        if page:
            source = ""
            ps = PageSource.objects.filter(page=page).order_by("-id").first()
            if ps:
                source = ps.text
            return Response({
                "status": "ok",
                "body": "",
                "page_id": page.pk,
                "title": page.title,
                "source": source,
                "revision_id": page.revision_number,
                "lock_status": "ok",
            })
        return Response({
            "status": "ok",
            "body": "",
            "page_id": None,
            "title": "",
            "source": "",
            "revision_id": 0,
            "lock_status": "ok",
        })

    def _handle_revisions(self, request, site):
        page_slug = request.data.get("page_unix_name", "")
        page = get_object_or_404(Page, site=site, unix_name=page_slug)
        revisions = page.revisions.select_related("user").order_by("-revision_number")

        rows = []
        for rev in revisions[:50]:
            rows.append(
                f'<tr>'
                f'<td>{rev.revision_number}</td>'
                f'<td>{rev.user_string or "system"}</td>'
                f'<td>{rev.date_created.strftime("%d %b %Y %H:%M") if rev.date_created else ""}</td>'
                f'<td>{rev.comments or ""}</td>'
                f'<td>{"S" if rev.flag_text else ""}{"T" if rev.flag_title else ""}{"R" if rev.flag_rename else ""}{"N" if rev.flag_new else ""}</td>'
                f'</tr>'
            )

        html = (
            f'<table class="page-history">'
            f'<tr><th>Rev.</th><th>User</th><th>Date</th><th>Comment</th><th>Flags</th></tr>'
            f'{"".join(rows)}'
            f'</table>'
        )
        return Response({"status": "ok", "body": html})

    def _handle_source(self, request, site):
        page_slug = request.data.get("page_unix_name", "")
        rev_num = request.data.get("revision_number")
        page = get_object_or_404(Page, site=site, unix_name=page_slug)

        if rev_num is not None:
            rev = PageRevision.objects.filter(page=page, revision_number=rev_num).first()
            source = rev.source.text if rev and rev.source else ""
        else:
            ps = PageSource.objects.filter(page=page).order_by("-id").first()
            source = ps.text if ps else ""

        import html as html_mod
        html = f'<div class="page-source"><pre>{html_mod.escape(source)}</pre></div>'
        return Response({"status": "ok", "body": html})

    def _handle_diff(self, request, site):
        page_slug = request.data.get("page_unix_name", "")
        rev_a = int(request.data.get("revision_a", 0))
        rev_b = int(request.data.get("revision_b", 1))
        page = get_object_or_404(Page, site=site, unix_name=page_slug)

        rev_obj_a = PageRevision.objects.filter(page=page, revision_number=rev_a).first()
        rev_obj_b = PageRevision.objects.filter(page=page, revision_number=rev_b).first()

        source_a = rev_obj_a.source.text if rev_obj_a and rev_obj_a.source else ""
        source_b = rev_obj_b.source.text if rev_obj_b and rev_obj_b.source else ""

        import difflib
        diff = difflib.unified_diff(
            source_a.splitlines(keepends=True),
            source_b.splitlines(keepends=True),
            fromfile=f"rev {rev_a}",
            tofile=f"rev {rev_b}",
        )
        import html as html_mod
        diff_text = html_mod.escape("".join(diff))
        html = f'<div class="page-diff"><pre>{diff_text}</pre></div>'
        return Response({"status": "ok", "body": html})

    def _handle_who_rated(self, request, site):
        page_slug = request.data.get("page_unix_name", "")
        page = get_object_or_404(Page, site=site, unix_name=page_slug)
        votes = PageRateVote.objects.filter(page=page).select_related("user")

        rows = []
        for v in votes:
            sign = "+" if v.rate > 0 else ""
            rows.append(f'<li>{v.user.username}: {sign}{v.rate}</li>')

        html = f'<div class="who-rated"><ul>{"".join(rows)}</ul></div>'
        return Response({"status": "ok", "body": html})

    def _handle_tags(self, request, site):
        page_slug = request.data.get("page_unix_name", "")
        tags_str = request.data.get("tags", "")
        page = get_object_or_404(Page, site=site, unix_name=page_slug)

        if request.method == "POST" and tags_str is not None:
            page.tags.all().delete()
            for tag in tags_str.split():
                tag = tag.strip().lower()
                if tag:
                    PageTag.objects.create(site=site, page=page, tag=tag)

        current_tags = list(page.tags.values_list("tag", flat=True))
        html = f'<div class="page-tags"><span>{"  ".join(current_tags)}</span></div>'
        return Response({"status": "ok", "body": html, "tags": current_tags})

    def _handle_listpages(self, request, site):
        params = {k: v for k, v in request.data.items() if k not in ("moduleName", "callType", "site")}
        context = {"site": site, "page": None, "user": request.user if request.user.is_authenticated else None}
        html = ModuleRegistry.render("ListPages", params, context)
        return Response({"status": "ok", "body": html})

    def _handle_forum_start(self, request, site):
        from folia.forums.models import ForumGroup
        groups = ForumGroup.objects.filter(site=site, visible=True).prefetch_related("categories")

        html_parts = []
        for group in groups:
            html_parts.append(f'<div class="forum-group"><div class="head">{group.name}</div>')
            if group.description:
                html_parts.append(f'<div class="description">{group.description}</div>')
            html_parts.append('<table class="forum-cat-list">')
            html_parts.append('<tr><th>Category</th><th>Threads</th><th>Posts</th></tr>')
            for cat in group.categories.all():
                html_parts.append(
                    f'<tr><td><a href="/forum/c-{cat.pk}/{cat.name}">{cat.name}</a>'
                    f'<div class="description">{cat.description or ""}</div></td>'
                    f'<td>{cat.number_threads}</td><td>{cat.number_posts}</td></tr>'
                )
            html_parts.append('</table></div>')

        return Response({"status": "ok", "body": "".join(html_parts)})

    def _handle_forum_category(self, request, site):
        from folia.forums.models import ForumCategory, ForumThread
        cat_id = request.data.get("category_id")
        cat = get_object_or_404(ForumCategory, pk=cat_id, group__site=site)
        threads = ForumThread.objects.filter(category=cat, site=site).select_related("user").order_by("-sticky", "-date_started")

        rows = []
        for t in threads[:50]:
            sticky = '<span class="sticky">Sticky: </span>' if t.sticky else ""
            rows.append(
                f'<tr><td>{sticky}<a href="/forum/t-{t.pk}/{t.title}">{t.title}</a></td>'
                f'<td>{t.user_string or ""}</td>'
                f'<td>{t.number_posts}</td>'
                f'<td>{t.date_started.strftime("%d %b %Y") if t.date_started else ""}</td></tr>'
            )

        html = (
            f'<div class="forum-category-header"><h1>{cat.name}</h1>'
            f'<p>{cat.description or ""}</p></div>'
            f'<table class="forum-thread-list">'
            f'<tr><th>Thread</th><th>Started by</th><th>Posts</th><th>Date</th></tr>'
            f'{"".join(rows)}</table>'
        )
        return Response({"status": "ok", "body": html})

    def _handle_forum_thread(self, request, site):
        from folia.forums.models import ForumThread, ForumPost
        thread_id = request.data.get("thread_id")
        thread = get_object_or_404(ForumThread, pk=thread_id, site=site)
        posts = ForumPost.objects.filter(thread=thread).select_related("user").order_by("date_posted")

        post_html = []
        for p in posts:
            rendered = render_wikidot_markup(p.text, site) if p.text else ""
            post_html.append(
                f'<div class="post" id="post-{p.pk}">'
                f'<div class="head"><span class="info">{p.user_string or "Anonymous"}</span>'
                f'<span class="date">{p.date_posted.strftime("%d %b %Y %H:%M") if p.date_posted else ""}</span></div>'
                f'<div class="content">{rendered}</div>'
                f'<div class="options"><a href="#" class="reply-btn" data-post-id="{p.pk}">Reply</a></div>'
                f'</div>'
            )

        html = (
            f'<div class="forum-thread-box">'
            f'<div class="head"><h1>{thread.title}</h1>'
            f'<p>{thread.description or ""}</p></div>'
            f'<div class="posts">{"".join(post_html)}</div></div>'
        )
        return Response({"status": "ok", "body": html})

    def _handle_forum_new_thread(self, request, site):
        html = (
            '<div class="forum-new-thread">'
            '<form id="new-thread-form">'
            '<div><label>Title:</label><input type="text" name="title" class="text"></div>'
            '<div><label>Description:</label><input type="text" name="description" class="text"></div>'
            '<div><label>Content:</label><textarea name="source" rows="10"></textarea></div>'
            '<div class="buttons"><input type="submit" value="Post Thread" class="btn btn-primary"></div>'
            '</form></div>'
        )
        return Response({"status": "ok", "body": html})

    def _handle_forum_new_post(self, request, site):
        html = (
            '<div class="forum-new-post">'
            '<form id="new-post-form">'
            '<div><label>Title:</label><input type="text" name="title" class="text"></div>'
            '<div><textarea name="source" rows="6"></textarea></div>'
            '<div class="buttons"><input type="submit" value="Post Reply" class="btn btn-primary"></div>'
            '</form></div>'
        )
        return Response({"status": "ok", "body": html})
