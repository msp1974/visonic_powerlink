"""Select handler."""

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import Platform

from .base_definitions import SelectEntityDefinition
from .base_entity import BaseEntity, register_entity
from .const import DOMAIN, RESTORE_ENTITIES
from .restore import restore_entities

_LOGGER = logging.getLogger(__name__)


# ===============================================================================
async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, add_entities: AddEntitiesCallback
):
    """Initialise climate platform."""
    platform = Platform.SELECT
    entity_class = Select

    @callback
    def register_new_entity(
        device: dr.DeviceEntry,
        entity_definition: SelectEntityDefinition,
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


class Select(BaseEntity, SelectEntity):
    """Select entity class."""

    _attr_has_entity_name = True

    @property
    def options(self) -> list[str]:
        """Return a set of selectable options."""
        return self.get_def_key(self.definition.options)

    @property
    def current_option(self) -> str | None:
        """Return the selected entity option to represent the entity state."""
        return self._value

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        payload = {
            "platform": Platform.SELECT,
            "action": "select_option",
            "option": option,
            "extra_data": self._config.extra_data,
        }
        await self.api.send_command(**payload)
