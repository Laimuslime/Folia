"""Data transformers for converting Wikidot data to Folia format."""
from ..config import MigrationConfig


class PageTransformer:
    """Transform Wikidot page data to Folia format."""

    def __init__(self, config: MigrationConfig):
        self.config = config

    def transform(self, wikidot_page: dict) -> dict:
        """Convert a Wikidot page dict to Folia page format."""
        slug = wikidot_page.get("fullname", wikidot_page.get("slug", ""))

        # Split category from slug
        category = "_default"
        page_slug = slug
        if ":" in slug:
            parts = slug.split(":", 1)
            category = parts[0]
            page_slug = parts[1]

        return {
            "slug": page_slug,
            "category": category,
            "title": wikidot_page.get("title", page_slug),
            "source": wikidot_page.get("content", wikidot_page.get("source", "")),
            "tags": wikidot_page.get("tags", []),
            "rating": wikidot_page.get("rating", 0),
            "created_at": wikidot_page.get("created_at"),
            "created_by": wikidot_page.get("created_by"),
        }


class UserTransformer:
    """Map Wikidot users to Folia users."""

    def __init__(self, config: MigrationConfig):
        self.config = config
        self.user_map: dict[str, str] = {}

    def transform(self, wikidot_user: str) -> str:
        """Map a Wikidot username to a Folia username."""
        if wikidot_user in self.user_map:
            return self.user_map[wikidot_user]
        # Default: use same username, sanitized
        folia_user = wikidot_user.lower().replace(" ", "_")
        self.user_map[wikidot_user] = folia_user
        return folia_user


class ForumTransformer:
    """Transform Wikidot forum data to Folia format."""

    def __init__(self, config: MigrationConfig):
        self.config = config

    def transform_category(self, wikidot_cat: dict) -> dict:
        return {
            "name": wikidot_cat.get("title", ""),
            "description": wikidot_cat.get("description", ""),
        }

    def transform_thread(self, wikidot_thread: dict) -> dict:
        return {
            "title": wikidot_thread.get("title", ""),
            "created_by": wikidot_thread.get("started_by", ""),
            "created_at": wikidot_thread.get("started_time"),
        }

    def transform_post(self, wikidot_post: dict) -> dict:
        return {
            "content": wikidot_post.get("content", wikidot_post.get("text", "")),
            "user": wikidot_post.get("poster", wikidot_post.get("user", "")),
            "title": wikidot_post.get("title", ""),
            "created_at": wikidot_post.get("odate", wikidot_post.get("created_at")),
        }
