"""Bot initialization and command registration for GoldPulse Bot."""

from __future__ import annotations

from telegram.ext import Application, CommandHandler

from .api_client import GoldApiClient
from .config import Settings, load_settings
from .database import AsyncSubscriberDatabase
from .handlers import help_command, price_command, start_command, stop_command
from .logging_config import logger
from .scheduler import schedule_price_updates


def build_application(settings: Settings | None = None) -> Application:
    """Build the PTB application with handlers, services, and scheduled job."""
    if settings is None:
        settings = load_settings()

    application = Application.builder().token(settings.telegram_bot_token).build()

    client = GoldApiClient(timeout=settings.request_timeout_seconds)
    database = AsyncSubscriberDatabase(settings.database_path)

    application.bot_data["api_client"] = client
    application.bot_data["db"] = database

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(CommandHandler("price", price_command))
    application.add_handler(CommandHandler("help", help_command))

    async def _post_init(app: Application) -> None:
        await schedule_price_updates(
            app, client, database, settings.poll_interval_seconds
        )

    async def _post_shutdown(app: Application) -> None:
        db: AsyncSubscriberDatabase | None = app.bot_data.get("db")
        client_instance: GoldApiClient | None = app.bot_data.get("api_client")
        if db is not None:
            await db.close()
        if client_instance is not None:
            await client_instance.aclose()

    application.post_init = _post_init
    application.post_shutdown = _post_shutdown

    logger.info("GoldPulse Bot application built.")
    return application


def main() -> None:
    """Entry point: load config, build app, and start polling (blocking)."""
    settings = load_settings()
    from .logging_config import configure_logging

    configure_logging(settings.log_level)
    application = build_application(settings)
    try:
        application.run_polling()
    except KeyboardInterrupt:
        logger.info("GoldPulse Bot stopped by user.")
    finally:
        logger.info("GoldPulse Bot shutdown complete.")
