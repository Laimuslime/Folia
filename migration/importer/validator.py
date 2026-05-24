"""Migration validator — verifies migration completeness."""
import logging
import requests
from ..config import MigrationConfig

logger = logging.getLogger(__name__)


class MigrationValidator:
    def __init__(self, config: MigrationConfig):
        self.config = config
        self.base_url = f"{config.target_url}/api/v1"
        self.session = requests.Session()
        if config.target_token:
            self.session.headers["Authorization"] = f"Bearer {config.target_token}"

    def validate(self) -> dict:
        """Run validation checks and return a report."""
        report = {
            "status": "ok",
            "target_pages": 0,
            "pages_with_content": 0,
            "empty_pages": 0,
            "source_pages": None,
            "missing_pages": 0,
            "issues": [],
        }

        site_slug = self.config.target_site_slug or self.config.source_site

        # Check target pages
        try:
            resp = self.session.get(f"{self.base_url}/pages/", params={"site": site_slug})
            if resp.ok:
                pages = resp.json()
                if isinstance(pages, dict) and "results" in pages:
                    pages = pages["results"]
                report["target_pages"] = len(pages)

                for page in pages:
                    # Check if page has content
                    page_resp = self.session.get(f"{self.base_url}/pages/{page['slug']}/", params={"site": site_slug})
                    if page_resp.ok:
                        page_detail = page_resp.json()
                        if page_detail.get("source") or page_detail.get("compiled_html"):
                            report["pages_with_content"] += 1
                        else:
                            report["empty_pages"] += 1
                            report["issues"].append(f"Empty page: {page['slug']}")
        except Exception as e:
            report["status"] = "error"
            report["issues"].append(f"Failed to check target: {e}")

        # Compare with source if API key provided
        if self.config.api_key and self.config.source_site:
            try:
                from ..wikidot_api.client import WikidotApiClient
                client = WikidotApiClient(self.config)
                source_slugs = client.list_pages()
                report["source_pages"] = len(source_slugs)

                # Check for missing pages
                target_slugs = set()
                resp = self.session.get(f"{self.base_url}/pages/", params={"site": site_slug})
                if resp.ok:
                    pages = resp.json()
                    if isinstance(pages, dict) and "results" in pages:
                        pages = pages["results"]
                    target_slugs = {p["slug"] for p in pages}

                missing = set(source_slugs) - target_slugs
                report["missing_pages"] = len(missing)
                if missing:
                    report["status"] = "issues"
                    for slug in list(missing)[:20]:
                        report["issues"].append(f"Missing page: {slug}")
                    if len(missing) > 20:
                        report["issues"].append(f"... and {len(missing) - 20} more")
            except Exception as e:
                report["issues"].append(f"Source comparison failed: {e}")

        if report["empty_pages"] > 0:
            report["status"] = "issues"

        return report
