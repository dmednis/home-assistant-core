"""Binary sensor platform for Airobot ventilation unit."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import override

from pyairobotmodbus.models import AirobotData, ErrorFlag

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import AirobotConfigEntry, AirobotVUCoordinator
from .entity import AirobotVUEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class AirobotVUBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes Airobot VU binary sensor entity."""

    is_on_fn: Callable[[AirobotData], bool]


BINARY_SENSOR_TYPES: tuple[AirobotVUBinarySensorEntityDescription, ...] = (
    AirobotVUBinarySensorEntityDescription(
        key="error_fire_alarm",
        translation_key="error_fire_alarm",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda data: bool(data.error_flags & ErrorFlag.FIRE_ALARM),
    ),
    AirobotVUBinarySensorEntityDescription(
        key="error_fan1",
        translation_key="error_fan1",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda data: bool(data.error_flags & ErrorFlag.FAN1),
    ),
    AirobotVUBinarySensorEntityDescription(
        key="error_fan2",
        translation_key="error_fan2",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda data: bool(data.error_flags & ErrorFlag.FAN2),
    ),
    AirobotVUBinarySensorEntityDescription(
        key="error_sensor_1",
        translation_key="error_sensor_1",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda data: bool(data.error_flags & ErrorFlag.SENSOR_1),
    ),
    AirobotVUBinarySensorEntityDescription(
        key="error_sensor_2",
        translation_key="error_sensor_2",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda data: bool(data.error_flags & ErrorFlag.SENSOR_2),
    ),
    AirobotVUBinarySensorEntityDescription(
        key="error_sensor_3",
        translation_key="error_sensor_3",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda data: bool(data.error_flags & ErrorFlag.SENSOR_3),
    ),
    AirobotVUBinarySensorEntityDescription(
        key="error_sensor_4",
        translation_key="error_sensor_4",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda data: bool(data.error_flags & ErrorFlag.SENSOR_4),
    ),
    AirobotVUBinarySensorEntityDescription(
        key="error_sensor_5",
        translation_key="error_sensor_5",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda data: bool(data.error_flags & ErrorFlag.SENSOR_5),
    ),
    AirobotVUBinarySensorEntityDescription(
        key="error_sensor_co2",
        translation_key="error_sensor_co2",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda data: bool(data.error_flags & ErrorFlag.SENSOR_CO2),
    ),
    AirobotVUBinarySensorEntityDescription(
        key="error_heater",
        translation_key="error_heater",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda data: bool(data.error_flags & ErrorFlag.HEATER),
    ),
    AirobotVUBinarySensorEntityDescription(
        key="error_low_supply",
        translation_key="error_low_supply",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda data: bool(data.error_flags & ErrorFlag.LOW_SUPPLY),
    ),
    AirobotVUBinarySensorEntityDescription(
        key="error_filter",
        translation_key="error_filter",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda data: bool(data.error_flags & ErrorFlag.FILTER),
    ),
    AirobotVUBinarySensorEntityDescription(
        key="server_connected",
        translation_key="server_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda data: data.server_connected,
    ),
    AirobotVUBinarySensorEntityDescription(
        key="filter_alert",
        translation_key="filter_alert",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda data: data.filter_alert,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AirobotConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Airobot binary sensor entities."""
    coordinator = entry.runtime_data
    if not isinstance(coordinator, AirobotVUCoordinator):
        return

    async_add_entities(
        AirobotVUBinarySensor(coordinator, description)
        for description in BINARY_SENSOR_TYPES
    )


class AirobotVUBinarySensor(AirobotVUEntity, BinarySensorEntity):
    """Representation of an Airobot VU binary sensor."""

    entity_description: AirobotVUBinarySensorEntityDescription

    @property
    @override
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return self.entity_description.is_on_fn(self.coordinator.data)
