"""Restore entities."""

import contextlib

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base_definitions import (
    EntityConfig,
    PlatformToDefinitionClassMapping,
    _AnyEntityDefinition,
)
from .base_entity import BaseEntity


def restore_entities(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    add_entities: AddEntitiesCallback,
    entity_class_name: str,
    entity_class: BaseEntity,
):
    """Restore all previsouly registered sensors."""
    sensors = []

    entity_registry = er.async_get(hass)
    entries = [
        entry
        for entry in er.async_entries_for_config_entry(
            entity_registry, config_entry.entry_id
        )
        if entry.entity_id.startswith(entity_class_name)
    ]

    for entry in entries:
        if (
            entry.entity_id.startswith(entity_class_name)
            and entry.config_entry_id == config_entry.entry_id
        ):
            if device := get_device_entry(hass, entry.device_id):
                definition_class = getattr(
                    PlatformToDefinitionClassMapping, entity_class_name
                )

                definition: _AnyEntityDefinition = definition_class(
                    key=entry.name,
                    name=entry.original_name,
                    icon=entry.original_icon,
                    entity_category=entry.entity_category,
                )

                with contextlib.suppress(AttributeError):
                    definition.device_class = (
                        entry.device_class or entry.original_device_class
                    )

                with contextlib.suppress(AttributeError):
                    definition.unit_of_measure = entry.unit_of_measurement

                config = EntityConfig(
                    unique_id=entry.unique_id,
                    device_identifier=device.identifiers,
                    config_entry=config_entry,
                )

                sensors.append(entity_class(hass, definition, config))

    if sensors:
        add_entities(sensors)


def get_device_entry(hass: HomeAssistant, device_id: int) -> dr.DeviceEntry:
    """Get device entry by device id."""
    device_registry = dr.async_get(hass)
    return device_registry.async_get(device_id)
