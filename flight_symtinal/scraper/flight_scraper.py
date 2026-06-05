"""Playwright scraper for one fixed flight itinerary."""

from __future__ import annotations

from dataclasses import dataclass

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


def fetch_mumbai_guwahati_price() -> FlightResult:
    """Open the fixed search page and try to read the first visible price."""
    # This URL is a simple starting point for the fixed itinerary.
    # In a later phase we can replace it with a stronger, site-specific flow.
    search_url = (
        "https://www.google.com/travel/flights?"
        "q=Flights%20from%20Mumbai%20to%20Guwahati"
    )

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

    return FlightResult(route="Mumbai -> Guwahati", price=parse_price(price_text))

