"""Calendar platform for Intervals.icu."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .api import IntervalsIcuApiError
from .const import CONF_ATHLETE_ID, DOMAIN
from .coordinator import IntervalsIcuCoordinator

_LOGGER = logging.getLogger(__name__)

# Event categories worth surfacing on the Home Assistant calendar.
CALENDAR_CATEGORIES = frozenset({"WORKOUT", "TARGET", "NOTE", "RACE"})

# Assumed duration for a timed event that does not carry one.
DEFAULT_EVENT_DURATION = timedelta(hours=1)


def _parse_event_datetime(
    date_str: str | None, fallback_date: date | None = None
) -> datetime | date:
    """Parse an Intervals.icu date/datetime string."""
    if date_str is None:
        return fallback_date or dt_util.now().date()
    # Intervals.icu uses "2024-01-15T00:00:00" for local datetimes
    if "T" in date_str:
        return datetime.fromisoformat(date_str)
    return date.fromisoformat(date_str)


def _as_local_aware(value: datetime) -> datetime:
    """Attach the Home Assistant local timezone to a naive datetime.

    Intervals.icu timestamps are local to the athlete's account and carry no
    offset. Comparing them against a naive ``datetime.now()`` mixes that
    account-local wall clock with the Home Assistant host clock, so the
    "next event" check drifts whenever the two timezones differ, and silently
    misbehaves across DST transitions. Interpreting the value in the Home
    Assistant timezone keeps the comparison well-defined and aware.
    """
    if value.tzinfo is not None:
        return value
    return value.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)


def _resolved_event_end(event: dict[str, Any], start: datetime | date) -> datetime:
    """Compute the event end as a timezone-aware local datetime."""
    if isinstance(start, datetime):
        moving_time = event.get("moving_time")
        duration = DEFAULT_EVENT_DURATION
        if moving_time:
            try:
                duration = timedelta(seconds=float(moving_time))
            except (TypeError, ValueError):
                duration = DEFAULT_EVENT_DURATION
        return _as_local_aware(start + duration)

    # All-day event: runs through the end of the following day, local time.
    next_day = datetime.combine(start + timedelta(days=1), datetime.min.time())
    return _as_local_aware(next_day)


def _event_to_calendar_event(event: dict[str, Any]) -> CalendarEvent:
    """Convert an Intervals.icu event to a CalendarEvent."""
    name = event.get("name") or event.get("type") or "Workout"
    category = event.get("category", "")
    event_type = event.get("type", "")

    if category and category != "WORKOUT":
        name = f"[{category.title()}] {name}"

    start = _parse_event_datetime(event.get("start_date_local"))
    moving_time = event.get("moving_time")

    if isinstance(start, datetime):
        if moving_time:
            try:
                delta = timedelta(seconds=float(moving_time))
            except (TypeError, ValueError):
                delta = DEFAULT_EVENT_DURATION
        else:
            delta = DEFAULT_EVENT_DURATION
        end: datetime | date = start + delta
    else:
        # All-day event
        end = start + timedelta(days=1)

    description_parts: list[str] = []
    if event_type:
        description_parts.append(f"Type: {event_type}")
    if event.get("description"):
        description_parts.append(event["description"])
    load = event.get("icu_training_load")
    if load:
        description_parts.append(f"Training Load: {load}")

    return CalendarEvent(
        summary=name,
        start=start,
        end=end,
        description="\n".join(description_parts) if description_parts else None,
    )


class IntervalsIcuCalendar(CoordinatorEntity[IntervalsIcuCoordinator], CalendarEntity):
    """Intervals.icu calendar showing planned workouts and events."""

    _attr_has_entity_name = True
    _attr_translation_key = "training_calendar"

    def __init__(
        self,
        coordinator: IntervalsIcuCoordinator,
        athlete_id: str,
    ) -> None:
        """Initialize the calendar."""
        super().__init__(coordinator)
        self._athlete_id = athlete_id
        self._attr_unique_id = f"{athlete_id}_calendar"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, athlete_id)},
            name="Intervals.icu",
            manufacturer="Intervals.icu",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event from coordinator data."""
        if not self.coordinator.data or not self.coordinator.data.events:
            return None

        now = dt_util.now()
        upcoming: list[CalendarEvent] = []
        for ev in self.coordinator.data.events:
            if ev.get("category") not in CALENDAR_CATEGORIES:
                continue
            cal_event = _event_to_calendar_event(ev)
            if _resolved_event_end(ev, cal_event.start) >= now:
                upcoming.append(cal_event)

        if not upcoming:
            return None

        # Select the soonest event explicitly instead of depending on the
        # order the API happened to return records in.
        return min(upcoming, key=lambda event: str(event.start))

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Fetch events from the API for a date range."""
        client = self.coordinator.client
        try:
            events = await client.get_events(
                oldest=start_date.date(),
                newest=end_date.date(),
            )
        except IntervalsIcuApiError:
            _LOGGER.exception("Error fetching calendar events")
            return []

        calendar_events = [
            _event_to_calendar_event(ev)
            for ev in events
            if ev.get("category") in CALENDAR_CATEGORIES
        ]
        calendar_events.sort(key=lambda event: str(event.start))
        return calendar_events
