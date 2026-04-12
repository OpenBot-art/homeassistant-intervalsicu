"""DataUpdateCoordinator for Intervals.icu."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import IntervalsIcuApiError, IntervalsIcuClient, IntervalsIcuNotFoundError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class IntervalsIcuData:
    """Container for data fetched from Intervals.icu."""

    def __init__(
        self,
        athlete: dict[str, Any],
        wellness: dict[str, Any] | None,
        activities: list[dict[str, Any]],
        events: list[dict[str, Any]],
    ) -> None:
        self.athlete = athlete
        self.wellness = wellness
        self.activities = activities
        self.events = events


class IntervalsIcuCoordinator(DataUpdateCoordinator[IntervalsIcuData]):
    """Coordinator to fetch data from Intervals.icu API."""

    def __init__(self, hass: HomeAssistant, client: IntervalsIcuClient) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.client = client

    async def _async_update_data(self) -> IntervalsIcuData:
        """Fetch data from the API."""
        today = date.today()
        try:
            athlete = await self.client.get_athlete()
        except IntervalsIcuApiError as err:
            raise UpdateFailed(f"Error fetching athlete data: {err}") from err

        try:
            wellness = await self.client.get_wellness(today)
        except IntervalsIcuNotFoundError:
            # Wellness data may not exist for today yet
            wellness = None
        except IntervalsIcuApiError as err:
            _LOGGER.warning("Error fetching wellness data: %s", err)
            wellness = None

        try:
            activities = await self.client.get_activities(
                oldest=today - timedelta(days=7),
                newest=today,
                limit=10,
            )
        except IntervalsIcuNotFoundError:
            activities = []
        except IntervalsIcuApiError as err:
            _LOGGER.warning("Error fetching activities: %s", err)
            activities = []

        try:
            events = await self.client.get_events(
                oldest=today,
                newest=today + timedelta(days=7),
            )
        except IntervalsIcuNotFoundError:
            events = []
        except IntervalsIcuApiError as err:
            _LOGGER.warning("Error fetching events: %s", err)
            events = []

        return IntervalsIcuData(
            athlete=athlete,
            wellness=wellness,
            activities=activities,
            events=events,
        )
