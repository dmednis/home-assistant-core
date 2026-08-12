"""Tests for the Airobot binary sensor platform."""

import pytest
from syrupy.assertion import SnapshotAssertion

from homeassistant.const import STATE_OFF, STATE_ON, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from tests.common import MockConfigEntry, snapshot_platform


@pytest.fixture
def platforms() -> list[Platform]:
    """Fixture to specify platforms to test."""
    return [Platform.BINARY_SENSOR]


@pytest.mark.usefixtures("entity_registry_enabled_by_default", "init_vu_integration")
async def test_binary_sensor_entities(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    mock_vu_config_entry: MockConfigEntry,
) -> None:
    """Test the binary sensor entities with snapshots."""
    await snapshot_platform(
        hass, entity_registry, snapshot, mock_vu_config_entry.entry_id
    )


@pytest.mark.usefixtures("entity_registry_enabled_by_default", "init_vu_integration")
async def test_binary_sensor_states(
    hass: HomeAssistant,
) -> None:
    """Test binary sensor states with default mock data (no errors)."""
    # All error flags should be off (ErrorFlag.NONE in mock data)
    # Entity IDs are based on translated names (e.g. "Fire alarm error" -> "fire_alarm_error")
    error_entities = [
        "binary_sensor.airobot_ventilation_fire_alarm_error",
        "binary_sensor.airobot_ventilation_fan_1_error",
        "binary_sensor.airobot_ventilation_fan_2_error",
        "binary_sensor.airobot_ventilation_sensor_1_error",
        "binary_sensor.airobot_ventilation_sensor_2_error",
        "binary_sensor.airobot_ventilation_sensor_3_error",
        "binary_sensor.airobot_ventilation_sensor_4_error",
        "binary_sensor.airobot_ventilation_sensor_5_error",
        "binary_sensor.airobot_ventilation_co2_sensor_error",
        "binary_sensor.airobot_ventilation_heater_error",
        "binary_sensor.airobot_ventilation_low_supply_error",
        "binary_sensor.airobot_ventilation_filter_error",
    ]
    for entity_id in error_entities:
        state = hass.states.get(entity_id)
        assert state is not None, f"Entity {entity_id} not found"
        assert state.state == STATE_OFF

    # filter_alert is False in mock data
    state = hass.states.get("binary_sensor.airobot_ventilation_filter_alert")
    assert state is not None
    assert state.state == STATE_OFF

    # server_connected is True in mock data
    state = hass.states.get("binary_sensor.airobot_ventilation_server_connected")
    assert state is not None
    assert state.state == STATE_ON
