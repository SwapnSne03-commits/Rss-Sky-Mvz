from datetime import datetime, timezone
from email.utils import format_datetime
from xml.etree.ElementTree import Element, SubElement, ElementTree
import hashlib

from .config import SITE_URL


FEED_TITLE = "Latest Posts"
FEED_DESCRIPTION = "Latest posts from our website"
FEED_FILE = "rss.xml"

MAX_ITEMS = 50


def _get_link_url(link) -> str:
    """
    Return the URL from either a string or link dictionary.
    """

    if isinstance(link, dict):
        return link.get(
            "url",
            "",
        ).strip()

    return str(link).strip()


def _get_link_host(link) -> str:
    """
    Return the host from a link dictionary.
    """

    if isinstance(link, dict):
        return link.get(
            "host",
            "",
        ).strip()

    return ""


def build_rss(
    posts: list[dict],
    output_file: str = FEED_FILE,
) -> int:
    """
    Build an RSS feed from already-scraped posts.

    IMPORTANT:
    This function does NOT scrape the website and does
    NOT perform database duplicate detection.

    Source-post duplicate detection is handled by main.py.
    """

    rss = Element(
        "rss",
        {
            "version": "2.0",
        },
    )

    channel = SubElement(
        rss,
        "channel",
    )

    SubElement(
        channel,
        "title",
    ).text = FEED_TITLE

    SubElement(
        channel,
        "link",
    ).text = SITE_URL

    SubElement(
        channel,
        "description",
    ).text = FEED_DESCRIPTION

    SubElement(
        channel,
        "language",
    ).text = "en"

    now = datetime.now(timezone.utc)

    SubElement(
        channel,
        "lastBuildDate",
    ).text = format_datetime(now)

    item_count = 0

    for post in posts:

        if item_count >= MAX_ITEMS:
            break

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

        if not movie_url:
            continue

        if not download_links:
            continue

        link_urls = []

        description_lines = [
            f"Movie URL: {movie_url}",
            "",
            "Download/Protected Links:",
        ]

        for index, link in enumerate(
            download_links,
            start=1,
        ):

            url = _get_link_url(link)

            if not url:
                continue

            host = _get_link_host(link)

            link_urls.append(url)

            description_lines.append(
                f"{index}. {url}"
            )

            if host:
                description_lines.append(
                    f"   Host: {host}"
                )

        if not link_urls:
            continue

        description = "\n".join(
            description_lines
        )

        # GUID is based on the SOURCE POST URL.
        #
        # Therefore:
        #
        # Same source post → same GUID
        # New source post → new GUID
        #
        # Even if the movie/download links are identical.
        guid = hashlib.sha256(
            movie_url.encode("utf-8")
        ).hexdigest()

        item = SubElement(
            channel,
            "item",
        )

        SubElement(
            item,
            "title",
        ).text = title

        SubElement(
            item,
            "link",
        ).text = movie_url

        SubElement(
            item,
            "guid",
        ).text = guid

        SubElement(
            item,
            "description",
        ).text = description

        SubElement(
            item,
            "pubDate",
        ).text = format_datetime(now)

        item_count += 1

    tree = ElementTree(rss)

    tree.write(
        output_file,
        encoding="utf-8",
        xml_declaration=True,
    )

    return item_count


if __name__ == "__main__":
    print(
        "rss.py is a library module."
    )
    print(
        "Use build_rss(posts) from the main runner."
        )
