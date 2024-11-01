"""Config flow to setup component."""

import logging
from typing import Any

import voluptuous as vol
from websockets import connect

from homeassistant.config_entries import (
    CONN_CLASS_LOCAL_POLL,
    ConfigFlow,
    ConfigFlowResult,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default="homeassistant.local"): str,
        vol.Required(CONF_PORT, default=8082): int,
        vol.Required("pin_required", default=False): bool,
    }
)


async def validate_input(data):
    """Validate the user input allows us to connect."""
    try:
        url = f"ws://{data.get(CONF_HOST)}:{data.get(CONF_PORT)}"
        async with connect(url) as websocket:
            await websocket.close()
    except Exception as err:
        # raise friendly error after wrong input
        raise CannotConnect from err
    return {"title": "Visonic PowerLink"}


class VPConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1
    CONNECTION_CLASS = CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        """Handle the initial step."""
        errors = {}
        # Validate user input
        if user_input is not None:
            try:
                info = await validate_input(user_input)
                return self.async_create_entry(title=info["title"], data=user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add reconfigure step to allow to reconfigure a config entry."""

        errors: dict[str, str] = {}
        config_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )

        if user_input is not None:
            try:
                await validate_input(user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    config_entry,
                    unique_id=config_entry.unique_id,
                    data={**config_entry.data, **user_input},
                    reason="reconfigure_successful",
                )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=config_entry.data[CONF_HOST]): str,
                    vol.Required(CONF_PORT, default=config_entry.data[CONF_PORT]): int,
                    vol.Required(
                        "pin_required", default=config_entry.data["pin_required"]
                    ): bool,
                }
            ),
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
