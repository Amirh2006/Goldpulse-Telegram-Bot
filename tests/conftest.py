"""Pytest fixtures and shared helpers for GoldPulse Bot tests."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from goldpulse_bot.api_client import GoldApiClient, GoldPrice
from goldpulse_bot.config import load_settings
from goldpulse_bot.database import AsyncSubscriberDatabase


@pytest.fixture
def event_loop_policy():
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def valid_price() -> GoldPrice:
    """A fully populated, valid gold price matching the real API schema."""
    return GoldPrice(
        price=4025.5,
        symbol="XAU",
        currency="USD",
        currency_symbol="$",
        updated_at=None,
        updated_at_readable="a few seconds ago",
    )


@pytest.fixture
def api_client() -> GoldApiClient:
    return GoldApiClient(base_url="https://api.gold-api.com/price/XAU", timeout=5.0)


@pytest.fixture
def tmp_db(tmp_path) -> AsyncSubscriberDatabase:
    db = AsyncSubscriberDatabase(str(tmp_path / "test_subscribers.sqlite"))
    yield db
    # close happens via to_thread; SQLite file removed with tmp_path


@pytest.fixture
def mock_bot() -> MagicMock:
    bot = MagicMock()
    bot.send_message = AsyncMock()
    return bot


@pytest.fixture
def mock_application(mock_bot) -> MagicMock:
    app = MagicMock()
    app.bot = mock_bot
    app.bot_data = {}
    jq = MagicMock()
    jq.get_jobs_by_name.return_value = []
    app.job_queue = jq
    return app


@pytest.fixture
def patched_client():
    """Patch GoldApiClient.fetch_gold_price so tests control API results."""
    with patch(
        "goldpulse_bot.api_client.GoldApiClient.fetch_gold_price", new_callable=AsyncMock
    ) as mock:
        yield mock


@pytest.fixture
def settings(tmp_path):
    env_file = None
    with patch(
        "goldpulse_bot.config.os.getenv",
        side_effect=lambda key, default=None: {
            "TELEGRAM_BOT_TOKEN": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            "DATABASE_PATH": str(tmp_path / "cfg_test.sqlite"),
        }.get(key, default),
    ):
        yield load_settings(env_file=None)


def run_async(coro):
    """Helper to run an async coroutine in a sync test."""
    return asyncio.run(coro)
