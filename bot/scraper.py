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
        response = self.session.get(
            url,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        return response.text

    def get_homepage(self) -> str:
        return self.fetch(SITE_URL)

    def get_download_links(self, movie_url: str) -> list[str]:
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

        for link in soup.find_all("a", href=True):

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

            if not any(
                keyword in text
                for keyword in keywords
            ):
                continue

            absolute_url = urljoin(
                movie_url,
                href,
            )

            if absolute_url in seen_links:
                continue

            seen_links.add(absolute_url)
            links.append(absolute_url)

        return links

    def get_latest_posts(self) -> list[dict]:
        html = self.get_homepage()

        soup = BeautifulSoup(
            html,
            "lxml",
        )

        posts = []
        seen_urls = set()

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

            # Only links from our website.
            if not absolute_url.startswith(
                SITE_URL
            ):
                continue

            # Only movie pages.
            # This excludes category pages
            # and other website links.
            if "/movie/" not in absolute_url.lower():
                continue

            # Avoid duplicate URLs on the homepage.
            if absolute_url in seen_urls:
                continue

            title = link.get_text(
                " ",
                strip=True,
            )

            if not title:
                continue

            seen_urls.add(absolute_url)

            download_links = self.get_download_links(
                absolute_url
            )

            posts.append(
                {
                    "title": title,
                    "url": absolute_url,
                    "download_links": download_links,
                }
            )

        return posts
