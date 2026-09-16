import logging
import time

from .health import start_health_server
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

        # -------------------------------------------------
        # AUTHORIZATION FOUNDATION
        # -------------------------------------------------
        #
        # Authorized groups will be stored here.
        #
        # The actual /sky_search handler will be added
        # in the next step.
        #

        self.authorized_groups = set()

        logger.info(
            "Authorization system initialized."
        )

    # =====================================================
    # AUTHORIZATION HELPERS
    # =====================================================

    def is_group_authorized(
        self,
        chat_id: int,
    ) -> bool:
        """
        Check whether a group is authorized
        to use Sky Search.
        """

        return chat_id in self.authorized_groups

    def authorize_group(
        self,
        chat_id: int,
    ) -> bool:
        """
        Authorize a group.

        Returns True when the group was newly added.
        Returns False if it was already authorized.
        """

        if chat_id in self.authorized_groups:
            return False

        self.authorized_groups.add(
            chat_id
        )

        logger.info(
            "Group authorized: %s",
            chat_id,
        )

        return True

    def unauthorize_group(
        self,
        chat_id: int,
    ) -> bool:
        """
        Remove a group from authorization.

        Returns True when removed.
        Returns False if the group was not authorized.
        """

        if chat_id not in self.authorized_groups:
            return False

        self.authorized_groups.remove(
            chat_id
        )

        logger.info(
            "Group authorization removed: %s",
            chat_id,
        )

        return True

    # =====================================================
    # SKY RSS
    # =====================================================

    def process_cycle(self) -> int:
        """
        Run one complete website-check cycle.

        Rules:

        1. Scan the website.
        2. Detect only previously unprocessed source posts.
        3. Extract allowed final file-host links.
        4. Publish every new source post to Telegram.
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

                result = (
                    self.publisher.publish_post(
                        title=title,
                        movie_url=movie_url,
                        download_links=download_links,
                    )
                )

            except Exception:

                logger.exception(
                    "Telegram publishing failed: %s",
                    movie_url,
                )

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

                continue

            successfully_published += 1

        logger.info(
            "Cycle completed. Successfully published: %d",
            successfully_published,
        )

        return successfully_published

    # =====================================================
    # MAIN LOOP
    # =====================================================

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

    start_health_server()

    bot = RSSBot()

    bot.run()


if __name__ == "__main__":
    main()
