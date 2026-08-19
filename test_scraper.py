from bot.scraper import WebsiteScraper


def main():
    scraper = WebsiteScraper()

    print("Checking website...")
    print()

    posts = scraper.get_latest_posts()

    print(f"Found {len(posts)} links.")
    print()

    for index, post in enumerate(posts[:30], start=1):
        print(f"{index}. {post['title']}")
        print(f"   {post['url']}")
        print()


if __name__ == "__main__":
    main()
