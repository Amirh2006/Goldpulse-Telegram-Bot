"""Tests for configuration loading and validation."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from goldpulse_bot.config import load_settings


def test_load_settings_missing_token_raises():
    with patch(
        "goldpulse_bot.config.os.getenv", return_value=""
    ):
        with pytest.raises(RuntimeError, match="TELEGRAM_BOT_TOKEN"):
            load_settings()


def test_load_settings_valid_token(tmp_path):
    env_file = None
    with patch(
        "goldpulse_bot.config.os.getenv",
        side_effect=lambda key, default=None: {
            "TELEGRAM_BOT_TOKEN": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
        }.get(key, default),
    ):
        settings = load_settings(env_file=None)
        assert settings.telegram_bot_token == "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
        assert settings.poll_interval_seconds == 120
        assert settings.request_timeout_seconds == 20


def test_load_settings_custom_interval(tmp_path):
    with patch(
        "goldpulse_bot.config.os.getenv",
        side_effect=lambda key, default=None: {
            "TELEGRAM_BOT_TOKEN": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            "POLL_INTERVAL_SECONDS": "60",
        }.get(key, default),
    ):
        settings = load_settings()
        assert settings.poll_interval_seconds == 60
