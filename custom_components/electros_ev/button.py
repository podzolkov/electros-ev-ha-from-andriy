"""Button platform for ElectroS EV Charger."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_CHARGER_LOGIN, DOMAIN
from .coordinator import ElectroSCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ElectroS buttons."""
    coordinator: ElectroSCoordinator = entry.runtime_data
    login = entry.data[CONF_CHARGER_LOGIN]

    async_add_entities([ElectroSResetEnergyButton(coordinator, entry, login)])


class ElectroSResetEnergyButton(CoordinatorEntity[ElectroSCoordinator], ButtonEntity):
    """Button to reset the consumed-energy (kWh) counter."""

    _attr_has_entity_name = True
    _attr_name = "Скинути кВт·год"
    _attr_icon = "mdi:counter"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: ElectroSCoordinator,
        entry: ConfigEntry,
        login: str,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._login = login
        self._attr_unique_id = f"{login}_reset_energy"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, login)},
            "name": f"ElectroS {login}",
            "manufacturer": "ElectroS",
            "model": "EV Charger",
        }

    async def async_press(self) -> None:
        """Reset the energy counter."""
        _LOGGER.info("Reset energy counter requested")
        await self.coordinator.async_reset_energy()
