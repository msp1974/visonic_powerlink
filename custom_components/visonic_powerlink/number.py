"""Number handler."""

import logging
from typing import Any

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import Platform

from .base_definitions import NumberEntityDefinition
from .base_entity import BaseEntity, register_entity
from .const import DOMAIN, RESTORE_ENTITIES
from .restore import restore_entities

_LOGGER = logging.getLogger(__name__)


# ===============================================================================
async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, add_entities: AddEntitiesCallback
):
    """Initialise climate platform."""
    platform = Platform.NUMBER
    entity_class = Number

    @callback
    def register_new_entity(
        device: dr.DeviceEntry,
        entity_definition: NumberEntityDefinition,
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


class Number(BaseEntity, NumberEntity):
    """Binary sensor class."""

    _attr_has_entity_name = True

    @property
    def native_min_value(self) -> float:
        """Return the minimum value."""
        return self.get_def_key(self._definition.min_value)

    @property
    def native_max_value(self) -> float:
        """Return the maximum value."""
        return self.get_def_key(self._definition.max_value)

    @property
    def native_value(self) -> float | None:
        """Return the value reported by the number."""
        return self._value

    @property
    def native_unit_of_measurement(self) -> str:
        """Return native unit of measure."""
        return self._definition.unit_of_measurement

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        payload = {
            "platform": Platform.NUMBER,
            "action": "set_value",
            "value": value,
            "extra_data": self._config.extra_data,
        }
        await self.api.send_command(**payload)
