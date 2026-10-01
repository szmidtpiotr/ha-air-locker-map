"""Testy integracji na prawdziwym rdzeniu Home Assistanta (pytest-homeassistant-custom-component)."""
import re

from homeassistant import config_entries
from homeassistant.const import CONCENTRATION_MICROGRAMS_PER_CUBIC_METER, CONF_API_KEY, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.air_locker_map.const import CONF_CODE, CONF_MODE, DOMAIN

from .conftest import KEY, SENSOR, URL

NEAREST = re.compile(r"^http://air\.test/api/v1/nearest.*")
LOCKER = re.compile(r"^http://air\.test/api/v1/lockers/KAP01M/nearest.*")


async def test_flow_home(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(NEAREST, json={"sensors": [SENSOR]})
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_URL: URL + "/", CONF_API_KEY: KEY, CONF_MODE: "home"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Powietrze — dom"
    assert result["data"][CONF_URL] == URL  # ukośnik na końcu zdjęty
    # klucz poszedł w nagłówku, nie w adresie
    _, url, _, headers = aioclient_mock.mock_calls[0]
    assert headers["X-API-Key"] == KEY and "api_key" not in str(url)


async def test_flow_locker_and_bad_key(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(LOCKER, status=403, text="Nieznany klucz")
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_URL: URL, CONF_API_KEY: "zly", CONF_MODE: "locker"}
    )
    assert result["step_id"] == "code"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_CODE: " kap01m "})
    assert result["errors"] == {"base": "invalid_auth"}

    aioclient_mock.clear_requests()
    aioclient_mock.get(LOCKER, json={"locker": {"name": "KAP01M"}, "sensors": [SENSOR]})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_CODE: "KAP01M"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_CODE] == "KAP01M"
    assert result["title"] == "Powietrze — przy KAP01M"


async def test_sensors(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(NEAREST, json={"sensors": [SENSOR]})
    entry = MockConfigEntry(domain=DOMAIN, title="Powietrze — dom", unique_id="home",
                            data={CONF_URL: URL, CONF_API_KEY: KEY, CONF_MODE: "home"})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    states = {s.entity_id: s for s in hass.states.async_all()}
    pm25 = next(s for s in states.values() if s.attributes.get("device_class") == "pm25")
    # HA używa greckiego μ (U+03BC), nie znaku mikro µ — porównujemy ze stałą
    assert pm25.state == "5.4"
    assert pm25.attributes["unit_of_measurement"] == CONCENTRATION_MICROGRAMS_PER_CUBIC_METER
    assert pm25.entity_id == "sensor.powietrze_dom_pm2_5"
    source = next(s for s in states.values() if s.state == "KAP02M")
    assert source.attributes["address"].startswith("Niepokalanowska")
    problem = next(s for s in states.values() if s.domain == "binary_sensor")
    assert problem.state == "off"
    # wilgotność i temperatura z obudowy domyślnie wyłączone
    assert not any(s.attributes.get("device_class") == "temperature" for s in states.values())


async def test_revoked_key_starts_reauth(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(NEAREST, status=403, text="unieważniony")
    entry = MockConfigEntry(domain=DOMAIN, unique_id="home",
                            data={CONF_URL: URL, CONF_API_KEY: KEY, CONF_MODE: "home"})
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    flows = hass.config_entries.flow.async_progress()
    assert any(f["context"]["source"] == "reauth" for f in flows)


async def test_smog_sensor_hysteresis(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """Przekroczenie normy: włącza się powyżej progu, nie gaśnie przy 30 (>28), gaśnie poniżej 28."""
    from datetime import timedelta

    from homeassistant.util import dt as dt_util
    from pytest_homeassistant_custom_component.common import async_fire_time_changed

    def reading(pm25):
        return {"sensors": [{**SENSOR, "measurements": {**SENSOR["measurements"], "pm25": pm25}}]}

    aioclient_mock.get(NEAREST, json=reading(40))
    entry = MockConfigEntry(domain=DOMAIN, title="Powietrze — dom", unique_id="home",
                            data={CONF_URL: URL, CONF_API_KEY: KEY, CONF_MODE: "home"}, options={"threshold": 35})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    eid = "binary_sensor.powietrze_dom_threshold_exceeded"
    assert hass.states.get(eid).state == "on"

    for value, expected in ((30, "on"), (27, "off"), (34, "off")):
        aioclient_mock.clear_requests()
        aioclient_mock.get(NEAREST, json=reading(value))
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=16 * (value + 1)))
        await hass.async_block_till_done()
        assert hass.states.get(eid).state == expected, value
    assert hass.states.get(eid).attributes["off_below"] == 28.0
