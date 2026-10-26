"""ElectroS EV Charger integration for Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .charger_api import ElectroSApi
from .const import (
    CONF_CHARGER_LOGIN,
    CONF_CHARGER_PASSWORD,
    CONF_HOST,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import ElectroSCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH, Platform.NUMBER]

type ElectroSConfigEntry = ConfigEntry[ElectroSCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: ElectroSConfigEntry) -> bool:
    """Set up ElectroS EV Charger from a config entry."""
    login = entry.data[CONF_CHARGER_LOGIN]
    password = entry.data[CONF_CHARGER_PASSWORD]
    scan_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    host = entry.data.get(CONF_HOST) or None

    api = ElectroSApi(login=login, password=password, host=host)
    coordinator = ElectroSCoordinator(hass, api, scan_interval)

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ElectroSConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
