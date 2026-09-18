"""End-to-end smoke check for the Intervals.icu integration logic.

Run with the repository virtualenv:

    ./.venv/Scripts/python.exe tools/smoke_check.py

Exercises the real client and coordinator against stubbed API responses to
confirm authentication, sorting, degradation and per-sport sensor generation
behave as intended outside of the unit test suite.
"""

from __future__ import annotations

import asyncio
import base64
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import aiohttp

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import _ha_stubs  # noqa: E402,F401  (installs HA stubs when HA is absent)

from custom_components.intervals_icu.api import IntervalsIcuClient  # noqa: E402
from custom_components.intervals_icu.coordinator import (  # noqa: E402
    IntervalsIcuCoordinator,
)
from custom_components.intervals_icu.sensor import _sport_setting_sensors  # noqa: E402


def main() -> int:
    session = MagicMock(spec=aiohttp.ClientSession)
    client = IntervalsIcuClient(session=session, athlete_id="i12345", api_key="secret")

    header = client._auth_headers["Authorization"]
    print("1. 认证头      :", header)
    print("   解码验证    :", base64.b64decode(header.removeprefix("Basic ")).decode())

    client.get_athlete = AsyncMock(
        return_value={
            "id": "i12345",
            "sportSettings": [
                {"type": "Run", "ftp": 250, "lthr": 168, "max_hr": 190},
                {"type": "Ride", "ftp": 280, "lthr": 165, "max_hr": 188},
            ],
        }
    )
    client.get_wellness = AsyncMock(
        return_value={"ctl": 62.4, "atl": 71.8, "hrvSDNN": 54}
    )
    client.get_activities = AsyncMock(
        return_value=[
            {"name": "周二慢跑", "start_date_local": "2026-09-15T06:30:00"},
            {"name": "", "start_date_local": "2026-09-17T18:00:00"},
            {"name": "周日长距离", "start_date_local": "2026-09-13T07:00:00"},
        ]
    )
    client.get_events = AsyncMock(
        return_value=[
            {
                "category": "WORKOUT",
                "name": "周五间歇",
                "start_date_local": "2026-09-25T18:00:00",
            },
            {
                "category": "WORKOUT",
                "name": "今天恢复跑",
                "start_date_local": "2026-09-18T18:00:00",
            },
            {"category": "NOTE", "name": "休息", "start_date_local": "2026-09-19"},
        ]
    )
    client.get_pace_curves = AsyncMock(
        return_value={"list": [{"distance": [5000.0], "values": [1284]}]}
    )

    coordinator = IntervalsIcuCoordinator(MagicMock(), client)
    data = asyncio.run(coordinator._async_update_data())

    print()
    print(
        "2. 最新活动    :",
        data.latest_activity["name"],
        "(期望 周二慢跑 — 空名记录被过滤)",
    )
    print("   活动顺序    :", [a["name"] for a in data.activities])
    print(
        "3. 下一个课表  :",
        data.next_workout["name"],
        "(期望 今天恢复跑 — 最早的一条)",
    )
    print("   事件顺序    :", [e.get("name") for e in data.events])
    print("4. Form (TSB)  :", round(data.wellness["ctl"] - data.wellness["atl"], 1))

    print()
    print("5. 每运动传感器 (修复前只暴露第一个运动的 FTP):")
    for description in _sport_setting_sensors(data):
        print(
            "   ",
            description.key.ljust(14),
            "|",
            description.name.ljust(18),
            "=",
            description.value_fn(data),
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
