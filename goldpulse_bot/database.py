"""Subscriber persistence backed by a local SQLite database.

Subscription IDs survive application restarts because they are stored on disk.
SQLite is blocking, so the async wrapper runs each operation on a thread pool
to avoid blocking the asyncio event loop.
"""

from __future__ import annotations

import asyncio
import sqlite3
from typing import List

from .logging_config import logger


class SubscriberDatabase:
    """SQLite store of subscribed Telegram chat IDs."""

    def __init__(self, database_path: str) -> None:
        self._database_path = database_path
        # check_same_thread=False allows use across threads (to_thread pool).
        self._conn = sqlite3.connect(database_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    def _init_schema(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS subscribers (
                    chat_id INTEGER PRIMARY KEY
                )
                """
            )

    def add_subscriber(self, chat_id: int) -> bool:
        """Subscribe a chat. Idempotent. Returns True if newly added."""
        try:
            with self._conn:
                cursor = self._conn.execute(
                    "INSERT OR IGNORE INTO subscribers (chat_id) VALUES (?)",
                    (chat_id,),
                )
            return cursor.rowcount == 1
        except sqlite3.Error as exc:
            logger.error("Failed to add subscriber %s: %s", chat_id, exc)
            return False

    def remove_subscriber(self, chat_id: int) -> bool:
        """Unsubscribe a chat. Idempotent. Returns True if a row was removed."""
        try:
            with self._conn:
                cursor = self._conn.execute(
                    "DELETE FROM subscribers WHERE chat_id = ?", (chat_id,)
                )
            return cursor.rowcount == 1
        except sqlite3.Error as exc:
            logger.error("Failed to remove subscriber %s: %s", chat_id, exc)
            return False

    def is_subscribed(self, chat_id: int) -> bool:
        cursor = self._conn.execute(
            "SELECT 1 FROM subscribers WHERE chat_id = ?", (chat_id,)
        )
        return cursor.fetchone() is not None

    def get_all_subscribers(self) -> List[int]:
        cursor = self._conn.execute(
            "SELECT chat_id FROM subscribers ORDER BY chat_id"
        )
        return [row[0] for row in cursor.fetchall()]

    def close(self) -> None:
        self._conn.close()


class AsyncSubscriberDatabase:
    """Async wrapper around :class:`SubscriberDatabase`."""

    def __init__(self, database_path: str) -> None:
        self._db = SubscriberDatabase(database_path)

    async def add_subscriber(self, chat_id: int) -> bool:
        return await asyncio.to_thread(self._db.add_subscriber, chat_id)

    async def remove_subscriber(self, chat_id: int) -> bool:
        return await asyncio.to_thread(self._db.remove_subscriber, chat_id)

    async def is_subscribed(self, chat_id: int) -> bool:
        return await asyncio.to_thread(self._db.is_subscribed, chat_id)

    async def get_all_subscribers(self) -> List[int]:
        return await asyncio.to_thread(self._db.get_all_subscribers)

    async def close(self) -> None:
        await asyncio.to_thread(self._db.close)
