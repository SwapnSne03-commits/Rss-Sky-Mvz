import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from .config import (
    SITE_URL,
    REQUEST_TIMEOUT,
    USER_AGENT,
)


class WebsiteScraper:
    def __init__(self):
        self.session = requests.Session()

        self.session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": (
                    "text/html,application/xhtml+xml,"
                    "application/xml;q=0.9,image/avif,"
                    "image/webp,*/*;q=0.8"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

    def fetch(self, url: str) -> str:
        """
        Download a webpage and return its HTML.
        """

        response = self.session.get(
            url,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        return response.text

    def get_homepage(self) -> str:
        """
        Fetch the main website homepage.
        """

        return self.fetch(SITE_URL)

    def get_latest_posts(self) -> list[dict]:
        """
        Extract movie post links from the website homepage.

        Returns:
            [
                {
                    "title": "...",
                    "url": "https://..."
                }
            ]
        """

        html = self.get_homepage()

        soup = BeautifulSoup(
            html,
            "lxml",
        )

        posts = []
        seen_urls = set()

        for link in soup.find_all("a", href=True):

            href = link.get("href", "").strip()

            if not href:
                continue

            absolute_url = urljoin(
                SITE_URL + "/",
                href,
            )

            # Only keep posts belonging to our website.
            if not absolute_url.startswith(SITE_URL):
                continue

            # Ignore the homepage itself.
            if absolute_url.rstrip("/") == SITE_URL:
                continue

            # Avoid processing the same URL twice.
            if absolute_url in seen_urls:
                continue

            title = link.get_text(
                " ",
                strip=True,
            )

            if not title:
                continue

            seen_urls.add(absolute_url)

            posts.append(
                {
                    "title": title,
                    "url": absolute_url,
                }
            )

        return posts
