"""Config flow for ElectroS EV Charger integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD

from .charger_api import ElectroSApi
from .const import (
    CONF_CHARGER_LOGIN,
    CONF_CHARGER_PASSWORD,
    CONF_HOST,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CHARGER_LOGIN): str,
        vol.Required(CONF_CHARGER_PASSWORD): str,
        vol.Optional(CONF_HOST): str,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            int, vol.Range(min=30, max=600)
        ),
    }
)


class ElectroSConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ElectroS EV Charger."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            login = user_input[CONF_CHARGER_LOGIN]
            password = user_input[CONF_CHARGER_PASSWORD]

            await self.async_set_unique_id(login)
            self._abort_if_unique_id_configured()

            api = ElectroSApi(
                login=login,
                password=password,
                host=user_input.get(CONF_HOST) or None,
            )
            try:
                if await api.test_connection():
                    return self.async_create_entry(
                        title=f"ElectroS {login}",
                        data=user_input,
                    )
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during config flow")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
