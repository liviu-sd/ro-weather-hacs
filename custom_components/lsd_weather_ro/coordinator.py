from dataclasses import dataclass
import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LOCATION, CONF_CODE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    TimestampDataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util.dt import utc_from_timestamp

from .anmh_weather import AnmhWeather

from .const import (
    DOMAIN,
    CURRENT_CONDITIONS_UPDATE_INTERVAL,
    FORECAST_DAILY_UPDATE_INTERVAL,
    CONF_FORECAST_LOCATION,
)

EXCEPTIONS = (TimeoutError, Exception)

_LOGGER = logging.getLogger(__name__)

@dataclass
class ANMHWeatherData:
    """Data for AccuWeather integration."""

    coordinator_current_conditions: ANMHCurrentConditionsUpdateCoordinator
    coordinator_daily_forecast: ANMHDailyForecastDataUpdateCoordinator


REQUEST_TIMEOUT = 120

# Define the type of data the coordinator will hold
type CoordinatorDataType = dict[str, list]


class ANMHCurrentConditionsUpdateCoordinator(
    DataUpdateCoordinator[CoordinatorDataType]
):
    """Class to manage fetching ANMH weather data."""

    config_entry: ConfigEntry
    weather_client: AnmhWeather

    def __init__(
        self, hass: HomeAssistant, configEntry: ConfigEntry, weather_client: AnmhWeather
    ) -> None:
        """Initialize the data update coordinator."""
        self.hass = hass
        self.config_entry = configEntry
        location = configEntry.data[CONF_LOCATION]

        self.weather_client = weather_client

        super().__init__(
            hass,
            _LOGGER,
            name=f"{location} (ANMH Weather Conditions)",
            update_interval=CURRENT_CONDITIONS_UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> CoordinatorDataType:
        """Fetch combined weather data from ANMH API via the library."""
        location = self.config_entry.data.get(CONF_LOCATION, "Unknown")

        _LOGGER.debug("Attempting to fetch combined ANMH data for %s", location)

        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                weather_data = await self.weather_client.get_weather()

        except EXCEPTIONS as error:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="current_conditions_update_error",
                translation_placeholders={"error": repr(error)},
            ) from error
        # except InvalidApiKeyError as err:
        #     raise ConfigEntryAuthFailed(
        #         translation_domain=DOMAIN,
        #         translation_key="auth_error",
        #         translation_placeholders={"entry": self.config_entry.title},
        #     ) from err

        # _LOGGER.debug("Requests remaining: %d", self.accuweather.requests_remaining)

        return weather_data


class ANMHDailyForecastDataUpdateCoordinator(
    # DataUpdateCoordinator[CoordinatorDataType]
    TimestampDataUpdateCoordinator[CoordinatorDataType]
):
    config_entry: ConfigEntry
    weather_client: AnmhWeather

    def __init__(
        self, hass: HomeAssistant, configEntry: ConfigEntry, weather_client: AnmhWeather
    ) -> None:
        """Initialize the data update coordinator."""
        self.hass = hass
        self.config_entry = configEntry
        forecast_location = configEntry.data[CONF_FORECAST_LOCATION]

        self.weather_client = weather_client

        super().__init__(
            hass,
            _LOGGER,
            config_entry=configEntry,
            name=f"{forecast_location} (ANMH Forecast Daily))",
            update_interval=FORECAST_DAILY_UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> CoordinatorDataType:
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                forecast_data = await self.weather_client.get_forecast()

        except EXCEPTIONS as error:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="forecast_update_error",
                translation_placeholders={"error": repr(error)},
            ) from error
        # except InvalidApiKeyError as err:
        #     raise ConfigEntryAuthFailed(
        #         translation_domain=DOMAIN,
        #         translation_key="auth_error",
        #         translation_placeholders={"entry": self.config_entry.title},
        #     ) from err

        # _LOGGER.debug("Requests remaining: %d", self.accuweather.requests_remaining)

        return forecast_data
