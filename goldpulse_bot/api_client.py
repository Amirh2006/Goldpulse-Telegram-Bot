"""Asynchronous client for the gold-price API.

Only fields present in the real API response are exposed. Prices are validated
and never fabricated or silently substituted when missing or invalid.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from .config import GOLD_API_URL


class GoldAPIError(Exception):
    """Raised when the gold-price API cannot provide a usable price."""


@dataclass(frozen=True)
class GoldPrice:
    """A validated gold price observation returned by the API."""

    price: float
    symbol: str
    currency: str
    currency_symbol: str | None
    updated_at: datetime | None
    updated_at_readable: str | None


def _parse_timestamp(value: Any) -> datetime | None:
    """Parse an ISO-8601 timestamp into an aware UTC datetime.

    Returns ``None`` when the value is missing or cannot be parsed, so the
    caller can decide whether to display a timestamp.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    try:
        # datetime.fromisoformat handles a trailing "Z" on Python 3.11+.
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class GoldApiClient:
    """Fetch the current XAU gold spot price from the public API."""

    def __init__(
        self,
        *,
        base_url: str = GOLD_API_URL,
        timeout: float = 20.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url
        self._timeout = timeout
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(timeout=timeout)

    async def __aenter__(self) -> "GoldApiClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying HTTP client if this instance owns it."""
        if self._owns_client:
            await self._client.aclose()

    async def fetch_gold_price(self) -> GoldPrice:
        """Return the latest validated gold price.

        Raises:
            GoldAPIError: on network errors, timeouts, HTTP errors, invalid
                JSON, or missing/invalid price values. Callers should log the
                error and skip rather than fabricating a price.
        """
        try:
            response = await self._client.get(self._base_url, timeout=self._timeout)
            response.raise_for_status()
            data = response.json()
        except httpx.TimeoutException as exc:
            raise GoldAPIError(f"Request to gold-price API timed out: {exc}") from exc
        except httpx.HTTPStatusError as exc:
            raise GoldAPIError(
                f"Gold-price API returned HTTP {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            raise GoldAPIError(f"Request to gold-price API failed: {exc}") from exc
        except ValueError as exc:  # includes JSON decode errors
            raise GoldAPIError(f"Gold-price API returned invalid JSON: {exc}") from exc

        if not isinstance(data, dict):
            raise GoldAPIError("Gold-price API response is not a JSON object.")

        price_raw = data.get("price")
        price = self._validate_price(price_raw)

        return GoldPrice(
            price=price,
            symbol=str(data.get("symbol", "")),
            currency=str(data.get("currency", "")),
            currency_symbol=(
                str(data["currencySymbol"])
                if isinstance(data.get("currencySymbol"), str)
                else None
            ),
            updated_at=_parse_timestamp(data.get("updatedAt")),
            updated_at_readable=(
                str(data["updatedAtReadable"])
                if isinstance(data.get("updatedAtReadable"), str)
                else None
            ),
        )

    @staticmethod
    def _validate_price(value: Any) -> float:
        """Validate the price field and return it as a float.

        Raises GoldAPIError when the price is missing, non-numeric, NaN,
        infinite, or not positive. We never fabricate or substitute a price.
        """
        if isinstance(value, bool) or value is None:
            raise GoldAPIError("Gold price is missing in API response.")
        if not isinstance(value, (int, float)):
            raise GoldAPIError(f"Gold price is not a number: {value!r}")
        price = float(value)
        if math.isnan(price) or math.isinf(price):
            raise GoldAPIError("Gold price is not a finite number.")
        if price <= 0:
            raise GoldAPIError(f"Gold price is not positive: {price}")
        return price
