"""Konfiguracja przez interfejs: serwer + klucz, potem tryb (dom / paczkomat / czujnik)."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_API_KEY, CONF_URL
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import AirLockerMapApi, AirLockerMapError, AuthError, NotFoundError
from .const import (
    CONF_THRESHOLD,
    DEFAULT_THRESHOLD,
    THRESHOLD_OPTIONS,
    CONF_CODE,
    CONF_INCLUDE_SUSPECT,
    CONF_MODE,
    CONF_SCAN_MINUTES,
    DEFAULT_SCAN_MINUTES,
    DEFAULT_URL,
    DOMAIN,
    MIN_SCAN_MINUTES,
    MODE_HOME,
    MODE_LOCKER,
    MODE_SENSOR,
)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL, default=DEFAULT_URL): TextSelector(TextSelectorConfig(type=TextSelectorType.URL)),
        vol.Required(CONF_API_KEY): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
        vol.Required(CONF_MODE, default=MODE_HOME): SelectSelector(
            SelectSelectorConfig(
                options=[MODE_HOME, MODE_LOCKER, MODE_SENSOR],
                mode=SelectSelectorMode.LIST,
                translation_key="mode",
            )
        ),
    }
)
CODE_SCHEMA = vol.Schema({vol.Required(CONF_CODE): str})


class AirLockerMapConfigFlow(ConfigFlow, domain=DOMAIN):
    """Konfiguracja Air Locker Map."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    async def _probe(self, data: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
        """Próbne zapytanie — zwraca (odczyt, None) albo (None, klucz błędu)."""
        api = AirLockerMapApi(async_get_clientsession(self.hass), data[CONF_URL], data[CONF_API_KEY])
        try:
            reading = await api.fetch(
                data[CONF_MODE],
                code=data.get(CONF_CODE),
                lat=self.hass.config.latitude,
                lon=self.hass.config.longitude,
            )
        except AuthError:
            return None, "invalid_auth"
        except NotFoundError:
            return None, "not_found"
        except AirLockerMapError:
            return None, "cannot_connect"
        return reading, None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self._data = {**user_input, CONF_URL: user_input[CONF_URL].rstrip("/")}
            if self._data[CONF_MODE] != MODE_HOME:
                return await self.async_step_code()
            await self.async_set_unique_id(f"{MODE_HOME}")
            self._abort_if_unique_id_configured()
            reading, error = await self._probe(self._data)
            if error:
                errors["base"] = error
            else:
                # bez nazwy czujnika w tytule — w trybie „najbliższy” czujnik może się zmienić,
                # a tytuł trafia do nazw encji
                return self.async_create_entry(title="Powietrze — dom", data=self._data)
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input or {}),
            errors=errors,
        )

    async def async_step_code(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            code = user_input[CONF_CODE].strip().upper().replace(" ", "")
            data = {**self._data, CONF_CODE: code}
            await self.async_set_unique_id(f"{data[CONF_MODE]}:{code}")
            self._abort_if_unique_id_configured()
            _, error = await self._probe(data)
            if error:
                errors["base"] = error
            else:
                title = f"Powietrze — przy {code}" if data[CONF_MODE] == MODE_LOCKER else f"Powietrze — {code}"
                return self.async_create_entry(title=title, data=data)
        return self.async_show_form(
            step_id="code",
            data_schema=CODE_SCHEMA,
            errors=errors,
            description_placeholders={"mode": self._data.get(CONF_MODE, "")},
        )

    # --- ponowne uwierzytelnienie, gdy klucz zostanie unieważniony

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {**entry.data, CONF_API_KEY: user_input[CONF_API_KEY]}
            _, error = await self._probe(data)
            if error:
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(entry, data=data)
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {vol.Required(CONF_API_KEY): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))}
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> OptionsFlow:
        return AirLockerMapOptionsFlow()


class AirLockerMapOptionsFlow(OptionsFlow):
    """Opcje: częstotliwość odpytywania i czy dopuszczać podejrzane czujniki."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            if CONF_THRESHOLD in user_input:
                user_input[CONF_THRESHOLD] = int(user_input[CONF_THRESHOLD])
            return self.async_create_entry(data=user_input)
        opts = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_MINUTES, default=opts.get(CONF_SCAN_MINUTES, DEFAULT_SCAN_MINUTES)
                    ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_MINUTES, max=240)),
                    vol.Required(
                        CONF_INCLUDE_SUSPECT, default=opts.get(CONF_INCLUDE_SUSPECT, False)
                    ): bool,
                    vol.Required(
                        CONF_THRESHOLD, default=str(opts.get(CONF_THRESHOLD, DEFAULT_THRESHOLD))
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=[str(t) for t in THRESHOLD_OPTIONS],
                            mode=SelectSelectorMode.DROPDOWN,
                            translation_key="threshold",
                        )
                    ),
                }
            ),
        )
