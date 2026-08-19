from bot.scraper import WebsiteScraper


def main():
    scraper = WebsiteScraper()

    print("Checking website...")
    print()

    posts = scraper.get_latest_posts()

    print(f"Found {len(posts)} links.")
    print()

    for index, post in enumerate(
        posts[:30],
        start=1,
    ):
        print(f"{index}. {post['title']}")
        print(f"   Movie URL: {post['url']}")

        download_links = post.get(
            "download_links",
            [],
        )

        if download_links:
            print("   Download/Protected Links:")

            for link_index, download_link in enumerate(
                download_links,
                start=1,
            ):
                print(
                    f"      {link_index}. {download_link}"
                )
        else:
            print(
                "   Download/Protected Links: None found"
            )

        print()
        print("-" * 70)
        print()


if __name__ == "__main__":
    main()
