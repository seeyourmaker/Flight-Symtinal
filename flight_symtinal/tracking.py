"""Track configured flight searches and save each price to CSV."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from flight_symtinal.config import PRICES_CSV
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


def run_tracking(routes: list[RouteConfig], csv_path: Path = PRICES_CSV) -> list[TrackedSearchResult]:
    """Scrape every configured date pair and append each result to CSV."""
    results: list[TrackedSearchResult] = []

    for route in routes:
        for date_pair in route.date_pairs:
            result = scrape_and_store(route, date_pair.departure, date_pair.return_date, csv_path)
            results.append(result)

    return results


def scrape_and_store(
    route: RouteConfig,
    departure: str,
    return_date: str,
    csv_path: Path,
) -> TrackedSearchResult:
    """Scrape one configured search and store the result in the CSV file."""
    flight_result = scrape_flight_price(route.origin, route.destination, departure, return_date)
    route_label = format_route_label(route.name, departure, return_date)
    append_price_row(csv_path, route_label, flight_result.price)

    return TrackedSearchResult(
        route_name=route.name,
        departure=departure,
        return_date=return_date,
        price=flight_result.price,
    )


def format_route_label(route_name: str, departure: str, return_date: str) -> str:
    """Create a clear route label for analytics and CSV history."""
    return f"{route_name} | {departure} -> {return_date}"
