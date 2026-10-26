"""Sensor platform for ElectroS EV Charger."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_CHARGER_LOGIN, DOMAIN, STATUS_TEXT
from .coordinator import ElectroSCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ElectroS sensors."""
    coordinator: ElectroSCoordinator = entry.runtime_data
    login = entry.data[CONF_CHARGER_LOGIN]

    entities = [
        ElectroSStatusSensor(coordinator, entry, login),
        ElectroSCurrentAmpsSensor(coordinator, entry, login),
        ElectroSMeasuredCurrentSensor(coordinator, entry, login),
        ElectroSVoltageSensor(coordinator, entry, login),
        ElectroSPowerSensor(coordinator, entry, login),
        ElectroSEnergySensor(coordinator, entry, login),
    ]
    async_add_entities(entities)


class ElectroSBaseSensor(CoordinatorEntity[ElectroSCoordinator], SensorEntity):
    """Base sensor for ElectroS charger."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ElectroSCoordinator,
        entry: ConfigEntry,
        login: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._login = login
        self._attr_device_info = {
            "identifiers": {(DOMAIN, login)},
            "name": f"ElectroS {login}",
            "manufacturer": "ElectroS",
            "model": "EV Charger",
        }


class ElectroSStatusSensor(ElectroSBaseSensor):
    """Sensor for charger status."""

    _attr_name = "Статус"
    _attr_icon = "mdi:ev-station"

    def __init__(self, coordinator, entry, login) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, login)
        self._attr_unique_id = f"{login}_status"

    @property
    def native_value(self) -> str | None:
        """Return the status."""
        if self.coordinator.data is None:
            return None
        code = self.coordinator.data.get("status_code")
        return STATUS_TEXT.get(code, self.coordinator.data.get("status_text", "unknown"))

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        if self.coordinator.data is None:
            return {}
        return {
            "online": self.coordinator.data.get("online"),
            "status_code": self.coordinator.data.get("status_code"),
            "status_text_en": self.coordinator.data.get("status_text"),
        }


class ElectroSCurrentAmpsSensor(ElectroSBaseSensor):
    """Sensor for configured charging current."""

    _attr_name = "Налаштований струм"
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_device_class = SensorDeviceClass.CURRENT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:current-ac"

    def __init__(self, coordinator, entry, login) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, login)
        self._attr_unique_id = f"{login}_current_amps"

    @property
    def native_value(self) -> int | None:
        """Return configured amps."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("current_amps")


class ElectroSMeasuredCurrentSensor(ElectroSBaseSensor):
    """Sensor for measured charging current."""

    _attr_name = "Виміряний струм"
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_device_class = SensorDeviceClass.CURRENT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:flash"

    def __init__(self, coordinator, entry, login) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, login)
        self._attr_unique_id = f"{login}_measured_current"

    @property
    def native_value(self) -> float | None:
        """Return measured current."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("measured_current")


class ElectroSVoltageSensor(ElectroSBaseSensor):
    """Sensor for mains voltage."""

    _attr_name = "Напруга мережі"
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:flash-outline"

    def __init__(self, coordinator, entry, login) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, login)
        self._attr_unique_id = f"{login}_mains_voltage"

    @property
    def native_value(self) -> int | None:
        """Return mains voltage."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("mains_voltage")


class ElectroSPowerSensor(ElectroSBaseSensor):
    """Sensor for charging power."""

    _attr_name = "Потужність зарядки"
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:lightning-bolt"

    def __init__(self, coordinator, entry, login) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, login)
        self._attr_unique_id = f"{login}_charging_power"

    @property
    def native_value(self) -> float | None:
        """Return charging power."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("charging_power_w")


class ElectroSEnergySensor(ElectroSBaseSensor):
    """Sensor for consumed energy (resettable counter, usable in the Energy dashboard)."""

    _attr_name = "Спожита енергія"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:counter"

    def __init__(self, coordinator, entry, login) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, login)
        self._attr_unique_id = f"{login}_energy"

    @property
    def native_value(self) -> float | None:
        """Return consumed energy."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("energy_kwh")
