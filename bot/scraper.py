import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

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
        response = self.session.get(
            url,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        return response.text

    def get_homepage(self) -> str:
        return self.fetch(SITE_URL)

    def get_download_links(
        self,
        movie_url: str,
    ) -> list[dict]:
        """
        Extract download/protected links from a movie page.

        Each returned item contains:
            {
                "url": "...",
                "host": "..."
            }
        """

        html = self.fetch(movie_url)

        soup = BeautifulSoup(
            html,
            "lxml",
        )

        links = []
        seen_links = set()

        keywords = (
            "GOOGLE DRIVE",
            "SERVER 01",
            "SERVER 02",
            "SERVER 03",
            "SERVER 04",
            "SERVER 05",
            "SERVER 06",
            "1080P WEB-DL",
        )

        for link in soup.find_all(
            "a",
            href=True,
        ):

            text = link.get_text(
                " ",
                strip=True,
            ).upper()

            href = link.get(
                "href",
                "",
            ).strip()

            if not href:
                continue

            # Only download/protected link buttons.
            if not any(
                keyword in text
                for keyword in keywords
            ):
                continue

            absolute_url = urljoin(
                movie_url,
                href,
            )

            parsed = urlparse(
                absolute_url
            )

            # Ignore invalid URLs.
            if not parsed.scheme:
                continue

            if not parsed.netloc:
                continue

            # Avoid duplicate download/protected URLs.
            if absolute_url in seen_links:
                continue

            host = parsed.netloc.lower()

            # Remove port if present.
            host = host.split(":", 1)[0]

            seen_links.add(absolute_url)

            links.append(
                {
                    "url": absolute_url,
                    "host": host,
                }
            )

        return links

    def get_latest_posts(self) -> list[dict]:
        html = self.get_homepage()

        soup = BeautifulSoup(
            html,
            "lxml",
        )

        posts = []
        seen_urls = set()

        site_host = urlparse(
            SITE_URL
        ).netloc.lower()

        for link in soup.find_all(
            "a",
            href=True,
        ):

            href = link.get(
                "href",
                "",
            ).strip()

            if not href:
                continue

            absolute_url = urljoin(
                SITE_URL + "/",
                href,
            )

            parsed_url = urlparse(
                absolute_url
            )

            # Only links from our website.
            if parsed_url.netloc.lower() != site_host:
                continue

            # Only movie pages.
            if "/movie/" not in parsed_url.path.lower():
                continue

            # Avoid duplicate movie URLs on homepage.
            if absolute_url in seen_urls:
                continue

            title = link.get_text(
                " ",
                strip=True,
            )

            if not title:
                continue

            seen_urls.add(absolute_url)

            # Extract download/protected links
            # from the movie page.
            try:
                download_links = self.get_download_links(
                    absolute_url
                )
            except requests.RequestException:
                download_links = []

            posts.append(
                {
                    "title": title,
                    "url": absolute_url,
                    "download_links": download_links,
                }
            )

        return posts
