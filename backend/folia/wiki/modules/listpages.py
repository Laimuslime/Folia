"""
ListPages Module — The most important Wikidot module.

Selects pages based on criteria and renders them using a template.
Supports: category, tags, order, limit, perPage, pagination, and variable substitution.
"""
import re
from django.db.models import Q, Count
from . import BaseModule, ModuleRegistry


@ModuleRegistry.register("ListPages")
class ListPagesModule(BaseModule):
    VALID_ORDERS = {
        "title": "title",
        "name": "unix_name",
        "created_at": "date_created",
        "updated_at": "date_last_edited",
        "rating": "rate",
        "random": "?",
    }

    VARIABLES = {
        "%%title%%": lambda p: p.title,
        "%%title_linked%%": lambda p: f'<a href="/{p.full_name}">{p.title}</a>',
        "%%link%%": lambda p: f"/{p.full_name}",
        "%%name%%": lambda p: p.unix_name,
        "%%fullname%%": lambda p: p.full_name,
        "%%category%%": lambda p: p.category.name if p.category else "_default",
        "%%created_at%%": lambda p: p.date_created.strftime("%d %b %Y %H:%M") if p.date_created else "",
        "%%updated_at%%": lambda p: p.date_last_edited.strftime("%d %b %Y %H:%M") if p.date_last_edited else "",
        "%%created_by%%": lambda p: p.owner_user.username if p.owner_user else "unknown",
        "%%created_by_linked%%": lambda p: f'<a href="/user:info/{p.owner_user.username}">{p.owner_user.username}</a>' if p.owner_user else "unknown",
        "%%rating%%": lambda p: str(p.rate),
        "%%comments%%": lambda p: str(p.discussion_threads.first().number_posts if p.discussion_threads.exists() else 0),
        "%%tags%%": lambda p: " ".join(t.tag for t in p.tags.all()),
        "%%tags_linked%%": lambda p: " ".join(f'<a href="/system:page-tags/tag/{t.tag}">_{t.tag}_</a>' for t in p.tags.all()),
        "%%content%%": lambda p: p.compiled_html,
        "%%content{n}%%": None,  # handled separately
        "%%first_paragraph%%": lambda p: _first_paragraph(p.compiled_html),
        "%%short%%": lambda p: _first_paragraph(p.compiled_html),
    }

    def render(self) -> str:
        from folia.wiki.models import Page, Category

        site = self.site
        if not site:
            return '<div class="error-block">No site context.</div>'

        pages = Page.objects.filter(site=site).select_related("category", "owner_user").prefetch_related("tags")

        # 分类过滤
        category_param = self.get_param("category", ".")
        if category_param == "*":
            pass  # all categories
        elif category_param == ".":
            if self.page and self.page.category:
                pages = pages.filter(category=self.page.category)
        else:
            cats = [c.strip() for c in re.split(r'[,;\s]+', category_param) if c.strip()]
            if cats:
                pages = pages.filter(category__name__in=cats)

        # 标签过滤
        tags_param = self.get_param("tags")
        if tags_param:
            tags_list = [t.strip() for t in re.split(r'[,;\s]+', tags_param) if t.strip()]
            include_tags = [t for t in tags_list if not t.startswith("-")]
            exclude_tags = [t[1:] for t in tags_list if t.startswith("-")]

            if include_tags:
                for tag in include_tags:
                    if tag.startswith("+"):
                        pages = pages.filter(tags__tag=tag[1:])
                    else:
                        pages = pages.filter(tags__tag=tag)
            if exclude_tags:
                pages = pages.exclude(tags__tag__in=exclude_tags)

        # 父页面过滤
        parent_param = self.get_param("parent")
        if parent_param == "-":
            pages = pages.filter(parent_page__isnull=True)
        elif parent_param == ".":
            if self.page:
                pages = pages.filter(parent_page=self.page)
        elif parent_param:
            pages = pages.filter(parent_page__unix_name=parent_param)

        # 跳过当前页面
        if self.get_param("skipCurrent", "no") in ("yes", "true"):
            if self.page:
                pages = pages.exclude(pk=self.page.pk)

        # 名称过滤
        name_param = self.get_param("name")
        if name_param:
            if "%" in name_param:
                safe_pattern = re.escape(name_param).replace(r"\%", ".*")
                pages = pages.filter(unix_name__regex=safe_pattern)
            else:
                pages = pages.filter(unix_name=name_param)

        # 评分过滤
        rating_param = self.get_param("rating")
        if rating_param:
            if rating_param.startswith(">"):
                pages = pages.filter(rate__gt=int(rating_param[1:]))
            elif rating_param.startswith("<"):
                pages = pages.filter(rate__lt=int(rating_param[1:]))
            elif rating_param.startswith("="):
                pages = pages.filter(rate=int(rating_param[1:]))

        # 创建日期过滤
        created_at = self.get_param("created_at")
        if created_at:
            if created_at.startswith("last"):
                # e.g., "last 3 days"
                import datetime
                match = re.match(r'last\s+(\d+)\s+(\w+)', created_at)
                if match:
                    num = int(match.group(1))
                    unit = match.group(2)
                    if "day" in unit:
                        delta = datetime.timedelta(days=num)
                    elif "hour" in unit:
                        delta = datetime.timedelta(hours=num)
                    else:
                        delta = datetime.timedelta(days=num)
                    from django.utils import timezone
                    pages = pages.filter(date_created__gte=timezone.now() - delta)

        # 排序
        order_param = self.get_param("order", "created_at desc")
        order_parts = order_param.split()
        order_field = self.VALID_ORDERS.get(order_parts[0], "date_created")
        if len(order_parts) > 1 and order_parts[1].lower() == "desc":
            order_field = f"-{order_field}"
        pages = pages.order_by(order_field)

        # 限制数量
        limit = int(self.get_param("limit", "20"))
        per_page = int(self.get_param("perPage", "0"))

        if per_page > 0:
            # 分页
            current_page_num = int(self.context.get("p", 1))
            total = pages.count()
            total_pages = (total + per_page - 1) // per_page
            start = (current_page_num - 1) * per_page
            pages = pages[start:start + per_page]
        else:
            pages = pages[:limit]

        # 获取正文模板
        body = self.get_param("_body", "%%title_linked%%\n")

        # 分离头部/尾部
        header = ""
        footer = ""
        if "%%content%%\n" in body:
            parts = body.split("%%content%%\n", 1)
            header = parts[0] if len(parts) > 1 else ""
            body = parts[1] if len(parts) > 1 else body

        # 渲染每个页面
        items = []
        for page in pages:
            item_html = self._render_item(body, page)
            items.append(item_html)

        if not items:
            empty_msg = self.get_param("emptyOutput", "")
            if empty_msg:
                return f'<p>{empty_msg}</p>'
            return '<p class="list-pages-empty">No pages match.</p>'

        # 包装输出
        wrapper = self.get_param("wrapper", "yes")
        separator = self.get_param("separate", "yes")

        if separator == "no":
            result = "".join(items)
        else:
            result = "\n".join(items)

        if wrapper != "no":
            result = f'<div class="list-pages-box">{result}</div>'

        # Pagination
        if per_page > 0 and total_pages > 1:
            result += self._render_pagination(current_page_num, total_pages)

        return result

    def _render_item(self, template: str, page) -> str:
        result = template
        for var, func in self.VARIABLES.items():
            if func and var in result:
                try:
                    result = result.replace(var, func(page))
                except Exception:
                    result = result.replace(var, "")

        # 处理 %%content{n}%% — 前 n 段
        content_n = re.findall(r'%%content\{(\d+)\}%%', result)
        for n in content_n:
            html = page.compiled_html
            paragraphs = re.findall(r'<p>.*?</p>', html, re.DOTALL)
            result = result.replace(f"%%content{{{n}}}%%", "\n".join(paragraphs[:int(n)]))

        return f'<div class="list-pages-item">{result}</div>'

    def _render_pagination(self, current: int, total: int) -> str:
        links = []
        for i in range(1, total + 1):
            if i == current:
                links.append(f'<span class="current">{i}</span>')
            else:
                links.append(f'<a href="?p={i}">{i}</a>')
        return f'<div class="pager">{"".join(links)}</div>'


def _first_paragraph(html: str) -> str:
    match = re.search(r'<p>(.*?)</p>', html, re.DOTALL)
    return match.group(1) if match else ""
