"""Minimal stand-ins for Home Assistant modules used by the test suite.

The real ``homeassistant`` distribution pulls in a large dependency tree
(FastAPI, SQLAlchemy, numpy, ...) which is impractical to install just to run
the pure-logic unit tests in this repository. These stubs provide exactly the
surface the integration imports so ``tests/`` can run in a bare environment.

They are only used when ``homeassistant`` is not importable; when the real
package is present it is imported normally and these stubs are ignored.
"""

from __future__ import annotations

import sys
import types
from dataclasses import dataclass, field
from datetime import timedelta, timezone
from typing import Any


def _install() -> None:
    try:
        import homeassistant  # noqa: F401

        return
    except ImportError:
        pass

    def _module(name: str) -> types.ModuleType:
        module = types.ModuleType(name)
        sys.modules[name] = module
        return module

    # --- homeassistant.core -------------------------------------------------
    core = _module("homeassistant.core")
    class _Config:
        """Minimal ``hass.config`` carrying the active language."""

        def __init__(self, language: str | None = None) -> None:
            self.language = language

    class HomeAssistant:
        """Minimal HomeAssistant instance."""

        def __init__(self, language: str | None = None) -> None:
            self.config = _Config(language)
            self.data: dict[str, Any] = {}

    core.HomeAssistant = HomeAssistant

    # --- homeassistant.const ------------------------------------------------
    const = _module("homeassistant.const")

    class _Unit:
        def __init__(self, value: str) -> None:
            self.value = value

        def __str__(self) -> str:  # pragma: no cover - trivial
            return self.value

    const.UnitOfMass = type("UnitOfMass", (), {"KILOGRAMS": "kg"})
    const.UnitOfTime = type("UnitOfTime", (), {"SECONDS": "s"})

    # --- homeassistant.util.dt ---------------------------------------------
    util = _module("homeassistant.util")
    util_dt = _module("homeassistant.util.dt")
    util_dt.DEFAULT_TIME_ZONE = timezone(timedelta(hours=8))
    util_dt.now = lambda: __import__("datetime").datetime.now(
        util_dt.DEFAULT_TIME_ZONE
    )
    util.dt = util_dt

    # --- homeassistant.config_entries --------------------------------------
    config_entries = _module("homeassistant.config_entries")

    class ConfigEntry:
        def __init__(self, data: dict[str, Any] | None = None) -> None:
            self.data = data or {}
            self.entry_id = "test-entry"

        def async_on_unload(self, _func: Any) -> None:
            return None

    class ConfigFlow:
        def __init_subclass__(cls, **kwargs: Any) -> None:
            super().__init_subclass__()

    config_entries.ConfigEntry = ConfigEntry
    config_entries.ConfigFlow = ConfigFlow
    config_entries.ConfigFlowResult = dict

    # --- homeassistant.components.sensor -----------------------------------
    components = _module("homeassistant.components")
    sensor = _module("homeassistant.components.sensor")

    class SensorDeviceClass:
        WEIGHT = "weight"
        DURATION = "duration"
        DISTANCE = "distance"
        POWER = "power"
        DATE = "date"

    class SensorStateClass:
        MEASUREMENT = "measurement"
        TOTAL_INCREASING = "total_increasing"

    @dataclass(frozen=True, kw_only=True)
    class SensorEntityDescription:
        key: str = ""
        name: str | None = None
        translation_key: str | None = None
        translation_placeholders: dict[str, str] | None = None
        native_unit_of_measurement: str | None = None
        device_class: Any = None
        state_class: Any = None

    class SensorEntity:
        pass

    sensor.SensorDeviceClass = SensorDeviceClass
    sensor.SensorStateClass = SensorStateClass
    sensor.SensorEntityDescription = SensorEntityDescription
    sensor.SensorEntity = SensorEntity
    components.sensor = sensor

    # --- homeassistant.components.calendar ---------------------------------
    calendar = _module("homeassistant.components.calendar")

    @dataclass
    class CalendarEvent:
        summary: str
        start: Any
        end: Any
        description: str | None = None

    class CalendarEntity:
        pass

    calendar.CalendarEvent = CalendarEvent
    calendar.CalendarEntity = CalendarEntity
    components.calendar = calendar

    # --- homeassistant.helpers.* -------------------------------------------
    helpers = _module("homeassistant.helpers")

    class DeviceEntryType:
        SERVICE = "service"

    @dataclass
    class DeviceInfo:
        identifiers: set = field(default_factory=set)
        name: str | None = None
        manufacturer: str | None = None
        entry_type: Any = None

    device_registry = _module("homeassistant.helpers.device_registry")
    device_registry.DeviceEntryType = DeviceEntryType
    device_registry.DeviceInfo = DeviceInfo
    helpers.device_registry = device_registry

    entity_platform = _module("homeassistant.helpers.entity_platform")
    entity_platform.AddEntitiesCallback = Any
    helpers.entity_platform = entity_platform

    entity_registry = _module("homeassistant.helpers.entity_registry")

    class _EntityRegistry:
        def __init__(self) -> None:
            self._entities: dict[str, str] = {}

        def async_get_entity_id(self, domain: str, platform: str, uid: str) -> Any:
            return self._entities.get(uid)

        def async_update_entity(self, entity_id: str, new_unique_id: str) -> None:
            for uid, eid in list(self._entities.items()):
                if eid == entity_id:
                    del self._entities[uid]
            self._entities[new_unique_id] = entity_id

        def async_remove(self, entity_id: str) -> None:
            for uid, eid in list(self._entities.items()):
                if eid == entity_id:
                    del self._entities[uid]

    entity_registry.async_get = lambda hass: _EntityRegistry()
    helpers.entity_registry = entity_registry

    aiohttp_client = _module("homeassistant.helpers.aiohttp_client")
    aiohttp_client.async_get_clientsession = lambda hass: None
    helpers.aiohttp_client = aiohttp_client

    update_coordinator = _module("homeassistant.helpers.update_coordinator")

    class UpdateFailed(Exception):
        pass

    class _Generic:
        """Support ``Class[TypeArg]`` subscription used in annotations."""

        def __class_getitem__(cls, _item: Any) -> type:
            return cls

    class DataUpdateCoordinator(_Generic):
        def __init__(
            self, hass: Any, logger: Any, *, name: str, update_interval: Any
        ) -> None:
            self.hass = hass
            self.logger = logger
            self.name = name
            self.update_interval = update_interval
            self.data: Any = None
            self.last_update_success = True

        def async_add_listener(self, _func: Any) -> Any:
            return lambda: None

    class CoordinatorEntity(_Generic):
        def __init__(self, coordinator: Any) -> None:
            self.coordinator = coordinator
            self.hass = getattr(coordinator, "hass", None)

        @property
        def available(self) -> bool:
            return self.coordinator.last_update_success

        @property
        def unique_id(self) -> Any:
            return getattr(self, "_attr_unique_id", None)

        @property
        def name(self) -> Any:
            return getattr(self, "_attr_name", None)

    update_coordinator.UpdateFailed = UpdateFailed
    update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
    update_coordinator.CoordinatorEntity = CoordinatorEntity
    helpers.update_coordinator = update_coordinator


_install()
