"""Tests for scheduled price-update notification logic."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from goldpulse_bot.api_client import GoldAPIError, GoldPrice
from goldpulse_bot.scheduler import (
    JOB_NAME,
    format_price_message,
    schedule_price_updates,
)


class TestFormatPriceMessage:
    def test_full_price(self):
        price = GoldPrice(
            price=4025.5,
            symbol="XAU",
            currency="USD",
            currency_symbol="$",
            updated_at=None,
            updated_at_readable="a few seconds ago",
        )
        msg = format_price_message(price)
        assert "Gold price (XAU): $4,025.50 USD" in msg

    def test_no_currency_symbol(self):
        price = GoldPrice(
            price=4025.5,
            symbol="XAU",
            currency="USD",
            currency_symbol=None,
            updated_at=None,
            updated_at_readable=None,
        )
        msg = format_price_message(price)
        assert "$" not in msg
        assert "4,025.50 USD" in msg

    def test_updated_at_formatted(self):
        from datetime import datetime, timezone

        price = GoldPrice(
            price=100,
            symbol="XAU",
            currency="USD",
            currency_symbol="$",
            updated_at=datetime(2026, 10, 23, 12, 3, 43, tzinfo=timezone.utc),
            updated_at_readable=None,
        )
        msg = format_price_message(price)
        assert "Updated: 2026-10-23 12:03:43 UTC" in msg


class TestSchedulePriceUpdatesIdempotent:
    def test_schedules_job_once(self, mock_application, monkeypatch):
        from goldpulse_bot.database import AsyncSubscriberDatabase

        client = MagicMock()
        database = MagicMock(spec=AsyncSubscriberDatabase)

        import asyncio

        asyncio.run(
            schedule_price_updates(mock_application, client, database, 120)
        )
        mock_application.job_queue.run_repeating.assert_called_once()
        kwargs = mock_application.job_queue.run_repeating.call_args.kwargs
        assert kwargs["name"] == JOB_NAME
        assert kwargs["interval"] == 120
        assert kwargs["first"] == 120

    def test_does_not_reschedule_existing_job(self, mock_application, monkeypatch):
        from goldpulse_bot.database import AsyncSubscriberDatabase

        existing = MagicMock()
        mock_application.job_queue.get_jobs_by_name.return_value = [existing]

        client = MagicMock()
        database = MagicMock(spec=AsyncSubscriberDatabase)

        import asyncio

        asyncio.run(
            schedule_price_updates(mock_application, client, database, 120)
        )
        mock_application.job_queue.run_repeating.assert_not_called()

    def test_no_job_queue_logs_error(self, caplog):
        app = MagicMock()
        app.job_queue = None

        client = MagicMock()
        database = MagicMock()

        import asyncio

        asyncio.run(schedule_price_updates(app, client, database, 120))
        assert "JobQueue is unavailable" in caplog.text


class TestSendPriceUpdateSkipsOnFailure:
    @pytest.mark.asyncio
    async def test_api_failure_skips_update(self, mock_application, patched_client):
        from goldpulse_bot.database import AsyncSubscriberDatabase

        patched_client.side_effect = GoldAPIError("API down")
        database = MagicMock(spec=AsyncSubscriberDatabase)
        database.get_all_subscribers = AsyncMock(return_value=[1, 2])
        client = MagicMock()
        client.fetch_gold_price = patched_client

        from goldpulse_bot.scheduler import _send_price_update

        await _send_price_update(mock_application, client, database)
        mock_application.bot.send_message.assert_not_awaited()
        database.get_all_subscribers.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_no_subscribers_no_messages(self, mock_application, patched_client):
        from goldpulse_bot.scheduler import _send_price_update

        patched_client.return_value = GoldPrice(
            price=100, symbol="XAU", currency="USD", currency_symbol="$",
            updated_at=None, updated_at_readable=None,
        )
        database = MagicMock()
        database.get_all_subscribers = AsyncMock(return_value=[])
        client = MagicMock()
        client.fetch_gold_price = patched_client

        await _send_price_update(mock_application, client, database)
        mock_application.bot.send_message.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delivery_failure_does_not_crash_bot(
        self, mock_application, patched_client
    ):
        from goldpulse_bot.scheduler import _send_price_update

        patched_client.return_value = GoldPrice(
            price=100, symbol="XAU", currency="USD", currency_symbol="$",
            updated_at=None, updated_at_readable=None,
        )
        mock_application.bot.send_message.side_effect = Exception("blocked by user")
        database = MagicMock()
        database.get_all_subscribers = AsyncMock(return_value=[1, 2])
        client = MagicMock()
        client.fetch_gold_price = patched_client

        # Should not raise
        await _send_price_update(mock_application, client, database)
        assert mock_application.bot.send_message.await_count == 2
