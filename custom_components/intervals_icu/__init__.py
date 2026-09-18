"""The Intervals.icu integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import IntervalsIcuClient
from .const import (
    CONF_API_KEY,
    CONF_ATHLETE_ID,
    DOMAIN,
    RENAMED_SENSOR_KEYS,
)
from .coordinator import IntervalsIcuCoordinator

PLATFORMS = ["calendar", "sensor"]


async def _async_migrate_renamed_sensors(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Rename entity unique IDs for sensors whose key changed.

    Renaming a sensor key changes its unique ID, which would otherwise orphan
    the existing entity and lose its long-term statistics. Rewriting the
    registry entry in place preserves the entity ID and its history.
    """
    registry = er.async_get(hass)
    athlete_id = entry.data[CONF_ATHLETE_ID]

    for old_key, new_key in RENAMED_SENSOR_KEYS.items():
        old_unique_id = f"{athlete_id}_{old_key}"
        new_unique_id = f"{athlete_id}_{new_key}"

        entity_id = registry.async_get_entity_id("sensor", DOMAIN, old_unique_id)
        if entity_id is None:
            continue

        if registry.async_get_entity_id("sensor", DOMAIN, new_unique_id) is not None:
            # The new entity already exists; drop the stale renamed one.
            registry.async_remove(entity_id)
            continue

        registry.async_update_entity(entity_id, new_unique_id=new_unique_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Intervals.icu from a config entry."""
    await _async_migrate_renamed_sensors(hass, entry)

    session = async_get_clientsession(hass)
    client = IntervalsIcuClient(
        session=session,
        athlete_id=entry.data[CONF_ATHLETE_ID],
        api_key=entry.data[CONF_API_KEY],
    )

    coordinator = IntervalsIcuCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
