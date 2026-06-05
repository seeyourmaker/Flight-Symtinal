"""Application entry point for Flight Symtinal."""

import sys

from flight_symtinal.alerts.telegram_bot import (
    build_summary_message,
    send_telegram_message,
)
from flight_symtinal.config import PRICES_CSV, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from flight_symtinal.core.analytics import (
    format_summary,
    load_price_history,
    summarize_prices,
)


def main() -> None:
    """Load the CSV history and print or send a price summary."""
    records = load_price_history(PRICES_CSV)

    if not records:
        print(f"No price history found at {PRICES_CSV}.")
        return

    route = records[-1].route or "Unknown route"
    summary = summarize_prices(records)
    summary_text = format_summary(route, summary)

    if len(sys.argv) > 1 and sys.argv[1] == "telegram-test":
        send_telegram_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, "Flight Symtinal test message.")
        print("Telegram test message sent.")
        return

    if len(sys.argv) > 1 and sys.argv[1] == "telegram-summary":
        message = build_summary_message(route, summary_text)
        send_telegram_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, message)
        print("Telegram summary sent.")
        return

    print(summary_text)


if __name__ == "__main__":
    main()
