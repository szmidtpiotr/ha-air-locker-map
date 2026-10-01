"""Czujnik problemu: odczyt wygląda na zepsuty (zawieszony, zalany, nierealny, odstający)."""
from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import AirLockerMapConfigEntry
from .entity import AirLockerMapEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: AirLockerMapConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([AirLockerMapSuspect(entry.runtime_data)])


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
