import os

from dotenv import load_dotenv


load_dotenv()


BOT_TOKEN = os.getenv(
    "BOT_TOKEN",
    "",
).strip()

CHANNEL_ID = os.getenv(
    "CHANNEL_ID",
    "",
).strip()


SITE_URL = os.getenv(
    "SITE_URL",
    "https://skymovieshd.forex",
).rstrip("/")


CHECK_INTERVAL = int(
    os.getenv(
        "CHECK_INTERVAL",
        "120",
    )
)


REQUEST_TIMEOUT = int(
    os.getenv(
        "REQUEST_TIMEOUT",
        "20",
    )
)


# GitHub repository used for persistent
# source-post tracking.
GITHUB_TOKEN = os.getenv(
    "GITHUB_TOKEN",
    "",
).strip()

GITHUB_REPOSITORY = os.getenv(
    "GITHUB_REPOSITORY",
    "",
).strip()

GITHUB_STATE_FILE = os.getenv(
    "GITHUB_STATE_FILE",
    "data/processed_posts.json",
).strip()


# Protected-link/intermediary service
# used by the website.
PROTECTED_LINK_DOMAIN = "howblogs.xyz"


# Only these file-hosts should finally
# appear in Telegram.
ALLOWED_HOSTS = {
    "gofile.io": "Gofile",
    "vikingfile.com": "VikingFile",
    "hubcloud": "HubCloud",
    "gdflix": "GDFLIX",
    "drivehub": "DriveHub",
    "multicloud": "MultiCloud",
    "hubdrive": "HubDrive",
}


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


def validate_config() -> None:
    """Validate required environment variables."""

    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN is missing from the environment."
        )

    if not CHANNEL_ID:
        raise RuntimeError(
            "CHANNEL_ID is missing from the environment."
        )

    if not GITHUB_TOKEN:
        raise RuntimeError(
            "GITHUB_TOKEN is missing from the environment."
        )

    if not GITHUB_REPOSITORY:
        raise RuntimeError(
            "GITHUB_REPOSITORY is missing from the environment."
        )
