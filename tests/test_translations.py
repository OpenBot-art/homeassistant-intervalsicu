"""Tests that the translation files stay in sync with each other."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from string import Formatter

COMPONENT = (
    Path(__file__).resolve().parent.parent / "custom_components" / "intervals_icu"
)
TRANSLATIONS = COMPONENT / "translations"
SOURCE = COMPONENT / "strings.json"
REFERENCE = TRANSLATIONS / "en.json"


def _flatten(node: object, prefix: str = "") -> dict[str, object]:
    """Flatten a nested dict into dotted paths."""
    if isinstance(node, dict):
        flat: dict[str, object] = {}
        for key, value in node.items():
            path = f"{prefix}.{key}" if prefix else key
            flat.update(_flatten(value, path))
        return flat
    return {prefix: node}


def _load(path: Path) -> dict[str, object]:
    return _flatten(json.loads(path.read_text(encoding="utf-8")))


def _placeholders(value: object) -> set[str]:
    if not isinstance(value, str):
        return set()
    return {field for _, field, _, _ in Formatter().parse(value) if field}


class TestTranslationFiles(unittest.TestCase):
    """Guard the translation files against drift."""

    def setUp(self) -> None:
        self.source = _load(SOURCE)
        self.reference = _load(REFERENCE)

    def test_all_files_are_valid_json(self) -> None:
        for path in sorted(TRANSLATIONS.glob("*.json")):
            with self.subTest(path=path.name):
                json.loads(path.read_text(encoding="utf-8"))

    def test_strings_json_matches_english_translation(self) -> None:
        # Home Assistant requires these two to stay identical.
        self.assertEqual(self.source, self.reference)

    def test_every_language_matches_english_key_set(self) -> None:
        for path in sorted(TRANSLATIONS.glob("*.json")):
            if path.name == "en.json":
                continue
            with self.subTest(path=path.name):
                self.assertEqual(set(_load(path)), set(self.reference))

    def test_placeholders_match_across_languages(self) -> None:
        for path in sorted(TRANSLATIONS.glob("*.json")):
            data = _load(path)
            for key, reference_value in self.reference.items():
                if key not in data:
                    continue
                with self.subTest(path=path.name, key=key):
                    self.assertEqual(
                        _placeholders(data[key]),
                        _placeholders(reference_value),
                    )

    def test_no_empty_translations(self) -> None:
        for path in sorted(TRANSLATIONS.glob("*.json")):
            data = _load(path)
            for key, value in data.items():
                with self.subTest(path=path.name, key=key):
                    self.assertIsInstance(value, str)
                    self.assertTrue(value.strip(), f"empty translation at {key}")

    def test_chinese_translations_exist(self) -> None:
        self.assertTrue((TRANSLATIONS / "zh-Hans.json").exists())
        self.assertTrue((TRANSLATIONS / "zh-Hant.json").exists())


class TestTranslationKeysInCode(unittest.TestCase):
    """Ensure every declared sensor key is actually reachable from the code."""

    def test_all_sensor_translation_keys_are_referenced(self) -> None:
        sensor_src = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
        calendar_src = (COMPONENT / "calendar.py").read_text(encoding="utf-8")

        used = set(re.findall(r'translation_key="([a-z_0-9]+)"', sensor_src))
        used |= set(re.findall(r'_attr_translation_key = "([a-z_]+)"', calendar_src))
        # The per-sport sensors are built from a table, not a literal kwarg.
        for match in re.finditer(
            r'\(\s*"([a-z_0-9]+)"\s*,\s*"[^"]*"\s*,\s*[^,]+,\s*"([a-z_0-9]+)"\s*\)',
            sensor_src,
        ):
            used.add(match.group(2))

        declared = {
            key.removeprefix("entity.sensor.").removesuffix(".name")
            for key in _load(REFERENCE)
            if key.startswith("entity.sensor.")
        }

        self.assertEqual(
            sorted(declared - used),
            [],
            "sensor translation keys declared but never referenced in code",
        )

    def test_calendar_translation_key_is_referenced(self) -> None:
        calendar_src = (COMPONENT / "calendar.py").read_text(encoding="utf-8")
        self.assertIn('_attr_translation_key = "training_calendar"', calendar_src)
        self.assertIn("entity.calendar.training_calendar.name", _load(REFERENCE))


if __name__ == "__main__":
    unittest.main()
