"""Load and validate route tracking configuration from JSON."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DatePair:
    """One departure/return date combination."""

    departure: str
    return_date: str
    target_price: int | None = None


@dataclass(frozen=True)
class RouteConfig:
    """One tracked route with many date combinations."""

    name: str
    origin: str
    destination: str
    date_pairs: list[DatePair]


@dataclass(frozen=True)
class AlertSettings:
    """Global alert settings loaded from the JSON config."""

    significant_drop_percent: int = 10


@dataclass(frozen=True)
class RouteFileConfig:
    """Parsed contents of the route configuration file."""

    routes: list[RouteConfig]
    alert_settings: AlertSettings


def load_route_config(config_path: Path) -> RouteFileConfig:
    """Load the JSON config file and validate its contents."""
    if not config_path.exists():
        raise FileNotFoundError(f"Route config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as file:
        raw: dict[str, Any] = json.load(file)

    routes = raw.get("routes")
    if not isinstance(routes, list) or not routes:
        raise ValueError("Config must contain a non-empty 'routes' list.")

    alert_settings = _parse_alert_settings(raw.get("alert_settings"))
    parsed_routes: list[RouteConfig] = []

    for index, item in enumerate(routes, start=1):
        parsed_routes.append(_parse_route(item, index))

    return RouteFileConfig(routes=parsed_routes, alert_settings=alert_settings)


def _parse_alert_settings(item: object) -> AlertSettings:
    """Read optional alert settings from the config file."""
    if item is None:
        return AlertSettings()

    if not isinstance(item, dict):
        raise ValueError("'alert_settings' must be a JSON object.")

    value = item.get("significant_drop_percent", 10)
    if not isinstance(value, int) or value <= 0 or value >= 100:
        raise ValueError(
            "'significant_drop_percent' must be an integer between 1 and 99."
        )

    return AlertSettings(significant_drop_percent=value)


def _parse_route(item: object, index: int) -> RouteConfig:
    """Validate one route entry from JSON."""
    if not isinstance(item, dict):
        raise ValueError(f"Route #{index} must be a JSON object.")

    name = _require_text(item, "name", index)
    origin = _require_text(item, "origin", index)
    destination = _require_text(item, "destination", index)

    date_pairs_raw = item.get("date_pairs")
    if not isinstance(date_pairs_raw, list) or len(date_pairs_raw) < 5:
        raise ValueError(
            f"Route '{name}' must contain at least 5 date_pairs entries."
        )

    date_pairs = [
        _parse_date_pair(pair, name, pair_index)
        for pair_index, pair in enumerate(date_pairs_raw, start=1)
    ]

    return RouteConfig(
        name=name,
        origin=origin,
        destination=destination,
        date_pairs=date_pairs,
    )


def _parse_date_pair(item: object, route_name: str, index: int) -> DatePair:
    """Validate one departure/return date pair."""
    if not isinstance(item, dict):
        raise ValueError(f"Date pair #{index} for '{route_name}' must be an object.")

    departure = _require_date(item, "departure", route_name, index)
    return_date = _require_date(item, "return", route_name, index)
    target_price = item.get("target_price")
    if target_price is not None and (not isinstance(target_price, int) or target_price <= 0):
        raise ValueError(
            f"Route '{route_name}' date pair #{index} has invalid 'target_price'. "
            "Use a positive integer or omit the field."
        )

    if return_date <= departure:
        raise ValueError(
            f"Route '{route_name}' date pair #{index} has return date before departure date."
        )

    return DatePair(
        departure=departure.isoformat(),
        return_date=return_date.isoformat(),
        target_price=target_price,
    )


def _require_text(item: dict[str, object], key: str, index: int) -> str:
    """Read a required non-empty text field."""
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Route #{index} is missing a valid '{key}' value.")
    return value.strip()


def _require_date(
    item: dict[str, object],
    key: str,
    route_name: str,
    index: int,
) -> date:
    """Read and validate a date in YYYY-MM-DD format."""
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Route '{route_name}' date pair #{index} is missing '{key}'.")

    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(
            f"Route '{route_name}' date pair #{index} has invalid '{key}' date: {value!r}. "
            "Use YYYY-MM-DD."
        ) from exc
