"""Application entry point for Flight Symtinal."""

import sys

from flight_symtinal.alerts.telegram_bot import build_summary_message, send_telegram_message
from flight_symtinal.alerts.telegram_commands import run_telegram_polling
from flight_symtinal.config import (
    BASE_DIR,
    PRICES_CSV,
    get_telegram_bot_token,
    get_telegram_chat_id,
)
from flight_symtinal.core.analytics import format_summary, load_price_history, summarize_prices
from flight_symtinal.route_config import load_route_config
from flight_symtinal.tracking import run_tracking


ROUTE_CONFIG_PATH = BASE_DIR / "flight_symtinal" / "flight_routes.json"


def main() -> None:
    """Run configured flight tracking, then print or send a summary."""
    command = sys.argv[1] if len(sys.argv) > 1 else "run"
    bot_token = get_telegram_bot_token()
    chat_id = get_telegram_chat_id()

    if command == "telegram-test":
        send_telegram_message(
            bot_token,
            chat_id,
            "Flight Symtinal test message.",
        )
        print("Telegram test message sent.")
        return

    route_file_config = load_route_config(ROUTE_CONFIG_PATH)

    if command == "telegram-poll":
        run_telegram_polling(
            bot_token=bot_token,
            chat_id=chat_id,
            csv_path=PRICES_CSV,
            route_config=route_file_config,
        )
        return

    run_tracking(
        route_file_config.routes,
        PRICES_CSV,
        route_file_config.alert_settings.significant_drop_percent,
    )

    records = load_price_history(PRICES_CSV)
    if not records:
        print(f"No price history found at {PRICES_CSV}.")
        return

    route = records[-1].route or "Unknown route"
    summary = summarize_prices(records)
    summary_text = format_summary(route, summary)

    if command == "telegram-summary":
        message = build_summary_message(route, summary_text)
        send_telegram_message(bot_token, chat_id, message)
        print("Telegram summary sent.")
        return

    print(summary_text)


if __name__ == "__main__":
    main()
