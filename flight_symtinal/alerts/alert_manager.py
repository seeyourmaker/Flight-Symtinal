"""Smart alert evaluation and local alert state storage."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AlertEvent:
    """One alert that may be sent to Telegram."""

    alert_type: str
    route_label: str
    message: str
    signature: str


def load_alert_state(state_path: Path) -> dict[str, Any]:
    """Load alert history from disk."""
    if not state_path.exists():
        return {"routes": {}}

    with state_path.open("r", encoding="utf-8") as file:
        state = json.load(file)

    if not isinstance(state, dict):
        return {"routes": {}}

    state.setdefault("routes", {})
    return state


def save_alert_state(state_path: Path, state: dict[str, Any]) -> None:
    """Write alert history to disk."""
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with state_path.open("w", encoding="utf-8") as file:
        json.dump(state, file, indent=2, sort_keys=True)
        file.write("\n")


def evaluate_alerts(
    *,
    route_label: str,
    current_price: int,
    previous_prices: list[int],
    target_price: int | None,
    significant_drop_percent: int,
) -> list[AlertEvent]:
    """Build alert events for one route/date pair."""
    alerts: list[AlertEvent] = []

    if previous_prices:
        previous_low = min(previous_prices)
        if current_price < previous_low:
            alerts.append(
                AlertEvent(
                    alert_type="new_low",
                    route_label=route_label,
                    message=(
                        f"New low: {route_label}\n"
                        f"Price: {current_price}\n"
                        f"Previous low: {previous_low}"
                    ),
                    signature=f"new_low:{current_price}:{previous_low}",
                )
            )

        previous_price = previous_prices[-1]
        if _is_significant_drop(previous_price, current_price, significant_drop_percent):
            alerts.append(
                AlertEvent(
                    alert_type="significant_drop",
                    route_label=route_label,
                    message=(
                        f"Price drop: {route_label}\n"
                        f"Price: {current_price}\n"
                        f"Previous: {previous_price}\n"
                        f"Drop: {round(_drop_percent(previous_price, current_price), 1)}%"
                    ),
                    signature=f"significant_drop:{current_price}:{previous_price}:{significant_drop_percent}",
                )
            )

    if target_price is not None and current_price <= target_price:
        alerts.append(
            AlertEvent(
                alert_type="target_price",
                route_label=route_label,
                message=(
                    f"Target reached: {route_label}\n"
                    f"Price: {current_price}\n"
                    f"Target: {target_price}"
                ),
                signature=f"target_price:{current_price}:{target_price}",
            )
        )

    return alerts


def filter_unsent_alerts(
    state: dict[str, Any],
    alerts: list[AlertEvent],
    cooldown_hours: int = 24,
) -> list[AlertEvent]:
    """Suppress duplicate alerts and enforce cooldown windows."""
    now = datetime.now(timezone.utc)
    kept: list[AlertEvent] = []

    for alert in alerts:
        route_state = state.get("routes", {}).get(alert.route_label, {})
        alert_state = route_state.get(alert.alert_type, {})
        last_sent_at = alert_state.get("last_sent_at")
        last_signature = alert_state.get("last_signature")

        if last_sent_at:
            try:
                sent_at = datetime.fromisoformat(last_sent_at)
            except ValueError:
                sent_at = None
            if sent_at and now - sent_at < timedelta(hours=cooldown_hours):
                if last_signature == alert.signature:
                    continue
                continue

        if last_signature == alert.signature:
            continue

        kept.append(alert)

    return kept


def record_sent_alert(state: dict[str, Any], alert: AlertEvent) -> None:
    """Update state after an alert is sent."""
    routes = state.setdefault("routes", {})
    route_state = routes.setdefault(alert.route_label, {})
    route_state[alert.alert_type] = {
        "last_sent_at": datetime.now(timezone.utc).isoformat(),
        "last_signature": alert.signature,
    }


def _is_significant_drop(previous_price: int, current_price: int, threshold_percent: int) -> bool:
    """Check whether the current fare dropped by more than the configured threshold."""
    return _drop_percent(previous_price, current_price) > threshold_percent


def _drop_percent(previous_price: int, current_price: int) -> float:
    """Calculate the percentage drop from a previous fare."""
    if previous_price <= 0:
        return 0.0
    return ((previous_price - current_price) / previous_price) * 100
