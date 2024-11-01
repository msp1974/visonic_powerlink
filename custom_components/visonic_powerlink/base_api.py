from collections.abc import Callable
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval


class BaseAPI:
    """Base class for custom api."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        cb_message: Callable,
        cb_connection_stage_change: Callable | None = None,
        update_interval_seconds: int = 0,
    ) -> None:
        """Initialise."""
        self.hass = hass
        self.config_entry = config_entry
        self.cb_message = cb_message
        self.cb_connection = cb_connection_stage_change

        self._interval_timer = None

        if update_interval_seconds > 10:
            self._interval_timer = async_track_time_interval(
                hass, self.async_update_data, timedelta(seconds=update_interval_seconds)
            )

    async def initialise(self):
        """Initialise connection to device."""
        raise NotImplementedError(
            "No initialise method defined in your custom api class."
        )

    async def on_shutdown(self):
        """Run on shutdown."""
        if self._interval_timer:
            self._interval_timer()

        await self.shutdown()

    async def shutdown(self):
        """Disconnect connection to device."""
        raise NotImplementedError(
            "No shutdown method defined in your custom api class."
        )

    async def async_update_data(self, *args):
        """Update data."""

    async def receive_data(self, data: dict[str, Any]):
        """Receive data method.

        Use this to request data or as a callback from a push api
        """
        self.cb_message(await self.preprocess_data(data))

    async def send_command(self, **kwargs):
        """Handle command issue to websocket."""
        raise NotImplementedError(
            "No send_command method defined in your custom api class."
        )

    async def preprocess_data(self, data: dict[str | Any]) -> dict[str, Any]:
        """Preprocess data from api."""
        return data
