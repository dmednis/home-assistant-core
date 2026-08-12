"""Fan platform for Airobot ventilation unit."""

import math
from typing import Any, override

from pyairobotmodbus.exceptions import AirobotError
from pyairobotmodbus.models import OperatingMode

from homeassistant.components.fan import (
    FanEntity,
    FanEntityDescription,
    FanEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import AirobotConfigEntry, AirobotVUCoordinator
from .entity import AirobotVUEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AirobotConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Airobot fan entity."""
    coordinator = entry.runtime_data
    if not isinstance(coordinator, AirobotVUCoordinator):
        return

    async_add_entities([AirobotVUFan(coordinator)])


class AirobotVUFan(AirobotVUEntity, FanEntity):
    """Representation of an Airobot ventilation unit fan."""

    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.TURN_OFF
        | FanEntityFeature.TURN_ON
    )
    _attr_speed_count = 10
    _attr_translation_key = "ventilation"
    _attr_name = None

    def __init__(self, coordinator: AirobotVUCoordinator) -> None:
        """Initialize the fan entity."""
        super().__init__(coordinator, FanEntityDescription(key="ventilation"))

    @property
    @override
    def is_on(self) -> bool:
        """Return true if the fan is on."""
        return self.coordinator.data.power_on

    @property
    @override
    def percentage(self) -> int:
        """Return the current speed percentage.

        In manual mode the manual fan level setpoint drives the fans and
        reflects a speed change immediately, while the actual fan level
        sensor lags behind. When boost or overpressure is active the
        device overrides the setpoint, so report the actual level.
        """
        if not self.is_on:
            return 0
        data = self.coordinator.data
        if (
            data.operating_mode == OperatingMode.MANUAL
            and not data.boost_on
            and not data.overpressure_on
        ):
            return data.manual_fan_level * 10
        return data.supply_fan_level * 10

    async def _async_set_fan_speed(self, percentage: int) -> None:
        """Set the manual fan level, switching to manual mode if needed.

        The device only honors the manual fan level register in manual
        mode; in automatic mode the write would be silently ignored.
        """
        if self.coordinator.data.operating_mode != OperatingMode.MANUAL:
            await self.coordinator.client.async_set_mode(OperatingMode.MANUAL)
        await self.coordinator.client.async_set_fan_speed(math.ceil(percentage / 10))

    @override
    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        if percentage == 0:
            # Consistent with async_set_percentage: 0% means off
            await self.async_turn_off()
            return
        try:
            await self.coordinator.client.async_set_power(True)
            if percentage is not None:
                await self._async_set_fan_speed(percentage)
        except AirobotError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="fan_command_failed",
            ) from err
        await self.coordinator.async_request_refresh()

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the fan."""
        try:
            await self.coordinator.client.async_set_power(False)
        except AirobotError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="fan_command_failed",
            ) from err
        await self.coordinator.async_request_refresh()

    @override
    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        try:
            if percentage == 0:
                await self.coordinator.client.async_set_power(False)
            else:
                if not self.coordinator.data.power_on:
                    await self.coordinator.client.async_set_power(True)
                await self._async_set_fan_speed(percentage)
        except AirobotError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="fan_command_failed",
            ) from err
        await self.coordinator.async_request_refresh()
