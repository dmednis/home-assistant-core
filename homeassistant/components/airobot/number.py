"""Number platform for Airobot thermostat and ventilation unit."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import override

from pyairobotmodbus.exceptions import AirobotError as VUAirobotError
from pyairobotrest.const import HYSTERESIS_BAND_MAX, HYSTERESIS_BAND_MIN
from pyairobotrest.exceptions import AirobotError

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
)
from homeassistant.const import (
    EntityCategory,
    UnitOfDensity,
    UnitOfRatio,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
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
class AirobotNumberEntityDescription(NumberEntityDescription):
    """Describes Airobot number entity."""

    value_fn: Callable[[AirobotDataUpdateCoordinator], float]
    set_value_fn: Callable[[AirobotDataUpdateCoordinator, float], Awaitable[None]]


@dataclass(frozen=True, kw_only=True)
class AirobotVUNumberEntityDescription(NumberEntityDescription):
    """Describes Airobot VU number entity."""

    value_fn: Callable[[AirobotVUCoordinator], float]
    set_value_fn: Callable[[AirobotVUCoordinator, float], Awaitable[None]]


NUMBERS: tuple[AirobotNumberEntityDescription, ...] = (
    AirobotNumberEntityDescription(
        key="hysteresis_band",
        translation_key="hysteresis_band",
        device_class=NumberDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=HYSTERESIS_BAND_MIN / 10.0,
        native_max_value=HYSTERESIS_BAND_MAX / 10.0,
        native_step=0.1,
        value_fn=lambda coordinator: coordinator.data.settings.hysteresis_band,
        set_value_fn=lambda coordinator, value: coordinator.client.set_hysteresis_band(
            value
        ),
    ),
)

VU_NUMBERS: tuple[AirobotVUNumberEntityDescription, ...] = (
    AirobotVUNumberEntityDescription(
        key="co2_setpoint",
        translation_key="co2_setpoint",
        entity_category=EntityCategory.CONFIG,
        native_unit_of_measurement=UnitOfRatio.PARTS_PER_MILLION,
        native_min_value=450,
        native_max_value=2000,
        native_step=1,
        value_fn=lambda coordinator: coordinator.data.co2_setpoint,
        set_value_fn=lambda coordinator, value: (
            coordinator.client.async_set_co2_setpoint(int(value))
        ),
    ),
    AirobotVUNumberEntityDescription(
        key="humidity_setpoint",
        translation_key="humidity_setpoint",
        entity_category=EntityCategory.CONFIG,
        native_unit_of_measurement=UnitOfRatio.PERCENTAGE,
        native_min_value=5,
        native_max_value=95,
        native_step=0.5,
        value_fn=lambda coordinator: coordinator.data.humidity_setpoint,
        set_value_fn=lambda coordinator, value: (
            coordinator.client.async_set_humidity_setpoint(value)
        ),
    ),
    AirobotVUNumberEntityDescription(
        key="voc_setpoint",
        translation_key="voc_setpoint",
        entity_category=EntityCategory.CONFIG,
        native_min_value=0,
        native_max_value=500,
        native_step=1,
        value_fn=lambda coordinator: coordinator.data.voc_setpoint,
        set_value_fn=lambda coordinator, value: (
            coordinator.client.async_set_voc_setpoint(int(value))
        ),
    ),
    AirobotVUNumberEntityDescription(
        key="pm25_setpoint",
        translation_key="pm25_setpoint",
        entity_category=EntityCategory.CONFIG,
        native_unit_of_measurement=UnitOfDensity.MICROGRAMS_PER_CUBIC_METER,
        native_min_value=0,
        native_max_value=999,
        native_step=1,
        value_fn=lambda coordinator: coordinator.data.pm25_setpoint,
        set_value_fn=lambda coordinator, value: (
            coordinator.client.async_set_pm25_setpoint(int(value))
        ),
    ),
    AirobotVUNumberEntityDescription(
        key="boost_timeout",
        translation_key="boost_timeout",
        entity_category=EntityCategory.CONFIG,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        native_min_value=180,
        native_max_value=3600,
        native_step=1,
        value_fn=lambda coordinator: coordinator.data.boost_timeout,
        set_value_fn=lambda coordinator, value: (
            coordinator.client.async_set_boost_timeout(int(value))
        ),
    ),
    AirobotVUNumberEntityDescription(
        key="overpressure_timeout",
        translation_key="overpressure_timeout",
        entity_category=EntityCategory.CONFIG,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        native_min_value=180,
        native_max_value=3600,
        native_step=1,
        value_fn=lambda coordinator: coordinator.data.overpressure_timeout,
        set_value_fn=lambda coordinator, value: (
            coordinator.client.async_set_overpressure_timeout(int(value))
        ),
    ),
    AirobotVUNumberEntityDescription(
        key="filter_reminder_interval",
        translation_key="filter_reminder_interval",
        entity_category=EntityCategory.CONFIG,
        native_unit_of_measurement=UnitOfTime.HOURS,
        native_min_value=720,
        native_max_value=8760,
        native_step=1,
        value_fn=lambda coordinator: coordinator.data.filter_reminder_interval,
        set_value_fn=lambda coordinator, value: (
            coordinator.client.async_set_filter_reminder_interval(int(value))
        ),
    ),
    AirobotVUNumberEntityDescription(
        key="overpressure_fan_level",
        translation_key="overpressure_fan_level",
        entity_category=EntityCategory.CONFIG,
        native_min_value=0,
        native_max_value=10,
        native_step=1,
        value_fn=lambda coordinator: coordinator.data.overpressure_fan_level,
        set_value_fn=lambda coordinator, value: (
            coordinator.client.async_set_overpressure_fan_level(int(value))
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AirobotConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Airobot number platform."""
    coordinator = entry.runtime_data
    if isinstance(coordinator, AirobotVUCoordinator):
        async_add_entities(
            AirobotVUNumber(coordinator, description) for description in VU_NUMBERS
        )
        return

    async_add_entities(
        AirobotNumber(coordinator, description) for description in NUMBERS
    )


class AirobotNumber(AirobotEntity, NumberEntity):
    """Representation of an Airobot number entity."""

    entity_description: AirobotNumberEntityDescription

    def __init__(
        self,
        coordinator: AirobotDataUpdateCoordinator,
        description: AirobotNumberEntityDescription,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.data.status.device_id}_{description.key}"

    @property
    @override
    def native_value(self) -> float:
        """Return the current value."""
        return self.entity_description.value_fn(self.coordinator)

    @override
    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        try:
            await self.entity_description.set_value_fn(self.coordinator, value)
        except AirobotError as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="set_value_failed",
            ) from err
        else:
            await self.coordinator.async_request_refresh()


class AirobotVUNumber(AirobotVUEntity, NumberEntity):
    """Representation of an Airobot VU number entity."""

    entity_description: AirobotVUNumberEntityDescription

    @property
    @override
    def native_value(self) -> float:
        """Return the current value."""
        return self.entity_description.value_fn(self.coordinator)

    @override
    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        try:
            await self.entity_description.set_value_fn(self.coordinator, value)
        except VUAirobotError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="set_value_failed",
            ) from err
        else:
            await self.coordinator.async_request_refresh()
