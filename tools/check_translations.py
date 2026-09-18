"""Validate translation files against the English source.

Run with the repository virtualenv:

    ./.venv/Scripts/python.exe tools/check_translations.py

Checks that:
  * every translation file parses as JSON,
  * each language exposes exactly the same key structure as ``en.json``
    (a mismatch makes Home Assistant silently fall back to English),
  * every ``translation_key`` referenced in the code has an entry,
  * placeholder sets match between languages.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from string import Formatter

ROOT = Path(__file__).resolve().parent.parent
COMPONENT = ROOT / "custom_components" / "intervals_icu"
TRANSLATIONS = COMPONENT / "translations"

SOURCE = COMPONENT / "strings.json"
REFERENCE = TRANSLATIONS / "en.json"


def flatten(node: object, prefix: str = "") -> dict[str, object]:
    """Flatten a nested dict into dotted paths."""
    if isinstance(node, dict):
        flat: dict[str, object] = {}
        for key, value in node.items():
            path = f"{prefix}.{key}" if prefix else key
            flat.update(flatten(value, path))
        return flat
    return {prefix: node}


def placeholders(value: object) -> set[str]:
    """Extract ``{name}`` placeholders from a translation string."""
    if not isinstance(value, str):
        return set()
    return {
        field for _, field, _, _ in Formatter().parse(value) if field
    }


def main() -> int:
    failures: list[str] = []

    for path in (SOURCE, REFERENCE, *sorted(TRANSLATIONS.glob("*.json"))):
        if not path.exists():
            failures.append(f"missing file: {path.relative_to(ROOT)}")
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as err:
            failures.append(f"invalid JSON in {path.relative_to(ROOT)}: {err}")

    if failures:
        for failure in failures:
            print("FAIL:", failure)
        return 1

    source = flatten(json.loads(SOURCE.read_text(encoding="utf-8")))
    reference = flatten(json.loads(REFERENCE.read_text(encoding="utf-8")))
    source_keys = set(source)
    reference_keys = set(reference)

    print(f"source      : strings.json ({len(source_keys)} keys)")
    print(f"reference   : en.json ({len(reference_keys)} keys)")

    if source_keys != reference_keys:
        for key in sorted(source_keys - reference_keys):
            failures.append(f"en.json missing key: {key}")
        for key in sorted(reference_keys - source_keys):
            failures.append(f"en.json has extra key: {key}")

    print()
    for path in sorted(TRANSLATIONS.glob("*.json")):
        if path.name == "en.json":
            continue
        data = flatten(json.loads(path.read_text(encoding="utf-8")))
        keys = set(data)
        status = "OK  "
        problems: list[str] = []

        for key in sorted(reference_keys - keys):
            problems.append(f"missing key: {key}")
        for key in sorted(keys - reference_keys):
            problems.append(f"extra key: {key}")
        for key in sorted(keys & reference_keys):
            if placeholders(reference[key]) != placeholders(data[key]):
                problems.append(
                    f"placeholder mismatch at {key}: "
                    f"{sorted(placeholders(reference[key]))} != "
                    f"{sorted(placeholders(data[key]))}"
                )
        for key in sorted(keys & reference_keys):
            value = data[key]
            if not isinstance(value, str) or not value.strip():
                problems.append(f"empty translation at {key}")

        if problems:
            status = "FAIL"
            failures.extend(f"{path.name}: {problem}" for problem in problems)

        print(f"{status}        : {path.name} ({len(keys)} keys)")

    print()
    sensor_src = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
    calendar_src = (COMPONENT / "calendar.py").read_text(encoding="utf-8")
    used = set(re.findall(r'translation_key="([a-z_0-9]+)"', sensor_src))
    used |= set(re.findall(r'"([a-z_]+)"\),?$', sensor_src, re.MULTILINE)) & set()
    used |= set(re.findall(r'_attr_translation_key = "([a-z_]+)"', calendar_src))

    # Per-sport keys are referenced from the _SPORT_FIELDS table at runtime
    # rather than appearing as a literal ``translation_key=`` argument.
    for match in re.finditer(
        r'\(\s*"([a-z_0-9]+)"\s*,\s*"[^"]*"\s*,\s*[^,]+,\s*"([a-z_0-9]+)"\s*\)',
        sensor_src,
    ):
        used.add(match.group(2))

    declared_sensor_keys = {
        key.removeprefix("entity.sensor.").removesuffix(".name")
        for key in reference_keys
        if key.startswith("entity.sensor.")
    }
    unreferenced = sorted(declared_sensor_keys - used)

    print(f"translation_key used in code : {len(used)}")
    if unreferenced:
        failures.extend(
            f"declared but not referenced in code: entity.sensor.{key}"
            for key in unreferenced
        )
        print("note: declared but not referenced (review manually):")
        for key in unreferenced:
            print("  -", key)

    print()
    if failures:
        for failure in failures:
            print("FAIL:", failure)
        print(f"\n{len(failures)} problem(s) found")
        return 1

    print("all translation files are consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
