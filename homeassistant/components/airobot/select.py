"""Select platform for Airobot ventilation unit."""

from typing import override

from pyairobotmodbus.exceptions import AirobotError
from pyairobotmodbus.models import OperatingMode

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import AirobotConfigEntry, AirobotVUCoordinator
from .entity import AirobotVUEntity

PARALLEL_UPDATES = 1

MODE_OPTIONS = {
    "automatic": OperatingMode.AUTOMATIC,
    "manual": OperatingMode.MANUAL,
}
MODE_REVERSE = {v: k for k, v in MODE_OPTIONS.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AirobotConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Airobot select entity."""
    coordinator = entry.runtime_data
    if not isinstance(coordinator, AirobotVUCoordinator):
        return

    async_add_entities([AirobotVUOperatingModeSelect(coordinator)])


class AirobotVUOperatingModeSelect(AirobotVUEntity, SelectEntity):
    """Representation of the Airobot ventilation unit operating mode select."""

    _attr_translation_key = "operating_mode"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = list(MODE_OPTIONS.keys())

    def __init__(self, coordinator: AirobotVUCoordinator) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator, SelectEntityDescription(key="operating_mode"))

    @property
    @override
    def current_option(self) -> str:
        """Return the current operating mode."""
        return MODE_REVERSE[self.coordinator.data.operating_mode]

    @override
    async def async_select_option(self, option: str) -> None:
        """Set the operating mode."""
        try:
            await self.coordinator.client.async_set_mode(MODE_OPTIONS[option])
        except AirobotError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="set_mode_failed",
            ) from err
        await self.coordinator.async_request_refresh()
