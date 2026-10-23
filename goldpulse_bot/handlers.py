"""Telegram command handlers for GoldPulse Bot."""

from __future__ import annotations

from typing import Any

from telegram import Update
from telegram.ext import ContextTypes

from .api_client import GoldApiClient, GoldAPIError, GoldPrice
from .database import AsyncSubscriberDatabase
from .logging_config import logger
from .scheduler import format_price_message


def _get_services(
    context: ContextTypes.DEFAULT_TYPE,
) -> tuple[AsyncSubscriberDatabase, GoldApiClient]:
    db = context.application.bot_data.get("db")
    client = context.application.bot_data.get("api_client")
    if db is None or client is None:
        raise RuntimeError("Bot services are not initialized.")
    return db, client


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start -- explain the bot, subscribe the user, send current price."""
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None:
        return

    db, client = _get_services(context)

    already_subscribed = await db.is_subscribed(chat.id)
    newly_added = await db.add_subscriber(chat.id)

    if already_subscribed:
        await message.reply_text(
            "You are already subscribed to GoldPulse gold price updates."
        )
    else:
        await message.reply_text(
            "👋 Welcome to GoldPulse Bot! You are now subscribed to gold price "
            "updates every two minutes. Use /stop to unsubscribe."
        )

    try:
        price = await client.fetch_gold_price()
        await message.reply_text(format_price_message(price))
    except GoldAPIError as exc:
        logger.error("Could not fetch current price for /start: %s", exc)
        await message.reply_text(
            "You are subscribed, but I could not retrieve the current gold "
            "price right now. You will receive updates once the price is "
            "available."
        )


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/stop -- unsubscribe the user from automatic notifications."""
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None:
        return

    db, _client = _get_services(context)

    removed = await db.remove_subscriber(chat.id)
    if removed:
        await message.reply_text(
            "You have been unsubscribed from GoldPulse gold price updates."
        )
    else:
        await message.reply_text(
            "You were not subscribed to GoldPulse gold price updates."
        )


async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/price -- request the latest available price immediately."""
    message = update.effective_message
    if message is None:
        return

    _db, client = _get_services(context)

    try:
        price = await client.fetch_gold_price()
        await message.reply_text(format_price_message(price))
    except GoldAPIError as exc:
        logger.error("Could not fetch price for /price: %s", exc)
        await message.reply_text(
            "Sorry, I couldn't retrieve the current gold price right now. "
            "Please try again later."
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/help -- display a concise description of the bot and all commands."""
    message = update.effective_message
    if message is None:
        return

    text = (
        "GoldPulse Bot -- current global gold spot price (XAU/USD).\n\n"
        "Commands:\n"
        "/start -- Subscribe to gold price updates every 2 minutes and get the "
        "current price.\n"
        "/stop -- Unsubscribe from automatic price updates.\n"
        "/price -- Get the latest gold price immediately.\n"
        "/help -- Show this help message.\n\n"
        "Only subscribed users receive scheduled notifications."
    )
    await message.reply_text(text)
