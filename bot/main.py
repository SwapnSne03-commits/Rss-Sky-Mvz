import time
import logging

from .config import (
    CHECK_INTERVAL,
    validate_config,
)
from .database import Database
from .scraper import WebsiteScraper
from .publisher import TelegramPublisher


logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(message)s"
    ),
)

logger = logging.getLogger(__name__)


class RSSBot:
    def __init__(self):
        validate_config()

        self.scraper = WebsiteScraper()
        self.database = Database()
        self.publisher = TelegramPublisher()

    def process_posts(self) -> int:
        """
        Check the website and publish newly discovered
        source posts to Telegram.

        A source post is marked as processed only after
        Telegram publishing succeeds.
        """

        logger.info(
            "Checking website for new posts..."
        )

        posts = self.scraper.get_latest_posts()

        logger.info(
            "Found %d movie posts on website.",
            len(posts),
        )

        published_count = 0

        for post in posts:
            title = post.get(
                "title",
                "",
            ).strip()

            movie_url = post.get(
                "url",
                "",
            ).strip()

            download_links = post.get(
                "download_links",
                [],
            )

            if not movie_url:
                continue

            # Check the SOURCE POST, not the movie title
            # and not the download links.
            if self.database.post_exists(
                movie_url
            ):
                logger.info(
                    "Already processed: %s",
                    movie_url,
                )
                continue

            if not download_links:
                logger.info(
                    "No download links found: %s",
                    movie_url,
                )
                continue

            logger.info(
                "New source post found: %s",
                title,
            )

            try:
                result = self.publisher.publish_post(
                    title=title,
                    movie_url=movie_url,
                    download_links=download_links,
                )

            except Exception:
                logger.exception(
                    "Telegram publishing failed: %s",
                    movie_url,
                )

                # IMPORTANT:
                # Do NOT save the source post here.
                # It will be retried during the next cycle.
                continue

            if not result.get("ok"):
                logger.error(
                    "Telegram API returned failure: %s",
                    result,
                )
                continue

            # Only mark the SOURCE POST as processed
            # after Telegram successfully accepts it.
            saved = self.database.save_post(
                post_url=movie_url,
                title=title,
            )

            if saved:
                published_count += 1

                logger.info(
                    "Published successfully: %s",
                    title,
                )
            else:
                logger.warning(
                    "Post was published but could not "
                    "be recorded as processed: %s",
                    movie_url,
                )

        logger.info(
            "Cycle finished. Published: %d",
            published_count,
        )

        return published_count

    def run(self):
        logger.info(
            "RSS-Sky-Mvz bot started."
        )

        logger.info(
            "Check interval: %d seconds",
            CHECK_INTERVAL,
        )

        while True:
            try:
                self.process_posts()

            except Exception:
                logger.exception(
                    "Unexpected error during check cycle."
                )

            logger.info(
                "Sleeping for %d seconds...",
                CHECK_INTERVAL,
            )

            time.sleep(CHECK_INTERVAL)


def main():
    bot = RSSBot()
    bot.run()


if __name__ == "__main__":
    main()
