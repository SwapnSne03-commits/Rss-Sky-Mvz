from datetime import datetime, timezone
from email.utils import format_datetime
from xml.etree.ElementTree import Element, SubElement, ElementTree

from .config import SITE_URL
from .scraper import WebsiteScraper


FEED_TITLE = "Latest Posts"
FEED_DESCRIPTION = "Latest posts from our website"
FEED_FILE = "rss.xml"

MAX_ITEMS = 50


def generate_rss(output_file: str = FEED_FILE) -> int:
    scraper = WebsiteScraper()
    posts = scraper.get_latest_posts()

    posts = posts[:MAX_ITEMS]

    rss = Element(
        "rss",
        {
            "version": "2.0",
        },
    )

    channel = SubElement(rss, "channel")

    SubElement(channel, "title").text = FEED_TITLE
    SubElement(channel, "link").text = SITE_URL
    SubElement(channel, "description").text = FEED_DESCRIPTION
    SubElement(channel, "language").text = "en"

    now = datetime.now(timezone.utc)
    SubElement(channel, "lastBuildDate").text = format_datetime(now)

    for post in posts:
        item = SubElement(channel, "item")

        title = post.get("title", "").strip()
        url = post.get("url", "").strip()

        SubElement(item, "title").text = title
        SubElement(item, "link").text = url
        SubElement(item, "guid").text = url
        SubElement(item, "description").text = title

    tree = ElementTree(rss)

    tree.write(
        output_file,
        encoding="utf-8",
        xml_declaration=True,
    )

    return len(posts)


if __name__ == "__main__":
    count = generate_rss()
    print(f"RSS generated successfully: {count} items")
    print(f"File: {FEED_FILE}")
