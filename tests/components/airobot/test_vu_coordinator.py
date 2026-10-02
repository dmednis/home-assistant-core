"""Tests for the Airobot VU coordinator."""

from unittest.mock import AsyncMock, patch

from pyairobotmodbus.exceptions import (
    AirobotConnectionError,
    AirobotReadError,
    AirobotTimeoutError,
)
import pytest

from homeassistant.components.airobot.const import DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from tests.common import MockConfigEntry
from tests.typing import WebSocketGenerator


@pytest.fixture
def platforms() -> list[Platform]:
    """No platforms for coordinator-only tests."""
    return []


async def _list_modbus_connections(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator
) -> list[dict]:
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "modbus/connections/list"})
    return (await client.receive_json())["result"]["connections"]


@pytest.mark.usefixtures("init_vu_integration")
async def test_vu_setup_entry_success(
    hass: HomeAssistant, mock_vu_config_entry: MockConfigEntry
) -> None:
    """Test successful setup of a VU config entry."""
    assert mock_vu_config_entry.state is ConfigEntryState.LOADED


@pytest.mark.usefixtures("init_vu_integration")
async def test_vu_shares_modbus_connection(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    mock_vu_config_entry: MockConfigEntry,
) -> None:
    """Test the unit is reached over the Modbus integration's shared connection."""
    assert await _list_modbus_connections(hass, hass_ws_client) == [
        {
            "endpoint": ["tcp", "192.168.1.200", 502],
            "connected": False,
            "source": "config_entry",
            "units": {mock_vu_config_entry.entry_id: [1]},
        }
    ]

    await hass.config_entries.async_unload(mock_vu_config_entry.entry_id)
    await hass.async_block_till_done()

    # Unloading releases the unit, closing the connection behind it
    assert await _list_modbus_connections(hass, hass_ws_client) == []


@pytest.mark.parametrize(
    ("method_name", "exception"),
    [
        pytest.param(
            "async_get_identity",
            AirobotConnectionError("Connection failed"),
            id="identity_connection_error",
        ),
        pytest.param(
            "async_get_data",
            AirobotConnectionError("Connection failed"),
            id="data_connection_error",
        ),
        pytest.param(
            "async_get_data",
            AirobotTimeoutError("Timeout"),
            id="data_timeout",
        ),
    ],
)
async def test_vu_setup_entry_exceptions(
    hass: HomeAssistant,
    mock_vu_client: AsyncMock,
    mock_vu_config_entry: MockConfigEntry,
    method_name: str,
    exception: Exception,
) -> None:
    """Test VU setup fails with connection exceptions."""
    mock_vu_config_entry.add_to_hass(hass)
    getattr(mock_vu_client, method_name).side_effect = exception

    await hass.config_entries.async_setup(mock_vu_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_vu_config_entry.state is ConfigEntryState.SETUP_RETRY


# The device is registered by its entities
@pytest.mark.parametrize("platforms", [[Platform.SENSOR]])
@pytest.mark.usefixtures("init_vu_integration")
async def test_vu_device_serial_number(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    mock_vu_config_entry: MockConfigEntry,
) -> None:
    """Test the device carries the serial number read from the unit."""
    device = device_registry.async_get_device_by_identifier(
        (DOMAIN, mock_vu_config_entry.entry_id), mock_vu_config_entry.entry_id
    )
    assert device is not None
    assert device.serial_number == "01234567"


async def test_vu_setup_without_identity_registers(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    mock_vu_client: AsyncMock,
    mock_vu_config_entry: MockConfigEntry,
) -> None:
    """Test firmware without the identity registers still sets up."""
    mock_vu_client.async_get_identity.side_effect = AirobotReadError("Illegal address")
    mock_vu_config_entry.add_to_hass(hass)

    with patch("homeassistant.components.airobot.VU_PLATFORMS", [Platform.SENSOR]):
        await hass.config_entries.async_setup(mock_vu_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_vu_config_entry.state is ConfigEntryState.LOADED
    device = device_registry.async_get_device_by_identifier(
        (DOMAIN, mock_vu_config_entry.entry_id), mock_vu_config_entry.entry_id
    )
    assert device is not None
    assert device.serial_number is None
