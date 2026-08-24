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
        Detect quality-specific section names.

        Examples:
        720P 10Bit HEVC LINK
        1080P 10Bit HEVC LINK
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

    @staticmethod
    def _is_watch_online_url(url: str) -> bool:
        """
        Detect direct Watch Online links.

        Example:
        https://tpead.net/v/A4LZoQ1aKecXAxP
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

        hostname = (
            parsed.netloc
            .lower()
            .strip()
        )

        if hostname.startswith("www."):
            hostname = hostname[4:]

        return (
            hostname == "tpead.net"
            or hostname.endswith(
                ".tpead.net"
            )
        )

    def _get_allowed_host_name(
        self,
        hostname: str,
    ) -> str | None:

        hostname = self._clean_host(
            hostname
        )

        if not hostname:
            return None

        for domain, display_name in ALLOWED_HOSTS.items():

            domain = self._clean_host(
                domain
            )

            if hostname == domain:
                return display_name

            if hostname.endswith(
                "." + domain
            ):
                return display_name

            if domain in hostname:
                return display_name

        return None

    def _is_allowed_url(
        self,
        url: str,
    ) -> bool:

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
        Open an intermediary/quality page and extract
        only configured allowed file-host links.

        If section is supplied, extracted links receive
        that quality section.

        For normal Server links, section is intentionally
        left empty so they remain under All Cloud Links.
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

        # -------------------------------------------------
        # Check final URL after redirects
        # -------------------------------------------------

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

        # -------------------------------------------------
        # Extract normal <a href=""> links
        # -------------------------------------------------

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

    def _extract_quality_links(
        self,
        movie_url: str,
        soup,
        seen_final_urls: set,
    ) -> list[dict]:
        """
        Detect clickable quality links directly from
        the movie page.

        Example:

        720P 10Bit HEVC LINK
                ↓
        https://howblogs.xyz/e31cd0
                ↓
        allowed file-share links

        The extracted file links are assigned to the
        original quality text.
        """

        quality_links = []

        for link in soup.find_all(
            "a",
            href=True,
        ):

            quality_text = self._clean_text(
                link.get_text(
                    " ",
                    strip=True,
                )
            )

            if not quality_text:
                continue

            if not self._is_quality_text(
                quality_text
            ):
                continue

            href = link.get(
                "href",
                "",
            ).strip()

            if not href:
                continue

            quality_url = urljoin(
                movie_url,
                href,
            )

            # Do not treat a direct file-host URL
            # as a quality intermediary page.
            if self._is_allowed_url(
                quality_url
            ):
                continue

            try:
                extracted_links = (
                    self._extract_allowed_links(
                        quality_url,
                        section=quality_text,
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

                final_host = self._clean_host(
                    urlparse(
                        url
                    ).netloc
                )

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
                    "section": quality_text,
                }

                seen_final_urls.add(
                    url
                )

                quality_links.append(
                    result
                )

        return quality_links

    def get_download_links(
        self,
        movie_url: str,
    ) -> list[dict]:

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

        protected_host = self._clean_host(
            PROTECTED_LINK_DOMAIN
        )

        # =================================================
        # 1. QUALITY-SPECIFIC LINKS
        # =================================================

        quality_links = (
            self._extract_quality_links(
                movie_url,
                soup,
                seen_final_urls,
            )
        )

        final_links.extend(
            quality_links
        )

        # =================================================
        # 2. ALL OTHER LINKS ON MOVIE PAGE
        # =================================================

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
                movie_url,
                href,
            )

            parsed = urlparse(
                absolute_url
            )

            if parsed.scheme not in (
                "http",
                "https",
            ):
                continue

            # ---------------------------------------------
            # WATCH ONLINE
            # ---------------------------------------------

            if self._is_watch_online_url(
                absolute_url
            ):

                if absolute_url in seen_final_urls:
                    continue

                result = {
                    "url": absolute_url,
                    "host": "watch_online",
                    "section": "WATCH ONLINE",
                }

                seen_final_urls.add(
                    absolute_url
                )

                final_links.append(
                    result
                )

                continue

            hostname = self._clean_host(
                parsed.netloc
            )

            # ---------------------------------------------
            # Skip clickable quality links.
            #
            # They were already processed above.
            # ---------------------------------------------

            link_text = self._clean_text(
                link.get_text(
                    " ",
                    strip=True,
                )
            )

            if self._is_quality_text(
                link_text
            ):
                continue

            # ---------------------------------------------
            # Only process configured protected/server
            # intermediary links.
            # ---------------------------------------------

            if hostname != protected_host:
                continue

            if absolute_url in seen_intermediary_urls:
                continue

            seen_intermediary_urls.add(
                absolute_url
            )

            # -------------------------------------------------
            # IMPORTANT:
            #
            # Normal Server 01 / Server 02 / Server 03...
            # links MUST NOT inherit a quality section.
            #
            # Previously _find_quality_section() was used here.
            # That caused texts such as:
            #
            # WATCH ONLINE
            # SERVER 01
            # SERVER 02
            # 1080P 10Bit HEVC LINK
            #
            # to get mixed into the section detection.
            #
            # These normal server links belong to
            # All Cloud Links.
            # -------------------------------------------------

            try:
                extracted_links = (
                    self._extract_allowed_links(
                        absolute_url,
                        section=None,
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

                final_host = self._clean_host(
                    urlparse(
                        url
                    ).netloc
                )

                # Never return the protected server itself.
                if final_host == protected_host:
                    continue

                display_name = (
                    self._get_allowed_host_name(
                        final_host
                    )
                )

                if not display_name:
                    continue

                # -------------------------------------------------
                # NO SECTION HERE.
                #
                # This guarantees that normal Server links
                # go to All Cloud Links in Publisher.py.
                # -------------------------------------------------

                result = {
                    "url": url,
                    "host": display_name,
                }

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
