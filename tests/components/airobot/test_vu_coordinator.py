"""Tests for the Airobot VU coordinator."""

from unittest.mock import AsyncMock

from pyairobotmodbus.exceptions import AirobotConnectionError, AirobotTimeoutError
import pytest

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry


@pytest.fixture
def platforms() -> list[Platform]:
    """No platforms for coordinator-only tests."""
    return []


@pytest.mark.usefixtures("init_vu_integration")
async def test_vu_setup_entry_success(
    hass: HomeAssistant, mock_vu_config_entry: MockConfigEntry
) -> None:
    """Test successful setup of a VU config entry."""
    assert mock_vu_config_entry.state is ConfigEntryState.LOADED


@pytest.mark.parametrize(
    ("exception", "expected_state"),
    [
        (AirobotConnectionError("Connection failed"), ConfigEntryState.SETUP_RETRY),
        (AirobotTimeoutError("Timeout"), ConfigEntryState.SETUP_RETRY),
    ],
)
async def test_vu_setup_entry_exceptions(
    hass: HomeAssistant,
    mock_vu_client: AsyncMock,
    mock_vu_config_entry: MockConfigEntry,
    exception: Exception,
    expected_state: ConfigEntryState,
) -> None:
    """Test VU setup fails with connection exceptions."""
    mock_vu_config_entry.add_to_hass(hass)
    mock_vu_client.async_get_data.side_effect = exception

    await hass.config_entries.async_setup(mock_vu_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_vu_config_entry.state is expected_state
    # The client connected during coordinator setup must not leak
    mock_vu_client.disconnect.assert_called_once()


@pytest.mark.usefixtures("init_vu_integration")
async def test_vu_unload_entry(
    hass: HomeAssistant,
    mock_vu_config_entry: MockConfigEntry,
    mock_vu_client: AsyncMock,
) -> None:
    """Test unloading a VU config entry disconnects client."""
    assert mock_vu_config_entry.state is ConfigEntryState.LOADED

    await hass.config_entries.async_unload(mock_vu_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_vu_config_entry.state is ConfigEntryState.NOT_LOADED
    mock_vu_client.disconnect.assert_called_once()
