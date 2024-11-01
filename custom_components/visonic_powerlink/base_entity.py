"""Base entity."""

from dataclasses import dataclass  # noqa: I001
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntry, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import Platform
from homeassistant.helpers.restore_state import RestoreEntity

from . import APIManager
from .const import DOMAIN
from .entity_definitions import ENTITY_DEFS
from .base_api import BaseAPI
from .base_definitions import (
    _AnyEntityDefinition,
    EntityConfig,
    EntityData,
)
from .helpers import get_key

TEXT_UNKNOWN = "unknown"
_LOGGER = logging.getLogger(__name__)


@dataclass
class ExtraStoredData:
    """Class to hold extra data to restore."""

    data: dict[str, str | int | float]

    def as_dict(self) -> dict[str, Any]:
        """Return a dict representation of the extra data.

        Must be serializable by Home Assistant's JSONEncoder.
        """
        return self.data


@callback
def register_entity(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    add_entities: AddEntitiesCallback,
    platform: Platform,
    entity_class,
    device: DeviceEntry,
    entity_definition: _AnyEntityDefinition,
    unique_id: str,
    init_value: Any,
    attributes: dict[str, Any],
    extra_data: Any,
):
    """Register a new entity."""
    _LOGGER.debug(
        "Registering new %s entity: %s value: %s, attributes: %s, extra data: %s",
        platform,
        entity_definition.key,
        init_value,
        attributes,
        extra_data,
    )

    if init_value is None:
        _LOGGER.error(
            "Unable to add %s entity, %s.  Parameter does not exist for this device",
            platform,
            entity_definition,
        )
        return

    config = EntityConfig(
        unique_id=unique_id,
        device_identifier=device.identifiers,
        initial_value=EntityData(
            data=init_value,
            attributes=attributes,
        ),
        config_entry=config_entry,
        extra_data=extra_data,
    )

    add_entities([entity_class(hass, entity_definition, config)])


class BaseEntity(RestoreEntity, Entity):
    """Base APSystems sensor class."""

    _attr_has_entity_name = True

    def __init__(
        self,
        hass: HomeAssistant,
        definition: _AnyEntityDefinition,
        config: EntityConfig,
    ) -> None:
        """Initialise sensor."""
        self.hass = hass
        self._definition = definition
        self._config = config

        self._api_manager: APIManager = self.hass.data[DOMAIN][
            self._config.config_entry.entry_id
        ]["api_handler"]

        self._attr_device_class = (
            definition.device_class if hasattr(definition, "device_class") else None
        )
        self._attr_device_info = DeviceInfo(identifiers=self._config.device_identifier)
        self._attr_name = self.get_def_key(config.name) or self.get_def_key(
            definition.name
        )
        self._attr_entity_category = definition.entity_category
        self._attr_icon = definition.icon
        self._extra_data = None
        self._attr_unique_id = self._config.unique_id

        self._value = None

    def get_entity_def(self, group_unique_id: str, entity_def_key: str) -> Any:
        """Get entity definition from group unique id and entity def key."""
        for entities_def in ENTITY_DEFS:
            if entities_def.unique_id == group_unique_id:
                for entity_def in entities_def.entity_definitions:
                    if entity_def.key == entity_def_key:
                        return entity_def
        return None

    @property
    def api(self) -> BaseAPI:
        """Return reference to api."""
        return self._api_manager.api

    @property
    def definition(self) -> _AnyEntityDefinition:
        """Get this entities definition."""
        return self.get_entity_def(
            self._config.extra_data.get("group_uid"),
            self._config.extra_data.get("key"),
        )

    @property
    def data(self) -> dict[str, Any]:
        """Get data."""
        return self._api_manager.data

    @property
    def device_data(self) -> dict[str, Any]:
        """Get data."""
        return get_key(self._config.extra_data.get("data_path"), self._api_manager.data)

    @property
    def should_poll(self):
        """Should poll for updates."""
        return False

    @property
    def available(self) -> bool:
        """Return availability status."""
        # TODO: Amend this to entity def!
        return str(self._value).lower() != TEXT_UNKNOWN

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        if self._config.initial_value:
            self.set_initial_value()
        else:
            await self.restore_state()

        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_{self._config.config_entry.entry_id}_{self._config.unique_id}",
                self.update_state,
            )
        )

    async def restore_state(self):
        """Get restored state from store."""
        if (extra_data := await self.async_get_last_extra_data()) is not None:
            self._config.extra_data = extra_data.as_dict()

        if (state := await self.async_get_last_state()) is not None:
            if state.state is not None:
                self._value = state.state
            if state.attributes is not None:
                attrs = state.attributes.copy()

            # Update state attributes
            if state_attrs := self.state_attributes:
                if attrs is None:
                    attrs = state_attrs
                else:
                    attrs.update(state_attrs)

            self._attr_extra_state_attributes = attrs

            _LOGGER.debug(
                "Restored state for %s of %s with attributes %s and extra data %s",
                self.entity_id,
                self._value,
                self._attr_extra_state_attributes,
                self._config.extra_data,
            )

    @property
    def extra_restore_state_data(self) -> ExtraStoredData | None:
        """Return entity specific state data to be restored."""
        return ExtraStoredData(self._config.extra_data)

    def set_initial_value(self):
        """Set initial values on sensor creation."""
        if self._config.initial_value is not None:
            self._value = self._config.initial_value.data

        if self._config.initial_value.attributes:
            _LOGGER.info("ATTRS: %s", self._config.initial_value.attributes)
        self._attr_extra_state_attributes = self._config.initial_value.attributes

    def update_attributes(self, attributes: dict[str, str | int]):
        """Update attribute values."""
        current_attributes = self._attr_extra_state_attributes.copy()
        if current_attributes is None:
            current_attributes = attributes
        else:
            current_attributes.update(attributes)

        self._attr_extra_state_attributes = current_attributes

    @callback
    def update_state(self, update_data: EntityData):
        """Update sensor value."""

        if (self._value == "on" and update_data.data) or (
            self._value == "off" and not update_data.data
        ):
            return

        if not (
            self._value == update_data.data
            or self._value == str(update_data.data)
            or self._value == str(update_data.data).lower()
        ):
            _LOGGER.debug(
                "Updating sensor: %s - old value %s, new value %s, attributes: %s",
                self.entity_id,
                self._value,
                update_data.data,
                update_data.attributes,
            )
            self._value = update_data.data

        if update_data.attributes:
            self.update_attributes(update_data.attributes)

        if update_data.extra_data:
            self._config.extra_data = update_data.extra_data
        self.async_write_ha_state()

    def get_def_key(self, definition_key: Any) -> str | int | float | bool | None:
        """Get value for definition key."""
        if self._config.extra_data:
            return self._api_manager.evaluate_def_key(
                definition_key, self._config.extra_data.get("data_path")
            )
        return None

    def process_args(self, args: dict) -> dict:
        """Process args for commands."""
        return_args = {}
        for name, value in args.items():
            if isinstance(value, str) and value[:1] == "[" and value[-1:] == "]":
                key = value[1:-1]
                return_args[name] = self._config.extra_data.get(key)
            else:
                return_args[name] = value

        return return_args
