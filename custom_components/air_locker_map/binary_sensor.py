"""Czujnik problemu: odczyt wygląda na zepsuty (zawieszony, zalany, nierealny, odstający)."""
from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_THRESHOLD, DEFAULT_THRESHOLD, RESOLVE_RATIO
from .coordinator import AirLockerMapConfigEntry
from .entity import AirLockerMapEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: AirLockerMapConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    threshold = entry.options.get(CONF_THRESHOLD, DEFAULT_THRESHOLD)
    async_add_entities([AirLockerMapSuspect(entry.runtime_data), AirLockerMapSmog(entry.runtime_data, threshold)])


class AirLockerMapSuspect(AirLockerMapEntity, BinarySensorEntity):
    _attr_translation_key = "suspect"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "suspect")

    @property
    def is_on(self) -> bool:
        return bool(self.reading.get("suspect")) or self.reading.get("status") not in (None, "ok")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"flags": self.reading.get("flags"), "reasons": self.reading.get("flag_labels"),
                "status": self.reading.get("status")}


class AirLockerMapSmog(AirLockerMapEntity, BinarySensorEntity):
    """Przekroczenie progu PM2.5 z histerezą: włącza się powyżej progu, wyłącza poniżej 80% progu."""

    _attr_translation_key = "smog"
    _attr_icon = "mdi:smog"

    def __init__(self, coordinator, threshold: float) -> None:
        super().__init__(coordinator, "smog")
        self._threshold = float(threshold)
        self._on = False

    def _handle_coordinator_update(self) -> None:
        pm25 = (self.reading.get("measurements") or {}).get("pm25")
        if pm25 is not None and not self.reading.get("suspect"):
            if not self._on and pm25 > self._threshold:
                self._on = True
            elif self._on and pm25 < self._threshold * RESOLVE_RATIO:
                self._on = False
        super()._handle_coordinator_update()

    @property
    def is_on(self) -> bool:
        return self._on

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._handle_coordinator_update()  # od razu po starcie, bez czekania na kolejny cykl

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"threshold": self._threshold, "off_below": round(self._threshold * RESOLVE_RATIO, 1),
                "pm25": (self.reading.get("measurements") or {}).get("pm25"), "source": self.reading.get("name")}
