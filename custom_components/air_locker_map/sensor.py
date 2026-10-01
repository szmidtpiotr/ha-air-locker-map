"""Sensory odczytów: pyły, ciśnienie, wilgotność, temperatura + paczkomat źródłowy."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    PERCENTAGE,
    EntityCategory,
    UnitOfLength,
    UnitOfPressure,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import AirLockerMapConfigEntry
from .entity import AirLockerMapEntity


def _m(key: str) -> Callable[[dict[str, Any]], Any]:
    return lambda r: (r.get("measurements") or {}).get(key)


@dataclass(frozen=True, kw_only=True)
class AirLockerMapSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any]


SENSORS: tuple[AirLockerMapSensorDescription, ...] = (
    AirLockerMapSensorDescription(
        key="pm1", device_class=SensorDeviceClass.PM1, state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER, value_fn=_m("pm1"),
    ),
    AirLockerMapSensorDescription(
        key="pm25", device_class=SensorDeviceClass.PM25, state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER, value_fn=_m("pm25"),
    ),
    AirLockerMapSensorDescription(
        key="pm4", translation_key="pm4", state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER, icon="mdi:blur",
        value_fn=_m("pm4"), entity_registry_enabled_default=False,  # tylko nowsze czujniki
    ),
    AirLockerMapSensorDescription(
        key="pm10", device_class=SensorDeviceClass.PM10, state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER, value_fn=_m("pm10"),
    ),
    AirLockerMapSensorDescription(
        key="pressure_sl", translation_key="pressure_sl", device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        state_class=SensorStateClass.MEASUREMENT, native_unit_of_measurement=UnitOfPressure.HPA,
        value_fn=_m("pressure_sl"),
    ),
    AirLockerMapSensorDescription(
        key="pressure", translation_key="pressure_raw", device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        state_class=SensorStateClass.MEASUREMENT, native_unit_of_measurement=UnitOfPressure.HPA,
        value_fn=_m("pressure"), entity_registry_enabled_default=False,
    ),
    # wilgotność i temperatura mierzone w obudowie paczkomatu — domyślnie wyłączone
    AirLockerMapSensorDescription(
        key="humidity", translation_key="humidity_case", device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT, native_unit_of_measurement=PERCENTAGE,
        value_fn=_m("humidity"), entity_registry_enabled_default=False,
    ),
    AirLockerMapSensorDescription(
        key="temperature", translation_key="temperature_case", device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT, native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=_m("temperature"), entity_registry_enabled_default=False,
    ),
    AirLockerMapSensorDescription(
        key="distance", translation_key="distance", device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.METERS, entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda r: r.get("distance_m"),
    ),
    AirLockerMapSensorDescription(
        key="updated", translation_key="updated", device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda r: datetime.fromtimestamp(r["updated"], timezone.utc) if r.get("updated") else None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: AirLockerMapConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = [AirLockerMapSensor(coordinator, d) for d in SENSORS]
    entities.append(AirLockerMapSourceSensor(coordinator))
    async_add_entities(entities)


class AirLockerMapSensor(AirLockerMapEntity, SensorEntity):
    entity_description: AirLockerMapSensorDescription

    def __init__(self, coordinator, description: AirLockerMapSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.reading)


class AirLockerMapSourceSensor(AirLockerMapEntity, SensorEntity):
    """Z którego paczkomatu pochodzą odczyty — w trybach „najbliższy” może się zmieniać."""

    _attr_translation_key = "source"
    _attr_icon = "mdi:package-variant-closed"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "source")

    @property
    def native_value(self) -> str | None:
        return self.reading.get("name")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        r = self.reading
        return {
            "address": r.get("address"),
            "description": r.get("description"),
            "latitude": r.get("lat"),
            "longitude": r.get("lon"),
            "elevation": r.get("elevation"),
            "level": r.get("level"),
            "sensor_generation": r.get("sensor_generation"),
            "flags": r.get("flags"),
        }
