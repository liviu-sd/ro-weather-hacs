import logging
import asyncio


# from .config_flow import OptionsFlowHandler
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, CONF_LOCATION
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .anmh_weather import AnmhWeather

from .const import DOMAIN, DEFAULT_PLATFORMS, CONF_FORECAST_LOCATION
from .coordinator import (
    ANMHWeatherData,
    ANMHCurrentConditionsUpdateCoordinator,
    ANMHDailyForecastDataUpdateCoordinator,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up ANMH Weather component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up ANMH Weather integration from a config entry.

    Returns:
        bool: True if setup was successful, False otherwise.
    """

    location: str = config_entry.data[CONF_LOCATION]
    forecast_location: str = config_entry.data[CONF_FORECAST_LOCATION]

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    if config_entry.entry_id in hass.data[DOMAIN]:
        _LOGGER.warning(
            "Config entry %s for %s has already been setup!",
            config_entry.title,
            DOMAIN,
        )
        return False

    session = async_get_clientsession(hass)
    weather_client = AnmhWeather(
        location_name=location, forecast_location=forecast_location, session=session
    )
    coordinator_current_conditions = ANMHCurrentConditionsUpdateCoordinator(
        hass, config_entry, weather_client
    )
    coordinator_daily_forecast = ANMHDailyForecastDataUpdateCoordinator(
        hass, config_entry, weather_client
    )
    await asyncio.gather(
        coordinator_current_conditions.async_config_entry_first_refresh(),
        coordinator_daily_forecast.async_config_entry_first_refresh(),
    )

    config_entry.runtime_data = ANMHWeatherData(
        coordinator_current_conditions=coordinator_current_conditions,
        coordinator_daily_forecast=coordinator_daily_forecast,
    )

    # hass.data[DOMAIN][config_entry.entry_id] = coordinator_current_conditions

    await hass.config_entries.async_forward_entry_setups(
        config_entry, DEFAULT_PLATFORMS
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload ANMH Weather config entry."""
    platforms = entry.data.get("platforms", DEFAULT_PLATFORMS)
    unload_ok = True

    for platform in platforms:
        try:
            _LOGGER.debug(
                "Unloading platform %s for entry: %s", platform, entry.entry_id
            )
            platform_unloaded = await hass.config_entries.async_forward_entry_unload(
                entry, platform
            )
            if not platform_unloaded:
                _LOGGER.warning(
                    "Platform %s for entry %s was not fully unloaded",
                    platform,
                    entry.entry_id,
                )
            unload_ok = unload_ok and platform_unloaded
        except Exception as e:
            _LOGGER.error(
                "Error unloading platform %s for entry %s: %s",
                platform,
                entry.entry_id,
                e,
                exc_info=True,
            )
            unload_ok = False

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        _LOGGER.debug("Entry unloaded successfully: %s", entry.entry_id)
    else:
        _LOGGER.warning(
            "Entry %s not fully unloaded. Some resources may remain.", entry.entry_id
        )

    return unload_ok


# async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
#     platforms = entry.options.get("platforms", entry.data.get("platforms", []))
#     current_platforms = entry.data.get("platforms", [])
#     _LOGGER.debug("Update listener triggered for entry: %s", entry.entry_id)
#     _LOGGER.debug("Updated platforms: %s", platforms)

#     for platform in current_platforms:
#         if platform not in platforms:
#             await hass.config_entries.async_forward_entry_unload(entry, platform)

#     for platform in platforms:
#         if platform not in current_platforms:
#             await hass.config_entries.async_forward_entry_setups(entry, [platform])

#     hass.config_entries.async_update_entry(entry, options={"platforms": platforms})
