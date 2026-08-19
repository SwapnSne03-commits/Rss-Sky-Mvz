import sqlite3
from pathlib import Path

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

    def link_exists(self, url: str) -> bool:
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
        host: str,
        title: str = "",
        post_url: str = "",
    ) -> bool:
        """
        Save a new download link.

        Returns:
            True  -> link was new and saved
            False -> link already existed
        """

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
        links: list[dict],
        title: str = "",
        post_url: str = "",
    ) -> list[dict]:
        """
        Filter and save only previously unseen links.

        Each item in `links` should contain:
            {
                "url": "...",
                "host": "Gofile"
            }
        """

        new_links = []

        for item in links:
            url = item["url"]
            host = item["host"]

            if self.save_link(
                url=url,
                host=host,
                title=title,
                post_url=post_url,
            ):
                new_links.append(item)

        return new_links
