"""Track configured flight searches and save each price to CSV."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from flight_symtinal.alerts.alert_manager import (
    evaluate_alerts,
    filter_unsent_alerts,
    load_alert_state,
    record_sent_alert,
    save_alert_state,
)
from flight_symtinal.alerts.telegram_bot import send_telegram_message
from flight_symtinal.config import (
    ALERT_STATE_JSON,
    PRICES_CSV,
    get_telegram_bot_token,
    get_telegram_chat_id,
)
from flight_symtinal.core.analytics import load_price_history
from flight_symtinal.route_config import RouteConfig
from flight_symtinal.scraper.flight_scraper import scrape_flight_price
from flight_symtinal.storage.csv_store import append_price_row


@dataclass(frozen=True)
class TrackedSearchResult:
    """A single route/date run and its scraped price."""

    route_name: str
    departure: str
    return_date: str
    price: int


def run_tracking(
    routes: list[RouteConfig],
    csv_path: Path = PRICES_CSV,
    significant_drop_percent: int = 10,
) -> list[TrackedSearchResult]:
    """Scrape every configured date pair and append each result to CSV."""
    results: list[TrackedSearchResult] = []

    for route in routes:
        for date_pair in route.date_pairs:
            result = scrape_and_store(
                route,
                date_pair.departure,
                date_pair.return_date,
                csv_path,
                date_pair.target_price,
                significant_drop_percent,
            )
            results.append(result)

    return results


def scrape_and_store(
    route: RouteConfig,
    departure: str,
    return_date: str,
    csv_path: Path,
    target_price: int | None = None,
    significant_drop_percent: int = 10,
) -> TrackedSearchResult:
    """Scrape one configured search and store the result in the CSV file."""
    route_label = format_route_label(route.name, departure, return_date)
    previous_prices = [
        record.price
        for record in load_price_history(csv_path)
        if record.route == route_label
    ]

    flight_result = scrape_flight_price(route.origin, route.destination, departure, return_date)
    append_price_row(csv_path, route_label, flight_result.price)
    _send_route_alerts(
        route_label=route_label,
        current_price=flight_result.price,
        previous_prices=previous_prices,
        target_price=target_price,
        significant_drop_percent=significant_drop_percent,
    )

    return TrackedSearchResult(
        route_name=route.name,
        departure=departure,
        return_date=return_date,
        price=flight_result.price,
    )


def format_route_label(route_name: str, departure: str, return_date: str) -> str:
    """Create a clear route label for analytics and CSV history."""
    return f"{route_name} | {departure} -> {return_date}"


def _send_route_alerts(
    *,
    route_label: str,
    current_price: int,
    previous_prices: list[int],
    target_price: int | None,
    significant_drop_percent: int,
) -> None:
    """Evaluate alerts, suppress duplicates, and send Telegram messages."""
    bot_token = get_telegram_bot_token()
    chat_id = get_telegram_chat_id()
    state = load_alert_state(ALERT_STATE_JSON)
    alerts = evaluate_alerts(
        route_label=route_label,
        current_price=current_price,
        previous_prices=previous_prices,
        target_price=target_price,
        significant_drop_percent=significant_drop_percent,
    )
    pending_alerts = filter_unsent_alerts(state, alerts)

    for alert in pending_alerts:
        send_telegram_message(
            bot_token,
            chat_id,
            alert.message,
        )
        record_sent_alert(state, alert)

    save_alert_state(ALERT_STATE_JSON, state)
