"""Koordynator: jedno zapytanie do API na cykl, wspólne dla wszystkich encji wpisu."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AirLockerMapApi, AirLockerMapError, AuthError
from .const import (
    CONF_CODE,
    CONF_INCLUDE_SUSPECT,
    CONF_MODE,
    CONF_SCAN_MINUTES,
    DEFAULT_SCAN_MINUTES,
    DOMAIN,
    MODE_HOME,
)

_LOGGER = logging.getLogger(__name__)

type AirLockerMapConfigEntry = ConfigEntry[AirLockerMapCoordinator]


class AirLockerMapCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Pobiera odczyt czujnika dla jednego wpisu konfiguracyjnego."""

    config_entry: AirLockerMapConfigEntry

    def __init__(self, hass: HomeAssistant, entry: AirLockerMapConfigEntry) -> None:
        minutes = entry.options.get(CONF_SCAN_MINUTES, DEFAULT_SCAN_MINUTES)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=minutes),
        )
        self.api = AirLockerMapApi(
            async_get_clientsession(hass), entry.data[CONF_URL], entry.data[CONF_API_KEY]
        )

    async def _async_update_data(self) -> dict[str, Any]:
        entry = self.config_entry
        mode = entry.data[CONF_MODE]
        try:
            return await self.api.fetch(
                mode,
                code=entry.data.get(CONF_CODE),
                # tryb „dom” zawsze z aktualnej lokalizacji HA — zmiana adresu domu nie wymaga rekonfiguracji
                lat=self.hass.config.latitude if mode == MODE_HOME else None,
                lon=self.hass.config.longitude if mode == MODE_HOME else None,
                include_suspect=entry.options.get(CONF_INCLUDE_SUSPECT, False),
            )
        except AuthError as err:
            raise ConfigEntryAuthFailed("Klucz API odrzucony — mógł zostać unieważniony") from err
        except AirLockerMapError as err:
            raise UpdateFailed(str(err)) from err
