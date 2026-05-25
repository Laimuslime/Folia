"""
Standard Wikidot modules: Rate, TagCloud, PageTree, Backlinks, etc.
"""
import re
from collections import Counter
from django.db.models import Count, Sum
from . import BaseModule, ModuleRegistry


@ModuleRegistry.register("Rate")
class RateModule(BaseModule):
    def render(self) -> str:
        page = self.page
        if not page:
            return ""
        rating = page.rate
        return (
            f'<div class="page-rate-widget-box">'
            f'<span class="rate-points">rating:&nbsp;<span class="number">{rating:+d}</span></span>'
            f'<span class="rateup btn btn-default"><a title="vote up" href="#" data-action="rate" data-value="1">+</a></span>'
            f'<span class="ratedown btn btn-default"><a title="vote down" href="#" data-action="rate" data-value="-1">-</a></span>'
            f'<span class="cancel btn btn-default"><a title="cancel vote" href="#" data-action="rate" data-value="0">x</a></span>'
            f'</div>'
        )


@ModuleRegistry.register("PageRate")
class PageRateModule(RateModule):
    pass


@ModuleRegistry.register("TagCloud")
class TagCloudModule(BaseModule):
    def render(self) -> str:
        from folia.wiki.models import PageTag
        site = self.site
        if not site:
            return ""

        max_font = float(self.get_param("maxFontSize", "150"))
        min_font = float(self.get_param("minFontSize", "60"))
        max_color = self.get_param("maxColor", "8,8,64")
        min_color = self.get_param("minColor", "100,100,128")
        limit = int(self.get_param("limit", "50"))

        category = self.get_param("category")
        tags_qs = PageTag.objects.filter(site=site)
        if category and category != "*":
            tags_qs = tags_qs.filter(page__category__name=category)

        tag_counts = tags_qs.values("tag").annotate(count=Count("tag")).order_by("-count")[:limit]

        if not tag_counts:
            return '<p>No tags.</p>'

        max_count = tag_counts[0]["count"] if tag_counts else 1
        min_count = tag_counts[len(tag_counts) - 1]["count"] if tag_counts else 1

        items = []
        for tc in sorted(tag_counts, key=lambda x: x["tag"]):
            tag = tc["tag"]
            count = tc["count"]
            if max_count == min_count:
                ratio = 0.5
            else:
                ratio = (count - min_count) / (max_count - min_count)
            font_size = min_font + ratio * (max_font - min_font)
            items.append(
                f'<a href="/system:page-tags/tag/{tag}" style="font-size:{font_size:.0f}%">{tag}</a>'
            )

        return f'<div class="pages-tag-cloud-box">{"&nbsp; ".join(items)}</div>'


@ModuleRegistry.register("Backlinks")
class BacklinksModule(BaseModule):
    def render(self) -> str:
        from folia.wiki.models import PageLink
        page = self.page
        if not page:
            return ""

        links = PageLink.objects.filter(to_page=page).select_related("from_page")
        if not links:
            return '<p>No pages link to this page.</p>'

        items = []
        for link in links:
            p = link.from_page
            items.append(f'<li><a href="/{p.full_name}">{p.title}</a></li>')

        return f'<div class="backlinks-box"><ul>{"".join(items)}</ul></div>'


@ModuleRegistry.register("WantedPages")
class WantedPagesModule(BaseModule):
    def render(self) -> str:
        from folia.wiki.models import PageLink
        site = self.site
        if not site:
            return ""

        wanted = (
            PageLink.objects.filter(site=site, to_page__isnull=True)
            .values("to_page_name")
            .annotate(count=Count("id"))
            .order_by("-count")[:50]
        )

        if not wanted:
            return '<p>No wanted pages.</p>'

        items = []
        for w in wanted:
            name = w["to_page_name"]
            count = w["count"]
            items.append(f'<li><a href="/{name}" class="newpage">{name}</a> ({count} links)</li>')

        return f'<ul class="wanted-pages">{"".join(items)}</ul>'


@ModuleRegistry.register("PageTree")
class PageTreeModule(BaseModule):
    def render(self) -> str:
        from folia.wiki.models import Page
        site = self.site
        root_param = self.get_param("root")
        depth = int(self.get_param("depth", "0"))
        show_root = self.get_param("showRoot", "yes") == "yes"

        if root_param:
            root_page = Page.objects.filter(site=site, unix_name=root_param).first()
        else:
            root_page = self.page

        if not root_page:
            return '<p>Root page not found.</p>'

        html = self._render_tree(root_page, depth, 0, show_root)
        return f'<div class="page-tree">{html}</div>'

    def _render_tree(self, page, max_depth: int, current_depth: int, show_self: bool) -> str:
        items = []
        if show_self:
            items.append(f'<li><a href="/{page.full_name}">{page.title}</a>')

        if max_depth == 0 or current_depth < max_depth:
            children = page.children.all().order_by("title")
            if children:
                child_items = []
                for child in children:
                    child_html = self._render_tree(child, max_depth, current_depth + 1, True)
                    child_items.append(child_html)
                sub = f'<ul>{"".join(child_items)}</ul>'
                if show_self:
                    items.append(sub)
                    items.append('</li>')
                else:
                    return sub
            elif show_self:
                items.append('</li>')

        return "".join(items)


@ModuleRegistry.register("ChildPages")
class ChildPagesModule(BaseModule):
    def render(self) -> str:
        from folia.wiki.models import Page
        page = self.page
        if not page:
            return ""

        children = page.children.all().order_by("title")
        if not children:
            return '<p>No child pages.</p>'

        items = []
        for child in children:
            items.append(f'<li><a href="/{child.full_name}">{child.title}</a></li>')

        return f'<ul class="child-pages">{"".join(items)}</ul>'


@ModuleRegistry.register("RecentChanges")
class RecentChangesModule(BaseModule):
    def render(self) -> str:
        from folia.wiki.models import PageRevision
        site = self.site
        if not site:
            return ""

        limit = int(self.get_param("limit", "30"))
        revisions = (
            PageRevision.objects.filter(site=site)
            .select_related("page", "user")
            .order_by("-date_last_edited")[:limit]
        )

        if not revisions:
            return '<p>No recent changes.</p>'

        items = []
        for rev in revisions:
            page = rev.page
            user = rev.user.username if rev.user else rev.user_string or "anonymous"
            date = rev.date_last_edited.strftime("%d %b %Y %H:%M") if rev.date_last_edited else ""
            flags = []
            if rev.flag_new:
                flags.append("N")
            if rev.flag_text:
                flags.append("S")
            if rev.flag_title:
                flags.append("T")
            if rev.flag_rename:
                flags.append("R")
            flag_str = f' <span class="flags">({",".join(flags)})</span>' if flags else ""
            comment = f' <em class="comment">{rev.comments}</em>' if rev.comments else ""
            items.append(
                f'<tr>'
                f'<td class="title"><a href="/{page.full_name}">{page.title}</a>{flag_str}</td>'
                f'<td class="mod-date">{date}</td>'
                f'<td class="mod-by"><a href="/user:info/{user}">{user}</a></td>'
                f'<td class="revision-no">rev. {rev.revision_number}</td>'
                f'<td class="comments">{comment}</td>'
                f'</tr>'
            )

        return (
            f'<table class="wiki-content-table recent-changes">'
            f'<tbody>{"".join(items)}</tbody></table>'
        )


@ModuleRegistry.register("Members")
class MembersModule(BaseModule):
    def render(self) -> str:
        from folia.sites.models import Member
        site = self.site
        if not site:
            return ""

        members = Member.objects.filter(site=site).select_related("user").order_by("-date_joined")
        items = []
        for m in members:
            items.append(
                f'<li><a href="/user:info/{m.user.username}">{m.user.username}</a>'
                f' <span class="date">(joined {m.date_joined.strftime("%d %b %Y")})</span></li>'
            )

        return f'<div class="members-list"><ul>{"".join(items)}</ul></div>'


@ModuleRegistry.register("Join")
class JoinModule(BaseModule):
    def render(self) -> str:
        site = self.site
        if not site:
            return ""

        button_text = self.get_param("button", "加入站点")
        return (
            f'<div class="join-area">'
            f'<button class="btn btn-primary join-btn" data-site="{site.slug}">{button_text}</button>'
            f'</div>'
        )


@ModuleRegistry.register("CountPages")
class CountPagesModule(BaseModule):
    def render(self) -> str:
        from folia.wiki.models import Page
        site = self.site
        if not site:
            return "0"

        count = Page.objects.filter(site=site).count()
        return str(count)


@ModuleRegistry.register("CSS")
class CSSModule(BaseModule):
    def render(self) -> str:
        css = self.get_param("_body", "")
        return f'<style>{css}</style>'


@ModuleRegistry.register("IfTags")
class IfTagsModule(BaseModule):
    def render(self) -> str:
        page = self.page
        if not page:
            return ""

        tags_param = self.get_param("tags", "")
        if not tags_param:
            return self.get_param("_body", "")

        page_tags = set(page.tags.values_list("tag", flat=True))
        required = [t.strip() for t in tags_param.split(",") if t.strip()]

        match = all(t in page_tags for t in required)
        if match:
            return self.get_param("_body", "")
        return ""


@ModuleRegistry.register("IfCategory")
class IfCategoryModule(BaseModule):
    def render(self) -> str:
        page = self.page
        if not page:
            return ""

        category_param = self.get_param("category", "")
        if not category_param:
            return self.get_param("_body", "")

        page_cat = page.category.name if page.category else "_default"
        cats = [c.strip() for c in category_param.split(",")]

        if page_cat in cats:
            return self.get_param("_body", "")
        return ""


@ModuleRegistry.register("Gallery")
class GalleryModule(BaseModule):
    def render(self) -> str:
        from folia.wiki.models import File
        page = self.page
        if not page:
            return ""

        files = File.objects.filter(page=page, mimetype__startswith="image/")
        if not files:
            return '<p>No images.</p>'

        items = []
        for f in files:
            items.append(
                f'<div class="gallery-item">'
                f'<a href="/local--files/{page.full_name}/{f.filename}">'
                f'<img src="/local--files/{page.full_name}/{f.filename}" alt="{f.filename}">'
                f'</a></div>'
            )

        return f'<div class="scp-image-gallery">{"".join(items)}</div>'
