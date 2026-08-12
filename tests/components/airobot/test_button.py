"""Tests for the Airobot button platform."""

from unittest.mock import AsyncMock

from pyairobotmodbus.exceptions import (
    AirobotConnectionError as VUConnectionError,
    AirobotError as VUError,
    AirobotTimeoutError as VUTimeoutError,
)
from pyairobotrest.exceptions import (
    AirobotConnectionError,
    AirobotError,
    AirobotTimeoutError,
)
import pytest
from syrupy.assertion import SnapshotAssertion

from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from homeassistant.const import ATTR_ENTITY_ID, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from tests.common import MockConfigEntry, snapshot_platform


@pytest.fixture
def platforms() -> list[Platform]:
    """Fixture to specify platforms to test."""
    return [Platform.BUTTON]


@pytest.mark.usefixtures("entity_registry_enabled_by_default", "init_integration")
async def test_buttons(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the button entities."""
    await snapshot_platform(hass, entity_registry, snapshot, mock_config_entry.entry_id)


@pytest.mark.usefixtures("init_integration")
async def test_restart_button(
    hass: HomeAssistant,
    mock_airobot_client: AsyncMock,
) -> None:
    """Test restart button."""
    await hass.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {ATTR_ENTITY_ID: "button.test_thermostat_restart"},
        blocking=True,
    )

    mock_airobot_client.reboot_thermostat.assert_called_once()


@pytest.mark.usefixtures("init_integration")
async def test_restart_button_error(
    hass: HomeAssistant,
    mock_airobot_client: AsyncMock,
) -> None:
    """Test restart button error handling for unexpected errors."""
    mock_airobot_client.reboot_thermostat.side_effect = AirobotError("Test error")

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: "button.test_thermostat_restart"},
            blocking=True,
        )

    mock_airobot_client.reboot_thermostat.assert_called_once()


@pytest.mark.usefixtures("entity_registry_enabled_by_default", "init_integration")
async def test_recalibrate_co2_button(
    hass: HomeAssistant,
    mock_airobot_client: AsyncMock,
) -> None:
    """Test recalibrate CO2 sensor button."""
    await hass.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {ATTR_ENTITY_ID: "button.test_thermostat_recalibrate_co2_sensor"},
        blocking=True,
    )

    mock_airobot_client.recalibrate_co2_sensor.assert_called_once()


@pytest.mark.usefixtures("entity_registry_enabled_by_default", "init_integration")
@pytest.mark.parametrize(
    "exception",
    [
        AirobotError("Test error"),
        AirobotConnectionError("Connection lost"),
        AirobotTimeoutError("Timeout"),
    ],
)
async def test_recalibrate_co2_button_error(
    hass: HomeAssistant,
    mock_airobot_client: AsyncMock,
    exception: Exception,
) -> None:
    """Test recalibrate CO2 sensor button error handling."""
    mock_airobot_client.recalibrate_co2_sensor.side_effect = exception

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: "button.test_thermostat_recalibrate_co2_sensor"},
            blocking=True,
        )

    mock_airobot_client.recalibrate_co2_sensor.assert_called_once()


@pytest.mark.usefixtures("entity_registry_enabled_by_default", "init_vu_integration")
async def test_vu_buttons(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    mock_vu_config_entry: MockConfigEntry,
) -> None:
    """Test the VU button entities."""
    await snapshot_platform(
        hass, entity_registry, snapshot, mock_vu_config_entry.entry_id
    )


@pytest.mark.usefixtures("init_vu_integration")
async def test_vu_reset_filter_timer(
    hass: HomeAssistant,
    mock_vu_client: AsyncMock,
) -> None:
    """Test a successful filter timer reset refreshes coordinator data."""
    assert mock_vu_client.async_get_data.call_count == 1

    await hass.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {ATTR_ENTITY_ID: "button.airobot_ventilation_reset_filter_timer"},
        blocking=True,
    )
    await hass.async_block_till_done()

    mock_vu_client.async_reset_filter_timer.assert_called_once()
    # The filter state is refreshed right away instead of waiting for the poll
    assert mock_vu_client.async_get_data.call_count == 2


@pytest.mark.parametrize(
    "exception",
    [
        VUConnectionError("Connection lost"),
        VUTimeoutError("Timeout"),
        VUError("Generic error"),
    ],
)
@pytest.mark.parametrize(
    ("entity_id", "client_method"),
    [
        ("button.airobot_ventilation_restart", "async_reboot"),
        (
            "button.airobot_ventilation_reset_filter_timer",
            "async_reset_filter_timer",
        ),
    ],
)
@pytest.mark.usefixtures("init_vu_integration")
async def test_vu_button_errors(
    hass: HomeAssistant,
    mock_vu_client: AsyncMock,
    entity_id: str,
    client_method: str,
    exception: Exception,
) -> None:
    """Test a failed VU button press surfaces an error."""
    getattr(mock_vu_client, client_method).side_effect = exception

    with pytest.raises(HomeAssistantError) as exc_info:
        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )

    assert exc_info.value.translation_key == "button_press_failed"
    getattr(mock_vu_client, client_method).assert_called_once()
