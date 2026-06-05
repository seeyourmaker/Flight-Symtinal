"""Analytics helpers for flight price history."""

from __future__ import annotations

import csv
from dataclasses import dataclass
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

