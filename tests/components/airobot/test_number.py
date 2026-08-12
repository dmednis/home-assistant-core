"""Test the Airobot number platform."""

from unittest.mock import AsyncMock

from pyairobotmodbus.exceptions import AirobotConnectionError as VUConnectionError
from pyairobotrest.exceptions import AirobotError
import pytest
from syrupy.assertion import SnapshotAssertion

from homeassistant.components.number import (
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
)
from homeassistant.const import ATTR_ENTITY_ID, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
import homeassistant.helpers.entity_registry as er

from tests.common import MockConfigEntry, snapshot_platform


@pytest.fixture
def platforms() -> list[Platform]:
    """Fixture to specify platforms to test."""
    return [Platform.NUMBER]


@pytest.mark.usefixtures("entity_registry_enabled_by_default", "init_integration")
async def test_number_entities(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the number entities."""
    await snapshot_platform(hass, entity_registry, snapshot, mock_config_entry.entry_id)


@pytest.mark.usefixtures("entity_registry_enabled_by_default", "init_integration")
async def test_number_set_hysteresis_band(
    hass: HomeAssistant,
    mock_airobot_client: AsyncMock,
) -> None:
    """Test setting hysteresis band value."""
    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {
            ATTR_ENTITY_ID: "number.test_thermostat_hysteresis_band",
            ATTR_VALUE: 0.3,
        },
        blocking=True,
    )

    mock_airobot_client.set_hysteresis_band.assert_called_once_with(0.3)


@pytest.mark.usefixtures("entity_registry_enabled_by_default", "init_integration")
async def test_number_set_value_error(
    hass: HomeAssistant,
    mock_airobot_client: AsyncMock,
) -> None:
    """Test error handling when setting number value fails."""
    mock_airobot_client.set_hysteresis_band.side_effect = AirobotError("Device error")

    with pytest.raises(ServiceValidationError) as exc_info:
        await hass.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {
                ATTR_ENTITY_ID: "number.test_thermostat_hysteresis_band",
                ATTR_VALUE: 0.3,
            },
            blocking=True,
        )

    assert exc_info.value.translation_domain == "airobot"
    assert exc_info.value.translation_key == "set_value_failed"


@pytest.mark.usefixtures("entity_registry_enabled_by_default", "init_vu_integration")
async def test_vu_numbers(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    mock_vu_config_entry: MockConfigEntry,
) -> None:
    """Test the VU number entities."""
    await snapshot_platform(
        hass, entity_registry, snapshot, mock_vu_config_entry.entry_id
    )


@pytest.mark.usefixtures("entity_registry_enabled_by_default", "init_vu_integration")
async def test_vu_number_set_value(
    hass: HomeAssistant,
    mock_vu_client: AsyncMock,
) -> None:
    """Test setting a VU number value."""
    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {
            ATTR_ENTITY_ID: "number.airobot_ventilation_co2_setpoint",
            ATTR_VALUE: 900,
        },
        blocking=True,
    )

    mock_vu_client.async_set_co2_setpoint.assert_called_once_with(900)


@pytest.mark.usefixtures("entity_registry_enabled_by_default", "init_vu_integration")
async def test_vu_number_set_value_error(
    hass: HomeAssistant,
    mock_vu_client: AsyncMock,
) -> None:
    """Test communication failures surface as HomeAssistantError."""
    mock_vu_client.async_set_co2_setpoint.side_effect = VUConnectionError(
        "Connection lost"
    )

    with pytest.raises(HomeAssistantError) as exc_info:
        await hass.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {
                ATTR_ENTITY_ID: "number.airobot_ventilation_co2_setpoint",
                ATTR_VALUE: 900,
            },
            blocking=True,
        )

    assert exc_info.value.translation_key == "set_value_failed"
