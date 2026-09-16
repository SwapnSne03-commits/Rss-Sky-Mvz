import logging
import time
import uuid

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
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
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


class RSSBot:
    def __init__(self):
        validate_config()

        self.scraper = WebsiteScraper()
        self.database = Database()
        self.publisher = TelegramPublisher()

        self.sky_search_cache = {}

        self.telegram_app = (
            Application.builder()
            .token(BOT_TOKEN)
            .build()
        )

        self._register_handlers()

    @staticmethod
    def is_admin(update: Update) -> bool:
        user = update.effective_user

        if not user:
            return False

        return user.id in ADMIN_IDS

    async def unauthorized(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:

        if update.effective_message:
            await update.effective_message.reply_text(
                "⛔ You are not authorized to use this command."
            )

    def is_group_chat(
        self,
        update: Update,
    ) -> bool:

        chat = update.effective_chat

        if not chat:
            return False

        return chat.type in (
            "group",
            "supergroup",
        )

    def is_sky_group_authorized(
        self,
        update: Update,
    ) -> bool:

        chat = update.effective_chat

        if not chat:
            return False

        if chat.type not in (
            "group",
            "supergroup",
        ):
            return False

        return self.database.is_group_authorized(
            chat.id
        )

    async def cmd_sky_add(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:

        if not self.is_admin(update):
            await self.unauthorized(
                update,
                context,
            )
            return

        if not self.is_group_chat(update):
            if update.effective_message:
                await update.effective_message.reply_text(
                    "⚠️ This command can only be used inside "
                    "a group or supergroup."
                )
            return

        chat = update.effective_chat

        if not chat:
            return

        try:
            added = (
                self.database.add_authorized_group(
                    chat.id
                )
            )

        except Exception:
            logger.exception(
                "Failed to authorize group."
            )

            await update.effective_message.reply_text(
                "❌ Failed to authorize this group."
            )

            return

        if added:
            await update.effective_message.reply_text(
                "✅ <b>Sky Search Authorized</b>\n\n"
                "This group can now use "
                "<code>/sky_search</code>.",
                parse_mode="HTML",
            )
        else:
            await update.effective_message.reply_text(
                "ℹ️ This group is already authorized."
            )

    async def cmd_sky_remove(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:

        if not self.is_admin(update):
            await self.unauthorized(
                update,
                context,
            )
            return

        if not self.is_group_chat(update):
            if update.effective_message:
                await update.effective_message.reply_text(
                    "⚠️ This command can only be used inside "
                    "a group or supergroup."
                )
            return

        chat = update.effective_chat

        if not chat:
            return

        try:
            removed = (
                self.database.remove_authorized_group(
                    chat.id
                )
            )

        except Exception:
            logger.exception(
                "Failed to remove group authorization."
            )

            await update.effective_message.reply_text(
                "❌ Failed to remove authorization."
            )

            return

        if removed:
            await update.effective_message.reply_text(
                "✅ <b>Sky Search Authorization Removed</b>",
                parse_mode="HTML",
            )
        else:
            await update.effective_message.reply_text(
                "ℹ️ This group was not authorized."
            )

    async def cmd_sky_search(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:

        if not self.is_sky_group_authorized(update):
            await update.effective_message.reply_text(
                "⛔ This group is not authorized "
                "to use Sky Search."
            )
            return

        keyword = " ".join(
            context.args
        ).strip()

        if not keyword:
            await update.effective_message.reply_text(
                "Usage:\n/sky_search movie name"
            )
            return

        await update.effective_message.reply_text(
            f"🔎 Searching for: {keyword}"
        )

        try:
            results = self.scraper.search_movies(
                keyword
            )

        except Exception:
            logger.exception(
                "Sky Movies search failed."
            )

            await update.effective_message.reply_text(
                "❌ Search failed.\n"
                "Please try again later."
            )
            return

        if not results:
            await update.effective_message.reply_text(
                "❌ No results found for:\n"
                f"<code>"
                f"{self.publisher._escape_html(keyword)}"
                f"</code>",
                parse_mode="HTML",
            )
            return

        callbacks = []

        for result in results:

            token = uuid.uuid4().hex[:16]

            self.sky_search_cache[
                token
            ] = {
                "chat_id": update.effective_chat.id,
                "title": result["title"],
                "url": result["url"],
            }

            callbacks.append(
                f"sky_movie:{token}"
            )

        if len(self.sky_search_cache) > 1000:
            self.sky_search_cache.clear()

        try:
            self.publisher.send_search_results(
                keyword=keyword,
                results=results,
                callback_data=callbacks,
            )

        except Exception:
            logger.exception(
                "Failed to send search results."
            )

            await update.effective_message.reply_text(
                "❌ Failed to send search results."
            )

    async def callback_sky_movie(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:

        query = update.callback_query

        if not query:
            return

        await query.answer(
            "Loading movie links..."
        )

        data = query.data or ""

        if not data.startswith(
            "sky_movie:"
        ):
            return

        token = data.split(
            ":",
            1,
        )[1]

        item = self.sky_search_cache.get(
            token
        )

        if not item:
            await query.message.reply_text(
                "❌ This search result has expired."
            )
            return

        chat = update.effective_chat

        if not chat:
            return

        if chat.id != item["chat_id"]:
            return

        if not self.database.is_group_authorized(
            chat.id
        ):
            await query.message.reply_text(
                "⛔ This group is no longer authorized."
            )
            return

        title = item["title"]
        movie_url = item["url"]

        try:
            links = self.scraper.get_download_links(
                movie_url
            )

        except Exception:
            logger.exception(
                "Failed to extract movie links."
            )

            await query.message.reply_text(
                "❌ Failed to get movie links.\n"
                "Please try again later."
            )
            return

        if not links:
            await query.message.reply_text(
                "❌ No allowed file-host links found."
            )
            return

        try:
            message = self.publisher.build_post_message(
                title=title,
                download_links=links,
            )

            self.publisher.send_to_chat(
                chat_id=chat.id,
                text=message,
            )

        except Exception:
            logger.exception(
                "Failed to send movie links."
            )

            await query.message.reply_text(
                "❌ Failed to send movie links."
            )

    def _register_handlers(self) -> None:

        self.telegram_app.add_handler(
            CommandHandler(
                "sky_add",
                self.cmd_sky_add,
            )
        )

        self.telegram_app.add_handler(
            CommandHandler(
                "sky_remove",
                self.cmd_sky_remove,
            )
        )

        self.telegram_app.add_handler(
            CommandHandler(
                "sky_search",
                self.cmd_sky_search,
            )
        )

        self.telegram_app.add_handler(
            CallbackQueryHandler(
                self.callback_sky_movie,
                pattern=r"^sky_movie:",
            )
        )

    def process_cycle(self) -> int:

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

        new_posts = []

        for post in posts:

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
                continue

            if not download_links:
                continue

            new_posts.append(post)

        if not new_posts:
            return 0

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
                continue

            try:
                saved = self.database.save_post(
                    post_url=movie_url,
                    title=title,
                )

            except Exception:
                logger.exception(
                    "Failed to record source post."
                )
                continue

            if saved:
                successfully_published += 1

        return successfully_published

    def run(self):

        logger.info(
            "RSS-Sky-Mvz bot started."
        )

        while True:

            try:
                self.process_cycle()

            except Exception:
                logger.exception(
                    "Unexpected processing error."
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
