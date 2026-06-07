"""Telegram polling commands for Flight Symtinal."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from flight_symtinal.ai.advisor import BuyAdvice, RuleBasedAdviceProvider
from flight_symtinal.alerts.telegram_bot import send_telegram_message
from flight_symtinal.core.analytics import (
    build_route_snapshots,
    get_last_successful_run,
    load_price_history,
    summarize_route_records,
)
from flight_symtinal.route_config import RouteFileConfig


def run_telegram_polling(
    *,
    bot_token: str,
    chat_id: str,
    csv_path: Path,
    route_config: RouteFileConfig,
    poll_interval_seconds: int = 30,
) -> None:
    """Poll Telegram for incoming commands and respond in chat."""
    bot_token = bot_token.strip()
    chat_id = chat_id.strip()

    if not bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN is missing.")
    if not chat_id:
        raise ValueError("TELEGRAM_CHAT_ID is missing.")

    offset = 0

    while True:
        updates = _get_updates(bot_token, offset)

        for update in updates:
            offset = update["update_id"] + 1
            message = update.get("message", {})
            text = (message.get("text") or "").strip()
            incoming_chat_id = str(message.get("chat", {}).get("id", ""))

            if incoming_chat_id != chat_id:
                continue

            if not text.startswith("/"):
                continue

            response = handle_command(text, csv_path, route_config)
            send_telegram_message(bot_token, chat_id, response)

        time.sleep(poll_interval_seconds)


def handle_command(command_text: str, csv_path: Path, route_config: RouteFileConfig) -> str:
    """Return a text response for one Telegram command."""
    records = load_price_history(csv_path)
    snapshots = build_route_snapshots(records)
    command, *args = command_text.split(maxsplit=1)
    route_name = args[0].strip() if args else ""

    if command == "/help":
        return _help_text()

    if command == "/routes":
        return _routes_text(route_config)

    if command == "/current":
        return _current_text(snapshots)

    if command == "/lowest":
        return _lowest_text(snapshots)

    if command == "/targets":
        return _targets_text(route_config)

    if command == "/status":
        return _status_text(route_config, records)

    if command == "/route":
        return _route_text(route_name, route_config, records)

    if command == "/shouldibuy":
        return _should_i_buy_text(route_name, route_config, snapshots)

    return "Unknown command. Send /help for available commands."


def _help_text() -> str:
    """List all supported commands."""
    return (
        "Flight Symtinal commands\n"
        "/help - show commands\n"
        "/routes - list configured routes\n"
        "/current - latest fare for every route/date pair\n"
        "/lowest - lowest recorded fare for every route/date pair\n"
        "/targets - show configured target prices\n"
        "/status - show system status\n"
        "/route <name> - show details for one route\n"
        "/shouldibuy <route> - get a buy/wait/monitor recommendation"
    )


def _routes_text(route_config: RouteFileConfig) -> str:
    """List configured routes and date counts."""
    lines = ["Configured routes:"]
    for route in route_config.routes:
        lines.append(f"- {route.name}: {len(route.date_pairs)} date combinations")
    return "\n".join(lines)


def _current_text(snapshots) -> str:
    """Show the latest fare for each route/date pair."""
    if not snapshots:
        return "No price history yet."

    lines = ["Current fares:"]
    for snapshot in snapshots:
        lines.append(f"- {snapshot.route}: {snapshot.current_price}")
    return "\n".join(lines)


def _lowest_text(snapshots) -> str:
    """Show the lowest recorded fare for each route/date pair."""
    if not snapshots:
        return "No price history yet."

    lines = ["Lowest fares:"]
    for snapshot in snapshots:
        lines.append(f"- {snapshot.route}: {snapshot.lowest_price}")
    return "\n".join(lines)


def _targets_text(route_config: RouteFileConfig) -> str:
    """Show target prices from the JSON config."""
    lines = ["Target prices:"]
    for route in route_config.routes:
        for date_pair in route.date_pairs:
            label = f"{route.name} | {date_pair.departure} -> {date_pair.return_date}"
            target = date_pair.target_price if date_pair.target_price is not None else "not set"
            lines.append(f"- {label}: {target}")
    return "\n".join(lines)


def _status_text(route_config: RouteFileConfig, records) -> str:
    """Show high-level system status."""
    itineraries = sum(len(route.date_pairs) for route in route_config.routes)
    last_run = get_last_successful_run(records) or "unknown"
    return (
        "Status:\n"
        f"- routes: {len(route_config.routes)}\n"
        f"- tracked itineraries: {itineraries}\n"
        f"- CSV records: {len(records)}\n"
        f"- last successful run: {last_run}"
    )


def _route_text(route_name: str, route_config: RouteFileConfig, records) -> str:
    """Show detailed analytics for one configured route."""
    if not route_name:
        return "Use /route <name>. Example: /route Mumbai to Goa"

    selected = next((route for route in route_config.routes if route.name.lower() == route_name.lower()), None)
    if selected is None:
        return f"Route not found: {route_name}"

    route_records = [record for record in records if record.route.startswith(selected.name)]
    if not route_records:
        return f"No price history yet for {selected.name}."

    snapshot = summarize_route_records(selected.name, route_records)
    return (
        f"Route: {selected.name}\n"
        f"Current price: {snapshot.current_price}\n"
        f"Lowest price: {snapshot.lowest_price}\n"
        f"Highest price: {snapshot.highest_price}\n"
        f"Average price: {snapshot.average_price:.2f}\n"
        f"Observations: {snapshot.observations}"
    )


def _should_i_buy_text(route_name: str, route_config: RouteFileConfig, snapshots) -> str:
    """Return a recommendation for one route using existing analytics."""
    if not route_name:
        return "Use /shouldibuy <route>. Example: /shouldibuy Mumbai to Goa"

    selected = next(
        (route for route in route_config.routes if route.name.lower() == route_name.lower()),
        None,
    )
    if selected is None:
        return f"Route not found: {route_name}"

    route_snapshots = [snapshot for snapshot in snapshots if snapshot.route.startswith(selected.name)]
    if not route_snapshots:
        return f"No price history yet for {selected.name}."

    snapshot = max(route_snapshots, key=lambda item: item.last_seen)
    target_price = _find_target_price(selected, snapshot.route)

    provider = RuleBasedAdviceProvider()
    advice = provider.recommend(snapshot, target_price)
    return _format_advice(selected.name, snapshot.route, snapshot, target_price, advice)


def _get_updates(bot_token: str, offset: int) -> list[dict]:
    """Fetch pending Telegram updates using long polling."""
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    payload = urllib.parse.urlencode(
        {
            "timeout": 25,
            "offset": offset,
            "allowed_updates": json.dumps(["message"]),
        }
    ).encode("utf-8")

    request = urllib.request.Request(url, data=payload, method="POST")

    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            body = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Telegram polling failed: {exc}") from exc

    data = json.loads(body)
    if not data.get("ok"):
        raise RuntimeError(f"Telegram API returned an error: {data}")

    return data.get("result", [])


def _find_target_price(route, route_label: str) -> int | None:
    """Find the configured target price for a specific itinerary."""
    for date_pair in route.date_pairs:
        label = f"{route.name} | {date_pair.departure} -> {date_pair.return_date}"
        if label == route_label:
            return date_pair.target_price
    return None


def _format_advice(
    route_name: str,
    route_label: str,
    snapshot,
    target_price: int | None,
    advice: BuyAdvice,
) -> str:
    """Render a concise buy/wait/monitor answer."""
    target_text = str(target_price) if target_price is not None else "not set"
    return (
        f"{route_name}\n"
        f"Route: {route_label}\n"
        f"Recommendation: {advice.recommendation}\n"
        f"Reason: {advice.reasoning}\n"
        f"Current: {snapshot.current_price}\n"
        f"Lowest: {snapshot.lowest_price}\n"
        f"Highest: {snapshot.highest_price}\n"
        f"Average: {snapshot.average_price:.2f}\n"
        f"Observations: {snapshot.observations}\n"
        f"Target: {target_text}"
    )
