"""Verify that README.md documents the sensors the code actually exposes.

Run with the repository virtualenv:

    ./.venv/Scripts/python.exe tools/check_readme.py

The README previously listed sensors that no longer exist and omitted the
dynamic per-sport and best-effort sensors entirely. This script compares the
documented sensor names against the integration's translations so the docs
cannot silently drift from the code again.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import _ha_stubs  # noqa: E402,F401

from custom_components.intervals_icu.sensor import SENSOR_DESCRIPTIONS  # noqa: E402

README = ROOT / "README.md"
TRANSLATIONS = (
    ROOT / "custom_components" / "intervals_icu" / "translations"
)


def main() -> int:
    readme = README.read_text(encoding="utf-8")
    zh = json.loads((TRANSLATIONS / "zh-Hans.json").read_text(encoding="utf-8"))
    en = json.loads((TRANSLATIONS / "en.json").read_text(encoding="utf-8"))
    zh_sensors = zh["entity"]["sensor"]
    en_sensors = en["entity"]["sensor"]

    failures: list[str] = []

    missing_zh = []
    missing_en = []
    for description in SENSOR_DESCRIPTIONS:
        key = description.translation_key
        if key is None:
            continue
        zh_name = zh_sensors.get(key, {}).get("name")
        en_name = en_sensors.get(key, {}).get("name")
        if zh_name and zh_name not in readme:
            missing_zh.append((description.key, zh_name))
        if en_name and en_name not in readme:
            missing_en.append((description.key, en_name))

    print(f"static sensors in code : {len(SENSOR_DESCRIPTIONS)}")
    print(f"static sensors in zh   : {len(zh_sensors)}")
    print()

    if missing_zh:
        print("undocumented in the Chinese section:")
        for key, name in missing_zh:
            print(f"  - {key:<28} ({name})")
        failures.extend(f"missing zh doc for {key}" for key, _ in missing_zh)

    if missing_en:
        print("undocumented in the English section:")
        for key, name in missing_en:
            print(f"  - {key:<28} ({name})")
        failures.extend(f"missing en doc for {key}" for key, _ in missing_en)

    if not missing_zh and not missing_en:
        print("every sensor is documented in both languages")

    # Section headings that must exist for the bilingual layout.
    for heading in ("## English", "## 功能特性", "## 安装", "## 传感器"):
        if heading not in readme:
            failures.append(f"missing section: {heading}")

    # Sensor count quoted in the README must match reality.
    expected_count = len(SENSOR_DESCRIPTIONS)
    for claim in (f"{expected_count} 个静态传感器", f"{expected_count} static sensors"):
        if claim not in readme:
            failures.append(f"README does not state '{claim}'")

    print()
    if failures:
        for failure in failures:
            print("FAIL:", failure)
        print(f"\n{len(failures)} problem(s) found")
        return 1

    print("README is consistent with the code")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
