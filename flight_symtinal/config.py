"""Shared configuration values for the project."""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PRICES_CSV = DATA_DIR / "prices.csv"
ALERT_STATE_JSON = DATA_DIR / "alert_state.json"
ALERT_COOLDOWN_HOURS = 24

if load_dotenv is not None:
    load_dotenv(BASE_DIR / ".env")


def get_telegram_bot_token() -> str:
    """Read the Telegram bot token from the current environment."""
    return os.getenv("TELEGRAM_BOT_TOKEN", "").strip()


def get_telegram_chat_id() -> str:
    """Read the Telegram chat ID from the current environment."""
    return os.getenv("TELEGRAM_CHAT_ID", "").strip()
