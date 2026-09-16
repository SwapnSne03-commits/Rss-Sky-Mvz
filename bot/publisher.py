import requests

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .config import (
    BOT_TOKEN,
    CHANNEL_ID,
    REQUEST_TIMEOUT,
)


TELEGRAM_API_URL = (
    "https://api.telegram.org/bot{}/{}"
)


class TelegramPublisher:
    def __init__(
        self,
        bot_token: str = BOT_TOKEN,
        channel_id: str = CHANNEL_ID,
    ):
        self.bot_token = bot_token
        self.channel_id = channel_id

    def _api_url(self, method: str) -> str:
        return TELEGRAM_API_URL.format(
            self.bot_token,
            method,
        )

    def _check_config(self) -> None:
        if not self.bot_token:
            raise RuntimeError(
                "BOT_TOKEN is missing."
            )

        if not self.channel_id:
            raise RuntimeError(
                "CHANNEL_ID is missing."
            )

    @staticmethod
    def _escape_html(text: str) -> str:
        return (
            text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    def send_message(
        self,
        text: str,
    ) -> dict:

        self._check_config()

        response = requests.post(
            self._api_url("sendMessage"),
            data={
                "chat_id": self.channel_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        result = response.json()

        if not result.get("ok"):
            raise RuntimeError(
                f"Telegram API error: {result}"
            )

        return result

    def send_search_results(
        self,
        keyword: str,
        results: list[dict],
        callback_data: list[str],
    ) -> dict:

        self._check_config()

        keyword = keyword.strip()

        buttons = []

        for index, result in enumerate(
            results
        ):

            if index >= len(callback_data):
                break

            title = result.get(
                "title",
                "",
            ).strip()

            callback = callback_data[
                index
            ]

            if not title or not callback:
                continue

            buttons.append(
                [
                    InlineKeyboardButton(
                        text=title,
                        callback_data=callback,
                    )
                ]
            )

        if not buttons:
            raise ValueError(
                "No valid search results found."
            )

        text = (
            "🔎 <b>Results for "
            f"{self._escape_html(keyword)}:</b>"
        )

        response = requests.post(
            self._api_url("sendMessage"),
            data={
                "chat_id": self.channel_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
                "reply_markup": (
                    InlineKeyboardMarkup(
                        buttons
                    ).to_json()
                ),
            },
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        result = response.json()

        if not result.get("ok"):
            raise RuntimeError(
                f"Telegram API error: {result}"
            )

        return result

    def publish_post(
        self,
        title: str,
        movie_url: str,
        download_links: list[dict] | None = None,
    ) -> dict:

        title = title.strip()

        download_links = (
            download_links or []
        )

        gofile_url = ""
        other_gofile_links = []
        cloud_links = []
        quality_sections = {}
        watch_online_links = []

        seen_urls = set()

        for link in download_links:

            if not isinstance(
                link,
                dict,
            ):
                continue

            url = link.get(
                "url",
                "",
            ).strip()

            host = link.get(
                "host",
                "",
            ).strip().lower()

            section = link.get(
                "section",
                "",
            ).strip()

            if not url:
                continue

            if url in seen_urls:
                continue

            seen_urls.add(url)

            if host == "gofile":

                if not gofile_url:
                    gofile_url = url
                else:
                    other_gofile_links.append(
                        url
                    )

                continue

            if (
                host == "watch_online"
                or section.upper()
                == "WATCH ONLINE"
            ):

                watch_online_links.append(
                    url
                )

                continue

            if section:

                if section not in quality_sections:
                    quality_sections[
                        section
                    ] = []

                quality_sections[
                    section
                ].append(url)

                continue

            cloud_links.append(
                url
            )

        if (
            not gofile_url
            and not other_gofile_links
            and not cloud_links
            and not quality_sections
            and not watch_online_links
        ):
            raise ValueError(
                "No allowed file-host links found."
            )

        lines = [
            "<b>🎬 New Post Just Dropped! ✅</b>",
            "",
            (
                "<b>📌 Title :</b> "
                f"<code>"
                f"{self._escape_html(title)}"
                f"</code>"
            ),
        ]

        if gofile_url:

            lines.extend(
                [
                    "",
                    "<b>🔰 GoFile Link 🔰</b>",
                    (
                        "• "
                        f"<b>"
                        f"{self._escape_html(gofile_url)}"
                        f"</b>"
                    ),
                ]
            )

            if other_gofile_links:

                lines.append(
                    "  ↳ <b>Others Gofile Links</b>"
                )

                for index, url in enumerate(
                    other_gofile_links,
                    start=1,
                ):

                    lines.append(
                        (
                            f"    {index}. "
                            f"<b>"
                            f"{self._escape_html(url)}"
                            f"</b>"
                        )
                    )

        if cloud_links:

            lines.extend(
                [
                    "",
                    "<b>🍿 All Cloud Links 🍿</b>",
                ]
            )

            for index, url in enumerate(
                cloud_links,
                start=1,
            ):

                lines.append(
                    (
                        f"<b>{index}. "
                        f"{self._escape_html(url)}"
                        f"</b>"
                    )
                )

        for section, urls in quality_sections.items():

            if not urls:
                continue

            lines.extend(
                [
                    "",
                    (
                        f"<b>"
                        f"{self._escape_html(section)}"
                        f"</b>"
                    ),
                ]
            )

            for index, url in enumerate(
                urls,
                start=1,
            ):

                lines.append(
                    (
                        f"<b>{index}. "
                        f"{self._escape_html(url)}"
                        f"</b>"
                    )
                )

        if watch_online_links:

            lines.extend(
                [
                    "",
                    "<b>👀 WATCH ONLINE</b>",
                ]
            )

            for index, url in enumerate(
                watch_online_links,
                start=1,
            ):

                lines.append(
                    (
                        f"<b>{index}. "
                        f"{self._escape_html(url)}"
                        f"</b>"
                    )
                )

        message = "\n".join(
            lines
        )

        return self.send_message(
            message
                    )
