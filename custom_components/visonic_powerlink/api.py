"""Websocket client handler."""

import asyncio
from collections.abc import Callable
import contextlib
from enum import IntEnum
import json
import logging
import socket

from websockets import ConnectionClosed
from websockets.asyncio.client import ClientConnection, connect

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_ARMING,
    STATE_ALARM_DISARMED,
    STATE_ALARM_DISARMING,
    STATE_ALARM_PENDING,
    STATE_ALARM_TRIGGERED,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import json as hajs

from .base_api import BaseAPI


class ArmModes(IntEnum):
    """Arm mode command codes."""

    DISARM = 0
    EXIT_DELAY_ARM_HOME = 1
    EXIT_DELAY_ARM_AWAY = 2
    ENTRY_DELAY = 3
    ARM_HOME = 4
    ARM_AWAY = 5
    WALK_TEST = 6
    USER_TEST = 7
    ARM_INSTANT_HOME = 14
    ARM_INSTANT_AWAY = 15


_LOGGER = logging.getLogger(__name__)


class API(BaseAPI):
    """Websocket client."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        cb_message: Callable,
        cb_connection_stage_change: Callable,
    ) -> None:
        """Initialise."""
        super().__init__(hass, config_entry, cb_message, cb_connection_stage_change)
        self.ws: ClientConnection = None
        self.connected: bool = False

    async def initialise(self):
        """Start client."""
        host = self.config_entry.data.get(CONF_HOST)
        port = self.config_entry.data.get(CONF_PORT)
        if host and port:
            url = f"ws://{host}:{port}"
            self.config_entry.async_create_background_task(
                self.hass, self.run_websocket(url), "Websocket Task"
            )

        else:
            _LOGGER.error("Unable to initialise. Invalid config flow configuration")

    async def run_websocket(self, url: str):
        """Run websocket - run this as task."""
        while True:
            try:
                async with connect(url) as websocket:
                    self.set_connection_state(True)
                    self.ws = websocket
                    _LOGGER.info("Connected to websocket server at %s", url)
                    await self.send('{"request":"status"}')
                    try:
                        async for message in websocket:
                            _LOGGER.debug("Websocket message received")
                            with contextlib.suppress(json.JSONDecodeError):
                                message = json.loads(message)
                                if message.get("panel"):
                                    self.cb_message(message)

                    except (ConnectionError, ConnectionClosed):
                        self.set_connection_state(False)
                        _LOGGER.warning(
                            "Websocket connection closed. Will try to reconnect"
                        )
                        continue
            except ConnectionRefusedError:
                _LOGGER.error(
                    "Unable to connect to websocket server at %s.  Retrying in 5s",
                    url,
                )
                self.set_connection_state(False)
                await asyncio.sleep(5)
            except (socket.gaierror, OSError):
                _LOGGER.error(
                    "Unable to connect to websockets host.  Ensure the Visonic Proxy addon is running and then check your configuration"
                )
                break

    async def shutdown(self):
        """Disconnect WS client."""
        if self.ws:
            await self.ws.close()

    async def send_command(self, **kwargs):
        """Handle command issue to websocket."""
        _LOGGER.debug("Send command data: %s", kwargs)
        str_json = None
        platform = kwargs.get("platform")
        if extra_data := kwargs.get("extra_data"):
            # Alarm
            if platform == Platform.ALARM_CONTROL_PANEL:
                str_json = {
                    "request": "arm",
                    "partition": int(extra_data.get("partition")),
                    "state": extra_data.get(kwargs.get("action")),
                }
                if code := extra_data.get("code"):
                    str_json["code"] = code
            # Switches
            if platform == Platform.SWITCH:
                switch_type = extra_data.get("type")
                str_json = {
                    "request": kwargs["action"],
                    "type": switch_type,
                }
                if switch_type in ["bypass", "chime"]:
                    str_json["zone"] = int(extra_data.get("zone_id"))

                elif switch_type == "pgm":
                    str_json["pgm_id"] = int(extra_data.get("pgm_id"))

            elif platform == Platform.BUTTON:
                request = extra_data.get("request")
                if request == "arm":
                    str_json = {
                        "request": request,
                        "partition": extra_data.get("partition"),
                        "state": extra_data.get("state"),
                    }

        if self.connected and str_json:
            _LOGGER.debug("SENDING: %s", str_json)
            await self.send(str_json)
        else:
            _LOGGER.warning("Unknown command")

    async def send(self, msg: dict | str):
        """Send to ws."""

        if isinstance(msg, dict):
            try:
                msg = hajs.json_dumps(msg)
            except json.JSONEncoder:
                return
        await self.ws.send(msg)

    def set_connection_state(self, state: bool):
        """Set connection state."""
        if self.connected != state:
            self.connected = state
            # if self.cb_connection:
            #    self.cb_connection(self.connected)

    def alarm_state_mapping(self, state: dict) -> str:
        """Map partiiton state to HA values."""
        status = state.get("status")
        # arming = kwargs.get("arming")
        disarming = state.get("disarming")

        if disarming and status != "Disarmed":
            return STATE_ALARM_DISARMING
        if status in ["ExitDelay_ArmHome", "ExitDelay_ArmAway"]:
            return STATE_ALARM_ARMING
        if status == "EntryDelay":
            return STATE_ALARM_PENDING
        if status == "Armed Home":
            return STATE_ALARM_ARMED_HOME
        if status == "Armed Away":
            return STATE_ALARM_ARMED_AWAY
        if status == "Disarmed":
            return STATE_ALARM_DISARMED
        if status == "Triggered":
            return STATE_ALARM_TRIGGERED
        return status
