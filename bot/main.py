import logging
import threading
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

        self.telegram_app = (
            Application.builder()
            .token(BOT_TOKEN)
            .build()
        )

        self.search_cache = {}

        self._register_handlers()

    @staticmethod
    def is_admin(
        update: Update,
    ) -> bool:

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
                "Failed to authorize Sky Search group: %s",
                chat.id,
            )

            if update.effective_message:
                await update.effective_message.reply_text(
                    "❌ Failed to authorize this group.\n"
                    "Please try again later."
                )

            return

        if not update.effective_message:
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
                "ℹ️ This group is already authorized "
                "for Sky Search."
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
                "Failed to remove Sky Search authorization: %s",
                chat.id,
            )

            if update.effective_message:
                await update.effective_message.reply_text(
                    "❌ Failed to remove this group's "
                    "Sky Search authorization.\n"
                    "Please try again later."
                )

            return

        if not update.effective_message:
            return

        if removed:

            await update.effective_message.reply_text(
                "✅ <b>Sky Search Authorization Removed</b>\n\n"
                "This group can no longer use "
                "<code>/sky_search</code>.",
                parse_mode="HTML",
            )

        else:

            await update.effective_message.reply_text(
                "ℹ️ This group was not authorized "
                "for Sky Search."
            )

    async def cmd_sky_search(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:

        if not self.is_sky_group_authorized(update):

            if update.effective_message:
                await update.effective_message.reply_text(
                    "⛔ This group is not authorized "
                    "to use Sky Search."
                )

            return

        if not update.effective_message:
            return

        keyword = " ".join(
            context.args
        ).strip()

        if not keyword:
            await update.effective_message.reply_text(
                "Usage:\n"
                "/sky_search movie name"
            )
            return

        await update.effective_message.reply_text(
            f"🔎 Searching for: {keyword}"
        )

        try:
            results = (
                self.scraper.search_movies(
                    keyword
                )
            )

        except Exception:
            logger.exception(
                "Sky Movies search failed: %s",
                keyword,
            )

            await update.effective_message.reply_text(
                "❌ Search failed.\n"
                "Please try again later."
            )

            return

        if not results:

            await update.effective_message.reply_text(
                (
                    "❌ No results found for:\n"
                    f"<code>"
                    f"{self.publisher._escape_html(keyword)}"
                    f"</code>"
                ),
                parse_mode="HTML",
            )

            return

        search_id = uuid.uuid4().hex[:12]

        self.search_cache[search_id] = {
            "results": results,
            "chat_id": update.effective_chat.id,
            "user_id": update.effective_user.id,
        }

        keyboard = []

        for index, result in enumerate(
            results,
            start=1,
        ):

            title = result.get(
                "title",
                "",
            ).strip()

            if not title:
                continue

            callback_data = (
                f"sky:{search_id}:{index - 1}"
            )

            keyboard.append(
                [
                    InlineKeyboardButton(
                        title,
                        callback_data=callback_data,
                    )
                ]
            )

        if not keyboard:

            await update.effective_message.reply_text(
                "❌ No valid results found."
            )

            return

        text = (
            "🔎 <b>Sky Movies Search</b>\n\n"
            f"Keyword: <code>"
            f"{self.publisher._escape_html(keyword)}"
            f"</code>\n\n"
            "Select a movie:"
        )

        await update.effective_message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                keyboard
            ),
        )

        logger.info(
            "Sky Search completed: %s | Results: %d",
            keyword,
            len(keyboard),
        )

    async def cb_sky_movie(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:

        query = update.callback_query

        if not query:
            return

        await query.answer()

        data = query.data or ""

        parts = data.split(":")

        if len(parts) != 3:
            return

        _, search_id, index_text = parts

        cached = self.search_cache.get(
            search_id
        )

        if not cached:
            await query.answer(
                "This search result has expired.",
                show_alert=True,
            )
            return

        try:
            index = int(index_text)
        except ValueError:
            return

        results = cached.get(
            "results",
            []
        )

        if index < 0 or index >= len(results):
            return

        result = results[index]

        title = result.get(
            "title",
            "",
        ).strip()

        movie_url = result.get(
            "url",
            "",
        ).strip()

        if not title or not movie_url:
            await query.answer(
                "Movie data is unavailable.",
                show_alert=True,
            )
            return

        if query.message:
            await query.message.reply_text(
                f"⏳ Getting links for:\n"
                f"<b>{self.publisher._escape_html(title)}</b>",
                parse_mode="HTML",
            )

        logger.info(
            "Sky Search movie selected: %s",
            movie_url,
        )

        try:
            download_links = (
                self.scraper.get_download_links(
                    movie_url
                )
            )

        except Exception:
            logger.exception(
                "Failed to extract movie links: %s",
                movie_url,
            )

            if query.message:
                await query.message.reply_text(
                    "❌ Failed to get movie links.\n"
                    "Please try again later."
                )

            return

        if not download_links:

            if query.message:
                await query.message.reply_text(
                    "❌ No allowed download links found."
                )

            return

        try:
            message = (
                self.publisher.build_links_message(
                    title=title,
                    download_links=download_links,
                )
            )

        except Exception:
            logger.exception(
                "Failed to build links message: %s",
                movie_url,
            )

            if query.message:
                await query.message.reply_text(
                    "❌ Failed to prepare movie links."
                )

            return

        if query.message:
            await query.message.reply_text(
                message,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )

        logger.info(
            "Sky Search movie links sent: %s",
            title,
        )

    def _register_handlers(
        self,
    ) -> None:

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
                self.cb_sky_movie,
                pattern=r"^sky:",
            )
        )

    def process_cycle(
        self,
    ) -> int:

        logger.info(
            "Starting website check..."
        )

        try:
            posts = (
                self.scraper.get_latest_posts()
            )

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
                saved = (
                    self.database.save_post(
                        post_url=movie_url,
                        title=title,
                    )
                )

            except Exception:
                logger.exception(
                    "Failed to record source post: %s",
                    movie_url,
                )
                continue

            if saved:
                successfully_published += 1

        logger.info(
            "Cycle completed. Successfully published: %d",
            successfully_published,
        )

        return successfully_published

    def run(self):
        logger.info("RSS-Sky-Mvz bot started.")
        logger.info(
            "Check interval: %d seconds",
            CHECK_INTERVAL,
        )

        def worker():
            while True:
                try:
                    self.process_cycle()
                except Exception:
                    logger.exception(
                        "Unexpected error in processing cycle."
                    )

                time.sleep(CHECK_INTERVAL)

        threading.Thread(
            target=worker,
            daemon=True,
        ).start()

        self.telegram_app.run_polling()

def main():

    start_health_server()

    bot = RSSBot()

    bot.run()


if __name__ == "__main__":
    main()
