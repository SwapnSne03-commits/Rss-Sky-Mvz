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
        disable_web_page_preview: bool = False,
    ) -> dict:
        """
        Send a text message to the configured
        Telegram channel.

        Returns the Telegram API response.
        """

        self._check_config()

        if not text.strip():
            raise ValueError(
                "Telegram message cannot be empty."
            )

        response = requests.post(
            self._api_url("sendMessage"),
            data={
                "chat_id": self.channel_id,
                "text": text,
                "disable_web_page_preview": (
                    disable_web_page_preview
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
        """
        Publish one NEW source website post to Telegram.

        Duplicate source-post detection is handled by
        Database/main.py, not by this publisher.

        Each download link should contain:

            {
                "url": "...",
                "host": "..."
            }
        """

        title = title.strip()
        movie_url = movie_url.strip()

        download_links = download_links or []

        if not title:
            raise ValueError(
                "Post title cannot be empty."
            )

        if not movie_url:
            raise ValueError(
                "Movie URL cannot be empty."
            )

        lines = [
            title,
            "",
            f"Movie URL: {movie_url}",
        ]

        valid_links = []

        for link in download_links:

            if isinstance(link, dict):
                url = link.get(
                    "url",
                    "",
                ).strip()

                host = link.get(
                    "host",
                    "",
                ).strip()

            else:
                url = str(link).strip()
                host = ""

            if not url:
                continue

            valid_links.append(
                (
                    url,
                    host,
                )
            )

        if valid_links:
            lines.extend(
                [
                    "",
                    "Download/Protected Links:",
                ]
            )

            for index, (
                url,
                host,
            ) in enumerate(
                valid_links,
                start=1,
            ):

                lines.append(
                    f"{index}. {url}"
                )

                if host:
                    lines.append(
                        f"   Host: {host}"
                    )

        message = "\n".join(lines)

        return self.send_message(
            message,
            disable_web_page_preview=False,
        )
