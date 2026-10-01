"""Wspólna baza encji: jedno urządzenie na wpis konfiguracyjny."""
from __future__ import annotations

from homeassistant.const import CONF_URL
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN
from .coordinator import AirLockerMapCoordinator


class AirLockerMapEntity(CoordinatorEntity[AirLockerMapCoordinator]):
    """Encja oparta o odczyt z koordynatora."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION

    def __init__(self, coordinator: AirLockerMapCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="air-locker-map",
            model="Czujnik w paczkomacie InPost",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=entry.data[CONF_URL],
        )

    @property
    def reading(self) -> dict:
        return self.coordinator.data or {}
