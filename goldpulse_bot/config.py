"""Application configuration for GoldPulse Bot.

All configuration is read from environment variables. A ``.env`` file is used
for local development (see ``.env.example``). Secrets are never logged or
printed to the console.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - python-dotenv is a hard dependency
    load_dotenv = None  # type: ignore[assignment]


#: Primary gold price API endpoint (XAU is the ISO symbol for gold).
GOLD_API_URL = "https://api.gold-api.com/price/XAU"

#: Interval between scheduled price fetches, in seconds (120s = 2 minutes).
POLL_INTERVAL_SECONDS = 120

#: HTTP request timeout in seconds.
REQUEST_TIMEOUT_SECONDS = 20

#: Default path to the SQLite subscribers database.
DEFAULT_DATABASE_PATH = "goldpulse_subscribers.sqlite"


@dataclass(frozen=True)
class Settings:
    """Resolved runtime settings."""

    telegram_bot_token: str
    gold_api_url: str = GOLD_API_URL
    poll_interval_seconds: int = POLL_INTERVAL_SECONDS
    request_timeout_seconds: int = REQUEST_TIMEOUT_SECONDS
    database_path: str = DEFAULT_DATABASE_PATH
    log_level: str = "INFO"


def load_settings(env_file: Optional[str] = None) -> Settings:
    """Load settings from environment, optionally loading a ``.env`` file first.

    Raises:
        RuntimeError: if the required Telegram bot token is missing.
    """
    if load_dotenv is not None:
        load_dotenv(env_file, override=False)

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "Missing required configuration: TELEGRAM_BOT_TOKEN environment "
            "variable is not set. Copy .env.example to .env and add your bot "
            "token, then run the bot again."
        )

    def _int(name: str, default: int) -> int:
        try:
            return int(os.getenv(name, str(default)))
        except (TypeError, ValueError):
            return default

    return Settings(
        telegram_bot_token=token,
        gold_api_url=os.getenv("GOLD_API_URL", GOLD_API_URL).strip() or GOLD_API_URL,
        poll_interval_seconds=_int("POLL_INTERVAL_SECONDS", POLL_INTERVAL_SECONDS),
        request_timeout_seconds=_int("REQUEST_TIMEOUT_SECONDS", REQUEST_TIMEOUT_SECONDS),
        database_path=os.getenv("DATABASE_PATH", DEFAULT_DATABASE_PATH).strip()
        or DEFAULT_DATABASE_PATH,
        log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
    )
