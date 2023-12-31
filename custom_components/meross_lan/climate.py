from __future__ import annotations

import typing

from homeassistant import const as hac
from homeassistant.components import climate
from homeassistant.components.climate import HVACAction, HVACMode

from . import meross_entity as me
from .merossclient import const as mc  # mEROSS cONST
from .number import MLConfigNumber

if typing.TYPE_CHECKING:
    from typing import ClassVar, Final

    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from .meross_device import MerossDeviceBase


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_devices
):
    me.platform_setup_entry(hass, config_entry, async_add_devices, climate.DOMAIN)


class MtsClimate(me.MerossEntity, climate.ClimateEntity):
    PLATFORM = climate.DOMAIN

    ATTR_TEMPERATURE: Final = climate.ATTR_TEMPERATURE
    TEMP_CELSIUS: Final = hac.TEMP_CELSIUS

    PRESET_CUSTOM: Final = "custom"
    PRESET_COMFORT: Final = "comfort"
    PRESET_SLEEP: Final = "sleep"
    PRESET_AWAY: Final = "away"
    PRESET_AUTO: Final = "auto"

    manager: MerossDeviceBase

    _attr_preset_modes: Final = [
        PRESET_CUSTOM,
        PRESET_COMFORT,
        PRESET_SLEEP,
        PRESET_AWAY,
        PRESET_AUTO,
    ]
    _attr_supported_features: Final = (
        climate.ClimateEntityFeature.PRESET_MODE
        | climate.ClimateEntityFeature.TARGET_TEMPERATURE
    )

    # these mappings are defined in inherited MtsXXX
    # they'll map between mts device 'mode' and HA 'preset'
    MTS_MODE_TO_PRESET_MAP: ClassVar[dict[int, str]]
    PRESET_TO_TEMPERATUREKEY_MAP: ClassVar[dict[str, str]]
    # in general Mts thermostats are only heating..MTS200 with 'summer mode' could override this
    MTS_HVAC_MODES: Final = [HVACMode.OFF, HVACMode.HEAT]

    __slots__ = (
        "_attr_current_temperature",
        "_attr_hvac_action",
        "_attr_hvac_mode",
        "_attr_hvac_modes",
        "_attr_max_temp",
        "_attr_min_temp",
        "_attr_preset_mode",
        "_attr_target_temperature",
        "_mts_active",
        "_mts_mode",
        "_mts_onoff",
        "_mts_summermode",
    )

    def __init__(self, manager: MerossDeviceBase, channel: object):
        self._attr_current_temperature = None
        self._attr_hvac_action = None
        self._attr_hvac_mode = None
        self._attr_hvac_modes = self.MTS_HVAC_MODES
        self._attr_max_temp = 35
        self._attr_min_temp = 5
        self._attr_preset_mode = None
        self._attr_target_temperature = None
        self._mts_active = None
        self._mts_mode: int | None = None
        self._mts_onoff = None
        self._mts_summermode = None
        super().__init__(manager, channel, None, None)

    def update_mts_state(self):
        self._attr_preset_mode = self.MTS_MODE_TO_PRESET_MAP.get(self._mts_mode)  # type: ignore
        if self._mts_onoff:
            if self._mts_summermode:
                self._attr_hvac_mode = HVACMode.COOL
                self._attr_hvac_action = (
                    HVACAction.COOLING if self._mts_active else HVACAction.IDLE
                )
            else:
                self._attr_hvac_mode = HVACMode.HEAT
                self._attr_hvac_action = (
                    HVACAction.HEATING if self._mts_active else HVACAction.IDLE
                )
        else:
            self._attr_hvac_mode = HVACMode.OFF
            self._attr_hvac_action = HVACAction.OFF

        self._attr_state = self._attr_hvac_mode if self.manager.online else None

        if self._hass_connected:
            self._async_write_ha_state()

    @property
    def supported_features(self):
        return self._attr_supported_features

    @property
    def temperature_unit(self):
        return MtsClimate.TEMP_CELSIUS

    @property
    def min_temp(self):
        return self._attr_min_temp

    @property
    def max_temp(self):
        return self._attr_max_temp

    @property
    def hvac_modes(self):
        return self._attr_hvac_modes

    @property
    def hvac_mode(self):
        return self._attr_hvac_mode

    @property
    def hvac_action(self):
        return self._attr_hvac_action

    @property
    def current_temperature(self):
        return self._attr_current_temperature

    @property
    def target_temperature(self):
        return self._attr_target_temperature

    @property
    def target_temperature_step(self):
        return 0.5

    @property
    def preset_modes(self):
        return self._attr_preset_modes

    @property
    def preset_mode(self):
        return self._attr_preset_mode

    @property
    def translation_key(self):
        return "mts_climate"

    async def async_turn_on(self):
        await self.async_request_onoff(1)

    async def async_turn_off(self):
        await self.async_request_onoff(0)

    async def async_set_preset_mode(self, preset_mode: str):
        raise NotImplementedError()

    async def async_set_temperature(self, **kwargs):
        raise NotImplementedError()

    async def async_request_onoff(self, onoff: int):
        raise NotImplementedError()


class MtsSetPointNumber(MLConfigNumber):
    """
    Helper entity to configure MTS (thermostats) setpoints
    AKA: Heat(comfort) - Cool(sleep) - Eco(away)
    """

    PRESET_TO_ICON_MAP: Final = {
        MtsClimate.PRESET_COMFORT: "mdi:sun-thermometer",
        MtsClimate.PRESET_SLEEP: "mdi:power-sleep",
        MtsClimate.PRESET_AWAY: "mdi:bag-checked",
    }

    def __init__(self, climate: MtsClimate, preset_mode: str):
        self._climate = climate
        self._preset_mode = preset_mode
        self.key_value = climate.PRESET_TO_TEMPERATUREKEY_MAP[preset_mode]
        self._attr_icon = MtsSetPointNumber.PRESET_TO_ICON_MAP[preset_mode]
        self._attr_name = f"{preset_mode} {MLConfigNumber.DeviceClass.TEMPERATURE}"
        super().__init__(
            climate.manager,
            climate.channel,
            f"config_{mc.KEY_TEMPERATURE}_{self.key_value}",
            MLConfigNumber.DeviceClass.TEMPERATURE,
        )

    @property
    def native_max_value(self):
        return self._climate._attr_max_temp

    @property
    def native_min_value(self):
        return self._climate._attr_min_temp

    @property
    def native_step(self):
        return self._climate.target_temperature_step

    @property
    def native_unit_of_measurement(self):
        return MtsClimate.TEMP_CELSIUS

    @property
    def ml_multiplier(self):
        return 10
