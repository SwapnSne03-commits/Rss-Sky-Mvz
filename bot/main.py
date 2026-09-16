import logging
import time

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from .health import start_health_server
from .config import (
    ADMIN_IDS,
    BOT_TOKEN,
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

        # Telegram command application.
        self.telegram_app = (
            Application.builder()
            .token(BOT_TOKEN)
            .build()
        )

        self._register_handlers()

    # =====================================================
    # ADMIN AUTHORIZATION FOUNDATION
    # =====================================================

    @staticmethod
    def is_admin(
        update: Update,
    ) -> bool:
        """
        Check whether the Telegram user is an authorized admin.
        """

        user = update.effective_user

        if not user:
            return False

        return user.id in ADMIN_IDS

    async def unauthorized(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """
        Common response for unauthorized users.

        This will be used by future admin commands.
        """

        if update.effective_message:
            await update.effective_message.reply_text(
                "⛔ You are not authorized to use this command."
            )

    # =====================================================
    # COMMAND REGISTRATION
    # =====================================================

    def _register_handlers(self) -> None:
        """
        Register Telegram command handlers.

        Actual admin commands will be added step by step.
        """

        # Foundation placeholder.
        #
        # Future examples:
        #
        # self.telegram_app.add_handler(
        #     CommandHandler("status", self.cmd_status)
        # )
        #
        # self.telegram_app.add_handler(
        #     CommandHandler("pause", self.cmd_pause)
        # )

    # =====================================================
    # WEBSITE PROCESSING
    # =====================================================

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

        Download-link history is NOT used to decide
        whether a source post should be published.
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
    # BOT RUNNER
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
