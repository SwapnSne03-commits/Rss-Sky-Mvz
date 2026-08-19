from bot.publisher import TelegramPublisher


def main():
    publisher = TelegramPublisher()

    print("Testing Telegram publisher...")
    print()

    result = publisher.send_message(
        "RSS-Sky-Mvz Telegram publisher test."
    )

    message = result.get(
        "result",
        {},
    )

    print("Message sent successfully.")
    print(
        f"Message ID: {message.get('message_id')}"
    )


if __name__ == "__main__":
    main()
