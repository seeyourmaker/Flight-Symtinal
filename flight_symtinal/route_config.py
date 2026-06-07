"""Load and validate route tracking configuration from JSON."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


@dataclass(frozen=True)
class DatePair:
    """One departure/return date combination."""

    departure: str
    return_date: str


@dataclass(frozen=True)
class RouteConfig:
    """One tracked route with many date combinations."""

    name: str
    origin: str
    destination: str
    date_pairs: list[DatePair]


def load_route_config(config_path: Path) -> list[RouteConfig]:
    """Load the JSON config file and validate its contents."""
    if not config_path.exists():
        raise FileNotFoundError(f"Route config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as file:
        raw = json.load(file)

    routes = raw.get("routes")
    if not isinstance(routes, list) or not routes:
        raise ValueError("Config must contain a non-empty 'routes' list.")

    parsed_routes: list[RouteConfig] = []

    for index, item in enumerate(routes, start=1):
        parsed_routes.append(_parse_route(item, index))

    return parsed_routes


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

    date_pairs = [_parse_date_pair(pair, name, pair_index) for pair_index, pair in enumerate(date_pairs_raw, start=1)]

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

    if return_date <= departure:
        raise ValueError(
            f"Route '{route_name}' date pair #{index} has return date before departure date."
        )

    return DatePair(departure=departure.isoformat(), return_date=return_date.isoformat())


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

