import sqlite3
from pathlib import Path
from urllib.parse import urlparse

from .config import DATABASE_PATH


class Database:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path

        Path(db_path).parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._create_tables()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _create_tables(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL UNIQUE,
                    host TEXT NOT NULL,
                    first_seen_title TEXT,
                    first_seen_post TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            conn.commit()

    @staticmethod
    def _normalize_url(url: str) -> str:
        """
        Normalize a protected/download URL before storing
        and checking it.
        """

        return url.strip()

    @staticmethod
    def _get_host(url: str) -> str:
        """
        Extract hostname from a protected/download URL.
        """

        parsed = urlparse(url)

        host = parsed.netloc.lower()

        if host.startswith("www."):
            host = host[4:]

        return host

    def link_exists(self, url: str) -> bool:
        """
        Check whether this protected/download URL
        has already been seen.
        """

        url = self._normalize_url(url)

        if not url:
            return False

        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT 1
                FROM links
                WHERE url = ?
                LIMIT 1
                """,
                (url,),
            )

            return cursor.fetchone() is not None

    def save_link(
        self,
        url: str,
        host: str = "",
        title: str = "",
        post_url: str = "",
    ) -> bool:
        """
        Save a protected/download link.

        Duplicate detection is based ONLY on the
        protected/download URL.

        Returns:
            True  -> link was new and saved
            False -> link already existed
        """

        url = self._normalize_url(url)

        if not url:
            return False

        if not host:
            host = self._get_host(url)

        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO links
                (
                    url,
                    host,
                    first_seen_title,
                    first_seen_post
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    url,
                    host,
                    title,
                    post_url,
                ),
            )

            conn.commit()

            return cursor.rowcount == 1

    def get_new_links(
        self,
        links: list,
        title: str = "",
        post_url: str = "",
    ) -> list:
        """
        Filter and save only previously unseen
        protected/download links.

        The input can contain either:

            [
                "https://example.com/abc",
                "https://example.com/xyz"
            ]

        or:

            [
                {
                    "url": "https://example.com/abc",
                    "host": "example.com"
                }
            ]

        Returns the same type of item that was supplied.
        """

        new_links = []

        for item in links:

            if isinstance(item, str):
                url = item
                host = ""

            elif isinstance(item, dict):
                url = item.get("url", "")
                host = item.get("host", "")

            else:
                continue

            url = self._normalize_url(url)

            if not url:
                continue

            if self.save_link(
                url=url,
                host=host,
                title=title,
                post_url=post_url,
            ):
                new_links.append(item)

        return new_links
