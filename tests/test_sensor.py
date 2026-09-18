"""Tests for the Intervals.icu sensor helper functions."""

from __future__ import annotations

import sys
import unittest
from unittest.mock import MagicMock

from . import _ha_stubs  # noqa: F401  (installs HA stubs when HA is absent)
from custom_components.intervals_icu.coordinator import IntervalsIcuData
from custom_components.intervals_icu.sensor import (
    SPORT_DISPLAY_NAMES,
    SPORT_DISPLAY_NAMES_HANT,
    _format_distance,
    _sport_setting_available_for,
    _sport_setting_sensors,
    _sport_setting_sports,
    _sport_setting_value_for,
    IntervalsIcuSensor,
    localize_sport,
    SENSOR_DESCRIPTIONS,
)


def _make_data(athlete: dict | None = None, **kwargs) -> IntervalsIcuData:
    return IntervalsIcuData(
        athlete=athlete or {},
        wellness=kwargs.get("wellness"),
        activities=kwargs.get("activities", []),
        events=kwargs.get("events", []),
        pace_curve=kwargs.get("pace_curve"),
    )


class TestSportSettingSports(unittest.TestCase):
    """Test enumeration of per-sport settings."""

    def test_returns_empty_without_sport_settings(self) -> None:
        self.assertEqual(_sport_setting_sports(_make_data()), [])

    def test_pairs_are_sorted_for_stable_entity_ids(self) -> None:
        data = _make_data(
            athlete={
                "sportSettings": [
                    {"type": "Run", "ftp": 250},
                    {"type": "Ride", "ftp": 280},
                ]
            }
        )

        self.assertEqual(
            [name for name, _ in _sport_setting_sports(data)], ["Ride", "Run"]
        )

    def test_non_dict_entries_are_skipped(self) -> None:
        data = _make_data(athlete={"sportSettings": ["bogus", {"type": "Ride"}]})

        self.assertEqual(len(_sport_setting_sports(data)), 1)

    def test_falls_back_to_sport_key_then_default(self) -> None:
        data = _make_data(
            athlete={"sportSettings": [{"sport": "Swim"}, {"ftp": 200}]}
        )

        names = [name for name, _ in _sport_setting_sports(data)]
        self.assertIn("Swim", names)
        self.assertIn("Default", names)


class TestSportSettingValueFor(unittest.TestCase):
    """Test per-sport value and availability lookups."""

    def setUp(self) -> None:
        self.data = _make_data(
            athlete={
                "sportSettings": [
                    {"type": "Ride", "ftp": 280, "lthr": 165},
                    {"type": "Run", "ftp": 250},
                ]
            }
        )

    def test_returns_value_for_matching_sport(self) -> None:
        self.assertEqual(_sport_setting_value_for("Ride", "ftp")(self.data), 280)
        self.assertEqual(_sport_setting_value_for("Run", "ftp")(self.data), 250)

    def test_returns_none_for_unknown_sport(self) -> None:
        self.assertIsNone(_sport_setting_value_for("Swim", "ftp")(self.data))

    def test_availability_reflects_presence_of_field(self) -> None:
        self.assertTrue(_sport_setting_available_for("Ride", "lthr")(self.data))
        self.assertFalse(_sport_setting_available_for("Run", "lthr")(self.data))

    def test_availability_false_for_unknown_sport(self) -> None:
        self.assertFalse(_sport_setting_available_for("Swim", "ftp")(self.data))


class TestSportSettingSensors(unittest.TestCase):
    """Test dynamic per-sport sensor generation."""

    def test_generates_one_set_per_sport(self) -> None:
        data = _make_data(
            athlete={
                "sportSettings": [
                    {"type": "Ride", "ftp": 280},
                    {"type": "Run", "ftp": 250},
                ]
            }
        )

        descriptions = _sport_setting_sensors(data)

        self.assertEqual(len(descriptions), 6)
        keys = [description.key for description in descriptions]
        self.assertIn("ftp_ride", keys)
        self.assertIn("ftp_run", keys)
        self.assertIn("lthr_ride", keys)
        self.assertIn("max_hr_run", keys)

    def test_sport_name_is_included_in_display_name(self) -> None:
        data = _make_data(athlete={"sportSettings": [{"type": "Ride"}]})

        descriptions = _sport_setting_sensors(data)

        self.assertEqual(descriptions[0].name, "Ride FTP")

    def test_no_sport_settings_yields_no_sensors(self) -> None:
        self.assertEqual(_sport_setting_sensors(_make_data()), ())

    def test_sport_slug_is_identifier_safe(self) -> None:
        data = _make_data(athlete={"sportSettings": [{"type": "Mountain Bike"}]})

        descriptions = _sport_setting_sensors(data)

        self.assertEqual(descriptions[0].key, "ftp_mountain_bike")


class TestLocalizeSport(unittest.TestCase):
    """Test sport display-name localization."""

    def test_chinese_labels_are_returned_for_zh_hans(self) -> None:
        self.assertEqual(localize_sport("Ride", "zh-Hans"), "骑行")
        self.assertEqual(localize_sport("Run", "zh-Hans"), "跑步")

    def test_traditional_chinese_uses_traditional_glyphs(self) -> None:
        self.assertEqual(localize_sport("Ride", "zh-Hant"), "騎行")
        self.assertEqual(localize_sport("WeightTraining", "zh-Hant"), "力量訓練")

    def test_zh_tw_is_treated_as_traditional(self) -> None:
        self.assertEqual(localize_sport("Ride", "zh-TW"), "騎行")

    def test_sports_without_variant_fall_back_to_simplified(self) -> None:
        # "Run" reads identically in both scripts, so it lives only in the
        # simplified table and is reused for traditional.
        self.assertEqual(localize_sport("Run", "zh-Hant"), "跑步")

    def test_english_returns_raw_api_value(self) -> None:
        self.assertEqual(localize_sport("Ride", "en"), "Ride")

    def test_unknown_sport_falls_back_to_raw_value(self) -> None:
        self.assertEqual(localize_sport("Quidditch", "zh-Hans"), "Quidditch")

    def test_mapping_covers_the_common_sports(self) -> None:
        for sport in ("Ride", "Run", "Swim", "Walk", "Hike"):
            with self.subTest(sport=sport):
                self.assertIn(sport, SPORT_DISPLAY_NAMES)

    def test_traditional_table_avoid_simplified_glyphs(self) -> None:
        # Guard against copying simplified labels into the traditional table.
        simplified_only = {"骑": "騎", "训": "訓", "虚": "虛", "电": "電"}
        for sport, label in SPORT_DISPLAY_NAMES_HANT.items():
            with self.subTest(sport=sport):
                for simplified, traditional in simplified_only.items():
                    self.assertNotIn(
                        simplified,
                        label,
                        f"{label!r} contains {simplified!r}, expected {traditional!r}",
                    )


class TestSensorPlaceholderLocalization(unittest.TestCase):
    """Test that the {sport} placeholder is localized before rendering."""

    def _make_sensor(self, language: str | None):
        core = sys.modules["homeassistant.core"]
        hass = core.HomeAssistant(language)

        coordinator = type("C", (), {})()
        coordinator.hass = hass
        coordinator.last_update_success = True
        coordinator.data = MagicMock()

        description = _sport_setting_sensors(
            _make_data(athlete={"sportSettings": [{"type": "Ride", "ftp": 280}]})
        )[0]
        return IntervalsIcuSensor(coordinator, description, "i12345")

    def test_sport_placeholder_is_translated_for_chinese(self) -> None:
        sensor = self._make_sensor("zh-Hans")
        self.assertEqual(sensor.translation_placeholders["sport"], "骑行")

    def test_sport_placeholder_is_raw_for_english(self) -> None:
        sensor = self._make_sensor("en")
        self.assertEqual(sensor.translation_placeholders["sport"], "Ride")

    def test_entity_id_is_unaffected_by_language(self) -> None:
        zh_sensor = self._make_sensor("zh-Hans")
        en_sensor = self._make_sensor("en")
        self.assertEqual(zh_sensor.unique_id, en_sensor.unique_id)
        self.assertEqual(zh_sensor.unique_id, "i12345_ftp_ride")


class TestStaticDescriptions(unittest.TestCase):
    """Guard the static sensor list against key regressions."""

    def test_no_duplicate_keys(self) -> None:
        keys = [description.key for description in SENSOR_DESCRIPTIONS]
        self.assertEqual(len(keys), len(set(keys)))

    def test_hrv_rmssd_key_is_gone(self) -> None:
        keys = {description.key for description in SENSOR_DESCRIPTIONS}
        self.assertNotIn("hrv_rmssd", keys)
        self.assertIn("hrv_sdnn", keys)

    def test_per_sport_keys_are_not_statically_defined(self) -> None:
        keys = {description.key for description in SENSOR_DESCRIPTIONS}
        for key in ("ftp", "lthr", "max_hr"):
            self.assertNotIn(key, keys)


class TestFormatDistance(unittest.TestCase):
    """Test human-readable distance labels."""

    def test_named_distances(self) -> None:
        self.assertEqual(_format_distance(5000.0), "5k")
        self.assertEqual(_format_distance(42195.0), "marathon")

    def test_round_kilometres(self) -> None:
        self.assertEqual(_format_distance(2000.0), "2k")

    def test_fractional_kilometres(self) -> None:
        self.assertEqual(_format_distance(1500.0), "1.5k")

    def test_sub_kilometre_distance(self) -> None:
        self.assertEqual(_format_distance(400.0), "400m")


if __name__ == "__main__":
    unittest.main()
