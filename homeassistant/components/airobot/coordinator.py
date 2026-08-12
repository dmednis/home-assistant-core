"""Coordinators for the Airobot integration."""

import asyncio
from datetime import timedelta
import logging
from typing import override

from pyairobotmodbus import AirobotModbusClient
from pyairobotmodbus.exceptions import AirobotError as VUError
from pyairobotmodbus.models import AirobotData as AirobotVUData
from pyairobotrest import AirobotClient
from pyairobotrest.exceptions import AirobotAuthError, AirobotConnectionError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .models import AirobotData

_LOGGER = logging.getLogger(__name__)

# Update interval - the devices measure air every 30 seconds
UPDATE_INTERVAL = timedelta(seconds=30)

type AirobotConfigEntry = ConfigEntry[
    AirobotDataUpdateCoordinator | AirobotVUCoordinator
]


class AirobotDataUpdateCoordinator(DataUpdateCoordinator[AirobotData]):
    """Class to manage fetching Airobot data."""

    config_entry: AirobotConfigEntry

    def __init__(self, hass: HomeAssistant, entry: AirobotConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
            config_entry=entry,
        )
        session = async_get_clientsession(hass)

        self.client = AirobotClient(
            host=entry.data[CONF_HOST],
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
            session=session,
        )

    @override
    async def _async_update_data(self) -> AirobotData:
        """Fetch data from API endpoint."""
        try:
            status, settings = await asyncio.gather(
                self.client.get_statuses(),
                self.client.get_settings(),
            )
        except AirobotAuthError as err:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN,
                translation_key="authentication_failed",
            ) from err
        except AirobotConnectionError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="connection_failed",
            ) from err

        return AirobotData(status=status, settings=settings)


class AirobotVUCoordinator(DataUpdateCoordinator[AirobotVUData]):
    """Class to manage fetching Airobot VU data via Modbus."""

    config_entry: AirobotConfigEntry

    def __init__(self, hass: HomeAssistant, entry: AirobotConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
            config_entry=entry,
        )
        self.client = AirobotModbusClient(host=entry.data[CONF_HOST])

    @override
    async def _async_setup(self) -> None:
        """Connect the Modbus client."""
        try:
            await self.client.connect()
        except VUError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="connection_failed",
            ) from err

    @override
    async def async_shutdown(self) -> None:
        """Disconnect the Modbus client on shutdown.

        Runs on unload, on failed setup, and on Home Assistant stop, so a
        client connected during _async_setup never leaks.
        """
        await super().async_shutdown()
        await self.client.disconnect()

    @override
    async def _async_update_data(self) -> AirobotVUData:
        """Fetch data from the Modbus device."""
        try:
            return await self.client.async_get_data()
        except VUError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="connection_failed",
            ) from err
