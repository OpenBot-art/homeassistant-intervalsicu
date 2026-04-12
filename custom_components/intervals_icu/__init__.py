"""The Intervals.icu integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import IntervalsIcuClient
from .const import CONF_API_KEY, CONF_ATHLETE_ID, DOMAIN
from .coordinator import IntervalsIcuCoordinator

PLATFORMS = ["calendar", "sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Intervals.icu from a config entry."""
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
