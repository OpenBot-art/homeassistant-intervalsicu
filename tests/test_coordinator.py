"""Tests for the Intervals.icu data coordinator."""

from __future__ import annotations

import unittest
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock

from custom_components.intervals_icu.api import (
    IntervalsIcuApiError,
    IntervalsIcuNotFoundError,
)
from custom_components.intervals_icu.coordinator import (
    IntervalsIcuCoordinator,
    IntervalsIcuData,
    parse_sort_datetime,
    sort_by_start_descending,
)


class TestParseSortDatetime(unittest.TestCase):
    """Test the tolerant datetime parser used for sorting."""

    def test_parses_iso_datetime(self) -> None:
        self.assertEqual(
            parse_sort_datetime("2026-04-12T07:30:00"),
            datetime(2026, 4, 12, 7, 30),
        )

    def test_parses_plain_date(self) -> None:
        self.assertEqual(
            parse_sort_datetime("2026-04-12"),
            datetime(2026, 4, 12, 0, 0),
        )

    def test_missing_and_invalid_values_sort_to_minimum(self) -> None:
        for value in (None, "", "not-a-date", 12345):
            with self.subTest(value=value):
                self.assertEqual(parse_sort_datetime(value), datetime.min)


class TestSortByStartDescending(unittest.TestCase):
    """Test newest-first sorting of API records."""

    def test_sorts_newest_first_regardless_of_input_order(self) -> None:
        records = [
            {"name": "oldest", "start_date_local": "2026-04-01T06:00:00"},
            {"name": "newest", "start_date_local": "2026-04-15T06:00:00"},
            {"name": "middle", "start_date_local": "2026-04-08T06:00:00"},
        ]

        result = sort_by_start_descending(
            records, date_key="start_date_local", fallback_key="start_date"
        )

        self.assertEqual(
            [record["name"] for record in result],
            ["newest", "middle", "oldest"],
        )

    def test_falls_back_to_alternate_key(self) -> None:
        records = [
            {"name": "with_local", "start_date_local": "2026-04-01T06:00:00"},
            {"name": "utc_only", "start_date": "2026-04-20T06:00:00"},
        ]

        result = sort_by_start_descending(
            records, date_key="start_date_local", fallback_key="start_date"
        )

        self.assertEqual(result[0]["name"], "utc_only")

    def test_records_without_dates_do_not_sort_first(self) -> None:
        records = [
            {"name": "undated"},
            {"name": "dated", "start_date_local": "2026-04-01T06:00:00"},
        ]

        result = sort_by_start_descending(
            records, date_key="start_date_local", fallback_key="start_date"
        )

        self.assertEqual(result[0]["name"], "dated")
        self.assertEqual(result[-1]["name"], "undated")

    def test_does_not_mutate_input(self) -> None:
        records = [
            {"name": "a", "start_date_local": "2026-04-01T06:00:00"},
            {"name": "b", "start_date_local": "2026-04-15T06:00:00"},
        ]
        original = list(records)

        sort_by_start_descending(
            records, date_key="start_date_local", fallback_key="start_date"
        )

        self.assertEqual(records, original)


class TestIntervalsIcuData(unittest.TestCase):
    """Test the convenience accessors on the data container."""

    def _make_data(
        self,
        activities: list[dict] | None = None,
        events: list[dict] | None = None,
    ) -> IntervalsIcuData:
        return IntervalsIcuData(
            athlete={},
            wellness=None,
            activities=activities or [],
            events=events or [],
            pace_curve=None,
        )

    def test_latest_activity_is_none_when_empty(self) -> None:
        self.assertIsNone(self._make_data().latest_activity)

    def test_latest_activity_returns_first_entry(self) -> None:
        data = self._make_data(activities=[{"name": "first"}, {"name": "second"}])
        self.assertEqual(data.latest_activity["name"], "first")

    def test_next_workout_skips_non_workout_categories(self) -> None:
        data = self._make_data(
            events=[
                {"category": "NOTE", "name": "note"},
                {"category": "WORKOUT", "name": "interval session"},
            ]
        )
        self.assertEqual(data.next_workout["name"], "interval session")

    def test_next_workout_is_none_when_no_workouts(self) -> None:
        data = self._make_data(events=[{"category": "NOTE", "name": "note"}])
        self.assertIsNone(data.next_workout)


class TestCoordinatorUpdate(unittest.IsolatedAsyncioTestCase):
    """Test the coordinator fetch and degradation behaviour."""

    def setUp(self) -> None:
        self.client = MagicMock()
        self.client.get_athlete = AsyncMock(return_value={"id": "i12345"})
        self.client.get_wellness = AsyncMock(return_value=None)
        self.client.get_activities = AsyncMock(return_value=[])
        self.client.get_events = AsyncMock(return_value=[])
        self.client.get_pace_curves = AsyncMock(return_value={"list": []})

        self.coordinator = IntervalsIcuCoordinator(MagicMock(), self.client)

    async def _update(self) -> IntervalsIcuData:
        return await self.coordinator._async_update_data()

    async def test_activities_are_sorted_newest_first(self) -> None:
        self.client.get_activities.return_value = [
            {"name": "older", "start_date_local": "2026-04-01T06:00:00"},
            {"name": "newer", "start_date_local": "2026-04-10T06:00:00"},
        ]

        data = await self._update()

        self.assertEqual(data.latest_activity["name"], "newer")

    async def test_unnamed_activities_are_filtered_out(self) -> None:
        self.client.get_activities.return_value = [
            {"name": "", "start_date_local": "2026-04-15T06:00:00"},
            {"name": "real ride", "start_date_local": "2026-04-10T06:00:00"},
        ]

        data = await self._update()

        self.assertEqual(len(data.activities), 1)
        self.assertEqual(data.latest_activity["name"], "real ride")

    async def test_events_are_sorted_soonest_first(self) -> None:
        self.client.get_events.return_value = [
            {"category": "WORKOUT", "name": "later", "start_date_local": "2026-04-20"},
            {"category": "WORKOUT", "name": "sooner", "start_date_local": "2026-04-16"},
        ]

        data = await self._update()

        self.assertEqual(data.next_workout["name"], "sooner")

    async def test_partial_failures_degrade_to_empty(self) -> None:
        self.client.get_wellness.side_effect = IntervalsIcuApiError("boom")
        self.client.get_activities.side_effect = IntervalsIcuApiError("boom")
        self.client.get_events.side_effect = IntervalsIcuNotFoundError("gone")
        self.client.get_pace_curves.side_effect = IntervalsIcuApiError("boom")

        data = await self._update()

        self.assertIsNone(data.wellness)
        self.assertEqual(data.activities, [])
        self.assertEqual(data.events, [])
        self.assertIsNone(data.pace_curve)

    async def test_pace_curve_uses_first_list_entry(self) -> None:
        self.client.get_pace_curves.return_value = {
            "list": [{"distance": [5000.0], "values": [1200]}, {"distance": []}]
        }

        data = await self._update()

        self.assertEqual(data.pace_curve["values"], [1200])

    async def test_empty_pace_curve_list_becomes_none(self) -> None:
        self.client.get_pace_curves.return_value = {"list": []}

        data = await self._update()

        self.assertIsNone(data.pace_curve)


if __name__ == "__main__":
    unittest.main()
