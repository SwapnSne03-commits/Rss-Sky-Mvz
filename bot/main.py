import logging
import time

from .config import (
    CHECK_INTERVAL,
    validate_config,
)
from .database import Database
from .publisher import TelegramPublisher
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

        Rules:

        1. Scan the website.
        2. Detect only previously unprocessed source posts.
        3. Extract the allowed final file-host links.
        4. Publish every new source post to Telegram.
        5. Mark the source post as processed only after
           successful Telegram publishing.

        IMPORTANT:

        Download-link history is NOT used to decide whether
        a source post should be published.

        Therefore:

        Same movie + same links + NEW source post
        = NEW Telegram post.

        Only the exact same already-processed source post
        is ignored on the next polling cycle.
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

            # --------------------------------------------------
            # SOURCE POST DUPLICATE CHECK ONLY
            # --------------------------------------------------
            #
            # We deliberately do NOT check:
            #
            # - movie title
            # - movie name
            # - download links
            # - file-host URLs
            #
            # A genuinely new source post must be published
            # even when every link is identical to an older post.
            #

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
                    "No allowed file-host links found: %s",
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

        successfully_published = 0

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
                "Publishing new source post: %s",
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

                # Do NOT mark this source post as processed.
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

            # --------------------------------------------------
            # MARK SOURCE POST AS PROCESSED
            # --------------------------------------------------
            #
            # This happens ONLY after Telegram accepted the post.
            #

            try:
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
                    logger.info(
                        "Source post was already recorded: %s",
                        movie_url,
                    )

            except Exception:
                logger.exception(
                    "Failed to record source post: %s",
                    movie_url,
                )

                # Telegram has already received the post,
                # so we count it as published.
                #
                # The database failure will be retried on the
                # next cycle, which may cause a duplicate Telegram
                # post if the database remains unavailable.
                continue

            successfully_published += 1

        logger.info(
            "Cycle completed. Successfully published: %d",
            successfully_published,
        )

        return successfully_published

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
