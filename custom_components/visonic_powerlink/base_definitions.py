"""Entity Definition classes."""

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntityFeature,
    CodeFormat,
)
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.number import NumberMode
from homeassistant.components.sensor import SensorStateClass
from homeassistant.components.sensor.const import SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, Platform

from .api import API

_LOGGER = logging.getLogger(__name__)


@dataclass
class LambdaData:
    """Data Object passed to lambda calls."""

    api: API
    config: ConfigEntry
    device_data: dict[str, Any]
    all_data: dict[str, Any]
    value: Any | None = None


@dataclass
class LambdaFn:
    """Type hinting class for lambda function."""

    fn: Callable[[LambdaData], Any]


@dataclass
class DataKey:
    """Data key attribute."""

    key: str
    transform_fn: Callable | None = None
    value_if_none: Any | None = None


@dataclass
class DeviceData(DataKey):
    """Device data key attribute."""


@dataclass
class AllData(DataKey):
    """All data key attribute."""


@dataclass
class ConfigData(DataKey):
    """Config data key attribute."""


@dataclass
class ConfigOption(DataKey):
    """Config option key attribute."""


@dataclass
class PathIndex:
    """Path key index attribute."""

    path_index: int


@dataclass(frozen=True, kw_only=True)
class BaseEntityDefinition:
    """Class for sensor definition."""

    key: str
    name: str
    value: str | Callable | DeviceData | PathIndex | None = None
    icon: str | None = None
    entity_category: EntityCategory | None = None
    filter: Callable | None = None
    extra_data: dict | None = None
    defunct: bool = False  # will remove entity
    attributes: dict | None = None  # dict of name: value
    availability: Callable | DeviceData | None = None


@dataclass(frozen=True, kw_only=True)
class AlarmControlPanelEntityDefinition(BaseEntityDefinition):
    """Class for alarm control panel definition."""

    _platform = Platform.ALARM_CONTROL_PANEL

    state_mapping_fn: tuple[str | list[str], str] | Callable | None = None
    code_format: CodeFormat = CodeFormat.NUMBER
    supported_features: AlarmControlPanelEntityFeature = (
        AlarmControlPanelEntityFeature.ARM_HOME
        | AlarmControlPanelEntityFeature.ARM_AWAY
        | AlarmControlPanelEntityFeature.TRIGGER
    )
    code_arm_required: bool = True
    is_ready_fn: Callable | bool = True
    arm_home_args: dict | None = None
    arm_away_args: dict | None = None
    arm_night_args: dict | None = None
    arm_vacation_args: dict | None = None
    arm_custom_bypass_args: dict | None = None
    disarm_args: dict | None = None


@dataclass(frozen=True, kw_only=True)
class BinarySensorEntityDefinition(BaseEntityDefinition):
    """Class for binary sensor definition."""

    _platform = Platform.BINARY_SENSOR

    device_class: BinarySensorDeviceClass | None = None


@dataclass(frozen=True, kw_only=True)
class ButtonEntityDefinition(BaseEntityDefinition):
    """Class for button definition."""

    _platform = Platform.BUTTON

    press_args: dict | None = None


@dataclass(frozen=True, kw_only=True)
class NumberEntityDefinition(BaseEntityDefinition):
    """Class for number definition."""

    _platform = Platform.NUMBER

    min_value: float = 0
    max_value: float = 100
    step: float = 1
    mode: NumberMode = NumberMode.AUTO
    unit_of_measurement: str | None = None


@dataclass(frozen=True, kw_only=True)
class SelectEntityDefinition(BaseEntityDefinition):
    """Class for select definition."""

    _platform = Platform.SELECT

    options: list[str] | None = None


@dataclass(frozen=True, kw_only=True)
class SensorEntityDefinition(BaseEntityDefinition):
    """Class for sensor definition."""

    _platform = Platform.SENSOR

    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None
    unit_of_measure: str | None = None


@dataclass(frozen=True, kw_only=True)
class SwitchEntityDefinition(BaseEntityDefinition):
    """Class for switch definition."""

    _platform = Platform.SWITCH


@dataclass(frozen=True, kw_only=True)
class _AnyEntityDefinition(
    AlarmControlPanelEntityDefinition,
    BinarySensorEntityDefinition,
    ButtonEntityDefinition,
    NumberEntityDefinition,
    SelectEntityDefinition,
    SensorEntityDefinition,
    SwitchEntityDefinition,
):
    """Typing class for entity definitions."""


@dataclass
class PlatformToDefinitionClassMapping:
    """Mapping of platform to entity definition class."""

    alarm_control_panel = AlarmControlPanelEntityDefinition
    binary_sensor = BinarySensorEntityDefinition
    button = ButtonEntityDefinition
    number = NumberEntityDefinition
    select = SelectEntityDefinition
    sensor = SensorEntityDefinition
    switch = SwitchEntityDefinition


@dataclass(frozen=True, kw_only=True)
class DeviceDefinition:
    """Class for device definition."""

    identifier: str | Callable
    name: str | Callable
    manufacturer: str | Callable
    model: str | Callable
    serial: str | Callable | None = None


@dataclass(frozen=True, kw_only=True)
class EntitiesDefinition:
    """Class for device entities definition."""

    unique_id: str
    data_path: str | None = None
    list_data_id_key: str | Callable | None = None
    filter: DeviceData | Callable | None = None
    device_definition: DeviceDefinition | None = None
    entity_definitions: tuple[_AnyEntityDefinition, ...] | None = None


@dataclass
class EntityData:
    """Class to pass data to sensor."""

    data: Any
    attributes: dict[str, Any] | None = None
    extra_data: dict[str, Any] | None = None


@dataclass
class EntityConfig:
    """Class for a sensor config."""

    unique_id: str | None = None
    config_entry: ConfigEntry | None = None
    name: str | None = None
    device_identifier: str | None = None
    initial_value: EntityData | None = None
    display_uom: str | None = None
    display_precision: int | None = None
    extra_data: dict[str, Any] | None = None
