"""Scheduled gold-price notification logic backed by PTB JobQueue."""

from __future__ import annotations

from typing import Any

from telegram.ext import ContextTypes

from .api_client import GoldApiClient, GoldAPIError, GoldPrice
from .database import AsyncSubscriberDatabase
from .logging_config import logger

JOB_NAME = "gold_price_update"


def format_price_message(price: GoldPrice) -> str:
    """Build a human-readable price update message.

    Only currency and symbol values supplied by the API response are used. The
    pricing unit is not claimed unless the API states it.
    """
    if price.currency_symbol:
        amount = f"{price.currency_symbol}{price.price:,.2f}"
    else:
        amount = f"{price.price:,.2f}"
    parts = [f"💰 Gold price ({price.symbol}): {amount} {price.currency}".strip()]
    if price.updated_at is not None:
        parts.append(f"Updated: {price.updated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    return "\n".join(parts)


async def schedule_price_updates(
    application: Any,
    client: GoldApiClient,
    database: AsyncSubscriberDatabase,
    interval_seconds: int,
) -> None:
    """Schedule the recurring price-update job exactly once.

    Idempotent: a job already registered under ``JOB_NAME`` is not rescheduled,
    which prevents accidentally scheduling the same job more than once and
    therefore prevents duplicate scheduled messages.
    """
    job_queue = application.job_queue
    if job_queue is None:
        logger.error(
            "JobQueue is unavailable; scheduled price updates are disabled."
        )
        return

    if job_queue.get_jobs_by_name(JOB_NAME):
        logger.info(
            "Price-update job %r is already scheduled; not rescheduling.", JOB_NAME
        )
        return

    async def callback(context: ContextTypes.DEFAULT_TYPE) -> None:
        await _send_price_update(application, client, database)

    job_queue.run_repeating(
        callback,
        interval=interval_seconds,
        first=interval_seconds,
        name=JOB_NAME,
    )
    logger.info(
        "Scheduled gold-price updates every %ds (job %r).", interval_seconds, JOB_NAME
    )


async def _send_price_update(
    application: Any,
    client: GoldApiClient,
    database: AsyncSubscriberDatabase,
) -> None:
    """Fetch the latest price and broadcast it to all subscribers.

    API failures are logged and the update is skipped -- no false price is ever
    sent. Per-user Telegram delivery failures are logged and do not crash the
    broadcast or the whole bot.
    """
    try:
        price = await client.fetch_gold_price()
    except GoldAPIError as exc:
        logger.error("Scheduled price fetch failed, skipping update: %s", exc)
        return

    subscribers = await database.get_all_subscribers()
    if not subscribers:
        return

    message = format_price_message(price)
    for chat_id in subscribers:
        try:
            await application.bot.send_message(chat_id=chat_id, text=message)
        except Exception as exc:  # Telegram delivery failures must not crash the bot
            logger.error(
                "Failed to deliver price update to chat %s: %s", chat_id, exc
            )
