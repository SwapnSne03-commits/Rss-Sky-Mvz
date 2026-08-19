from datetime import datetime, timezone
from email.utils import format_datetime
from xml.etree.ElementTree import Element, SubElement, ElementTree
import hashlib

from .config import SITE_URL
from .scraper import WebsiteScraper
from .database import Database


FEED_TITLE = "Latest Posts"
FEED_DESCRIPTION = "Latest posts from our website"
FEED_FILE = "rss.xml"

MAX_ITEMS = 50


def generate_rss(output_file: str = FEED_FILE) -> int:
    scraper = WebsiteScraper()
    database = Database()

    posts = scraper.get_latest_posts()

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

    SubElement(channel, "title").text = FEED_TITLE
    SubElement(channel, "link").text = SITE_URL
    SubElement(channel, "description").text = FEED_DESCRIPTION
    SubElement(channel, "language").text = "en"

    now = datetime.now(timezone.utc)

    SubElement(channel, "lastBuildDate").text = format_datetime(
        now
    )

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

        if not download_links:
            continue

        # Save newly discovered links to database.
        # Existing links are ignored by the database.
        database.get_new_links(
            download_links,
            title=title,
            post_url=movie_url,
        )

        # Convert link dictionaries into URL strings.
        link_urls = []

        for link in download_links:
            if isinstance(link, dict):
                url = link.get(
                    "url",
                    "",
                ).strip()
            else:
                url = str(link).strip()

            if url:
                link_urls.append(url)

        if not link_urls:
            continue

        description_lines = [
            f"Movie URL: {movie_url}",
            "",
            "Download/Protected Links:",
        ]

        for index, link in enumerate(
            download_links,
            start=1,
        ):
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

            description_lines.append(
                f"{index}. {url}"
            )

            if host:
                description_lines.append(
                    f"   Host: {host}"
                )

        description = "\n".join(
            description_lines
        )

        # Create a stable GUID based on the
        # movie URL and its download links.
        guid_source = (
            movie_url
            + "|"
            + "|".join(link_urls)
        )

        guid = hashlib.sha256(
            guid_source.encode("utf-8")
        ).hexdigest()

        item = SubElement(
            channel,
            "item",
        )

        SubElement(item, "title").text = title
        SubElement(item, "link").text = movie_url
        SubElement(item, "guid").text = guid
        SubElement(item, "description").text = description
        SubElement(item, "pubDate").text = format_datetime(
            now
        )

        item_count += 1

    tree = ElementTree(rss)

    tree.write(
        output_file,
        encoding="utf-8",
        xml_declaration=True,
    )

    return item_count


if __name__ == "__main__":
    count = generate_rss()

    print(
        f"RSS generated successfully: {count} items"
    )

    print(
        f"File: {FEED_FILE}"
        )
