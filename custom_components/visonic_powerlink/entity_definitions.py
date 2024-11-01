"""Entity definitions."""

from homeassistant.components.alarm_control_panel import CodeFormat
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor.const import SensorDeviceClass
from homeassistant.const import EntityCategory, UnitOfTemperature, UnitOfTime

from .api import ArmModes
from .base_definitions import (  # noqa: TID252
    AlarmControlPanelEntityDefinition,
    AllData,
    BinarySensorEntityDefinition,
    ButtonEntityDefinition,
    ConfigData,
    DeviceData,
    DeviceDefinition,
    EntitiesDefinition,
    LambdaFn,
    SensorEntityDefinition,
    SwitchEntityDefinition,
)
from .helpers import slugify  # noqa: TID252

# -----------------------------------------------
# If data_key is set:
# if data_key results in a dict or list, it is iterated over.
# Results are passed to
# device_name, parameter, value_fn and filter
#
# If not defined full data is passed to device_name, parameter, value_fn and filter


ENTITY_DEFS: tuple[EntitiesDefinition, ...] = (
    # --------------------------------
    # Connection Entities
    # --------------------------------
    EntitiesDefinition(
        unique_id="connections",
        data_path="",
        device_definition=DeviceDefinition(
            identifier=ConfigData("host", transform_fn=lambda v: f"{slugify(v)}_proxy"),
            name=ConfigData("host", transform_fn=lambda v: f"Proxy {slugify(v)}"),
            manufacturer="Visonic",
            model="Proxy",
        ),
        entity_definitions=(
            BinarySensorEntityDefinition(
                key="api_connection_status",
                name="Websocket Status",
                value=DeviceData("api_connected"),
                device_class=BinarySensorDeviceClass.CONNECTIVITY,
                defunct=True,
            ),
            BinarySensorEntityDefinition(
                key="alarm_connection",
                name="Alarm Connection",
                value=DeviceData("connections.alarm", transform_fn=lambda v: v > 0),
                device_class=BinarySensorDeviceClass.CONNECTIVITY,
            ),
            SensorEntityDefinition(
                key="addon_version",
                name="Addon Version",
                value=DeviceData("version"),
                entity_category=EntityCategory.DIAGNOSTIC,
            ),
        ),
    ),
    # --------------------------------
    # Panel Entities
    # --------------------------------
    EntitiesDefinition(
        unique_id="panel",
        data_path="panel",
        device_definition=DeviceDefinition(
            identifier=DeviceData("id", transform_fn=lambda v: f"{v}_panel"),
            name=DeviceData("id", transform_fn=lambda v: f"Panel {v}"),
            manufacturer="Visonic",
            model=DeviceData("hw_version"),
        ),
        entity_definitions=(
            ButtonEntityDefinition(
                key="arm_all_home",
                name="Arm All Home",
                value=True,
                filter=DeviceData("partitions_enabled"),
                extra_data={
                    "request": "arm",
                    "partition": 7,
                    "state": ArmModes.ARM_HOME,
                },
            ),
            ButtonEntityDefinition(
                key="arm_all_away",
                name="Arm All Away",
                value=True,
                filter=DeviceData("partitions_enabled"),
                extra_data={
                    "request": "arm",
                    "partition": 7,
                    "state": ArmModes.ARM_AWAY,
                },
            ),
            ButtonEntityDefinition(
                key="disarm_all",
                name="Disarm All",
                value=True,
                filter=DeviceData("partitions_enabled"),
                extra_data={"request": "arm", "partition": 7, "state": ArmModes.DISARM},
            ),
            SensorEntityDefinition(
                key="last_update",
                name="Last Update",
                value=DeviceData("datetime"),
                entity_category=EntityCategory.DIAGNOSTIC,
            ),
            BinarySensorEntityDefinition(
                key="multiple_partitions",
                name="Multiple Partitions",
                value=DeviceData("partitions_enabled"),
                entity_category=EntityCategory.DIAGNOSTIC,
            ),
            SensorEntityDefinition(
                key="eprom_version",
                name="Eprom Version",
                value=DeviceData("eprom_version"),
                entity_category=EntityCategory.DIAGNOSTIC,
            ),
            SensorEntityDefinition(
                key="hardware_version",
                name="Hardware Version",
                value=DeviceData("hw_version"),
                entity_category=EntityCategory.DIAGNOSTIC,
            ),
            SensorEntityDefinition(
                key="software_Version",
                name="Software Version",
                value=DeviceData("sw_version"),
                entity_category=EntityCategory.DIAGNOSTIC,
            ),
            SensorEntityDefinition(
                key="powerlink_sw_version",
                name="Powerlink SW Version",
                value=DeviceData("plink_sw_version"),
                entity_category=EntityCategory.DIAGNOSTIC,
            ),
        ),
    ),
    # --------------------------------
    # Partition Entities
    # --------------------------------
    EntitiesDefinition(
        unique_id="partitions",
        data_path="partitions.[all]",
        filter=DeviceData("Partition Active"),
        device_definition=DeviceDefinition(
            identifier=AllData("panel.id", transform_fn=lambda v: f"{v}_partition_[1]"),
            name="Partition [1]",
            manufacturer="Visonic",
            model="Partition",
        ),
        entity_definitions=(
            AlarmControlPanelEntityDefinition(
                key="alarm",
                name="Alarm",
                value=DeviceData("State"),
                is_ready_fn=DeviceData("Ready"),
                code_arm_required=LambdaFn(lambda d: d.config.data.get("pin_required")),
                code_format=CodeFormat.NUMBER,
                state_mapping_fn=LambdaFn(lambda d: d.api.alarm_state_mapping(d.value)),
                extra_data={
                    "partition": "[1]",
                    "arm_home": ArmModes.ARM_HOME,
                    "arm_away": ArmModes.ARM_AWAY,
                    "disarm": ArmModes.DISARM,
                },
            ),
            BinarySensorEntityDefinition(
                key="ready",
                name="Ready",
                value=DeviceData("Ready", transform_fn=lambda v: not v),
                device_class=BinarySensorDeviceClass.PROBLEM,
            ),
            BinarySensorEntityDefinition(
                key="bypass",
                name="Bypass",
                value=DeviceData("Bypass"),
            ),
            BinarySensorEntityDefinition(
                key="trouble",
                name="Trouble",
                value=DeviceData("Trouble"),
                device_class=BinarySensorDeviceClass.PROBLEM,
            ),
            BinarySensorEntityDefinition(
                key="active",
                name="Active",
                value=DeviceData("Partition Active"),
            ),
        ),
    ),
    # --------------------------------
    # Device Entities
    # --------------------------------
    EntitiesDefinition(
        unique_id="devices",
        data_path="devices.[all].[all]",
        device_definition=DeviceDefinition(
            identifier=AllData("panel.id", transform_fn=lambda v: f"{v}_[2]_[1]"),
            name=DeviceData("name"),
            manufacturer="Visonic",
            model=DeviceData("device_model"),
        ),
        entity_definitions=(
            BinarySensorEntityDefinition(
                key="disarm_active",
                name="Disarm Active",
                value=DeviceData("disarm_active"),
                entity_category=EntityCategory.DIAGNOSTIC,
            ),
            SensorEntityDefinition(
                key="disarm_active_delay",
                name="Disarm Active Delay",
                value=DeviceData("disarm_active_delay_mins"),
                device_class=SensorDeviceClass.DURATION,
                unit_of_measure=UnitOfTime.MINUTES,
                entity_category=EntityCategory.DIAGNOSTIC,
            ),
            BinarySensorEntityDefinition(
                key="magnet_state",
                name="State",
                value=DeviceData("last_event", transform_fn=lambda v: v == "open"),
                device_class=BinarySensorDeviceClass.OPENING,
                filter=DeviceData("device_type", transform_fn=lambda v: v == "MAGNET"),
            ),
            BinarySensorEntityDefinition(
                key="motion_state",
                name="Motion",
                value=DeviceData("motion_detected"),
                device_class=BinarySensorDeviceClass.MOTION,
                filter=DeviceData(
                    "device_type", transform_fn=lambda v: v in ["MOTION", "CAMERA"]
                ),
            ),
            BinarySensorEntityDefinition(
                key="alarm_led",
                name="Alarm Led",
                value=DeviceData("alarm_led"),
                entity_category=EntityCategory.DIAGNOSTIC,
            ),
            BinarySensorEntityDefinition(
                key="active_tamper_alert",
                name="Active Tamper Alert",
                value=DeviceData("active_tamper"),
                device_class=BinarySensorDeviceClass.TAMPER,
            ),
            BinarySensorEntityDefinition(
                key="tamper_alert",
                name="Tamper Alert",
                value=DeviceData("tamper_alert"),
                device_class=BinarySensorDeviceClass.TAMPER,
            ),
            BinarySensorEntityDefinition(
                key="tripped",
                name="Tripped",
                value=DeviceData("tripped"),
                device_class=BinarySensorDeviceClass.MOTION,
            ),
            SensorEntityDefinition(
                key="temperature",
                name="Temperature",
                icon="mdi:home-thermometer",
                value=DeviceData("temperature"),
                unit_of_measure=UnitOfTemperature.CELSIUS,
            ),
            SensorEntityDefinition(
                key="brightness",
                name="Brightness",
                icon="mdi:brightness-4",
                value=DeviceData("brightness", transform_fn=lambda v: v.title()),
            ),
            SensorEntityDefinition(
                key="partitions",
                name="Partitions",
                icon="mdi:home-lock",
                filter=DeviceData("partitions"),
                value=DeviceData(
                    "partitions", transform_fn=lambda v: ",".join(list(map(str, v)))
                ),
                entity_category=EntityCategory.DIAGNOSTIC,
            ),
            SwitchEntityDefinition(
                key="bypass",
                name="Bypass",
                value=DeviceData("bypass"),
                extra_data={
                    "type": "bypass",
                    "zone_id": "[1]",
                },
            ),
            SwitchEntityDefinition(
                key="pgm",
                name="PGM",
                value=DeviceData("on"),
                extra_data={
                    "type": "pgm",
                    "pgm_id": "[1]",
                },
            ),
        ),
    ),
)
