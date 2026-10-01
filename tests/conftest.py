"""Wspólne fikstury testów."""
import pytest

URL = "http://air.test"
KEY = "alm_test"

SENSOR = {
    "name": "KAP02M", "address": "Niepokalanowska 2B, 05-085 Kampinos", "description": "Przy sklepie",
    "lat": 52.27, "lon": 20.46, "elevation": 86.0, "updated": 1790871312, "changed": 1790871312,
    "status": "ok", "level": "VERY_GOOD", "sensor_generation": "old",
    "measurements": {"pm1": 3.7, "pm25": 5.4, "pm4": None, "pm10": 6.2, "pressure": 1029.1,
                     "pressure_sl": 1029.1, "humidity": 59.0, "temperature": 20.3},
    "suspect": False, "flags": [], "flag_labels": [], "distance_m": 564,
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def sensor_payload():
    return dict(SENSOR)
