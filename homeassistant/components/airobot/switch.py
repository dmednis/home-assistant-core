"""Switch platform for Airobot thermostat and ventilation unit."""

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any, override

from pyairobotmodbus.exceptions import AirobotError as VUAirobotError
from pyairobotrest.exceptions import AirobotError

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import (
    AirobotConfigEntry,
    AirobotDataUpdateCoordinator,
    AirobotVUCoordinator,
)
from .entity import AirobotEntity, AirobotVUEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class AirobotSwitchEntityDescription(SwitchEntityDescription):
    """Describes Airobot switch entity."""

    is_on_fn: Callable[[AirobotDataUpdateCoordinator], bool]
    turn_on_fn: Callable[[AirobotDataUpdateCoordinator], Coroutine[Any, Any, None]]
    turn_off_fn: Callable[[AirobotDataUpdateCoordinator], Coroutine[Any, Any, None]]


@dataclass(frozen=True, kw_only=True)
class AirobotVUSwitchEntityDescription(SwitchEntityDescription):
    """Describes Airobot VU switch entity."""

    is_on_fn: Callable[[AirobotVUCoordinator], bool]
    turn_on_fn: Callable[[AirobotVUCoordinator], Coroutine[Any, Any, None]]
    turn_off_fn: Callable[[AirobotVUCoordinator], Coroutine[Any, Any, None]]


SWITCH_TYPES: tuple[AirobotSwitchEntityDescription, ...] = (
    AirobotSwitchEntityDescription(
        key="child_lock",
        translation_key="child_lock",
        entity_category=EntityCategory.CONFIG,
        is_on_fn=lambda coordinator: (
            coordinator.data.settings.setting_flags.childlock_enabled
        ),
        turn_on_fn=lambda coordinator: coordinator.client.set_child_lock(True),
        turn_off_fn=lambda coordinator: coordinator.client.set_child_lock(False),
    ),
    AirobotSwitchEntityDescription(
        key="actuator_exercise_disabled",
        translation_key="actuator_exercise_disabled",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        is_on_fn=lambda coordinator: (
            coordinator.data.settings.setting_flags.actuator_exercise_disabled
        ),
        turn_on_fn=lambda coordinator: coordinator.client.toggle_actuator_exercise(
            True
        ),
        turn_off_fn=lambda coordinator: coordinator.client.toggle_actuator_exercise(
            False
        ),
    ),
)

VU_SWITCH_TYPES: tuple[AirobotVUSwitchEntityDescription, ...] = (
    AirobotVUSwitchEntityDescription(
        key="boost",
        translation_key="boost",
        is_on_fn=lambda coordinator: coordinator.data.boost_on,
        turn_on_fn=lambda coordinator: coordinator.client.async_set_boost(True),
        turn_off_fn=lambda coordinator: coordinator.client.async_set_boost(False),
    ),
    AirobotVUSwitchEntityDescription(
        key="overpressure",
        translation_key="overpressure",
        is_on_fn=lambda coordinator: coordinator.data.overpressure_on,
        turn_on_fn=lambda coordinator: coordinator.client.async_set_overpressure(True),
        turn_off_fn=lambda coordinator: coordinator.client.async_set_overpressure(
            False
        ),
    ),
    AirobotVUSwitchEntityDescription(
        key="bypass",
        translation_key="bypass",
        is_on_fn=lambda coordinator: coordinator.data.bypass_on,
        turn_on_fn=lambda coordinator: coordinator.client.async_set_bypass(True),
        turn_off_fn=lambda coordinator: coordinator.client.async_set_bypass(False),
    ),
    AirobotVUSwitchEntityDescription(
        key="humidity_control",
        translation_key="humidity_control",
        entity_category=EntityCategory.CONFIG,
        is_on_fn=lambda coordinator: coordinator.data.humidity_control_enabled,
        turn_on_fn=lambda coordinator: coordinator.client.async_set_humidity_control(
            True
        ),
        turn_off_fn=lambda coordinator: coordinator.client.async_set_humidity_control(
            False
        ),
    ),
    AirobotVUSwitchEntityDescription(
        key="voc_control",
        translation_key="voc_control",
        entity_category=EntityCategory.CONFIG,
        is_on_fn=lambda coordinator: coordinator.data.voc_control_enabled,
        turn_on_fn=lambda coordinator: coordinator.client.async_set_voc_control(True),
        turn_off_fn=lambda coordinator: coordinator.client.async_set_voc_control(False),
    ),
    AirobotVUSwitchEntityDescription(
        key="pm_control",
        translation_key="pm_control",
        entity_category=EntityCategory.CONFIG,
        is_on_fn=lambda coordinator: coordinator.data.pm_control_enabled,
        turn_on_fn=lambda coordinator: coordinator.client.async_set_pm_control(True),
        turn_off_fn=lambda coordinator: coordinator.client.async_set_pm_control(False),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AirobotConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Airobot switch entities."""
    coordinator = entry.runtime_data
    if isinstance(coordinator, AirobotVUCoordinator):
        async_add_entities(
            AirobotVUSwitch(coordinator, description) for description in VU_SWITCH_TYPES
        )
        return

    async_add_entities(
        AirobotSwitch(coordinator, description) for description in SWITCH_TYPES
    )


class AirobotSwitch(AirobotEntity, SwitchEntity):
    """Representation of an Airobot switch."""

    entity_description: AirobotSwitchEntityDescription

    def __init__(
        self,
        coordinator: AirobotDataUpdateCoordinator,
        description: AirobotSwitchEntityDescription,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.data.status.device_id}_{description.key}"

    @property
    @override
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self.entity_description.is_on_fn(self.coordinator)

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        try:
            await self.entity_description.turn_on_fn(self.coordinator)
        except AirobotError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="switch_turn_on_failed",
                translation_placeholders={"switch": self.entity_description.key},
            ) from err
        await self.coordinator.async_request_refresh()

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        try:
            await self.entity_description.turn_off_fn(self.coordinator)
        except AirobotError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="switch_turn_off_failed",
                translation_placeholders={"switch": self.entity_description.key},
            ) from err
        await self.coordinator.async_request_refresh()


class AirobotVUSwitch(AirobotVUEntity, SwitchEntity):
    """Representation of an Airobot VU switch."""

    entity_description: AirobotVUSwitchEntityDescription

    @property
    @override
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self.entity_description.is_on_fn(self.coordinator)

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        try:
            await self.entity_description.turn_on_fn(self.coordinator)
        except VUAirobotError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="switch_turn_on_failed",
                translation_placeholders={"switch": self.entity_description.key},
            ) from err
        await self.coordinator.async_request_refresh()

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        try:
            await self.entity_description.turn_off_fn(self.coordinator)
        except VUAirobotError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="switch_turn_off_failed",
                translation_placeholders={"switch": self.entity_description.key},
            ) from err
        await self.coordinator.async_request_refresh()
