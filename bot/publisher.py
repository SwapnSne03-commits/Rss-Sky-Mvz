import html
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

    def publish_post(
        self,
        title: str,
        movie_url: str,
        download_links: list[dict] | None = None,
    ) -> dict:

        title = title.strip()
        download_links = download_links or []

        gofile_url = ""
        cloud_urls = []

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

            if not url:
                continue

            if url in seen_urls:
                continue

            seen_urls.add(url)

            if host == "gofile":
                if not gofile_url:
                    gofile_url = url
            else:
                cloud_urls.append(url)

        if not gofile_url and not cloud_urls:
            raise ValueError(
                "No allowed file-host links found."
            )

        safe_title = html.escape(title)

        lines = [
            "✅ <b>NEW FILE UPLOADED</b>",
            "",
            f"📌 <b>Title :-</b> <code>{safe_title}</code>",
        ]

        if gofile_url:
            lines.extend(
                [
                    "",
                    "🔰 <b>GoFile Link 🔰</b>",
                    f"• {gofile_url}",
                ]
            )

        if cloud_urls:
            lines.extend(
                [
                    "",
                    "🍿 <b>All Cloud Links 🍿</b>",
                ]
            )

            for index, url in enumerate(
                cloud_urls,
                start=1,
            ):
                lines.append(
                    f"{index}. {url}"
                )

        message = "\n".join(lines)

        return self.send_message(message)
