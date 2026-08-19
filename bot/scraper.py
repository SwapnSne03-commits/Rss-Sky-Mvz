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

    def _get_allowed_host_name(
        self,
        hostname: str,
    ) -> str | None:
        """
        Return the configured display name if the hostname
        belongs to one of our allowed file hosts.
        """

        hostname = self._clean_host(hostname)

        if not hostname:
            return None

        for domain, display_name in ALLOWED_HOSTS.items():

            domain = self._clean_host(domain)

            # Exact match.
            if hostname == domain:
                return display_name

            # Support subdomains such as:
            # dl.gofile.io
            # www.hubcloud.example
            if hostname.endswith("." + domain):
                return display_name

            # Some configured hosts may be partial identifiers,
            # such as "hubcloud" or "gdflix".
            if domain in hostname:
                return display_name

        return None

    def _is_allowed_url(
        self,
        url: str,
    ) -> bool:
        """
        Check whether a URL belongs to one of the allowed
        final file-host services.
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
            self._get_allowed_host_name(hostname)
            is not None
        )

    def _extract_allowed_links(
        self,
        page_url: str,
    ) -> list[dict]:
        """
        Open an intermediary page and extract only
        explicitly allowed final file-host links.

        The intermediary URL itself is NEVER returned.
        """

        html = self.fetch(page_url)

        soup = BeautifulSoup(
            html,
            "lxml",
        )

        links = []
        seen_urls = set()

        # First check the final URL after normal HTTP redirects.
        try:
            response = self.session.get(
                page_url,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
            )

            final_url = response.url

            if self._is_allowed_url(final_url):
                host = self._clean_host(
                    urlparse(final_url).netloc
                )

                display_name = (
                    self._get_allowed_host_name(host)
                    or host
                )

                links.append(
                    {
                        "url": final_url,
                        "host": display_name,
                    }
                )

                seen_urls.add(final_url)

        except requests.RequestException:
            pass

        # Extract normal <a href="..."> links from the
        # intermediary page.
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

            seen_urls.add(
                absolute_url
            )

            links.append(
                {
                    "url": absolute_url,
                    "host": display_name,
                }
            )

        return links

    def get_download_links(
        self,
        movie_url: str,
    ) -> list[dict]:
        """
        Find all available intermediary/server links
        from a movie page and extract only the allowed
        final file-host links from them.

        IMPORTANT:
        howblogs.xyz links themselves are never returned.
        """

        html = self.fetch(movie_url)

        soup = BeautifulSoup(
            html,
            "lxml",
        )

        final_links = []
        seen_final_urls = set()
        seen_intermediary_urls = set()

        movie_host = self._clean_host(
            urlparse(movie_url).netloc
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

            try:
                extracted_links = (
                    self._extract_allowed_links(
                        intermediary_url
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
                    urlparse(url).netloc
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

                seen_final_urls.add(url)

                final_links.append(
                    {
                        "url": url,
                        "host": display_name,
                    }
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
            urlparse(SITE_URL).netloc
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
            if "/movie/" not in parsed_url.path.lower():
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
