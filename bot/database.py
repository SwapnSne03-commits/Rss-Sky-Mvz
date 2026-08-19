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

            # Download/protected links table.
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

            # Source website posts table.
            #
            # IMPORTANT:
            # Duplicate detection for posts is based ONLY
            # on the exact source post URL.
            #
            # Therefore the same movie can be published again
            # when the website creates a new source post URL.
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_url TEXT NOT NULL UNIQUE,
                    title TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            conn.commit()

    def _normalize_url(self, url: str) -> str:
        return url.strip()

    @staticmethod
    def _get_host(url: str) -> str:
        parsed = urlparse(url)

        host = parsed.netloc.lower()

        if host.startswith("www."):
            host = host[4:]

        return host

    # ---------------------------------------------------------
    # SOURCE POST METHODS
    # ---------------------------------------------------------

    def post_exists(self, post_url: str) -> bool:
        """
        Check whether the exact source website post
        has already been processed.

        Duplicate detection is based ONLY on post_url.
        """

        post_url = self._normalize_url(
            post_url
        )

        if not post_url:
            return False

        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT 1
                FROM posts
                WHERE post_url = ?
                LIMIT 1
                """,
                (post_url,),
            )

            return cursor.fetchone() is not None

    def save_post(
        self,
        post_url: str,
        title: str = "",
    ) -> bool:
        """
        Save a successfully processed source post.

        Returns:
            True  -> new source post was saved
            False -> source post already existed
        """

        post_url = self._normalize_url(
            post_url
        )

        if not post_url:
            return False

        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO posts
                (
                    post_url,
                    title
                )
                VALUES (?, ?)
                """,
                (
                    post_url,
                    title,
                ),
            )

            conn.commit()

            return cursor.rowcount == 1

    # ---------------------------------------------------------
    # DOWNLOAD LINK METHODS
    # ---------------------------------------------------------

    def link_exists(self, url: str) -> bool:
        """
        Check whether a download/protected URL
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
        Save a download/protected link.

        Duplicate detection here applies ONLY to the
        download URL itself.
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
        Filter and save previously unseen download links.

        Supports both:

            "https://example.com/file"

        and:

            {
                "url": "https://example.com/file",
                "host": "example.com"
            }
        """

        new_links = []

        for item in links:

            if isinstance(item, str):
                url = item
                host = ""

            elif isinstance(item, dict):
                url = item.get(
                    "url",
                    "",
                )
                host = item.get(
                    "host",
                    "",
                )

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
