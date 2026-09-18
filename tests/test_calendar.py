"""Tests for the Intervals.icu calendar platform helpers."""

from __future__ import annotations

import unittest
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from custom_components.intervals_icu.api import IntervalsIcuApiError
from custom_components.intervals_icu.calendar import (
    CALENDAR_CATEGORIES,
    DEFAULT_EVENT_DURATION,
    IntervalsIcuCalendar,
    _event_to_calendar_event,
    _parse_event_datetime,
    _resolved_event_end,
)


class TestCalendarCategories(unittest.TestCase):
    """Guard the category filter against accidental changes."""

    def test_expected_categories(self) -> None:
        self.assertEqual(
            CALENDAR_CATEGORIES, {"WORKOUT", "TARGET", "NOTE", "RACE"}
        )


class TestParseEventDatetime(unittest.TestCase):
    """Test parsing of Intervals.icu date strings."""

    def test_parses_local_datetime_string(self) -> None:
        self.assertEqual(
            _parse_event_datetime("2026-04-12T07:30:00"),
            datetime(2026, 4, 12, 7, 30),
        )

    def test_parses_plain_date_as_all_day(self) -> None:
        self.assertEqual(_parse_event_datetime("2026-04-12"), date(2026, 4, 12))

    def test_missing_value_uses_fallback(self) -> None:
        self.assertEqual(
            _parse_event_datetime(None, fallback_date=date(2026, 1, 1)),
            date(2026, 1, 1),
        )


class TestEventToCalendarEvent(unittest.TestCase):
    """Test conversion of raw API events into CalendarEvent objects."""

    def test_timed_event_uses_moving_time_as_duration(self) -> None:
        event = {
            "name": "Tempo Run",
            "category": "WORKOUT",
            "type": "Run",
            "start_date_local": "2026-04-12T07:30:00",
            "moving_time": 3600,
        }

        result = _event_to_calendar_event(event)

        self.assertEqual(result.summary, "Tempo Run")
        self.assertEqual(result.start, datetime(2026, 4, 12, 7, 30))
        self.assertEqual(
            result.end, datetime(2026, 4, 12, 7, 30) + timedelta(hours=1)
        )

    def test_timed_event_without_duration_defaults_to_one_hour(self) -> None:
        event = {
            "name": "Ride",
            "category": "WORKOUT",
            "start_date_local": "2026-04-12T18:00:00",
        }

        result = _event_to_calendar_event(event)

        self.assertEqual(result.end - result.start, DEFAULT_EVENT_DURATION)

    def test_invalid_moving_time_falls_back_to_default_duration(self) -> None:
        event = {
            "name": "Ride",
            "category": "WORKOUT",
            "start_date_local": "2026-04-12T18:00:00",
            "moving_time": "not-a-number",
        }

        result = _event_to_calendar_event(event)

        self.assertEqual(result.end - result.start, DEFAULT_EVENT_DURATION)

    def test_non_workout_category_is_prefixed(self) -> None:
        event = {
            "name": "Spring Classic",
            "category": "RACE",
            "start_date_local": "2026-04-12",
        }

        result = _event_to_calendar_event(event)

        self.assertTrue(result.summary.startswith("[Race]"))

    def test_workout_category_is_not_prefixed(self) -> None:
        event = {
            "name": "Tempo Run",
            "category": "WORKOUT",
            "start_date_local": "2026-04-12",
        }

        result = _event_to_calendar_event(event)

        self.assertEqual(result.summary, "Tempo Run")

    def test_all_day_event_spans_one_day(self) -> None:
        event = {
            "name": "Rest day",
            "category": "NOTE",
            "start_date_local": "2026-04-12",
        }

        result = _event_to_calendar_event(event)

        self.assertEqual(result.start, date(2026, 4, 12))
        self.assertEqual(result.end, date(2026, 4, 13))

    def test_description_collects_type_and_training_load(self) -> None:
        event = {
            "name": "Tempo Run",
            "category": "WORKOUT",
            "type": "Run",
            "start_date_local": "2026-04-12T07:30:00",
            "description": "6 x 800m",
            "icu_training_load": 85,
        }

        result = _event_to_calendar_event(event)

        self.assertIn("Type: Run", result.description)
        self.assertIn("6 x 800m", result.description)
        self.assertIn("Training Load: 85", result.description)

    def test_missing_name_falls_back_to_type(self) -> None:
        event = {
            "category": "WORKOUT",
            "type": "Swim",
            "start_date_local": "2026-04-12T07:30:00",
        }

        result = _event_to_calendar_event(event)

        self.assertEqual(result.summary, "Swim")


class TestResolvedEventEnd(unittest.TestCase):
    """Test end calculation used by the next-event lookup."""

    def test_all_day_event_end_is_timezone_aware(self) -> None:
        end = _resolved_event_end({}, date(2026, 4, 12))

        self.assertIsNotNone(end.tzinfo)
        self.assertEqual(end.date(), date(2026, 4, 13))

    def test_timed_event_end_is_timezone_aware(self) -> None:
        event = {"moving_time": 1800}

        end = _resolved_event_end(event, datetime(2026, 4, 12, 7, 30))

        self.assertIsNotNone(end.tzinfo)
        self.assertEqual(end.hour, 8)
        self.assertEqual(end.minute, 0)


class TestCalendarEventSelection(unittest.IsolatedAsyncioTestCase):
    """Test the coordinator-backed calendar entity."""

    def _make_calendar(self, events: list[dict]) -> IntervalsIcuCalendar:
        coordinator = MagicMock()
        coordinator.data = MagicMock()
        coordinator.data.events = events
        coordinator.client = MagicMock()
        coordinator.last_update_success = True

        calendar = IntervalsIcuCalendar(coordinator, "i12345")
        return calendar

    def test_event_is_none_without_data(self) -> None:
        calendar = self._make_calendar([])
        self.assertIsNone(calendar.event)

    def test_event_ignores_unsupported_categories(self) -> None:
        future = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S")
        calendar = self._make_calendar(
            [{"category": "HOLIDAY", "name": "Beach", "start_date_local": future}]
        )

        self.assertIsNone(calendar.event)

    def test_event_selects_soonest_upcoming(self) -> None:
        soon = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
        later = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%S")
        calendar = self._make_calendar(
            [
                {"category": "WORKOUT", "name": "later", "start_date_local": later},
                {"category": "WORKOUT", "name": "soon", "start_date_local": soon},
            ]
        )

        self.assertEqual(calendar.event.summary, "soon")

    def test_event_skips_past_events(self) -> None:
        past = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S")
        future = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S")
        calendar = self._make_calendar(
            [
                {"category": "WORKOUT", "name": "past", "start_date_local": past},
                {"category": "WORKOUT", "name": "future", "start_date_local": future},
            ]
        )

        self.assertEqual(calendar.event.summary, "future")

    async def test_get_events_sorts_chronologically(self) -> None:
        calendar = self._make_calendar([])
        calendar.coordinator.client.get_events = AsyncMock(
            return_value=[
                {"category": "WORKOUT", "name": "b", "start_date_local": "2026-04-20"},
                {"category": "WORKOUT", "name": "a", "start_date_local": "2026-04-16"},
            ]
        )

        result = await calendar.async_get_events(
            MagicMock(), datetime(2026, 4, 15), datetime(2026, 4, 21)
        )

        self.assertEqual([event.summary for event in result], ["a", "b"])

    async def test_get_events_filters_unsupported_categories(self) -> None:
        calendar = self._make_calendar([])
        calendar.coordinator.client.get_events = AsyncMock(
            return_value=[
                {"category": "HOLIDAY", "name": "Beach", "start_date_local": "2026-04-16"},
                {"category": "WORKOUT", "name": "Easy run", "start_date_local": "2026-04-17"},
                {"category": "RUN", "name": "Uncategorised", "start_date_local": "2026-04-18"},
            ]
        )

        result = await calendar.async_get_events(
            MagicMock(), datetime(2026, 4, 15), datetime(2026, 4, 21)
        )

        self.assertEqual([event.summary for event in result], ["Easy run"])

    async def test_get_events_returns_empty_on_api_error(self) -> None:
        calendar = self._make_calendar([])
        calendar.coordinator.client.get_events = AsyncMock(
            side_effect=IntervalsIcuApiError("boom")
        )

        result = await calendar.async_get_events(
            MagicMock(), datetime(2026, 4, 15), datetime(2026, 4, 21)
        )

        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
