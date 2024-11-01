"""Binary sensor handler."""

import logging
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import Platform

from .base_definitions import BinarySensorEntityDefinition
from .base_entity import BaseEntity, register_entity
from .const import DOMAIN, RESTORE_ENTITIES
from .restore import restore_entities

_LOGGER = logging.getLogger(__name__)


# ===============================================================================
async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, add_entities: AddEntitiesCallback
):
    """Initialise climate platform."""
    platform = Platform.BINARY_SENSOR
    entity_class = BinarySensor

    @callback
    def register_new_entity(
        device: dr.DeviceEntry,
        entity_definition: BinarySensorEntityDefinition,
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


class BinarySensor(BaseEntity, BinarySensorEntity):
    """Binary sensor class."""

    _attr_has_entity_name = True

    @property
    def is_on(self) -> bool:
        """Return if is on."""
        return self._value is True or self._value == "on"
