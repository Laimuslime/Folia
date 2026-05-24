"""Web scraper for Wikidot data not available via API."""
import requests
import time
import logging
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..config import MigrationConfig

logger = logging.getLogger(__name__)


class WikidotScraper:
    def __init__(self, config: MigrationConfig):
        self.config = config
        self.site = config.source_site
        self.base_url = f"https://{self.site}.wikidot.com"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Folia-Migration-Tool/1.0",
        })

    def get_page_source(self, slug: str) -> str | None:
        """Scrape page source via the edit interface."""
        url = f"{self.base_url}/{slug}"
        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")

            # Try to find page source in the page's AJAX data
            page_id_elem = soup.find("div", {"id": "page-content"})
            if page_id_elem:
                return str(page_id_elem)
            return None
        except Exception as e:
            logger.error(f"Failed to scrape {slug}: {e}")
            return None

    def get_page_history(self, slug: str) -> list[dict]:
        """Scrape page revision history."""
        url = f"{self.base_url}/{slug}"
        revisions = []
        try:
            # Wikidot uses AJAX for history, need to use their API endpoint
            resp = self.session.post(
                f"{self.base_url}/ajax-module-connector.php",
                data={
                    "moduleName": "history/PageRevisionListModule",
                    "page": "1",
                    "perpage": "100",
                    "page_id": "",  # Would need page_id
                },
                headers={"X-Requested-With": "XMLHttpRequest"},
                timeout=30,
            )
            if resp.ok:
                data = resp.json()
                if "body" in data:
                    soup = BeautifulSoup(data["body"], "lxml")
                    rows = soup.find_all("tr")
                    for row in rows[1:]:  # Skip header
                        cells = row.find_all("td")
                        if len(cells) >= 4:
                            revisions.append({
                                "number": cells[0].get_text(strip=True),
                                "user": cells[1].get_text(strip=True),
                                "date": cells[2].get_text(strip=True),
                                "comment": cells[3].get_text(strip=True),
                            })
        except Exception as e:
            logger.error(f"Failed to get history for {slug}: {e}")
        return revisions

    def download_file(self, page_slug: str, filename: str, output_dir: str) -> str | None:
        """Download a file attachment."""
        url = f"{self.base_url}/local--files/{page_slug}/{filename}"
        try:
            resp = self.session.get(url, stream=True, timeout=60)
            resp.raise_for_status()

            import os
            os.makedirs(output_dir, exist_ok=True)
            filepath = os.path.join(output_dir, filename)

            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

            return filepath
        except Exception as e:
            logger.error(f"Failed to download {filename} from {page_slug}: {e}")
            return None

    def get_all_page_slugs(self) -> list[str]:
        """Scrape the list of all pages from the site."""
        slugs = []
        page_num = 1

        while True:
            url = f"{self.base_url}/system:list-all-pages/p/{page_num}"
            try:
                resp = self.session.get(url, timeout=30)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "lxml")

                page_list = soup.find("div", class_="list-pages-box")
                if not page_list:
                    break

                links = page_list.find_all("a")
                if not links:
                    break

                for link in links:
                    href = link.get("href", "")
                    if href.startswith("/"):
                        slugs.append(href[1:])

                # Check for next page
                pager = soup.find("span", class_="pager-no")
                if not pager or f"/{page_num + 1}" not in str(soup):
                    break

                page_num += 1
                time.sleep(0.5)  # Rate limiting
            except Exception as e:
                logger.error(f"Failed to get page list (page {page_num}): {e}")
                break

        return slugs

    def get_page_votes(self, page_slug: str) -> dict:
        """Scrape voting data for a page."""
        try:
            resp = self.session.post(
                f"{self.base_url}/ajax-module-connector.php",
                data={
                    "moduleName": "pagerate/WhoRatedPageModule",
                    "pageId": "",  # Would need page_id
                },
                headers={"X-Requested-With": "XMLHttpRequest"},
                timeout=30,
            )
            if resp.ok:
                data = resp.json()
                if "body" in data:
                    soup = BeautifulSoup(data["body"], "lxml")
                    votes = []
                    spans = soup.find_all("span", class_="printuser")
                    for span in spans:
                        user = span.get_text(strip=True)
                        # Find the vote value next to the user
                        next_elem = span.find_next_sibling()
                        if next_elem:
                            vote_text = next_elem.get_text(strip=True)
                            value = 1 if "+" in vote_text else -1
                            votes.append({"user": user, "value": value})
                    return {"votes": votes, "rating": sum(v["value"] for v in votes)}
        except Exception as e:
            logger.error(f"Failed to get votes for {page_slug}: {e}")
        return {"votes": [], "rating": 0}
