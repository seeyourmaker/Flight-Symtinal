"""Telegram helpers for sending Flight Symtinal updates."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request


def build_summary_message(route: str, summary_text: str) -> str:
    """Combine a route name and analytics summary into one Telegram message."""
    return f"Flight update for {route}\n\n{summary_text}"


def send_telegram_message(bot_token: str, chat_id: str, message: str) -> None:
    """Send one plain text message using the Telegram Bot API."""
    if not bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN is missing.")

    if not chat_id:
        raise ValueError("TELEGRAM_CHAT_ID is missing.")

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": message,
        }
    ).encode("utf-8")

    request = urllib.request.Request(url, data=payload, method="POST")

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Telegram request failed: {exc}") from exc

    data = json.loads(body)
    if not data.get("ok"):
        raise RuntimeError(f"Telegram API returned an error: {data}")

