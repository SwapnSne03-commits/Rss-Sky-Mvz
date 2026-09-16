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


# =====================================================
# ADMIN CONFIGURATION
# =====================================================

ADMIN_IDS = {
    int(user_id.strip())
    for user_id in os.getenv(
        "ADMIN_IDS",
        "",
    ).split(",")
    if user_id.strip().isdigit()
}


# =====================================================
# SKY RSS CONFIGURATION
# =====================================================

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


# =====================================================
# GITHUB PERSISTENT STATE
# =====================================================

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


# =====================================================
# SKY AUTHORIZED GROUPS
# =====================================================

SKY_AUTHORIZED_GROUPS_FILE = os.getenv(
    "SKY_AUTHORIZED_GROUPS_FILE",
    "data/sky_authorized_groups.json",
).strip()


# =====================================================
# PROTECTED LINK SERVICE
# =====================================================

PROTECTED_LINK_DOMAIN = "howblogs.xyz"


# =====================================================
# ALLOWED FILE HOSTS
# =====================================================

ALLOWED_HOSTS = {
    "gofile.io": "Gofile",
    "vikingfile.com": "VikingFile",
    "hubcloud": "HubCloud",
    "gdflix": "GDFLIX",
    "drivehub": "DriveHub",
    "multicloud": "MultiCloud",
    "hubdrive": "HubDrive",
}


# =====================================================
# HTTP USER AGENT
# =====================================================

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


# =====================================================
# CONFIG VALIDATION
# =====================================================

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

    if not ADMIN_IDS:
        raise RuntimeError(
            "ADMIN_IDS is missing or contains no valid Telegram user IDs."
        )

    if not GITHUB_TOKEN:
        raise RuntimeError(
            "GITHUB_TOKEN is missing from the environment."
        )

    if not GITHUB_REPOSITORY:
        raise RuntimeError(
            "GITHUB_REPOSITORY is missing from the environment."
        )
