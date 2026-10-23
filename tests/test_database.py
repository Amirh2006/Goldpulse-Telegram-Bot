"""Tests for subscriber persistence."""

from __future__ import annotations

import pytest

from goldpulse_bot.database import AsyncSubscriberDatabase


class TestSubscriberDatabase:
    def test_add_and_is_subscribed(self, tmp_db):
        assert run_sync(tmp_db.add_subscriber(123)) is True
        assert run_sync(tmp_db.is_subscribed(123)) is True

    def test_add_subscriber_idempotent(self, tmp_db):
        assert run_sync(tmp_db.add_subscriber(123)) is True
        assert run_sync(tmp_db.add_subscriber(123)) is False

    def test_multiple_subscribers(self, tmp_db):
        assert run_sync(tmp_db.add_subscriber(1)) is True
        assert run_sync(tmp_db.add_subscriber(2)) is True
        assert run_sync(tmp_db.add_subscriber(3)) is True
        subscribers = run_sync(tmp_db.get_all_subscribers())
        assert subscribers == [1, 2, 3]

    def test_remove_subscriber(self, tmp_db):
        run_sync(tmp_db.add_subscriber(123))
        assert run_sync(tmp_db.remove_subscriber(123)) is True
        assert run_sync(tmp_db.is_subscribed(123)) is False

    def test_remove_subscriber_idempotent(self, tmp_db):
        assert run_sync(tmp_db.remove_subscriber(999)) is False

    def test_get_all_subscribers_empty(self, tmp_db):
        assert run_sync(tmp_db.get_all_subscribers()) == []

    def test_survives_new_instance(self, tmp_path):
        path = str(tmp_path / "persist.sqlite")
        db1 = AsyncSubscriberDatabase(path)
        run_sync(db1.add_subscriber(42))
        run_sync(db1.close())

        db2 = AsyncSubscriberDatabase(path)
        assert run_sync(db2.is_subscribed(42)) is True
        run_sync(db2.close())


def run_sync(coro):
    import asyncio

    return asyncio.run(coro)
