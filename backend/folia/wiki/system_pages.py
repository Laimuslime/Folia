"""
System pages — dynamically generated pages like Wikidot's system: category.
These handle list-all-pages, recent-changes, members, page-tags, etc.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta

from folia.wiki.models import Page, PageTag, LogEvent
from folia.sites.models import Site, Member


class SystemPageView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, page_name):
        site = getattr(request, "current_site", None)
        if not site:
            return Response({"detail": "Site required."}, status=400)

        handler = self._get_handler(page_name)
        if handler:
            return handler(request, site)

        return Response({"detail": f"System page '{page_name}' not found."}, status=404)

    def _get_handler(self, page_name):
        handlers = {
            "list-all-pages": self._list_all_pages,
            "recent-changes": self._recent_changes,
            "members": self._members,
            "page-tags": self._page_tags,
            "search": self._search,
        }
        return handlers.get(page_name)

    def _list_all_pages(self, request, site):
        pages = Page.objects.filter(site=site).select_related("category").order_by("unix_name")
        items = []
        for p in pages:
            items.append({
                "unix_name": p.unix_name,
                "title": p.title,
                "category": p.category.name if p.category else "_default",
                "date_created": p.date_created,
                "date_last_edited": p.date_last_edited,
            })
        return Response({
            "title": "List All Pages",
            "type": "system",
            "items": items,
            "compiled_html": self._render_page_list(items),
        })

    def _recent_changes(self, request, site):
        days = int(request.query_params.get("days", 30))
        since = timezone.now() - timedelta(days=days)
        events = LogEvent.objects.filter(site=site, date__gte=since).select_related("user", "page")[:100]

        items = []
        for ev in events:
            items.append({
                "type": ev.type,
                "text": ev.text,
                "user": ev.user.username if ev.user else ev.user_string,
                "page": ev.page.unix_name if ev.page else None,
                "date": ev.date,
            })

        html_rows = []
        for item in items:
            page_link = f'<a href="/{item["page"]}">{item["page"]}</a>' if item["page"] else ""
            html_rows.append(
                f'<tr><td>{item["date"].strftime("%d %b %Y %H:%M") if item["date"] else ""}</td>'
                f'<td>{item["type"]}</td><td>{page_link}</td>'
                f'<td>{item["user"] or ""}</td><td>{item["text"]}</td></tr>'
            )

        html = (
            '<table class="wiki-content-table">'
            '<tr><th>Date</th><th>Type</th><th>Page</th><th>User</th><th>Details</th></tr>'
            f'{"".join(html_rows)}</table>'
        )

        return Response({
            "title": "Recent Changes",
            "type": "system",
            "items": items,
            "compiled_html": html,
        })

    def _members(self, request, site):
        members = Member.objects.filter(site=site).select_related("user").order_by("-date_joined")
        items = []
        for m in members:
            items.append({
                "username": m.user.username,
                "date_joined": m.date_joined,
            })

        html_rows = []
        for item in items:
            html_rows.append(
                f'<tr><td><a href="/user:info/{item["username"]}">{item["username"]}</a></td>'
                f'<td>{item["date_joined"].strftime("%d %b %Y") if item["date_joined"] else ""}</td></tr>'
            )

        html = (
            '<table class="wiki-content-table">'
            '<tr><th>User</th><th>Joined</th></tr>'
            f'{"".join(html_rows)}</table>'
        )

        return Response({
            "title": "Members",
            "type": "system",
            "items": items,
            "compiled_html": html,
        })

    def _page_tags(self, request, site):
        tag = request.query_params.get("tag")
        if tag:
            pages = Page.objects.filter(site=site, tags__tag=tag).order_by("unix_name")
            items = [{"unix_name": p.unix_name, "title": p.title} for p in pages]
            html = f'<h2>Pages tagged "{tag}"</h2>' + self._render_page_list(
                [{"unix_name": p.unix_name, "title": p.title} for p in pages]
            )
        else:
            tags = PageTag.objects.filter(site=site).values_list("tag", flat=True).distinct().order_by("tag")
            items = [{"tag": t} for t in tags]
            html_parts = ['<div class="pages-tag-cloud-box">']
            for t in tags:
                count = PageTag.objects.filter(site=site, tag=t).count()
                html_parts.append(f'<a href="/system:page-tags/tag/{t}" style="font-size:{min(0.8 + count * 0.1, 2.0)}em">{t}</a> ')
            html_parts.append('</div>')
            html = "".join(html_parts)

        return Response({
            "title": "Page Tags",
            "type": "system",
            "items": items,
            "compiled_html": html,
        })

    def _search(self, request, site):
        query = request.query_params.get("q", "")
        if not query:
            return Response({
                "title": "Search",
                "type": "system",
                "items": [],
                "compiled_html": "<p>Enter a search query.</p>",
            })

        pages = Page.objects.filter(
            site=site, title__icontains=query
        ).order_by("-date_last_edited")[:50]

        items = [{"unix_name": p.unix_name, "title": p.title} for p in pages]
        html = f'<h2>Search results for "{query}"</h2>' + self._render_page_list(items)

        return Response({
            "title": f"Search: {query}",
            "type": "system",
            "items": items,
            "compiled_html": html,
        })

    def _render_page_list(self, items):
        if not items:
            return "<p>No pages found.</p>"
        rows = []
        for item in items:
            name = item.get("unix_name", "")
            title = item.get("title", name)
            rows.append(f'<li><a href="/{name}">{title}</a> ({name})</li>')
        return f'<ul>{"".join(rows)}</ul>'
