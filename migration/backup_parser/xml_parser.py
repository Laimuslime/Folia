"""Parser for Wikidot XML backup files."""
import xml.etree.ElementTree as ET
import logging
from pathlib import Path
from dateutil import parser as dateparser
from ..config import MigrationConfig

logger = logging.getLogger(__name__)


class WikidotBackupParser:
    def __init__(self, config: MigrationConfig):
        self.config = config
        self.filepath = config.source_file

    def parse(self) -> dict:
        """Parse a Wikidot backup XML file and return structured data."""
        data = {"pages": [], "files": [], "forum": [], "metadata": {}}

        tree = ET.parse(self.filepath)
        root = tree.getroot()

        # Handle different backup formats
        if root.tag == "wiki" or root.tag == "site":
            data["metadata"] = self._parse_site_meta(root)
            data["pages"] = self._parse_pages(root)
            data["files"] = self._parse_files(root)
        elif root.tag == "pages":
            data["pages"] = self._parse_pages_list(root)
        else:
            # Try to detect format
            pages_elem = root.find(".//pages") or root.find(".//page")
            if pages_elem is not None:
                if pages_elem.tag == "pages":
                    data["pages"] = self._parse_pages_list(pages_elem)
                else:
                    data["pages"] = [self._parse_single_page(pages_elem)]

        logger.info(f"Parsed {len(data['pages'])} pages from backup")
        return data

    def _parse_site_meta(self, root) -> dict:
        return {
            "name": self._get_text(root, "name", ""),
            "slug": self._get_text(root, "slug", ""),
            "subtitle": self._get_text(root, "subtitle", ""),
            "description": self._get_text(root, "description", ""),
        }

    def _parse_pages(self, root) -> list[dict]:
        pages = []
        pages_elem = root.find("pages")
        if pages_elem is None:
            # Try finding pages directly
            for page_elem in root.findall(".//page"):
                page = self._parse_single_page(page_elem)
                if page:
                    pages.append(page)
        else:
            pages = self._parse_pages_list(pages_elem)
        return pages

    def _parse_pages_list(self, pages_elem) -> list[dict]:
        pages = []
        for page_elem in pages_elem.findall("page"):
            page = self._parse_single_page(page_elem)
            if page:
                pages.append(page)
        return pages

    def _parse_single_page(self, page_elem) -> dict | None:
        try:
            slug = self._get_text(page_elem, "name", "") or self._get_text(page_elem, "slug", "") or self._get_text(page_elem, "fullname", "")
            if not slug:
                return None

            # Parse category from slug
            category = "_default"
            page_slug = slug
            if ":" in slug:
                parts = slug.split(":", 1)
                category = parts[0]
                page_slug = parts[1]

            # Get source/content
            source = self._get_text(page_elem, "source", "") or self._get_text(page_elem, "content", "")

            # Get tags
            tags_text = self._get_text(page_elem, "tags", "")
            tags = [t.strip() for t in tags_text.split() if t.strip()] if tags_text else []

            # Parse revisions if available
            revisions = []
            revisions_elem = page_elem.find("revisions")
            if revisions_elem is not None:
                for rev_elem in revisions_elem.findall("revision"):
                    rev = {
                        "number": int(self._get_text(rev_elem, "number", "0")),
                        "user": self._get_text(rev_elem, "user", ""),
                        "source": self._get_text(rev_elem, "source", "") or self._get_text(rev_elem, "content", ""),
                        "comment": self._get_text(rev_elem, "comment", ""),
                        "date": self._get_text(rev_elem, "date", ""),
                    }
                    revisions.append(rev)

            created_at = self._get_text(page_elem, "created_at", "") or self._get_text(page_elem, "date_created", "")
            updated_at = self._get_text(page_elem, "updated_at", "") or self._get_text(page_elem, "date_updated", "")

            return {
                "slug": page_slug,
                "full_slug": slug,
                "category": category,
                "title": self._get_text(page_elem, "title", slug),
                "source": source,
                "tags": tags,
                "rating": int(self._get_text(page_elem, "rating", "0")),
                "created_at": created_at,
                "created_by": self._get_text(page_elem, "created_by", "") or self._get_text(page_elem, "author", ""),
                "updated_at": updated_at,
                "revisions": revisions,
            }
        except Exception as e:
            logger.error(f"Error parsing page element: {e}")
            return None

    def _parse_files(self, root) -> list[dict]:
        files = []
        files_elem = root.find("files")
        if files_elem is None:
            return files

        for file_elem in files_elem.findall("file"):
            try:
                files.append({
                    "filename": self._get_text(file_elem, "name", "") or self._get_text(file_elem, "filename", ""),
                    "page_slug": self._get_text(file_elem, "page", ""),
                    "size": int(self._get_text(file_elem, "size", "0")),
                    "mime_type": self._get_text(file_elem, "mime", "") or self._get_text(file_elem, "content_type", ""),
                    "url": self._get_text(file_elem, "url", ""),
                })
            except Exception as e:
                logger.error(f"Error parsing file element: {e}")

        return files

    def _get_text(self, elem, tag: str, default: str = "") -> str:
        child = elem.find(tag)
        if child is not None and child.text:
            return child.text.strip()
        # Also check attributes
        return elem.get(tag, default)
