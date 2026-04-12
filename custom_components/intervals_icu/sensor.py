"""Sensor platform for Intervals.icu."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfMass,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_ATHLETE_ID, DOMAIN
from .coordinator import IntervalsIcuCoordinator, IntervalsIcuData


@dataclass(frozen=True, kw_only=True)
class IntervalsIcuSensorEntityDescription(SensorEntityDescription):
    """Describe an Intervals.icu sensor."""

    value_fn: Callable[[IntervalsIcuData], Any]
    available_fn: Callable[[IntervalsIcuData], bool] = lambda _data: True


def _wellness_value(key: str) -> Callable[[IntervalsIcuData], Any]:
    """Create a value function for a wellness field."""

    def _get(data: IntervalsIcuData) -> Any:
        if data.wellness is None:
            return None
        return data.wellness.get(key)

    return _get


def _wellness_available(data: IntervalsIcuData) -> bool:
    return data.wellness is not None


def _latest_activity_value(key: str) -> Callable[[IntervalsIcuData], Any]:
    """Create a value function for the latest activity field."""

    def _get(data: IntervalsIcuData) -> Any:
        if not data.activities:
            return None
        return data.activities[0].get(key)

    return _get


def _latest_activity_available(data: IntervalsIcuData) -> bool:
    return len(data.activities) > 0


def _next_event_value(key: str) -> Callable[[IntervalsIcuData], Any]:
    """Create a value function for the next planned event."""

    def _get(data: IntervalsIcuData) -> Any:
        workouts = [e for e in data.events if e.get("category") == "WORKOUT"]
        if not workouts:
            return None
        return workouts[0].get(key)

    return _get


def _next_event_available(data: IntervalsIcuData) -> bool:
    return any(e.get("category") == "WORKOUT" for e in data.events)


def _athlete_value(key: str) -> Callable[[IntervalsIcuData], Any]:
    def _get(data: IntervalsIcuData) -> Any:
        return data.athlete.get(key)

    return _get


SENSOR_DESCRIPTIONS: tuple[IntervalsIcuSensorEntityDescription, ...] = (
    # Wellness sensors
    IntervalsIcuSensorEntityDescription(
        key="weight",
        translation_key="weight",
        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
        device_class=SensorDeviceClass.WEIGHT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_wellness_value("weight"),
        available_fn=_wellness_available,
    ),
    IntervalsIcuSensorEntityDescription(
        key="resting_hr",
        translation_key="resting_hr",
        native_unit_of_measurement="bpm",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_wellness_value("restingHR"),
        available_fn=_wellness_available,
    ),
    IntervalsIcuSensorEntityDescription(
        key="hrv",
        translation_key="hrv",
        native_unit_of_measurement="ms",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_wellness_value("hrv"),
        available_fn=_wellness_available,
    ),
    IntervalsIcuSensorEntityDescription(
        key="sleep_time",
        translation_key="sleep_time",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_wellness_value("sleepTime"),
        available_fn=_wellness_available,
    ),
    IntervalsIcuSensorEntityDescription(
        key="sleep_score",
        translation_key="sleep_score",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_wellness_value("sleepScore"),
        available_fn=_wellness_available,
    ),
    IntervalsIcuSensorEntityDescription(
        key="readiness",
        translation_key="readiness",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_wellness_value("readiness"),
        available_fn=_wellness_available,
    ),
    IntervalsIcuSensorEntityDescription(
        key="spo2",
        translation_key="spo2",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_wellness_value("spO2"),
        available_fn=_wellness_available,
    ),
    IntervalsIcuSensorEntityDescription(
        key="steps",
        translation_key="steps",
        native_unit_of_measurement="steps",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_wellness_value("steps"),
        available_fn=_wellness_available,
    ),
    IntervalsIcuSensorEntityDescription(
        key="ctl",
        translation_key="ctl",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_wellness_value("ctl"),
        available_fn=_wellness_available,
    ),
    IntervalsIcuSensorEntityDescription(
        key="atl",
        translation_key="atl",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_wellness_value("atl"),
        available_fn=_wellness_available,
    ),
    IntervalsIcuSensorEntityDescription(
        key="ramp_rate",
        translation_key="ramp_rate",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_wellness_value("rampRate"),
        available_fn=_wellness_available,
    ),
    # Latest activity sensors
    IntervalsIcuSensorEntityDescription(
        key="last_activity_name",
        translation_key="last_activity_name",
        value_fn=_latest_activity_value("name"),
        available_fn=_latest_activity_available,
    ),
    IntervalsIcuSensorEntityDescription(
        key="last_activity_type",
        translation_key="last_activity_type",
        value_fn=_latest_activity_value("type"),
        available_fn=_latest_activity_available,
    ),
    IntervalsIcuSensorEntityDescription(
        key="last_activity_duration",
        translation_key="last_activity_duration",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        value_fn=_latest_activity_value("moving_time"),
        available_fn=_latest_activity_available,
    ),
    IntervalsIcuSensorEntityDescription(
        key="last_activity_distance",
        translation_key="last_activity_distance",
        native_unit_of_measurement="m",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_latest_activity_value("distance"),
        available_fn=_latest_activity_available,
    ),
    IntervalsIcuSensorEntityDescription(
        key="last_activity_training_load",
        translation_key="last_activity_training_load",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_latest_activity_value("icu_training_load"),
        available_fn=_latest_activity_available,
    ),
    # Next planned workout sensors
    IntervalsIcuSensorEntityDescription(
        key="next_workout_name",
        translation_key="next_workout_name",
        value_fn=_next_event_value("name"),
        available_fn=_next_event_available,
    ),
    IntervalsIcuSensorEntityDescription(
        key="next_workout_date",
        translation_key="next_workout_date",
        device_class=SensorDeviceClass.DATE,
        value_fn=_next_event_value("start_date_local"),
        available_fn=_next_event_available,
    ),
    IntervalsIcuSensorEntityDescription(
        key="next_workout_type",
        translation_key="next_workout_type",
        value_fn=_next_event_value("type"),
        available_fn=_next_event_available,
    ),
    # Athlete fitness metrics
    IntervalsIcuSensorEntityDescription(
        key="ftp",
        translation_key="ftp",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_athlete_value("icu_ftp"),
        available_fn=lambda data: data.athlete.get("icu_ftp") is not None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Intervals.icu sensors from a config entry."""
    coordinator: IntervalsIcuCoordinator = hass.data[DOMAIN][entry.entry_id]
    athlete_id = entry.data[CONF_ATHLETE_ID]

    async_add_entities(
        IntervalsIcuSensor(coordinator, description, athlete_id)
        for description in SENSOR_DESCRIPTIONS
    )


class IntervalsIcuSensor(CoordinatorEntity[IntervalsIcuCoordinator], SensorEntity):
    """Representation of an Intervals.icu sensor."""

    entity_description: IntervalsIcuSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: IntervalsIcuCoordinator,
        description: IntervalsIcuSensorEntityDescription,
        athlete_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{athlete_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, athlete_id)},
            name="Intervals.icu",
            manufacturer="Intervals.icu",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if not super().available:
            return False
        return self.entity_description.available_fn(self.coordinator.data)
