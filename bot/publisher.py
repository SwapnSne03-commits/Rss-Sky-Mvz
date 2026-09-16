import requests

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
        chat_id=None,
        reply_markup=None,
    ) -> dict:

        self._check_config()

        if chat_id is None:
            chat_id = self.channel_id

        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        if reply_markup is not None:
            data["reply_markup"] = reply_markup

        response = requests.post(
            self._api_url("sendMessage"),
            data=data,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        result = response.json()

        if not result.get("ok"):
            raise RuntimeError(
                f"Telegram API error: {result}"
            )

        return result

    def build_links_message(
        self,
        title: str,
        download_links: list[dict] | None = None,
    ) -> str:

        title = title.strip()
        download_links = download_links or []

        gofile_url = ""
        other_gofile_links = []
        cloud_links = []
        quality_sections = {}
        watch_online_links = []

        seen_urls = set()

        for link in download_links:

            if not isinstance(link, dict):
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

            if not url or url in seen_urls:
                continue

            seen_urls.add(url)

            if host == "gofile":

                if not gofile_url:
                    gofile_url = url
                else:
                    other_gofile_links.append(url)

                continue

            if (
                host == "watch_online"
                or section.upper() == "WATCH ONLINE"
            ):
                watch_online_links.append(url)
                continue

            if section:

                quality_sections.setdefault(
                    section,
                    [],
                ).append(url)

                continue

            cloud_links.append(url)

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
                        "• <b>"
                        f"{self._escape_html(gofile_url)}"
                        "</b>"
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
                            f"    {index}. <b>"
                            f"{self._escape_html(url)}"
                            "</b>"
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
                        "</b>"
                    )
                )

        for section, urls in quality_sections.items():

            if not urls:
                continue

            lines.extend(
                [
                    "",
                    (
                        "<b>"
                        f"{self._escape_html(section)}"
                        "</b>"
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
                        "</b>"
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
                        "</b>"
                    )
                )

        return "\n".join(lines)

    def publish_post(
        self,
        title: str,
        movie_url: str,
        download_links: list[dict] | None = None,
    ) -> dict:

        message = self.build_links_message(
            title=title,
            download_links=download_links,
        )

        return self.send_message(
            message
                    )
