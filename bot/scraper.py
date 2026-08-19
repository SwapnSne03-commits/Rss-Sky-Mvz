import re
import requests

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

from .config import (
    SITE_URL,
    REQUEST_TIMEOUT,
    USER_AGENT,
    PROTECTED_LINK_DOMAIN,
    ALLOWED_HOSTS,
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

    @staticmethod
    def _clean_host(host: str) -> str:
        host = host.lower().strip()

        if host.startswith("www."):
            host = host[4:]

        return host.split(":", 1)[0]

    @staticmethod
    def _clean_text(text: str) -> str:
        return " ".join(
            text.split()
        ).strip()

    @staticmethod
    def _is_quality_text(text: str) -> bool:
        """
        Detect only quality-related headings.

        Examples:
        1080p 10bit HEVC
        1080p WEB-DL
        2160p HEVC
        2160p SDR HEVC LINK
        """

        text = " ".join(
            text.split()
        ).strip()

        if not text:
            return False

        quality_pattern = re.compile(
            r"""
            \b
            (?:
                480p|
                576p|
                720p|
                1080p|
                1440p|
                2160p|
                4k
            )
            \b
            .*?
            (?:
                web[-\s]?dl|
                webdl|
                hevc|
                h265|
                x265|
                10bit|
                8bit|
                sdr|
                hdr
            )
            """,
            re.IGNORECASE | re.VERBOSE,
        )

        return bool(
            quality_pattern.search(text)
        )

    def _find_quality_section(
        self,
        link,
    ) -> str | None:
        """
        Find the nearest quality heading appearing
        before a download link on the movie page.

        Server headings such as SERVER 01, SERVER 02
        are ignored.
        """

        # Tags that commonly contain section headings.
        heading_tags = (
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "p",
            "div",
            "span",
            "strong",
            "b",
            "center",
            "td",
            "li",
        )

        for previous in link.find_all_previous(
            heading_tags
        ):
            text = self._clean_text(
                previous.get_text(
                    " ",
                    strip=True,
                )
            )

            if not text:
                continue

            # Ignore extremely large containers.
            # They are usually parent containers containing
            # many links rather than actual headings.
            if len(text) > 150:
                continue

            if self._is_quality_text(text):
                return text

        return None

    def _get_allowed_host_name(
        self,
        hostname: str,
    ) -> str | None:
        """
        Return the configured display name if the hostname
        belongs to one of our allowed file hosts.
        """

        hostname = self._clean_host(
            hostname
        )

        if not hostname:
            return None

        for domain, display_name in ALLOWED_HOSTS.items():

            domain = self._clean_host(
                domain
            )

            # Exact match.
            if hostname == domain:
                return display_name

            # Support subdomains.
            if hostname.endswith(
                "." + domain
            ):
                return display_name

            # Some configured hosts may be partial
            # identifiers such as hubcloud or gdflix.
            if domain in hostname:
                return display_name

        return None

    def _is_allowed_url(
        self,
        url: str,
    ) -> bool:
        """
        Check whether a URL belongs to one of the
        allowed final file-host services.
        """

        try:
            parsed = urlparse(url)
        except Exception:
            return False

        if parsed.scheme not in (
            "http",
            "https",
        ):
            return False

        hostname = parsed.netloc

        return (
            self._get_allowed_host_name(
                hostname
            )
            is not None
        )

    def _extract_allowed_links(
        self,
        page_url: str,
        section: str | None = None,
    ) -> list[dict]:
        """
        Open an intermediary page and extract only
        explicitly allowed final file-host links.

        The intermediary URL itself is never returned.

        The section value is preserved so Publisher.py
        can later group quality-specific links.
        """

        html = self.fetch(
            page_url
        )

        soup = BeautifulSoup(
            html,
            "lxml",
        )

        links = []
        seen_urls = set()

        # First check the final URL after normal
        # HTTP redirects.
        try:
            response = self.session.get(
                page_url,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
            )

            final_url = response.url

            if self._is_allowed_url(
                final_url
            ):
                host = self._clean_host(
                    urlparse(
                        final_url
                    ).netloc
                )

                display_name = (
                    self._get_allowed_host_name(
                        host
                    )
                    or host
                )

                item = {
                    "url": final_url,
                    "host": display_name,
                }

                if section:
                    item["section"] = section

                links.append(item)

                seen_urls.add(
                    final_url
                )

        except requests.RequestException:
            pass

        # Extract normal <a href="..."> links
        # from the intermediary page.
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
                page_url,
                href,
            )

            if not self._is_allowed_url(
                absolute_url
            ):
                continue

            if absolute_url in seen_urls:
                continue

            parsed = urlparse(
                absolute_url
            )

            hostname = self._clean_host(
                parsed.netloc
            )

            display_name = (
                self._get_allowed_host_name(
                    hostname
                )
                or hostname
            )

            item = {
                "url": absolute_url,
                "host": display_name,
            }

            if section:
                item["section"] = section

            seen_urls.add(
                absolute_url
            )

            links.append(item)

        return links

    def get_download_links(
        self,
        movie_url: str,
    ) -> list[dict]:
        """
        Find all intermediary/server links from a movie
        page and extract only allowed final file-host links.

        Quality headings such as:

        1080p WEB-DL
        1080p 10bit HEVC LINK
        2160p HEVC
        2160p SDR HEVC LINK

        are preserved with their corresponding links.

        Normal SERVER headings remain unclassified.
        """

        html = self.fetch(
            movie_url
        )

        soup = BeautifulSoup(
            html,
            "lxml",
        )

        final_links = []
        seen_final_urls = set()
        seen_intermediary_urls = set()

        site_host = self._clean_host(
            urlparse(
                movie_url
            ).netloc
        )

        protected_host = self._clean_host(
            PROTECTED_LINK_DOMAIN
        )

        # Find every link on the movie page that points
        # to our configured intermediary service.
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

            intermediary_url = urljoin(
                movie_url,
                href,
            )

            parsed = urlparse(
                intermediary_url
            )

            if parsed.scheme not in (
                "http",
                "https",
            ):
                continue

            hostname = self._clean_host(
                parsed.netloc
            )

            # Only process our intermediary service.
            if hostname != protected_host:
                continue

            if intermediary_url in seen_intermediary_urls:
                continue

            seen_intermediary_urls.add(
                intermediary_url
            )

            # Detect whether this particular link belongs
            # to a quality section.
            quality_section = (
                self._find_quality_section(
                    link
                )
            )

            try:
                extracted_links = (
                    self._extract_allowed_links(
                        intermediary_url,
                        section=quality_section,
                    )
                )

            except requests.RequestException:
                continue

            for item in extracted_links:

                url = item.get(
                    "url",
                    "",
                ).strip()

                if not url:
                    continue

                if url in seen_final_urls:
                    continue

                # Extra safety:
                # never allow the intermediary itself.
                final_host = self._clean_host(
                    urlparse(
                        url
                    ).netloc
                )

                if final_host == protected_host:
                    continue

                display_name = (
                    self._get_allowed_host_name(
                        final_host
                    )
                )

                if not display_name:
                    continue

                result = {
                    "url": url,
                    "host": display_name,
                }

                section = item.get(
                    "section"
                )

                if section:
                    result["section"] = section

                seen_final_urls.add(
                    url
                )

                final_links.append(
                    result
                )

        return final_links

    def get_latest_posts(self) -> list[dict]:
        html = self.get_homepage()

        soup = BeautifulSoup(
            html,
            "lxml",
        )

        posts = []
        seen_urls = set()

        site_host = self._clean_host(
            urlparse(
                SITE_URL
            ).netloc
        )

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

            # Only links from our own website.
            if self._clean_host(
                parsed_url.netloc
            ) != site_host:
                continue

            # Only movie pages.
            if "/movie/" not in (
                parsed_url.path.lower()
            ):
                continue

            # Avoid duplicate references to the same
            # movie post on the homepage.
            if absolute_url in seen_urls:
                continue

            title = link.get_text(
                " ",
                strip=True,
            )

            if not title:
                continue

            seen_urls.add(
                absolute_url
            )

            try:
                download_links = (
                    self.get_download_links(
                        absolute_url
                    )
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
