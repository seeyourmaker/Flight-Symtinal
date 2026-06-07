"""Playwright scraper for configured flight itineraries."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote_plus

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


@dataclass(frozen=True)
class FlightResult:
    """One scraped flight price result."""

    route: str
    price: int


def parse_price(raw_text: str) -> int:
    """Convert a price string like '₹12,345' into an integer."""
    digits = "".join(character for character in raw_text if character.isdigit())

    if not digits:
        raise ValueError(f"Could not find a price in: {raw_text!r}")

    return int(digits)


def build_search_url(origin: str, destination: str, departure: str, return_date: str) -> str:
    """Create a Google Flights search URL for one round trip."""
    query = f"Flights from {origin} to {destination} {departure} {return_date}"
    return f"https://www.google.com/travel/flights?q={quote_plus(query)}"


def scrape_flight_price(origin: str, destination: str, departure: str, return_date: str) -> FlightResult:
    """Open the search page and try to read the first visible price."""
    search_url = build_search_url(origin, destination, departure, return_date)

    selectors_to_try = [
        "[aria-label*='₹']",
        "text=₹",
        "span",
    ]

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(search_url, wait_until="domcontentloaded", timeout=60_000)

        price_text = None
        for selector in selectors_to_try:
            try:
                locator = page.locator(selector).first
                locator.wait_for(state="visible", timeout=10_000)
                candidate = locator.text_content() or ""
                if "₹" in candidate or any(char.isdigit() for char in candidate):
                    price_text = candidate
                    break
            except PlaywrightTimeoutError:
                continue

        browser.close()

    if not price_text:
        raise RuntimeError("Could not find a visible price on the page.")

    route_label = f"{origin} -> {destination} | {departure} -> {return_date}"
    return FlightResult(route=route_label, price=parse_price(price_text))
