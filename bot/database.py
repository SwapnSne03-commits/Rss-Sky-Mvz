import sqlite3
from pathlib import Path

from .config import DATABASE_PATH


class Database:
    def __init__(
        self,
        db_path: str = DATABASE_PATH,
    ):
        self.db_path = db_path

        Path(
            self.db_path
        ).parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._create_tables()

    def _connect(self):
        return sqlite3.connect(
            self.db_path
        )

    def _create_tables(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_url TEXT NOT NULL UNIQUE,
                    title TEXT,
                    created_at TIMESTAMP
                        DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            conn.commit()

    @staticmethod
    def _normalize_url(
        url: str,
    ) -> str:
        return url.strip()

    def post_exists(
        self,
        post_url: str,
    ) -> bool:
        """
        Check whether this exact website
        source post has already been published.

        IMPORTANT:
        Duplicate detection is based ONLY
        on the source post URL.

        Movie title and download links are
        NOT used for duplicate detection.
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

            return (
                cursor.fetchone()
                is not None
            )

    def save_post(
        self,
        post_url: str,
        title: str = "",
    ) -> bool:
        """
        Record a successfully published
        source post.

        Returns:

        True
            New source post saved.

        False
            Source post already existed.
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
                    title.strip(),
                ),
            )

            conn.commit()

            return cursor.rowcount == 1
