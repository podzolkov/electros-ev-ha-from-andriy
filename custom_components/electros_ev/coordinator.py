"""DataUpdateCoordinator for ElectroS EV Charger."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .charger_api import ElectroSApi, normalize_amps
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

COMMAND_SETTLE_DELAY = 3   # seconds to wait after sending a command before first refresh
POST_STOP_REFRESHES = 3    # how many times to refresh after stop
POST_STOP_INTERVAL = 5     # seconds between post-stop refreshes


class ElectroSCoordinator(DataUpdateCoordinator[dict]):
    """Coordinator to manage fetching ElectroS charger data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: ElectroSApi,
        scan_interval: int,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.api = api
        self.target_amps: int = 6        # desired amps set by user
        self._user_set_amps: bool = False # True once user has explicitly set amps

    async def _async_update_data(self) -> dict:
        """Fetch data from the charger."""
        try:
            data = await self.api.get_state()
        except Exception as err:
            raise UpdateFailed(f"Error communicating with charger: {err}") from err

        if data.get("status_text", "").startswith("error"):
            raise UpdateFailed(f"Charger returned error: {data['status_text']}")

        # Only sync target_amps from charger if user has NOT explicitly set it.
        # This prevents the poll from overwriting what the user set on the slider.
        if not self._user_set_amps:
            charger_amps = data.get("current_amps")
            if charger_amps is not None and charger_amps > 0:
                self.target_amps = charger_amps
                _LOGGER.debug("Synced target_amps from charger: %d A", charger_amps)

        return data

    async def async_start_charging(self, amps: int) -> bool:
        """Start charging at specified amperage with settle delay."""
        amps = normalize_amps(amps)
        if amps <= 0:
            _LOGGER.warning("Cannot start charging with 0 amps")
            return False
        _LOGGER.info("Starting charging at %d A", amps)
        success = await self.api.start_charging(amps)
        if success:
            self.target_amps = amps
            self._user_set_amps = True
            await asyncio.sleep(COMMAND_SETTLE_DELAY)
            await self.async_request_refresh()
        return success

    async def async_stop_charging(self) -> bool:
        """Stop charging and do multiple refreshes to update all sensors."""
        _LOGGER.info("Stopping charging")
        success = await self.api.stop_charging()
        if success:
            # Multiple refreshes so power/current/status all update promptly
            for i in range(POST_STOP_REFRESHES):
                await asyncio.sleep(COMMAND_SETTLE_DELAY if i == 0 else POST_STOP_INTERVAL)
                _LOGGER.debug("Post-stop refresh %d/%d", i + 1, POST_STOP_REFRESHES)
                await self.async_request_refresh()
        return success

    async def async_reset_energy(self) -> bool:
        """Reset the charger's consumed-energy counter and refresh."""
        _LOGGER.info("Resetting energy counter")
        success = await self.api.reset_energy()
        if success:
            await asyncio.sleep(COMMAND_SETTLE_DELAY)
            await self.async_request_refresh()
        return success

    async def async_set_amps(self, amps: int) -> bool:
        """Set target amperage.

        Always stores the value (so slider keeps it).
        Only sends command to charger if currently charging.
        """
        amps = normalize_amps(amps)
        if amps <= 0:
            _LOGGER.warning("Invalid amperage: %d", amps)
            return False

        old_amps = self.target_amps
        self.target_amps = amps
        self._user_set_amps = True  # lock: don't overwrite with charger poll
        _LOGGER.info("Target amps set to %d A (was %d A)", amps, old_amps)

        # Notify HA that the number entity value changed immediately
        self.async_update_listeners()

        # Only send command to charger if it's currently charging
        if self.data and self.data.get("status_text") == "charging":
            _LOGGER.info("Charger is active, updating amps to %d A", amps)
            success = await self.api.start_charging(amps)
            if success:
                await asyncio.sleep(COMMAND_SETTLE_DELAY)
                await self.async_request_refresh()
            return success

        # Not charging — value stored, will be used on next turn_on
        return True
