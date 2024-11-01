"""Switch handler."""

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import Platform

from .base_definitions import SwitchEntityDefinition
from .base_entity import BaseEntity, register_entity
from .const import DOMAIN, OPTIMISTIC_SWITCHES, RESTORE_ENTITIES
from .restore import restore_entities

_LOGGER = logging.getLogger(__name__)


# ===============================================================================
async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, add_entities: AddEntitiesCallback
):
    """Initialise climate platform."""
    platform = Platform.SWITCH
    entity_class = Switch

    @callback
    def register_new_entity(
        device: dr.DeviceEntry,
        entity_definition: SwitchEntityDefinition,
        unique_id: str,
        init_value: Any,
        attributes: dict[str, Any],
        extra_data: Any,
    ):
        register_entity(
            hass,
            config_entry,
            add_entities,
            platform,
            entity_class,
            device,
            entity_definition,
            unique_id,
            init_value,
            attributes,
            extra_data,
        )

    config_entry.async_on_unload(
        async_dispatcher_connect(
            hass,
            f"{DOMAIN}_{config_entry.entry_id}_register_{platform}_entity",
            register_new_entity,
        )
    )

    # Restore sensors for this config entry that have been registered previously.
    # Shows active sensors at startup even if no message from Panel yet received.
    # Restored sensors have their values from when HA was previously shut down/restarted.
    if RESTORE_ENTITIES:
        restore_entities(hass, config_entry, add_entities, platform, entity_class)


class Switch(BaseEntity, SwitchEntity):
    """Binary sensor class."""

    _attr_has_entity_name = True

    @property
    def is_on(self) -> bool:
        """Return if is on."""
        return self._value is True or self._value == STATE_ON

    async def async_turn_on(self, **kwargs):
        """Turn switch on."""
        payload = {
            "platform": Platform.SWITCH,
            "action": "turn_on",
            **kwargs,
            "extra_data": self._config.extra_data,
        }
        await self.api.send_command(**payload)
        if OPTIMISTIC_SWITCHES:
            self._value = True
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn switch off."""
        payload = {
            "platform": Platform.SWITCH,
            "action": "turn_off",
            **kwargs,
            "extra_data": self._config.extra_data,
        }
        await self.api.send_command(**payload)
        if OPTIMISTIC_SWITCHES:
            self._value = False
            self.async_write_ha_state()
