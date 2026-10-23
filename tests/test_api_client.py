"""Tests for the gold-price API client."""

from __future__ import annotations

import pytest
import httpx

from goldpulse_bot.api_client import GoldApiClient, GoldAPIError, GoldPrice
from goldpulse_bot.config import GOLD_API_URL


class TestGoldApiClientInitialization:
    def test_default_url(self):
        client = GoldApiClient()
        assert client._base_url == GOLD_API_URL

    def test_custom_url(self):
        client = GoldApiClient(base_url="https://example.com/price/XAU")
        assert client._base_url == "https://example.com/price/XAU"


class TestValidatePrice:
    def test_valid_integer_price(self):
        assert GoldApiClient._validate_price(4025) == 4025.0

    def test_valid_float_price(self):
        assert GoldApiClient._validate_price(4025.5) == 4025.5

    def test_valid_zero_price_rejected(self):
        with pytest.raises(GoldAPIError):
            GoldApiClient._validate_price(0)

    def test_negative_price_rejected(self):
        with pytest.raises(GoldAPIError):
            GoldApiClient._validate_price(-100)

    def test_nan_price_rejected(self):
        with pytest.raises(GoldAPIError):
            GoldApiClient._validate_price(float("nan"))

    def test_inf_price_rejected(self):
        with pytest.raises(GoldAPIError):
            GoldApiClient._validate_price(float("inf"))

    def test_negative_inf_price_rejected(self):
        with pytest.raises(GoldAPIError):
            GoldApiClient._validate_price(float("-inf"))

    def test_none_price_rejected(self):
        with pytest.raises(GoldAPIError):
            GoldApiClient._validate_price(None)

    def test_boolean_price_rejected(self):
        with pytest.raises(GoldAPIError):
            GoldApiClient._validate_price(True)

    def test_string_price_rejected(self):
        with pytest.raises(GoldAPIError):
            GoldApiClient._validate_price("4025.5")

    def test_list_price_rejected(self):
        with pytest.raises(GoldAPIError):
            GoldApiClient._validate_price([4025.5])


class TestFetchGoldPrice:
    @pytest.mark.asyncio
    async def test_valid_response(self, api_client, valid_price, httpx_mock):
        httpx_mock.add_response(
            url=api_client._base_url,
            json={
                "currency": "USD",
                "currencySymbol": "$",
                "exchangeRate": 1.0,
                "name": "Gold",
                "price": 4025.5,
                "symbol": "XAU",
                "updatedAt": "2026-10-23T12:03:43Z",
                "updatedAtReadable": "a few seconds ago",
            },
        )
        price = await api_client.fetch_gold_price()
        assert price.price == 4025.5
        assert price.symbol == "XAU"
        assert price.currency == "USD"
        assert price.currency_symbol == "$"
        assert price.updated_at is not None
        assert price.updated_at_readable == "a few seconds ago"

    @pytest.mark.asyncio
    async def test_valid_response_no_updated_at(self, api_client, httpx_mock):
        httpx_mock.add_response(
            url=api_client._base_url,
            json={
                "currency": "USD",
                "currencySymbol": "$",
                "exchangeRate": 1.0,
                "name": "Gold",
                "price": 4025.5,
                "symbol": "XAU",
            },
        )
        price = await api_client.fetch_gold_price()
        assert price.price == 4025.5
        assert price.updated_at is None
        assert price.updated_at_readable is None

    @pytest.mark.asyncio
    async def test_missing_price(self, api_client, httpx_mock):
        httpx_mock.add_response(
            url=api_client._base_url,
            json={
                "currency": "USD",
                "symbol": "XAU",
            },
        )
        with pytest.raises(GoldAPIError, match="missing"):
            await api_client.fetch_gold_price()

    @pytest.mark.asyncio
    async def test_invalid_price_type(self, api_client, httpx_mock):
        httpx_mock.add_response(
            url=api_client._base_url,
            json={"price": "not-a-number", "symbol": "XAU"},
        )
        with pytest.raises(GoldAPIError, match="not a number"):
            await api_client.fetch_gold_price()

    @pytest.mark.asyncio
    async def test_zero_price(self, api_client, httpx_mock):
        httpx_mock.add_response(
            url=api_client._base_url,
            json={"price": 0, "symbol": "XAU"},
        )
        with pytest.raises(GoldAPIError, match="not positive"):
            await api_client.fetch_gold_price()

    @pytest.mark.asyncio
    async def test_negative_price(self, api_client, httpx_mock):
        httpx_mock.add_response(
            url=api_client._base_url,
            json={"price": -50, "symbol": "XAU"},
        )
        with pytest.raises(GoldAPIError, match="not positive"):
            await api_client.fetch_gold_price()

    @pytest.mark.asyncio
    async def test_non_object_response(self, api_client, httpx_mock):
        httpx_mock.add_response(url=api_client._base_url, json=[1, 2, 3])
        with pytest.raises(GoldAPIError, match="not a JSON object"):
            await api_client.fetch_gold_price()

    @pytest.mark.asyncio
    async def test_invalid_json(self, api_client, httpx_mock):
        httpx_mock.add_response(
            url=api_client._base_url, text="not json", status_code=200
        )
        with pytest.raises(GoldAPIError, match="invalid JSON"):
            await api_client.fetch_gold_price()

    @pytest.mark.asyncio
    async def test_timeout(self, api_client, httpx_mock):
        httpx_mock.add_exception(httpx.ConnectTimeout("connect timed out"))
        with pytest.raises(GoldAPIError, match="timed out"):
            await api_client.fetch_gold_price()

    @pytest.mark.asyncio
    async def test_http_error(self, api_client, httpx_mock):
        httpx_mock.add_response(
            url=api_client._base_url, status_code=502, text="Bad Gateway"
        )
        with pytest.raises(GoldAPIError, match="HTTP 502"):
            await api_client.fetch_gold_price()

    @pytest.mark.asyncio
    async def test_network_error(self, api_client, httpx_mock):
        httpx_mock.add_exception(httpx.ConnectError("connection refused"))
        with pytest.raises(GoldAPIError, match="failed"):
            await api_client.fetch_gold_price()


class TestTimestampParsing:
    def test_iso_timestamp_with_z(self):
        from goldpulse_bot.api_client import _parse_timestamp

        dt = _parse_timestamp("2026-10-23T12:03:43Z")
        assert dt is not None
        assert dt.hour == 12
        assert dt.tzinfo is not None

    def test_invalid_timestamp_returns_none(self):
        from goldpulse_bot.api_client import _parse_timestamp

        assert _parse_timestamp("not-a-date") is None
        assert _parse_timestamp("") is None
        assert _parse_timestamp(None) is None

    def test_naive_timestamp_becomes_utc(self):
        from goldpulse_bot.api_client import _parse_timestamp

        dt = _parse_timestamp("2026-10-23T12:03:43")
        assert dt is not None
        assert dt.tzinfo is not None
