"""Shared configuration values for the project."""

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PRICES_CSV = DATA_DIR / "prices.csv"
ALERT_STATE_JSON = DATA_DIR / "alert_state.json"
ALERT_COOLDOWN_HOURS = 24

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
