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
        Publish a website post to Telegram.

        Each download link should contain:
            {
                "url": "...",
                "host": "..."
            }
        """

        title = title.strip()
        movie_url = movie_url.strip()

        download_links = download_links or []

        lines = [
            title,
            "",
            f"Movie URL: {movie_url}",
        ]

        if download_links:
            lines.extend(
                [
                    "",
                    "Download/Protected Links:",
                ]
            )

            for index, link in enumerate(
                download_links,
                start=1,
            ):
                url = link.get(
                    "url",
                    "",
                ).strip()

                host = link.get(
                    "host",
                    "",
                ).strip()

                if not url:
                    continue

                if host:
                    lines.append(
                        f"{index}. {url}"
                    )
                    lines.append(
                        f"   Host: {host}"
                    )
                else:
                    lines.append(
                        f"{index}. {url}"
                    )

        message = "\n".join(lines)

        return self.send_message(
            message,
            disable_web_page_preview=False,
              )
