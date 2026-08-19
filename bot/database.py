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

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_url TEXT NOT NULL UNIQUE,
                    title TEXT,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            conn.commit()

    @staticmethod
    def _normalize_url(url: str) -> str:
        return url.strip()

    @staticmethod
    def _get_host(url: str) -> str:
        parsed = urlparse(url)

        host = parsed.netloc.lower()

        if host.startswith("www."):
            host = host[4:]

        return host

    # --------------------------------------------------
    # SOURCE POST TRACKING
    # --------------------------------------------------

    def post_exists(self, post_url: str) -> bool:
        """
        Check whether this exact source website post
        has already been successfully processed.

        This is completely separate from download-link
        duplicate detection.
        """

        post_url = self._normalize_url(post_url)

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
        Mark a source website post as successfully
        processed.

        Returns:
            True  -> newly saved
            False -> already existed
        """

        post_url = self._normalize_url(post_url)

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

    # --------------------------------------------------
    # DOWNLOAD LINK TRACKING
    # --------------------------------------------------

    def link_exists(self, url: str) -> bool:
        """
        Check whether this download/protected URL
        has ever been seen before.
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

        Link duplicate detection is based ONLY on
        the download URL.

        A previously seen link does NOT mean that a
        new source post should be ignored.
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
        Save previously unseen download links.

        This method is for link history only.
        It must NOT be used to decide whether a
        source website post is new.
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
