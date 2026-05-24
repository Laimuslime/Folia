"""Wikidot XML-RPC API client for data export."""
import xmlrpc.client
import time
import logging
from typing import Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..config import MigrationConfig

logger = logging.getLogger(__name__)


class WikidotApiClient:
    API_URL = "https://www.wikidot.com/xml-rpc-api.php"

    def __init__(self, config: MigrationConfig):
        self.config = config
        self.site = config.source_site
        self.proxy = xmlrpc.client.ServerProxy(
            self.API_URL,
            allow_none=True,
        )
        self.auth = {"site": self.site, "key": config.api_key}

    def _call(self, method: str, params: dict = None) -> Any:
        merged = {**self.auth, **(params or {})}
        for attempt in range(self.config.retry_count):
            try:
                result = getattr(self.proxy, method)(merged)
                return result
            except Exception as e:
                if attempt < self.config.retry_count - 1:
                    time.sleep(self.config.retry_delay * (attempt + 1))
                    logger.warning(f"Retry {attempt + 1} for {method}: {e}")
                else:
                    raise

    def list_pages(self) -> list[str]:
        """Get all page slugs from the site."""
        result = self._call("pages.select", {"site": self.site})
        return [p["fullname"] for p in result]

    def get_page(self, slug: str) -> dict:
        """Get full page data including source."""
        return self._call("pages.get_one", {"site": self.site, "page": slug})

    def get_page_meta(self, slug: str) -> dict:
        """Get page metadata."""
        return self._call("pages.get_meta", {"site": self.site, "pages": [slug]})

    def get_page_tags(self, slug: str) -> list[str]:
        """Get tags for a page."""
        meta = self.get_page_meta(slug)
        page_data = meta.get(slug, {})
        return page_data.get("tags", [])

    def get_page_files(self, slug: str) -> list[dict]:
        """Get files attached to a page."""
        return self._call("files.select", {"site": self.site, "page": slug})

    def get_page_revisions(self, slug: str) -> list[dict]:
        """Get revision history for a page."""
        return self._call("pages.get_revisions", {"site": self.site, "page": slug})

    def get_forum_categories(self) -> list[dict]:
        """Get forum categories."""
        return self._call("forum.categories_select", {"site": self.site})

    def get_forum_threads(self, category_id: int) -> list[dict]:
        """Get threads in a forum category."""
        return self._call("forum.threads_select", {"site": self.site, "c": category_id})

    def get_forum_posts(self, thread_id: int) -> list[dict]:
        """Get posts in a thread."""
        return self._call("forum.posts_select", {"site": self.site, "t": thread_id})

    def export_all(self) -> dict:
        """Export all site data."""
        data = {"pages": [], "files": [], "forum": []}

        # Export pages
        slugs = self.list_pages()
        logger.info(f"Found {len(slugs)} pages to export")

        with ThreadPoolExecutor(max_workers=self.config.workers) as executor:
            futures = {executor.submit(self._export_page, slug): slug for slug in slugs}
            for future in as_completed(futures):
                slug = futures[future]
                try:
                    page_data = future.result()
                    if page_data:
                        data["pages"].append(page_data)
                except Exception as e:
                    logger.error(f"Failed to export page {slug}: {e}")

        # Export files
        if self.config.include_files:
            for page_data in data["pages"]:
                try:
                    files = self.get_page_files(page_data["slug"])
                    for f in files:
                        f["page_slug"] = page_data["slug"]
                    data["files"].extend(files)
                except Exception as e:
                    logger.error(f"Failed to get files for {page_data['slug']}: {e}")

        # Export forum
        if self.config.include_forum:
            data["forum"] = self._export_forum()

        return data

    def _export_page(self, slug: str) -> dict | None:
        try:
            page = self.get_page(slug)
            tags = self.get_page_tags(slug)
            return {
                "slug": slug,
                "title": page.get("title", slug),
                "source": page.get("content", ""),
                "tags": tags,
                "created_at": page.get("created_at"),
                "created_by": page.get("created_by"),
                "updated_at": page.get("updated_at"),
                "updated_by": page.get("updated_by"),
                "rating": page.get("rating", 0),
            }
        except Exception as e:
            logger.error(f"Error exporting {slug}: {e}")
            return None

    def _export_forum(self) -> list[dict]:
        forum_data = []
        try:
            categories = self.get_forum_categories()
            for cat in categories:
                cat_data = {
                    "id": cat["id"],
                    "name": cat.get("title", ""),
                    "description": cat.get("description", ""),
                    "threads": [],
                }
                threads = self.get_forum_threads(cat["id"])
                for thread in threads:
                    thread_data = {
                        "id": thread["id"],
                        "title": thread.get("title", ""),
                        "created_by": thread.get("started_by"),
                        "created_at": thread.get("started_time"),
                        "posts": [],
                    }
                    posts = self.get_forum_posts(thread["id"])
                    thread_data["posts"] = posts
                    cat_data["threads"].append(thread_data)
                forum_data.append(cat_data)
        except Exception as e:
            logger.error(f"Error exporting forum: {e}")
        return forum_data
