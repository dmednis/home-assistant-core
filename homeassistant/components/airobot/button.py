"""Button platform for Airobot integration."""

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any, override

from pyairobotmodbus.exceptions import AirobotError as VUAirobotError
from pyairobotrest.exceptions import AirobotError

from homeassistant.components.button import (
    ButtonDeviceClass,
    ButtonEntity,
    ButtonEntityDescription,
)
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
class AirobotButtonEntityDescription(ButtonEntityDescription):
    """Describes Airobot button entity."""

    press_fn: Callable[[AirobotDataUpdateCoordinator], Coroutine[Any, Any, None]]


@dataclass(frozen=True, kw_only=True)
class AirobotVUButtonEntityDescription(ButtonEntityDescription):
    """Describes Airobot VU button entity."""

    press_fn: Callable[[AirobotVUCoordinator], Coroutine[Any, Any, None]]


BUTTON_TYPES: tuple[AirobotButtonEntityDescription, ...] = (
    AirobotButtonEntityDescription(
        key="restart",
        device_class=ButtonDeviceClass.RESTART,
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda coordinator: coordinator.client.reboot_thermostat(),
    ),
    AirobotButtonEntityDescription(
        key="recalibrate_co2",
        translation_key="recalibrate_co2",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        press_fn=lambda coordinator: coordinator.client.recalibrate_co2_sensor(),
    ),
)

VU_BUTTON_TYPES: tuple[AirobotVUButtonEntityDescription, ...] = (
    AirobotVUButtonEntityDescription(
        key="restart",
        device_class=ButtonDeviceClass.RESTART,
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda coordinator: coordinator.client.async_reboot(),
    ),
    AirobotVUButtonEntityDescription(
        key="reset_filter_timer",
        translation_key="reset_filter_timer",
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda coordinator: coordinator.client.async_reset_filter_timer(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AirobotConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Airobot button entities."""
    coordinator = entry.runtime_data
    if isinstance(coordinator, AirobotVUCoordinator):
        async_add_entities(
            AirobotVUButton(coordinator, description) for description in VU_BUTTON_TYPES
        )
        return

    async_add_entities(
        AirobotButton(coordinator, description) for description in BUTTON_TYPES
    )


class AirobotButton(AirobotEntity, ButtonEntity):
    """Representation of an Airobot button."""

    entity_description: AirobotButtonEntityDescription

    def __init__(
        self,
        coordinator: AirobotDataUpdateCoordinator,
        description: AirobotButtonEntityDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.data.status.device_id}_{description.key}"

    @override
    async def async_press(self) -> None:
        """Handle the button press."""
        try:
            await self.entity_description.press_fn(self.coordinator)
        except AirobotError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="button_press_failed",
                translation_placeholders={"button": self.entity_description.key},
            ) from err


class AirobotVUButton(AirobotVUEntity, ButtonEntity):
    """Representation of an Airobot VU button."""

    entity_description: AirobotVUButtonEntityDescription

    @override
    async def async_press(self) -> None:
        """Handle the button press."""
        try:
            await self.entity_description.press_fn(self.coordinator)
        except VUAirobotError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="button_press_failed",
                translation_placeholders={"button": self.entity_description.key},
            ) from err
        await self.coordinator.async_request_refresh()
