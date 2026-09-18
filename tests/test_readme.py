"""Tests that README.md stays consistent with the code.

The README previously documented sensors that no longer existed and omitted
the dynamic per-sport and best-effort sensors. These tests pin the bilingual
structure and the sensor list so the docs cannot quietly drift again.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from . import _ha_stubs  # noqa: F401  (installs HA stubs when HA is absent)
from custom_components.intervals_icu.sensor import SENSOR_DESCRIPTIONS

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
TRANSLATIONS = ROOT / "custom_components" / "intervals_icu" / "translations"


class TestReadmeStructure(unittest.TestCase):
    """Test the bilingual document layout."""

    def setUp(self) -> None:
        self.readme = README.read_text(encoding="utf-8")

    def test_chinese_section_comes_first(self) -> None:
        zh_first = self.readme.index("## 功能特性")
        en_start = self.readme.index("## English")
        self.assertLess(zh_first, en_start, "Chinese content must come first")

    def test_language_switcher_is_present(self) -> None:
        self.assertIn("[English](#english)", self.readme)
        self.assertIn("**简体中文**", self.readme)

    def test_required_sections_exist(self) -> None:
        for heading in (
            "## 功能特性",
            "## 安装",
            "## 配置",
            "## 传感器",
            "## 语言",
            "## 开发",
            "## English",
        ):
            with self.subTest(heading=heading):
                self.assertIn(heading, self.readme)

    def test_states_the_real_sensor_count(self) -> None:
        count = len(SENSOR_DESCRIPTIONS)
        self.assertIn(f"{count} 个静态传感器", self.readme)
        self.assertIn(f"{count} static sensors", self.readme)

    def test_documents_the_renamed_hrv_sensor(self) -> None:
        # The old README carried a stale "HRV SDNN" entry under a mismatched
        # key; make sure the current name is documented instead.
        self.assertIn("心率变异性 SDNN", self.readme)
        self.assertIn("HRV SDNN", self.readme)

    def test_documents_per_sport_sensors(self) -> None:
        self.assertIn("按运动类型生成", self.readme)
        self.assertIn("Per sport", self.readme)

    def test_documents_the_localization_caveat(self) -> None:
        # Entity IDs stay English; sport labels are localized in code because
        # Home Assistant does not translate placeholder values.
        self.assertIn("实体 ID 始终为英文", self.readme)
        self.assertIn("does not translate them", self.readme)


class TestReadmeSensorCoverage(unittest.TestCase):
    """Test that every sensor is documented in both languages."""

    def setUp(self) -> None:
        self.readme = README.read_text(encoding="utf-8")
        self.zh = json.loads((TRANSLATIONS / "zh-Hans.json").read_text(encoding="utf-8"))
        self.en = json.loads((TRANSLATIONS / "en.json").read_text(encoding="utf-8"))

    def _documented(self, language_file: dict) -> list[tuple[str, str]]:
        sensors = language_file["entity"]["sensor"]
        missing: list[tuple[str, str]] = []
        for description in SENSOR_DESCRIPTIONS:
            key = description.translation_key
            if key is None:
                continue
            name = sensors.get(key, {}).get("name")
            if name and name not in self.readme:
                missing.append((description.key, name))
        return missing

    def test_all_sensors_documented_in_chinese(self) -> None:
        self.assertEqual(self._documented(self.zh), [])

    def test_all_sensors_documented_in_english(self) -> None:
        self.assertEqual(self._documented(self.en), [])

    def test_no_stale_sensor_entries(self) -> None:
        # These were documented by the original README but never existed in
        # the code; guard against them creeping back.
        for stale in ("Basal calories", "Active calories", "Total calories"):
            with self.subTest(stale=stale):
                self.assertNotIn(stale, self.readme)


if __name__ == "__main__":
    unittest.main()
