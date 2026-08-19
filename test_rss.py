from bot.rss import generate_rss


def main():
    print("Generating RSS feed...")
    print()

    count = generate_rss("test_rss.xml")

    print()
    print(f"RSS generated successfully.")
    print(f"Items: {count}")
    print("File: test_rss.xml")


if __name__ == "__main__":
    main()
