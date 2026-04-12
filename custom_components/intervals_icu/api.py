"""API client for Intervals.icu."""

from __future__ import annotations

from datetime import date
from typing import Any

import aiohttp

from .const import API_BASE_URL


class IntervalsIcuApiError(Exception):
    """Base exception for Intervals.icu API errors."""


class IntervalsIcuAuthError(IntervalsIcuApiError):
    """Authentication error."""


class IntervalsIcuNotFoundError(IntervalsIcuApiError):
    """Resource not found."""


class IntervalsIcuClient:
    """Async client for the Intervals.icu API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        athlete_id: str,
        api_key: str,
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._athlete_id = athlete_id
        self._auth = aiohttp.BasicAuth("API_KEY", api_key)

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> Any:
        """Make an authenticated API request."""
        url = f"{API_BASE_URL}{path}"
        try:
            async with self._session.request(
                method, url, auth=self._auth, **kwargs
            ) as resp:
                if resp.status == 401:
                    raise IntervalsIcuAuthError("Invalid API key or athlete ID")
                if resp.status == 404:
                    raise IntervalsIcuNotFoundError(f"Not found: {path}")
                resp.raise_for_status()
                return await resp.json()
        except aiohttp.ClientResponseError as err:
            raise IntervalsIcuApiError(
                f"API request failed: {err.status} {err.message}"
            ) from err
        except aiohttp.ClientError as err:
            raise IntervalsIcuApiError(f"Connection error: {err}") from err

    async def get_athlete(self) -> dict[str, Any]:
        """Get athlete profile information."""
        return await self._request("GET", f"/athlete/{self._athlete_id}")

    async def get_wellness(self, day: date | None = None) -> dict[str, Any]:
        """Get wellness data for a specific date (defaults to today)."""
        if day is None:
            day = date.today()
        return await self._request(
            "GET", f"/athlete/{self._athlete_id}/wellness/{day.isoformat()}"
        )

    async def get_wellness_range(
        self,
        oldest: date | None = None,
        newest: date | None = None,
    ) -> list[dict[str, Any]]:
        """Get wellness data for a date range."""
        params: dict[str, str] = {}
        if oldest is not None:
            params["oldest"] = oldest.isoformat()
        if newest is not None:
            params["newest"] = newest.isoformat()
        return await self._request(
            "GET",
            f"/athlete/{self._athlete_id}/wellness.json",
            params=params,
        )

    async def get_activities(
        self,
        oldest: date | None = None,
        newest: date | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get recent activities."""
        params: dict[str, str] = {"limit": str(limit)}
        if oldest is not None:
            params["oldest"] = oldest.isoformat()
        if newest is not None:
            params["newest"] = newest.isoformat()
        return await self._request(
            "GET",
            f"/athlete/{self._athlete_id}/activities",
            params=params,
        )

    async def get_events(
        self,
        oldest: date | None = None,
        newest: date | None = None,
    ) -> list[dict[str, Any]]:
        """Get calendar events (planned workouts, notes, etc.)."""
        params: dict[str, str] = {}
        if oldest is not None:
            params["oldest"] = oldest.isoformat()
        if newest is not None:
            params["newest"] = newest.isoformat()
        return await self._request(
            "GET",
            f"/athlete/{self._athlete_id}/events.json",
            params=params,
        )

    async def validate_credentials(self) -> dict[str, Any]:
        """Validate the API credentials by fetching athlete profile."""
        return await self.get_athlete()
