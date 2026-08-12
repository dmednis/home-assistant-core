"""The Airobot integration."""

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_DEVICE_TYPE, DEVICE_TYPE_VENTILATION
from .coordinator import (
    AirobotConfigEntry,
    AirobotDataUpdateCoordinator,
    AirobotVUCoordinator,
)

THERMOSTAT_PLATFORMS: list[Platform] = [
    Platform.BUTTON,
    Platform.CLIMATE,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]

VU_PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.FAN,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


def _is_ventilation_entry(entry: AirobotConfigEntry) -> bool:
    """Return True if the config entry is for a ventilation unit."""
    return entry.data.get(CONF_DEVICE_TYPE) == DEVICE_TYPE_VENTILATION


async def async_setup_entry(hass: HomeAssistant, entry: AirobotConfigEntry) -> bool:
    """Set up Airobot from a config entry."""
    coordinator: AirobotDataUpdateCoordinator | AirobotVUCoordinator
    if _is_ventilation_entry(entry):
        coordinator = AirobotVUCoordinator(hass, entry)
        platforms = VU_PLATFORMS
    else:
        coordinator = AirobotDataUpdateCoordinator(hass, entry)
        platforms = THERMOSTAT_PLATFORMS

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, platforms)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: AirobotConfigEntry) -> bool:
    """Unload a config entry."""
    platforms = VU_PLATFORMS if _is_ventilation_entry(entry) else THERMOSTAT_PLATFORMS
    return await hass.config_entries.async_unload_platforms(entry, platforms)
