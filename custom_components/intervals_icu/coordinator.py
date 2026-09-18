"""DataUpdateCoordinator for Intervals.icu."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import IntervalsIcuApiError, IntervalsIcuClient, IntervalsIcuNotFoundError
from .const import (
    ACTIVITY_LIMIT,
    ACTIVITY_LOOKBACK_DAYS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    EVENT_LOOKAHEAD_DAYS,
)

_LOGGER = logging.getLogger(__name__)


def parse_sort_datetime(value: Any) -> datetime:
    """Parse an Intervals.icu date/datetime string for sorting.

    Intervals.icu returns local timestamps without an offset (for example
    ``2026-04-12T07:30:00``) and plain dates (``2026-04-12``) for all-day
    entries. Missing or unparseable values sort to the beginning so they never
    masquerade as the most recent entry.
    """
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    if not value or not isinstance(value, str):
        return datetime.min
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return datetime.min


def sort_by_start_descending(
    items: list[dict[str, Any]], *, date_key: str, fallback_key: str
) -> list[dict[str, Any]]:
    """Sort records newest-first without relying on server-side ordering.

    The API is not documented to return activities or events in any particular
    order. Deriving ``activities[0]`` as "the latest activity" from the raw
    response is therefore an implicit contract that silently breaks if the
    server changes its ordering. Sorting explicitly makes the assumption
    visible and verifiable.
    """
    return sorted(
        items,
        key=lambda item: parse_sort_datetime(
            item.get(date_key) or item.get(fallback_key)
        ),
        reverse=True,
    )


class IntervalsIcuData:
    """Container for data fetched from Intervals.icu."""

    def __init__(
        self,
        athlete: dict[str, Any],
        wellness: dict[str, Any] | None,
        activities: list[dict[str, Any]],
        events: list[dict[str, Any]],
        pace_curve: dict[str, Any] | None,
    ) -> None:
        self.athlete = athlete
        self.wellness = wellness
        self.activities = activities
        self.events = events
        self.pace_curve = pace_curve

    @property
    def latest_activity(self) -> dict[str, Any] | None:
        """Return the most recent activity, or None when there is none."""
        return self.activities[0] if self.activities else None

    @property
    def next_workout(self) -> dict[str, Any] | None:
        """Return the earliest upcoming planned workout, or None.

        ``events`` is stored newest-first, so the earliest workout is the last
        element rather than the first. Selecting with ``min`` keeps the result
        correct independently of how the list happens to be ordered.
        """
        workouts = [e for e in self.events if e.get("category") == "WORKOUT"]
        if not workouts:
            return None
        return min(
            workouts,
            key=lambda event: parse_sort_datetime(
                event.get("start_date_local") or event.get("start_date")
            ),
        )


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
            all_activities = await self.client.get_activities(
                oldest=today - timedelta(days=ACTIVITY_LOOKBACK_DAYS),
                newest=today,
                limit=ACTIVITY_LIMIT,
            )
            # Filter out empty/wellness-only records that have no name
            activities = [a for a in all_activities if a.get("name")]
        except IntervalsIcuNotFoundError:
            activities = []
        except IntervalsIcuApiError as err:
            _LOGGER.warning("Error fetching activities: %s", err)
            activities = []

        activities = sort_by_start_descending(
            activities, date_key="start_date_local", fallback_key="start_date"
        )

        try:
            events = await self.client.get_events(
                oldest=today,
                newest=today + timedelta(days=EVENT_LOOKAHEAD_DAYS),
            )
        except IntervalsIcuNotFoundError:
            events = []
        except IntervalsIcuApiError as err:
            _LOGGER.warning("Error fetching events: %s", err)
            events = []

        events = sort_by_start_descending(
            events, date_key="start_date_local", fallback_key="start_date"
        )

        try:
            pace_curves = await self.client.get_pace_curves(sport="Run", curves="all")
            curve_list = pace_curves.get("list") or []
            pace_curve = curve_list[0] if curve_list else None
        except IntervalsIcuNotFoundError:
            pace_curve = None
        except IntervalsIcuApiError as err:
            _LOGGER.warning("Error fetching pace curves: %s", err)
            pace_curve = None

        return IntervalsIcuData(
            athlete=athlete,
            wellness=wellness,
            activities=activities,
            events=events,
            pace_curve=pace_curve,
        )
