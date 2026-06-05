"""CSV storage helpers for flight price history."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path


CSV_HEADER = ["timestamp", "route", "price"]


def ensure_csv_file(csv_path: Path) -> None:
    """Create the CSV file and its parent folder if they do not exist."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    if not csv_path.exists():
        with csv_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(CSV_HEADER)


def append_price_row(csv_path: Path, route: str, price: int) -> None:
    """Append one price snapshot to the CSV history."""
    ensure_csv_file(csv_path)

    timestamp = datetime.now(timezone.utc).isoformat()

    with csv_path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, route, price])

