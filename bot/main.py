import logging
import time
import uuid

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
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

        self.search_results = {}

        self.telegram_app = (
            Application.builder()
            .token(BOT_TOKEN)
            .build()
        )

        self._register_handlers()

    # =====================================================
    # ADMIN AUTHORIZATION
    # =====================================================

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

    # =====================================================
    # GROUP AUTHORIZATION
    # =====================================================

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

    # =====================================================
    # SKY ADD
    # =====================================================

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

    # =====================================================
    # SKY REMOVE
    # =====================================================

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
                "Failed to remove Sky Search group: %s",
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

    # =====================================================
    # SKY SEARCH
    # =====================================================

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

        logger.info(
            "Sky Search requested: %s",
            keyword,
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

        result_id = uuid.uuid4().hex

        self.search_results[result_id] = {
            "chat_id": update.effective_chat.id,
            "user_id": update.effective_user.id,
            "keyword": keyword,
            "results": results,
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
                f"skyselect:{result_id}:{index - 1}"
            )

            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"{index}. {title[:50]}",
                        callback_data=callback_data,
                    )
                ]
            )

        if not keyboard:

            await update.effective_message.reply_text(
                "❌ No valid results found."
            )

            self.search_results.pop(
                result_id,
                None,
            )

            return

        text = (
            "🔎 <b>Sky Movies Search</b>\n\n"
            "Keyword: "
            f"<code>"
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
            "Sky Search results sent: %s | Results: %d",
            keyword,
            len(keyboard),
        )

    # =====================================================
    # SKY SEARCH RESULT CALLBACK
    # =====================================================

    async def callback_sky_select(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:

        query = update.callback_query

        if not query:
            return

        await query.answer()

        user = update.effective_user
        chat = update.effective_chat

        if not user or not chat:
            return

        if chat.type not in (
            "group",
            "supergroup",
        ):

            await query.answer(
                "This action is only available in groups.",
                show_alert=True,
            )

            return

        if not self.database.is_group_authorized(
            chat.id
        ):

            await query.answer(
                "This group is not authorized.",
                show_alert=True,
            )

            return

        data = query.data or ""

        if not data.startswith(
            "skyselect:"
        ):
            return

        parts = data.split(
            ":",
            2,
        )

        if len(parts) != 3:
            return

        result_id = parts[1]
        index_text = parts[2]

        try:
            index = int(
                index_text
            )

        except ValueError:
            await query.answer(
                "Invalid selection.",
                show_alert=True,
            )
            return

        search_data = self.search_results.get(
            result_id
        )

        if not search_data:

            await query.answer(
                "This search result has expired.",
                show_alert=True,
            )

            return

        if search_data.get(
            "chat_id"
        ) != chat.id:

            await query.answer(
                "This result belongs to another chat.",
                show_alert=True,
            )

            return

        results = search_data.get(
            "results",
            [],
        )

        if index < 0 or index >= len(results):

            await query.answer(
                "Invalid movie selection.",
                show_alert=True,
            )

            return

        selected_movie = results[index]

        title = selected_movie.get(
            "title",
            "",
        ).strip()

        movie_url = selected_movie.get(
            "url",
            "",
        ).strip()

        if not title or not movie_url:

            await query.answer(
                "Movie information is unavailable.",
                show_alert=True,
            )

            return

        logger.info(
            "Sky Search movie selected: %s | %s",
            title,
            movie_url,
        )

        if query.message:

            await query.message.edit_text(
                (
                    "🎬 <b>Selected Movie</b>\n\n"
                    f"<b>{self.publisher._escape_html(title)}</b>\n\n"
                    "⏳ Extracting available links..."
                ),
                parse_mode="HTML",
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
                await query.message.edit_text(
                    (
                        "❌ Failed to extract links.\n"
                        "Please try again later."
                    )
                )

            return

        if not download_links:

            if query.message:
                await query.message.edit_text(
                    (
                        "❌ No allowed download links "
                        "were found for this movie."
                    )
                )

            return

        logger.info(
            "Movie link extraction completed: %s | Links: %d",
            title,
            len(download_links),
        )

        if query.message:

            await query.message.edit_text(
                (
                    "✅ <b>Movie Selected</b>\n\n"
                    f"<b>{self.publisher._escape_html(title)}</b>\n\n"
                    f"Found <b>{len(download_links)}</b> "
                    "available links."
                ),
                parse_mode="HTML",
            )

        self.search_results.pop(
            result_id,
            None,
        )

    # =====================================================
    # COMMAND REGISTRATION
    # =====================================================

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
                self.callback_sky_select,
                pattern=r"^skyselect:",
            )
        )

    # =====================================================
    # WEBSITE PROCESSING
    # =====================================================

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

            if not result.get(
                "ok"
            ):

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

                saved = (
                    self.database.save_post(
                        post_url=movie_url,
                        title=title,
                    )
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
            "Cycle completed. "
            "Successfully published: %d",
            successfully_published,
        )

        return successfully_published

    # =====================================================
    # BOT RUNNER
    # =====================================================

    def run(
        self,
    ):

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
