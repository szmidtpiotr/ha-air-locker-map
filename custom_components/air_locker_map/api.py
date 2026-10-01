"""Klient API air-locker-map (wersja 1)."""
from __future__ import annotations

from typing import Any

import aiohttp

from .const import MODE_HOME, MODE_LOCKER, MODE_SENSOR


class AirLockerMapError(Exception):
    """Błąd po stronie serwera albo sieci."""


class AuthError(AirLockerMapError):
    """Brak, zły albo unieważniony klucz API (401/403)."""


class NotFoundError(AirLockerMapError):
    """Nie ma takiego paczkomatu / czujnika (404)."""


class RateLimitError(AirLockerMapError):
    """Przekroczony limit zapytań klucza (429)."""


class AirLockerMapApi:
    """Cienka warstwa nad /api/v1 — zwraca jeden czujnik w formacie API (dict)."""

    def __init__(self, session: aiohttp.ClientSession, url: str, api_key: str) -> None:
        self._session = session
        self._url = url.rstrip("/")
        self._key = api_key.strip()

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            async with self._session.get(
                f"{self._url}/api/v1{path}",
                params=params,
                headers={"X-API-Key": self._key, "Accept": "application/json"},
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                if resp.status in (401, 403):
                    raise AuthError(await resp.text())
                if resp.status == 404:
                    raise NotFoundError(await resp.text())
                if resp.status == 429:
                    raise RateLimitError(await resp.text())
                if resp.status != 200:
                    raise AirLockerMapError(f"HTTP {resp.status}")
                return await resp.json()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise AirLockerMapError(str(err)) from err

    async def fetch(
        self,
        mode: str,
        *,
        code: str | None = None,
        lat: float | None = None,
        lon: float | None = None,
        include_suspect: bool = False,
    ) -> dict[str, Any]:
        """Odczyt czujnika dla danego trybu. Dla trybów „najbliższy” API samo pomija zepsute czujniki."""
        suspect = "true" if include_suspect else "false"
        if mode == MODE_SENSOR:
            return await self._get(f"/sensors/{code}")
        if mode == MODE_LOCKER:
            data = await self._get(f"/lockers/{code}/nearest", {"n": 1, "include_suspect": suspect})
        elif mode == MODE_HOME:
            data = await self._get("/nearest", {"lat": lat, "lon": lon, "n": 1, "include_suspect": suspect})
        else:
            raise ValueError(mode)
        if not data.get("sensors"):
            raise NotFoundError("brak działających czujników w pobliżu")
        return data["sensors"][0]
