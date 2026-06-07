"""Analytics helpers for flight price history."""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class PriceRecord:
    """One row from the price history CSV."""

    timestamp: str
    route: str
    price: int


@dataclass(frozen=True)
class PriceSummary:
    """Simple summary of one route's history."""

    current_price: int
    lowest_price: int
    highest_price: int
    average_price: float
    observations: int


@dataclass(frozen=True)
class RoutePriceSnapshot:
    """Aggregated analytics for one route/date combination."""

    route: str
    current_price: int
    lowest_price: int
    highest_price: int
    average_price: float
    observations: int
    last_seen: str


def load_price_history(csv_path: Path) -> list[PriceRecord]:
    """Read the CSV file and convert rows into PriceRecord objects."""
    if not csv_path.exists():
        return []

    records: list[PriceRecord] = []

    with csv_path.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            price_text = (row.get("price") or "").strip()
            if not price_text:
                continue

            records.append(
                PriceRecord(
                    timestamp=(row.get("timestamp") or "").strip(),
                    route=(row.get("route") or "").strip(),
                    price=int(price_text),
                )
            )

    return records


def summarize_prices(records: list[PriceRecord]) -> PriceSummary:
    """Calculate basic analytics for a list of price records."""
    if not records:
        raise ValueError("No price records available for analysis.")

    prices = [record.price for record in records]

    return PriceSummary(
        current_price=records[-1].price,
        lowest_price=min(prices),
        highest_price=max(prices),
        average_price=sum(prices) / len(prices),
        observations=len(records),
    )


def group_records_by_route(records: list[PriceRecord]) -> dict[str, list[PriceRecord]]:
    """Group all CSV rows by route label."""
    grouped: dict[str, list[PriceRecord]] = defaultdict(list)

    for record in records:
        grouped[record.route].append(record)

    return dict(grouped)


def summarize_route_records(route: str, records: list[PriceRecord]) -> RoutePriceSnapshot:
    """Calculate analytics for one route/date combination."""
    if not records:
        raise ValueError("No records available for route summary.")

    prices = [record.price for record in records]
    latest_record = records[-1]

    return RoutePriceSnapshot(
        route=route,
        current_price=latest_record.price,
        lowest_price=min(prices),
        highest_price=max(prices),
        average_price=sum(prices) / len(prices),
        observations=len(records),
        last_seen=latest_record.timestamp,
    )


def build_route_snapshots(records: list[PriceRecord]) -> list[RoutePriceSnapshot]:
    """Build analytics snapshots for every tracked route/date combination."""
    grouped = group_records_by_route(records)
    snapshots = [
        summarize_route_records(route, route_records)
        for route, route_records in grouped.items()
    ]
    return sorted(snapshots, key=lambda item: item.route)


def parse_timestamp(value: str) -> datetime | None:
    """Parse a CSV timestamp if possible."""
    if not value:
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def get_last_successful_run(records: list[PriceRecord]) -> str | None:
    """Return the most recent timestamp from the CSV."""
    parsed = [parse_timestamp(record.timestamp) for record in records]
    parsed = [item for item in parsed if item is not None]
    if not parsed:
        return None
    return max(parsed).astimezone(timezone.utc).isoformat()


def format_summary(route: str, summary: PriceSummary) -> str:
    """Create a readable terminal summary for one route."""
    return (
        f"Route: {route}\n"
        f"Current price: {summary.current_price}\n"
        f"Lowest price: {summary.lowest_price}\n"
        f"Highest price: {summary.highest_price}\n"
        f"Average price: {summary.average_price:.2f}\n"
        f"Observations: {summary.observations}"
    )
