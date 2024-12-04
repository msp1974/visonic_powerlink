"""Alarm control panel."""

import logging
from typing import Any

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
    CodeFormat,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import Platform

from .base_definitions import AlarmControlPanelEntityDefinition
from .base_entity import BaseEntity, register_entity
from .const import DOMAIN, RESTORE_ENTITIES
from .restore import restore_entities

_LOGGER = logging.getLogger(__name__)


# ===============================================================================
async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, add_entities: AddEntitiesCallback
):
    """Initialise climate platform."""
    platform = Platform.ALARM_CONTROL_PANEL
    entity_class = AlarmControlPanel

    @callback
    def register_new_entity(
        device: dr.DeviceEntry,
        entity_definition: AlarmControlPanelEntityDefinition,
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


class AlarmControlPanel(BaseEntity, AlarmControlPanelEntity):
    """Binary sensor class."""

    _attr_has_entity_name = True
    _attr_supported_features: AlarmControlPanelEntityFeature = (
        AlarmControlPanelEntityFeature.ARM_HOME
        | AlarmControlPanelEntityFeature.ARM_AWAY
        | AlarmControlPanelEntityFeature.TRIGGER
    )

    _disarm_in_progress: bool = False
    _arm_in_progress: bool = False

    def get_partition_state(self, status) -> str | None:
        """Get current state of partition."""
        status = {
            "status": status,
            "arming": self._arm_in_progress,
            "disarming": self._disarm_in_progress,
        }

        if self.definition.state_mapping_fn:
            status = self._api_manager.evaluate_def_key(
                self.definition.state_mapping_fn,
                self._config.extra_data.get("data_path"),
                status,
            )

        # Set arming and disarming
        if status == AlarmControlPanelState.DISARMED:
            self._disarm_in_progress = False
            self._arm_in_progress = False

        if status in [
            AlarmControlPanelState.ARMED_HOME,
            AlarmControlPanelState.ARMED_AWAY,
            AlarmControlPanelState.ARMED_NIGHT,
            AlarmControlPanelState.ARMED_VACATION,
            AlarmControlPanelState.ARMED_CUSTOM_BYPASS,
        ]:
            self._arm_in_progress = False
        return status

    @property
    def code_arm_required(self) -> bool:
        """Whether the code is required for arm actions."""
        return self.get_def_key(self.definition.code_arm_required)

    @property
    def code_format(self) -> CodeFormat | None:
        """Code format or None if no code is required."""
        return (
            self.get_def_key(self.definition.code_format)
            if self.code_arm_required
            else None
        )

    @property
    def alarm_state(self):
        """Return the state of the device."""
        return self.get_partition_state(self._value)

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Send disarm command."""
        await self.arm_alarm("disarm", code)

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        """Send arm home command."""
        await self.arm_alarm("arm_home", code)

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Send arm away command."""
        await self.arm_alarm("arm_away", code)

    async def async_alarm_arm_night(self, code: str | None = None) -> None:
        """Send arm night command."""
        await self.arm_alarm("arm_night", code)

    async def async_alarm_arm_vacation(self, code: str | None = None) -> None:
        """Send arm vacation command."""
        await self.arm_alarm("arm_vacation", code)

    async def async_alarm_arm_custom_bypass(self, code: str | None = None) -> None:
        """Send arm custom bypass command."""
        await self.arm_alarm("arm_custom_bypass", code)

    async def arm_alarm(self, action: str, code: str) -> None:
        """Arm/Disarm alarm."""

        if self._config.extra_data:
            if (
                action == "disarm"
                and self.get_partition_state(self._value)
                != AlarmControlPanelState.DISARMED
            ):
                self._disarm_in_progress = True
            elif (
                action != "disarm"
                and self.get_partition_state(self._value)
                == AlarmControlPanelState.DISARMED
            ):
                self._arm_in_progress = True
            else:
                return

            payload = {
                "platform": Platform.ALARM_CONTROL_PANEL,
                "action": action,
                "extra_data": self._config.extra_data,
            }

            if code:
                payload["extra_data"]["code"] = code

            if self.is_ready:
                await self.api.send_command(**payload)
            else:
                raise HomeAssistantError("Partition is not ready to arm")
        else:
            raise HomeAssistantError(
                "No command args in entity definition to allow arming"
            )

    async def async_alarm_trigger(self, code: str | None = None) -> None:
        """Send alarm trigger command."""

    @property
    def is_ready(self) -> bool:
        """Return if partition is ready."""
        if self.definition.is_ready_fn:
            return self.get_def_key(self.definition.is_ready_fn)
        return True
