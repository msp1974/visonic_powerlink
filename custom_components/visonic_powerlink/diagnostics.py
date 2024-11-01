"""Diagnostics support for Visonic."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntry

from . import APIManager
from .const import DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    return _async_get_diagnostics(hass, entry)


@callback
def _async_get_diagnostics(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    device: DeviceEntry | None = None,
) -> dict[str, Any]:
    api_handlder: APIManager = hass.data[DOMAIN][config_entry.entry_id]["api_handler"]

    return anonymise_data(api_handlder.data)


def anonymise_data(json_data: dict) -> dict:
    """Replace parts of the logfiles containing personal information."""

    replacements = {
        "id": "XXXXXX",
        "download_code": "0000",
        "master_user_code": "0000",
        "device_id": "000-0000",
    }

    if isinstance(json_data, dict):
        for key, value in json_data.items():
            if isinstance(value, dict):
                json_data[key] = anonymise_data(value)
            elif isinstance(value, list):
                key_data = []
                for item in value:
                    key_data.append(anonymise_data(item))
                json_data[key] = key_data
            elif key in replacements:
                json_data[key] = replacements[key]
    return json_data
