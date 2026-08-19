import logging
import time

from .config import (
    CHECK_INTERVAL,
    validate_config,
)
from .database import Database
from .publisher import TelegramPublisher
from .rss import build_rss
from .scraper import WebsiteScraper


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

    def process_cycle(self) -> int:
        """
        Run one complete website-check cycle.

        Workflow:

        1. Scrape the website once.
        2. Ignore source posts already processed.
        3. Publish each new source post to Telegram.
        4. Build RSS from successfully published posts.
        5. Mark the source post as processed only after
           successful Telegram publishing.
        """

        logger.info(
            "Starting website check..."
        )

        try:
            posts = self.scraper.get_latest_posts()
        except Exception:
            logger.exception(
                "Failed to scrape website."
            )
            return 0

        logger.info(
            "Found %d source posts.",
            len(posts),
        )

        new_posts = []

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

            # Source-post duplicate detection.
            #
            # This checks ONLY the exact source post URL.
            #
            # It does NOT check:
            # - movie title
            # - movie name
            # - download links
            #
            # Therefore a new website post for the same movie
            # can still be published.
            if self.database.post_exists(
                movie_url
            ):
                logger.info(
                    "Already processed source post: %s",
                    movie_url,
                )
                continue

            if not download_links:
                logger.info(
                    "No download links found: %s",
                    movie_url,
                )
                continue

            new_posts.append(
                post
            )

        if not new_posts:
            logger.info(
                "No new source posts found."
            )
            return 0

        logger.info(
            "New source posts to process: %d",
            len(new_posts),
        )

        successfully_published = []

        for post in new_posts:

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

            logger.info(
                "Publishing: %s",
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

                # Do NOT mark the source post as processed.
                #
                # It will be retried during the next cycle.
                continue

            if not result.get("ok"):
                logger.error(
                    "Telegram API returned failure: %s",
                    movie_url,
                )
                continue

            logger.info(
                "Telegram publishing successful: %s",
                title,
            )

            successfully_published.append(
                post
            )

        if not successfully_published:
            logger.info(
                "No posts were successfully published."
            )
            return 0

        # Build RSS from posts that were successfully
        # accepted by Telegram.
        try:
            rss_count = build_rss(
                successfully_published,
            )

            logger.info(
                "RSS generated successfully. Items: %d",
                rss_count,
            )

        except Exception:
            logger.exception(
                "RSS generation failed."
            )

        # Mark source posts as processed.
        #
        # This happens after Telegram publishing.
        for post in successfully_published:

            title = post.get(
                "title",
                "",
            ).strip()

            movie_url = post.get(
                "url",
                "",
            ).strip()

            saved = self.database.save_post(
                post_url=movie_url,
                title=title,
            )

            if saved:
                logger.info(
                    "Source post recorded: %s",
                    movie_url,
                )
            else:
                logger.warning(
                    "Source post was already recorded: %s",
                    movie_url,
                )

        return len(
            successfully_published
        )

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
                self.process_cycle()

            except Exception:
                logger.exception(
                    "Unexpected error in processing cycle."
                )

            logger.info(
                "Sleeping for %d seconds...",
                CHECK_INTERVAL,
            )

            time.sleep(
                CHECK_INTERVAL
            )


def main():
    bot = RSSBot()
    bot.run()


if __name__ == "__main__":
    main()
