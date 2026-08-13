"""Tests for the Airobot fan platform."""

from dataclasses import replace
from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock

from freezegun.api import FrozenDateTimeFactory
from pyairobotmodbus.exceptions import AirobotError
from pyairobotmodbus.models import AirobotData as VUData, OperatingMode
import pytest
from syrupy.assertion import SnapshotAssertion

from homeassistant.components.fan import (
    ATTR_PERCENTAGE,
    DOMAIN as FAN_DOMAIN,
    SERVICE_SET_PERCENTAGE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from homeassistant.const import ATTR_ENTITY_ID, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from tests.common import MockConfigEntry, async_fire_time_changed, snapshot_platform


async def _refresh_with_data(
    hass: HomeAssistant,
    mock_vu_client: AsyncMock,
    freezer: FrozenDateTimeFactory,
    data: VUData,
) -> None:
    """Push new device data through a coordinator refresh."""
    mock_vu_client.async_get_data.return_value = data
    freezer.tick(timedelta(seconds=30))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


@pytest.fixture
def platforms() -> list[Platform]:
    """Fixture to specify platforms to test."""
    return [Platform.FAN]


@pytest.mark.usefixtures("init_vu_integration")
async def test_fan_entities(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    mock_vu_config_entry: MockConfigEntry,
) -> None:
    """Test the fan entity snapshot."""
    await snapshot_platform(
        hass, entity_registry, snapshot, mock_vu_config_entry.entry_id
    )


@pytest.mark.parametrize(
    ("data_overrides", "expected_percentage"),
    [
        pytest.param({}, 30, id="automatic_mode_reports_actual_level"),
        pytest.param(
            {"operating_mode": OperatingMode.MANUAL},
            50,
            id="manual_mode_reports_setpoint",
        ),
        pytest.param(
            {"operating_mode": OperatingMode.MANUAL, "boost_on": True},
            30,
            id="boost_reports_actual_level",
        ),
        pytest.param(
            {"operating_mode": OperatingMode.MANUAL, "overpressure_on": True},
            30,
            id="overpressure_reports_actual_level",
        ),
    ],
)
@pytest.mark.usefixtures("init_vu_integration")
async def test_fan_percentage_source(
    hass: HomeAssistant,
    mock_vu_client: AsyncMock,
    mock_vu_data: VUData,
    freezer: FrozenDateTimeFactory,
    data_overrides: dict[str, Any],
    expected_percentage: int,
) -> None:
    """Test which fan level the percentage reflects in each mode.

    The fixture data has supply_fan_level=3 and manual_fan_level=5.
    """
    await _refresh_with_data(
        hass, mock_vu_client, freezer, replace(mock_vu_data, **data_overrides)
    )

    state = hass.states.get("fan.airobot_ventilation")
    assert state is not None
    assert state.attributes[ATTR_PERCENTAGE] == expected_percentage


@pytest.mark.usefixtures("init_vu_integration")
async def test_fan_turn_on(
    hass: HomeAssistant,
    mock_vu_client: AsyncMock,
) -> None:
    """Test turning on the fan."""
    await hass.services.async_call(
        FAN_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "fan.airobot_ventilation"},
        blocking=True,
    )

    mock_vu_client.async_set_power.assert_called_once_with(True)


@pytest.mark.usefixtures("init_vu_integration")
async def test_fan_turn_on_zero_percentage(
    hass: HomeAssistant,
    mock_vu_client: AsyncMock,
) -> None:
    """Test turning on the fan with 0% turns it off instead."""
    await hass.services.async_call(
        FAN_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "fan.airobot_ventilation", ATTR_PERCENTAGE: 0},
        blocking=True,
    )

    mock_vu_client.async_set_power.assert_called_once_with(False)
    mock_vu_client.async_set_fan_speed.assert_not_called()


@pytest.mark.usefixtures("init_vu_integration")
async def test_fan_turn_off(
    hass: HomeAssistant,
    mock_vu_client: AsyncMock,
) -> None:
    """Test turning off the fan."""
    await hass.services.async_call(
        FAN_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: "fan.airobot_ventilation"},
        blocking=True,
    )

    mock_vu_client.async_set_power.assert_called_once_with(False)


@pytest.mark.usefixtures("init_vu_integration")
async def test_fan_set_percentage(
    hass: HomeAssistant,
    mock_vu_client: AsyncMock,
) -> None:
    """Test setting the fan speed percentage."""
    await hass.services.async_call(
        FAN_DOMAIN,
        SERVICE_SET_PERCENTAGE,
        {ATTR_ENTITY_ID: "fan.airobot_ventilation", ATTR_PERCENTAGE: 50},
        blocking=True,
    )

    # The device only honors the manual fan level in manual mode
    mock_vu_client.async_set_mode.assert_called_once_with(OperatingMode.MANUAL)
    mock_vu_client.async_set_fan_speed.assert_called_once_with(5)


@pytest.mark.usefixtures("init_vu_integration")
async def test_fan_set_percentage_manual_mode(
    hass: HomeAssistant,
    mock_vu_client: AsyncMock,
    mock_vu_data: VUData,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test setting the fan speed percentage while already in manual mode."""
    await _refresh_with_data(
        hass,
        mock_vu_client,
        freezer,
        replace(mock_vu_data, operating_mode=OperatingMode.MANUAL),
    )

    await hass.services.async_call(
        FAN_DOMAIN,
        SERVICE_SET_PERCENTAGE,
        {ATTR_ENTITY_ID: "fan.airobot_ventilation", ATTR_PERCENTAGE: 50},
        blocking=True,
    )

    mock_vu_client.async_set_mode.assert_not_called()
    mock_vu_client.async_set_fan_speed.assert_called_once_with(5)


@pytest.mark.usefixtures("init_vu_integration")
async def test_fan_set_percentage_powers_on(
    hass: HomeAssistant,
    mock_vu_client: AsyncMock,
    mock_vu_data: VUData,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test setting a non-zero percentage on an off fan powers it on."""
    await _refresh_with_data(
        hass, mock_vu_client, freezer, replace(mock_vu_data, power_on=False)
    )

    await hass.services.async_call(
        FAN_DOMAIN,
        SERVICE_SET_PERCENTAGE,
        {ATTR_ENTITY_ID: "fan.airobot_ventilation", ATTR_PERCENTAGE: 50},
        blocking=True,
    )

    mock_vu_client.async_set_power.assert_called_once_with(True)
    mock_vu_client.async_set_fan_speed.assert_called_once_with(5)


@pytest.mark.usefixtures("init_vu_integration")
async def test_fan_set_percentage_zero(
    hass: HomeAssistant,
    mock_vu_client: AsyncMock,
) -> None:
    """Test setting the fan speed to zero turns off the fan."""
    await hass.services.async_call(
        FAN_DOMAIN,
        SERVICE_SET_PERCENTAGE,
        {ATTR_ENTITY_ID: "fan.airobot_ventilation", ATTR_PERCENTAGE: 0},
        blocking=True,
    )

    mock_vu_client.async_set_power.assert_called_once_with(False)


@pytest.mark.usefixtures("init_vu_integration")
@pytest.mark.parametrize(
    ("service", "service_data", "method_name"),
    [
        pytest.param(
            SERVICE_TURN_ON, {ATTR_PERCENTAGE: 50}, "async_set_fan_speed", id="turn_on"
        ),
        pytest.param(SERVICE_TURN_OFF, {}, "async_set_power", id="turn_off"),
        pytest.param(
            SERVICE_SET_PERCENTAGE,
            {ATTR_PERCENTAGE: 50},
            "async_set_fan_speed",
            id="set_percentage",
        ),
    ],
)
async def test_fan_command_errors(
    hass: HomeAssistant,
    mock_vu_client: AsyncMock,
    service: str,
    service_data: dict[str, Any],
    method_name: str,
) -> None:
    """Test fan commands raise on device errors."""
    getattr(mock_vu_client, method_name).side_effect = AirobotError("Test error")

    with pytest.raises(HomeAssistantError, match="Failed to send fan command"):
        await hass.services.async_call(
            FAN_DOMAIN,
            service,
            {ATTR_ENTITY_ID: "fan.airobot_ventilation", **service_data},
            blocking=True,
        )


@pytest.mark.usefixtures("init_integration")
async def test_fan_not_created_for_thermostat(hass: HomeAssistant) -> None:
    """Test no fan entities are created for a thermostat entry."""
    assert not hass.states.async_entity_ids(FAN_DOMAIN)
