"""Initialise Module for ECU Proxy."""

from collections.abc import Callable
import inspect
import logging
from typing import Any

from homeassistant.components.persistent_notification import async_create
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .api import API
from .base_definitions import (
    AllData,
    ConfigData,
    ConfigOption,
    DeviceData,
    EntityData,
    LambdaData,
    LambdaFn,
    PathIndex,
    _AnyEntityDefinition,
)
from .const import DOMAIN, RESTORE_ENTITIES
from .entity_definitions import ENTITY_DEFS
from .helpers import get_key, slugify

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Get server params and start Proxy."""

    hass.data.setdefault(DOMAIN, {})

    api_handler = APIManager(hass, config_entry)
    hass.data[DOMAIN][config_entry.entry_id] = {"api_handler": api_handler}

    await api_handler.initialise_api()
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    _LOGGER.debug("Finished setup")
    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    api_handlder: APIManager = hass.data[DOMAIN][config_entry.entry_id]["api_handler"]
    await api_handlder.async_shutdown()

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )

    # Remove the config entry from the hass data object.
    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)
        _LOGGER.debug("%s unloaded config id - %s", DOMAIN, config_entry.entry_id)

    # Return that unloading was successful.
    return unload_ok


# Enables users to delete a device
async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Remove inividual devices from the integration (ok)."""
    if device_entry is not None:
        # Notify the user that the device has been removed
        async_create(
            hass,
            f"The following device was removed from the system: {device_entry}",
            title="Device removal",
        )
        return True
    return False


def get_required_platforms() -> list[str]:
    """Get required platforms to load based on ENTITY DEFS."""
    platforms = []
    # Iterate entity defs
    for entities_defs in ENTITY_DEFS:
        platforms.extend(
            [entity_def._platform for entity_def in entities_defs.entity_definitions]  # noqa: SLF001
        )

    return list(set(platforms))


PLATFORMS = get_required_platforms()


class APIManager:
    """Class to manage API."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize coordinator."""
        self.hass = hass
        self.config_entry = config_entry
        self.api: API
        self.data: dict[str, Any] = {}
        self.running: bool = False
        self.initialised: bool = False

    async def initialise_api(self) -> None:
        """Initialise api."""
        self.api = API(
            self.hass,
            self.config_entry,
            self.async_update_callback,
            self.connection_state_change_callback,
        )
        await self.api.initialise()
        self.running = True

    async def async_shutdown(self) -> None:
        """Run shutdown clean up."""
        self.running = False
        await self.api.on_shutdown()

    def connection_state_change_callback(self, state: bool):
        """Handle websocket connection state change."""
        if not self.running:
            return
        _LOGGER.debug("Connection state changed to %s", state)
        self.data["api_connected"] = state
        self.process_update(self.data)

    def async_update_callback(self, data: dict[str, Any]):
        """Process update."""

        # Add websocket connection status
        if data:
            # _LOGGER.debug("DATA REC: %s", data)
            self.data = data
            self.data["api_connected"] = self.api.connected
            self.process_update(self.data)
            self.initialised = True

    def create_or_update_device(
        self, identifiers: tuple, manufacturer: str, name: str, model: str
    ):
        """Create new device."""
        _LOGGER.debug("Creating new device for %s %s %s", name, model, identifiers)
        # Create device
        device_registry = dr.async_get(self.hass)
        return device_registry.async_get_or_create(
            config_entry_id=self.config_entry.entry_id,
            identifiers=identifiers,
            manufacturer=manufacturer,
            name=name,
            model=model,
        )

    def create_or_update_entity(
        self,
        group_uid: str,
        entity_def: _AnyEntityDefinition,
        device: dr.DeviceEntry,
        data_path: str,
    ):
        """Create or update entities."""
        device_unique_id = self.get_indentifier_from_device(device, 1)
        unique_id = f"{device_unique_id}_{slugify(entity_def.key)}"

        entity_registry = er.async_get(self.hass)
        entity = self.get_entity_for_device_by_unique_id(
            entity_registry, device.id, unique_id
        )

        if not entity or (not RESTORE_ENTITIES and not self.initialised):
            # Create entity
            if not entity_def.defunct:
                value = self.evaluate_def_key(entity_def.value, data_path)

                if value is not None and (
                    entity_def.filter is None
                    or self.evaluate_def_key(entity_def.filter, data_path)
                ):
                    if entity_def.attributes:
                        attributes = self.evaluate_def_key(
                            entity_def.attributes,
                            data_path,
                            remove_from_dict_if_none=True,
                        )
                    else:
                        attributes = {}

                    if entity_def.extra_data:
                        extra_data = self.evaluate_def_key(
                            entity_def.extra_data, data_path
                        )
                    else:
                        extra_data = {}

                    extra_data["group_uid"] = group_uid
                    extra_data["key"] = entity_def.key
                    extra_data["data_path"] = data_path

                    platform = entity_def._platform  # noqa: SLF001
                    async_dispatcher_send(
                        self.hass,
                        f"{DOMAIN}_{self.config_entry.entry_id}_register_{platform}_entity",
                        device,
                        entity_def,
                        unique_id,
                        value,
                        attributes,
                        extra_data,
                    )
        else:
            # Remove entity or update entity def if required on first update.
            if not self.initialised:
                if entity_def.filter is None or self.evaluate_def_key(
                    entity_def.filter, data_path
                ):
                    # Remove entity if flagged as defunt
                    if entity_def.defunct:
                        entity_registry.async_remove(entity.entity_id)
                        return

                    # Update any changes to entity defs
                    entity_registry.async_update_entity(
                        entity.entity_id,
                        name=entity_def.name,
                        device_class=entity_def.device_class
                        if hasattr(entity_def, "device_class")
                        else None,
                        entity_category=entity_def.entity_category,
                        icon=entity_def.icon,
                        unit_of_measurement=entity_def.unit_of_measure
                        if hasattr(entity_def, "unit_of_measure")
                        else None,
                    )

            # Update entity
            if entity_def.value and (
                entity_def.filter is None
                or self.evaluate_def_key(entity_def.filter, data_path)
            ):
                value = self.evaluate_def_key(entity_def.value, data_path)

                if entity_def.attributes:
                    attributes = self.evaluate_def_key(
                        entity_def.attributes, data_path, remove_from_dict_if_none=True
                    )
                else:
                    attributes = {}

                if entity_def.extra_data:
                    extra_data = self.evaluate_def_key(entity_def.extra_data, data_path)
                    extra_data["group_uid"] = group_uid
                    extra_data["key"] = entity_def.key
                    extra_data["data_path"] = data_path
                else:
                    extra_data = {}

                update_data = EntityData(
                    data=value, attributes=attributes, extra_data=extra_data
                )
                async_dispatcher_send(
                    self.hass,
                    f"{DOMAIN}_{self.config_entry.entry_id}_{unique_id}",
                    update_data,
                )

    def process_update(self, data: dict[str, Any]):
        """Process updates for entity defs."""

        for entities_def in ENTITY_DEFS:
            # Set group unique id for later storing in entities extra data
            group_uid = entities_def.unique_id

            # Get list of data_keys to iterate
            if iterate_data_path := entities_def.data_path:
                data_path_list = self.get_data_key_list(
                    iterate_data_path, entities_def.list_data_id_key, data
                )
            else:
                data_path_list = [""]

            # Now iterate all data_paths
            for data_path in data_path_list:
                # validate path returns data
                if get_key(data_path, data) is None:
                    continue

                # Skip if top level filter
                if entities_def.filter and not self.evaluate_def_key(
                    entities_def.filter, data_path
                ):
                    continue

                # Get device info
                identifiers = {
                    (
                        DOMAIN,
                        slugify(
                            self.evaluate_def_key(
                                entities_def.device_definition.identifier, data_path
                            )
                        ),
                    )
                }
                device = self.get_device_by_identifiers(self.hass, identifiers)

                # Create device if not found
                if not device or (not RESTORE_ENTITIES and not self.initialised):
                    device_name = self.evaluate_def_key(
                        entities_def.device_definition.name, data_path
                    )

                    device_manufacturer = self.evaluate_def_key(
                        entities_def.device_definition.manufacturer, data_path
                    )

                    device_model = self.evaluate_def_key(
                        entities_def.device_definition.model, data_path
                    )

                    device = self.create_or_update_device(
                        identifiers=identifiers,
                        manufacturer=device_manufacturer,
                        name=device_name,
                        model=device_model,
                    )

                # Create or update entities
                for entity_def in entities_def.entity_definitions:
                    self.create_or_update_entity(
                        group_uid=group_uid,
                        entity_def=entity_def,
                        device=device,
                        data_path=data_path,
                    )

    def get_device_by_identifiers(self, hass: HomeAssistant, identifiers: tuple):
        """Get devices with identifiers."""
        device_registry = dr.async_get(hass)
        return device_registry.async_get_device(identifiers, None)

    def get_indentifier_from_device(self, device: dr.DeviceEntry, pos: int) -> str:
        """Get identifier from device."""
        try:
            identifiers = next(iter(device.identifiers))
            return identifiers[pos]
        except KeyError:
            return None

    def get_entity_for_device_by_unique_id(
        self, entity_registry: er.EntityRegistry, device_id: str, unique_id: str
    ) -> er.RegistryEntry:
        """Get entity id by unique id.  Return None if not found."""
        try:
            return [
                entity
                for entity in er.async_entries_for_device(
                    entity_registry, device_id, include_disabled_entities=True
                )
                if entity.unique_id == unique_id
            ][0]
        except IndexError:
            return None

    def evaluate_def_key(
        self,
        def_key_value: str | dict | Callable,
        data_path: str,
        entity_value: int | str | None = None,
        remove_from_dict_if_none: bool = False,
    ) -> str | int | bool | dict:
        """Process entity def key and return value."""
        result: str | int | float = None

        if isinstance(def_key_value, dict):
            result_dict = {}
            for key, value in def_key_value.items():
                result = self.evaluate_def_key(value, data_path)
                if remove_from_dict_if_none and result is None:
                    continue
                result_dict[key] = self.evaluate_def_key(value, data_path)
            return result_dict

        if isinstance(def_key_value, DeviceData | AllData):
            if isinstance(def_key_value, DeviceData):
                data = get_key(data_path, self.data)
            else:
                data = self.data

            result = get_key(def_key_value.key, data)

            if def_key_value.transform_fn and result is not None:
                result = def_key_value.transform_fn(result)
            if result is None and def_key_value.value_if_none is not None:
                result = def_key_value.value_if_none

        elif isinstance(def_key_value, ConfigData | ConfigOption):
            if isinstance(def_key_value, ConfigOption):
                data = self.config_entry.options
            else:
                data = self.config_entry.data

            try:
                result = data[def_key_value.key]
            except KeyError:
                result = None

            if def_key_value.transform_fn and result is not None:
                result = def_key_value.transform_fn(result)
            if result is None and def_key_value.value_if_none is not None:
                result = def_key_value.value_if_none

        elif isinstance(def_key_value, PathIndex):
            path_values = data_path.split(".")
            path_values.reverse()
            result = path_values[def_key_value.path_index - 1]

        elif isinstance(def_key_value, Callable | LambdaFn):
            data = get_key(data_path, self.data)
            try:
                if isinstance(def_key_value, Callable):
                    result = def_key_value(
                        LambdaData(
                            api=self.api,
                            config=self.config_entry,
                            device_data=data,
                            all_data=self.data,
                            value=entity_value,
                        )
                    )
                else:
                    result = def_key_value.fn(
                        LambdaData(
                            api=self.api,
                            config=self.config_entry,
                            device_data=data,
                            all_data=self.data,
                            value=entity_value,
                        )
                    )
            except Exception as ex:  # noqa: BLE001
                _LOGGER.error(
                    "Error processing definition entry: %s %s %s ",
                    data_path,
                    inspect.getsourcelines(def_key_value)[0][0]
                    if isinstance(def_key_value, Callable)
                    else def_key_value,
                    ex,
                )
                result = None

        else:
            result = def_key_value

        # Replace param with path value by param index
        # Value id is based on index of dotted data path with 1 the right most.
        if result and isinstance(result, str) and data_path:
            def_key_params = self.get_entity_def_params(result)
            path_values = data_path.split(".")
            path_values.reverse()

            # Clean any field id info from path values
            # To replace params from
            pvs = []
            for pv in path_values:
                if "|" in pv:
                    pvs.append(pv.split("|")[0])
                else:
                    pvs.append(pv)
            path_values = pvs

            for param in def_key_params:
                if param.isdigit():
                    try:
                        result = result.replace(
                            f"[{param}]", path_values[int(param) - 1]
                        )
                    except:  # noqa: E722
                        continue

        return result

    def evaluate_attributes(
        self, attributes: dict[str, str], data: dict[str, Any]
    ) -> dict[str, str | int | float]:
        """Evaluate entity def attributes dict to return values if exist."""
        result = {}
        for name, value_key in attributes:
            value = get_key(value_key, data)
            if value is not None:
                result[name] = value

        return result

    def get_entity_def_params(self, entity_def_str: str) -> list[str]:
        """Get list of params in an entity def."""
        if not isinstance(entity_def_str, str):
            return []

        params = []
        start_index = entity_def_str.find("[")

        while start_index != -1:
            end_index = entity_def_str.find("]", start_index + 1)
            if end_index != -1:
                params.append(entity_def_str[start_index + 1 : end_index])
            start_index = entity_def_str.find("[", start_index + 1)

        return params

    def get_data_key_list(self, data_key: str, list_id_key: str, data: dict[str, Any]):
        """Return list of data keys by enumerating any params in data_key."""
        if data_key.find("[") == -1:
            return [data_key]

        output = []
        final_output = []
        dk_split = data_key.split(".")

        if len(dk_split) == 1:
            output = [data_key]

        # Get index of first replacebale item.
        for itm in dk_split:
            if itm.startswith("["):
                idx = dk_split.index(itm)
                search_key = ".".join(dk_split[:idx])
                rem_key = ".".join(dk_split[idx + 1 :])
                # Get list of keys from data
                if itm == "[all]":
                    try:
                        d = get_key(search_key, data)

                        if isinstance(d, list):
                            # If data is list of json dict
                            if not list_id_key:
                                return []
                            key_list = [
                                f"{x.get(list_id_key)}|{list_id_key}" for x in d
                            ]
                        else:
                            # if data is json dict
                            key_list = d.keys()
                    except AttributeError:
                        key_list = []
                else:
                    key_list = (
                        itm.replace("[", "")
                        .replace("]", "")
                        .replace(" ", "")
                        .split(",")
                    )

                # Add to output
                output.extend(
                    [
                        f"{search_key}.{key}{"." + rem_key if rem_key else ""}"
                        for key in key_list
                    ]
                )
                break

        for dk in output:
            if dk.find("[") != -1:
                r = self.get_data_key_list(dk, list_id_key, data)
                final_output.extend(r)
            else:
                final_output.append(dk)

        return final_output
