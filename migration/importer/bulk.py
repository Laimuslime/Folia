"""Bulk importer — imports parsed data into Folia via API."""
import logging
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from ..config import MigrationConfig

logger = logging.getLogger(__name__)


class BulkImporter:
    def __init__(self, config: MigrationConfig):
        self.config = config
        self.base_url = f"{config.target_url}/api/v1"
        self.session = requests.Session()
        if config.target_token:
            self.session.headers["Authorization"] = f"Bearer {config.target_token}"

    def import_data(self, data: dict) -> dict:
        """Import all data into Folia."""
        result = {"pages_imported": 0, "files_imported": 0, "forum_imported": 0, "errors": 0}

        # Ensure target site exists
        site_slug = self.config.target_site_slug or self.config.source_site
        self._ensure_site(site_slug, data.get("metadata", {}))

        # Import pages
        pages = data.get("pages", [])
        logger.info(f"Importing {len(pages)} pages...")

        for page_data in tqdm(pages, desc="Importing pages", disable=not self.config.verbose):
            try:
                self._import_page(site_slug, page_data)
                result["pages_imported"] += 1
            except Exception as e:
                logger.error(f"Failed to import page {page_data.get('slug', '?')}: {e}")
                result["errors"] += 1

        # Import files
        files = data.get("files", [])
        if files:
            logger.info(f"Importing {len(files)} files...")
            for file_data in tqdm(files, desc="Importing files", disable=not self.config.verbose):
                try:
                    self._import_file(site_slug, file_data)
                    result["files_imported"] += 1
                except Exception as e:
                    logger.error(f"Failed to import file {file_data.get('filename', '?')}: {e}")
                    result["errors"] += 1

        # Import forum
        forum_data = data.get("forum", [])
        if forum_data:
            logger.info(f"Importing forum data...")
            for category in forum_data:
                try:
                    self._import_forum_category(site_slug, category)
                    result["forum_imported"] += 1
                except Exception as e:
                    logger.error(f"Failed to import forum category: {e}")
                    result["errors"] += 1

        return result

    def _ensure_site(self, slug: str, metadata: dict):
        """Create the target site if it doesn't exist."""
        try:
            resp = self.session.get(f"{self.base_url}/sites/{slug}/")
            if resp.status_code == 200:
                return
        except Exception:
            pass

        self.session.post(f"{self.base_url}/sites/", json={
            "slug": slug,
            "name": metadata.get("name", slug),
            "subtitle": metadata.get("subtitle", ""),
            "description": metadata.get("description", "Migrated from Wikidot"),
        })

    def _import_page(self, site_slug: str, page_data: dict):
        """Import a single page."""
        payload = {
            "site": site_slug,
            "slug": page_data["slug"],
            "title": page_data.get("title", page_data["slug"]),
            "source": page_data.get("source", ""),
            "category": page_data.get("category", "_default"),
            "tags": page_data.get("tags", []),
            "comment": "Migrated from Wikidot",
        }

        resp = self.session.post(f"{self.base_url}/pages/", json=payload)
        if resp.status_code not in (200, 201):
            raise Exception(f"HTTP {resp.status_code}: {resp.text[:200]}")

        # Import revisions if available
        revisions = page_data.get("revisions", [])
        if len(revisions) > 1:
            for rev in revisions[1:]:  # Skip first (already created)
                try:
                    self.session.put(f"{self.base_url}/pages/{page_data['slug']}/", json={
                        "site": site_slug,
                        "source": rev.get("source", ""),
                        "comment": rev.get("comment", f"Revision {rev.get('number', '')}"),
                    })
                except Exception:
                    pass

    def _import_file(self, site_slug: str, file_data: dict):
        """Import a file attachment."""
        url = file_data.get("url")
        if not url:
            return

        # Download file
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()

        # Upload to Folia
        page_slug = file_data.get("page_slug", "")
        files = {"file": (file_data["filename"], resp.content, file_data.get("mime_type", "application/octet-stream"))}
        upload_resp = self.session.post(
            f"{self.base_url}/pages/{page_slug}/files/",
            files=files,
            params={"site": site_slug},
        )
        if upload_resp.status_code not in (200, 201):
            raise Exception(f"Upload failed: {upload_resp.status_code}")

    def _import_forum_category(self, site_slug: str, category_data: dict):
        """Import a forum category with threads and posts."""
        # This would create forum groups/categories/threads/posts
        # Simplified for now
        for thread in category_data.get("threads", []):
            posts = thread.get("posts", [])
            if posts:
                first_post = posts[0] if posts else {}
                try:
                    self.session.post(f"{self.base_url}/forum/threads/", json={
                        "site": site_slug,
                        "title": thread.get("title", ""),
                        "content": first_post.get("content", ""),
                    })
                except Exception as e:
                    logger.error(f"Failed to import thread: {e}")
