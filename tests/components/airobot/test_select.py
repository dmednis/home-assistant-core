"""Tests for the Airobot select platform."""

from unittest.mock import AsyncMock

from pyairobotmodbus.exceptions import AirobotError
from pyairobotmodbus.models import OperatingMode
import pytest
from syrupy.assertion import SnapshotAssertion

from homeassistant.components.select import (
    ATTR_OPTION,
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from homeassistant.const import ATTR_ENTITY_ID, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from tests.common import MockConfigEntry, snapshot_platform


@pytest.fixture
def platforms() -> list[Platform]:
    """Fixture to specify platforms to test."""
    return [Platform.SELECT]


@pytest.mark.usefixtures("init_vu_integration")
async def test_select_entities(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    mock_vu_config_entry: MockConfigEntry,
) -> None:
    """Test the select entities."""
    await snapshot_platform(
        hass, entity_registry, snapshot, mock_vu_config_entry.entry_id
    )


@pytest.mark.usefixtures("init_vu_integration")
async def test_select_operating_mode(
    hass: HomeAssistant,
    mock_vu_client: AsyncMock,
) -> None:
    """Test selecting a different operating mode."""
    state = hass.states.get("select.airobot_ventilation_operating_mode")
    assert state is not None
    assert state.state == "automatic"

    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {
            ATTR_ENTITY_ID: "select.airobot_ventilation_operating_mode",
            ATTR_OPTION: "manual",
        },
        blocking=True,
    )

    mock_vu_client.async_set_mode.assert_called_once_with(OperatingMode.MANUAL)


@pytest.mark.usefixtures("init_vu_integration")
async def test_select_operating_mode_error(
    hass: HomeAssistant,
    mock_vu_client: AsyncMock,
) -> None:
    """Test selecting an operating mode raises on device error."""
    mock_vu_client.async_set_mode.side_effect = AirobotError("Test error")

    with pytest.raises(HomeAssistantError, match="Failed to set operating mode"):
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {
                ATTR_ENTITY_ID: "select.airobot_ventilation_operating_mode",
                ATTR_OPTION: "manual",
            },
            blocking=True,
        )


@pytest.mark.usefixtures("init_integration")
async def test_select_not_created_for_thermostat(hass: HomeAssistant) -> None:
    """Test no select entities are created for a thermostat entry."""
    assert not hass.states.async_entity_ids(SELECT_DOMAIN)
