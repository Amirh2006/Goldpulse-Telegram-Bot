"""Tests for Telegram command handlers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from goldpulse_bot.api_client import GoldAPIError, GoldPrice
from goldpulse_bot.handlers import (
    help_command,
    price_command,
    start_command,
    stop_command,
)


def _make_update(chat_id=123):
    update = MagicMock()
    update.effective_chat.id = chat_id
    update.effective_chat.type = "private"
    message = MagicMock()
    message.reply_text = AsyncMock()
    update.effective_message = message
    return update


def _make_context(db, client):
    context = MagicMock()
    context.application.bot_data = {"db": db, "api_client": client}
    return context


class TestStartCommand:
    @pytest.mark.asyncio
    async def test_subscribes_new_user_and_sends_price(self, tmp_path):
        from goldpulse_bot.database import AsyncSubscriberDatabase

        db = AsyncSubscriberDatabase(str(tmp_path / "start_test.sqlite"))
        client = MagicMock()
        client.fetch_gold_price = AsyncMock(
            return_value=GoldPrice(
                price=4025.5,
                symbol="XAU",
                currency="USD",
                currency_symbol="$",
                updated_at=None,
                updated_at_readable="now",
            )
        )

        update = _make_update(chat_id=1)
        context = _make_context(db, client)

        await start_command(update, context)

        assert await db.is_subscribed(1)
        assert update.effective_message.reply_text.await_count == 2
        await db.close()

    @pytest.mark.asyncio
    async def test_repeated_start_idempotent(self, tmp_path):
        from goldpulse_bot.database import AsyncSubscriberDatabase

        db = AsyncSubscriberDatabase(str(tmp_path / "start_idem.sqlite"))
        client = MagicMock()
        client.fetch_gold_price = AsyncMock(
            return_value=GoldPrice(
                price=1,
                symbol="XAU",
                currency="USD",
                currency_symbol="$",
                updated_at=None,
                updated_at_readable=None,
            )
        )

        update = _make_update(chat_id=2)
        context = _make_context(db, client)

        await start_command(update, context)
        await start_command(update, context)

        subscribers = await db.get_all_subscribers()
        assert subscribers == [2]
        await db.close()

    @pytest.mark.asyncio
    async def test_start_api_failure_still_subscribes(self, tmp_path):
        from goldpulse_bot.database import AsyncSubscriberDatabase

        db = AsyncSubscriberDatabase(str(tmp_path / "start_fail.sqlite"))
        client = MagicMock()
        client.fetch_gold_price = AsyncMock(side_effect=GoldAPIError("down"))

        update = _make_update(chat_id=3)
        context = _make_context(db, client)

        await start_command(update, context)
        assert await db.is_subscribed(3)
        assert update.effective_message.reply_text.await_count == 2
        await db.close()


class TestStopCommand:
    @pytest.mark.asyncio
    async def test_unsubscribes_user(self, tmp_path):
        from goldpulse_bot.database import AsyncSubscriberDatabase

        db = AsyncSubscriberDatabase(str(tmp_path / "stop_test.sqlite"))
        await db.add_subscriber(5)
        client = MagicMock()
        update = _make_update(chat_id=5)
        context = _make_context(db, client)

        await stop_command(update, context)
        assert not await db.is_subscribed(5)
        await db.close()

    @pytest.mark.asyncio
    async def test_stop_not_subscribed(self, tmp_path):
        from goldpulse_bot.database import AsyncSubscriberDatabase

        db = AsyncSubscriberDatabase(str(tmp_path / "stop_not_sub.sqlite"))
        client = MagicMock()
        update = _make_update(chat_id=6)
        context = _make_context(db, client)

        await stop_command(update, context)
        assert update.effective_message.reply_text.await_count == 1
        await db.close()


class TestPriceCommand:
    @pytest.mark.asyncio
    async def test_returns_price(self, tmp_path):
        from goldpulse_bot.database import AsyncSubscriberDatabase

        db = AsyncSubscriberDatabase(str(tmp_path / "price_test.sqlite"))
        client = MagicMock()
        client.fetch_gold_price = AsyncMock(
            return_value=GoldPrice(
                price=4025.5,
                symbol="XAU",
                currency="USD",
                currency_symbol="$",
                updated_at=None,
                updated_at_readable=None,
            )
        )
        update = _make_update(chat_id=7)
        context = _make_context(db, client)

        await price_command(update, context)
        sent = update.effective_message.reply_text.await_args.args[0]
        assert "4,025.50" in sent
        await db.close()

    @pytest.mark.asyncio
    async def test_api_failure_returns_error(self, tmp_path):
        from goldpulse_bot.database import AsyncSubscriberDatabase

        db = AsyncSubscriberDatabase(str(tmp_path / "price_fail.sqlite"))
        client = MagicMock()
        client.fetch_gold_price = AsyncMock(side_effect=GoldAPIError("down"))
        update = _make_update(chat_id=8)
        context = _make_context(db, client)

        await price_command(update, context)
        sent = update.effective_message.reply_text.await_args.args[0]
        assert "couldn't retrieve" in sent.lower()
        await db.close()


class TestHelpCommand:
    @pytest.mark.asyncio
    async def test_lists_commands(self, tmp_path):
        from goldpulse_bot.database import AsyncSubscriberDatabase

        db = AsyncSubscriberDatabase(str(tmp_path / "help_test.sqlite"))
        client = MagicMock()
        update = _make_update(chat_id=9)
        context = _make_context(db, client)

        await help_command(update, context)
        sent = update.effective_message.reply_text.await_args.args[0]
        for cmd in ["/start", "/stop", "/price", "/help"]:
            assert cmd in sent
        await db.close()
