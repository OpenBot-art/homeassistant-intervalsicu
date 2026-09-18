"""Render translation strings to confirm they resolve as expected.

Run with the repository virtualenv:

    ./.venv/Scripts/python.exe tools/render_translations.py [lang]

Prints the entity names Home Assistant would display for the given language,
including the per-sport sensors where the ``{sport}`` placeholder is filled in
from the athlete's configured sports.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import _ha_stubs  # noqa: E402,F401

from custom_components.intervals_icu.sensor import localize_sport  # noqa: E402

TRANSLATIONS = ROOT / "custom_components" / "intervals_icu" / "translations"

SPORTS = ["Ride", "Run"]


def main() -> int:
    lang = sys.argv[1] if len(sys.argv) > 1 else "zh-Hans"
    path = TRANSLATIONS / f"{lang}.json"
    if not path.exists():
        print(f"no such translation: {path.name}")
        return 1

    data = json.loads(path.read_text(encoding="utf-8"))
    sensors = data["entity"]["sensor"]
    calendar = data["entity"]["calendar"]

    print(f"=== {path.name} ===")
    print()
    print("配置流程:")
    step = data["config"]["step"]["user"]
    print(f"  标题      : {step['title']}")
    print(f"  说明      : {step['description']}")
    for key, label in step["data"].items():
        print(f"  字段 {key:<11}: {label}")
    print("  错误提示:")
    for key, message in data["config"]["error"].items():
        print(f"    {key:<16}: {message}")
    print("  中止提示:")
    for key, message in data["config"]["abort"].items():
        print(f"    {key:<16}: {message}")

    print()
    print("日历实体:")
    for entity in calendar.values():
        print(f"  {entity['name']}")

    print()
    print("实体名称 (静态):")
    static = {k: v["name"] for k, v in sensors.items() if "{sport}" not in v["name"]}
    for key, name in static.items():
        print(f"  {key:<28}: {name}")

    print()
    print("实体名称 (每运动，{sport} 已按语言本地化):")
    templated = {k: v["name"] for k, v in sensors.items() if "{sport}" in v["name"]}
    for sport in SPORTS:
        localized = localize_sport(sport, lang)
        for key, name in templated.items():
            rendered = name.replace("{sport}", localized)
            if lang.startswith("zh"):
                rendered += f"    (实体 ID: {key}_{sport.lower()})"
            print(f"  {key:<28}: {rendered}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

