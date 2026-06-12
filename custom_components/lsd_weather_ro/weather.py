import logging
from astral.sun import sun
from astral import LocationInfo
import datetime
from homeassistant.components.weather import (
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_TIME,
    ATTR_FORECAST_TEMP_LOW,
    ATTR_FORECAST_TEMP,
    ATTR_CONDITION_CLEAR_NIGHT,
    ATTR_CONDITION_SUNNY,
    CoordinatorWeatherEntity,
    Forecast,
    # WeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.const import (
    UnitOfLength,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfPrecipitationDepth,
    CONF_LOCATION,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .coordinator import (
    ANMHWeatherData,
    ANMHCurrentConditionsUpdateCoordinator,
    ANMHDailyForecastDataUpdateCoordinator,
)
from .const import DOMAIN, CONF_FORECAST_LOCATION
from .helpers import get_device_info, get__attr_unique_id

from .anmh_weather import (
    WeatherData,
    BaseTimelineEntry,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ANMH weather entity based on a config entry."""
    # coordinator: ANMHCurrentConditionsUpdateCoordinator = hass.data[DOMAIN][
    #     entry.entry_id
    # ]
    async_add_entities([AnmhWeatherEntity(entry.runtime_data, entry)])


class AnmhWeatherEntity(
    CoordinatorWeatherEntity[
        ANMHCurrentConditionsUpdateCoordinator,
        ANMHDailyForecastDataUpdateCoordinator,
    ],
    # WeatherEntity,
):
    """Representation of ANMH weather data."""

    _attr_has_entity_name = True
    _attr_name = None

    _attr_supported_features = (
        WeatherEntityFeature.FORECAST_DAILY
        # | WeatherEntityFeature.FORECAST_TWICE_DAILY
        # | WeatherEntityFeature.FORECAST_HOURLY
    )

    def __init__(
        self,
        anmhweather_data: ANMHWeatherData,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the weather entity."""
        super().__init__(
            observation_coordinator=anmhweather_data.coordinator_current_conditions,
            daily_coordinator=anmhweather_data.coordinator_daily_forecast,
        )

        self.config_entry = entry
        self._location = entry.data.get(CONF_LOCATION, "ANMH Weather")

        self._attr_unique_id = get__attr_unique_id("", entry.entry_id, "weather")

        self._attr_device_info = get_device_info(DOMAIN, self._location)
        self._forecast_location = entry.data[CONF_FORECAST_LOCATION]
        self.daily_coordinator = anmhweather_data.coordinator_daily_forecast
        self.coordinator_current_conditions = (
            anmhweather_data.coordinator_current_conditions
        )

    # --- Required properties ---
    @property
    def condition(self) -> str | None:
        """Return the current weather condition."""
        return condition_to_night_time(
            self.coordinator_current_conditions.data.condition
        )

    @property
    def native_temperature(self) -> float | None:
        """Return the current temperature."""
        return self.coordinator_current_conditions.data.temperature

    @property
    def native_temperature_unit(self) -> str:
        return UnitOfTemperature.CELSIUS

    @property
    def native_precipitation_unit(self) -> str:
        return UnitOfPrecipitationDepth.MILLIMETERS

    @property
    def native_dew_point(self) -> float | None:
        """Return the dew point."""
        return self.coordinator_current_conditions.data.dew_point

    @property
    def humidity(self) -> float | None:
        """Return the current humidity."""
        return self.coordinator_current_conditions.data.relative_humidity_percent

    @property
    def native_pressure(self) -> float | None:
        """Return the current sea-level pressure."""
        return self.coordinator_current_conditions.data.pressure

    @property
    def native_pressure_unit(self) -> str:
        return UnitOfPressure.MBAR

    @property
    def native_wind_speed(self) -> float | None:
        """Return the current wind speed."""
        return self.coordinator_current_conditions.data.wind_speed

    @property
    def native_wind_speed_unit(self) -> str:
        return UnitOfSpeed.METERS_PER_SECOND

    @property
    def wind_bearing(self) -> float | str | None:
        """Return the current wind bearing."""
        return self.coordinator_current_conditions.data.wind_direction_text

    @property
    def icon(self) -> str|None:
        if self.coordinator_current_conditions.data.condition is None:
            return "mdi:cloud-question-outline"

    # @property
    # def native_visibility(self) -> float | None:
    #     """Return the current visibility."""
    #     return self.coordinator_current_conditions.data.visibility_km
    #     return (
    #         self._current_data.visibility_km
    #         if hasattr(self._current_data, "visibility_km")
    #         else None
    #     )

    # @property
    # def native_visibility_unit(self) -> str:
    #     return UnitOfLength.KILOMETERS
    
    @callback
    def _async_forecast_daily(self) -> list[Forecast] | None:
        """Return the daily forecast in native units."""
        return [
            {
                ATTR_FORECAST_TIME: item.data.isoformat(),
                ATTR_FORECAST_TEMP: item.temp_max,
                ATTR_FORECAST_CONDITION: item.hass_weather_condition,
                ATTR_FORECAST_TEMP_LOW: item.temp_min,
                # ATTR_FORECAST_TIME: utc_from_timestamp(item["EpochDate"]).isoformat(),
                # ATTR_FORECAST_CLOUD_COVERAGE: item["CloudCoverDay"],
                # ATTR_FORECAST_HUMIDITY: item["RelativeHumidityDay"].get("Average"),
                # ATTR_FORECAST_NATIVE_TEMP: item["TemperatureMax"][ATTR_VALUE],
                # ATTR_FORECAST_NATIVE_TEMP_LOW: item["TemperatureMin"][ATTR_VALUE],
                # ATTR_FORECAST_NATIVE_APPARENT_TEMP: item["RealFeelTemperatureMax"][
                #     ATTR_VALUE
                # ],
                # ATTR_FORECAST_NATIVE_PRECIPITATION: item["TotalLiquidDay"][ATTR_VALUE],
                # ATTR_FORECAST_PRECIPITATION_PROBABILITY: item[
                #     "PrecipitationProbabilityDay"
                # ],
                # ATTR_FORECAST_NATIVE_WIND_SPEED: item["WindDay"][ATTR_SPEED][
                #     ATTR_VALUE
                # ],
                # ATTR_FORECAST_NATIVE_WIND_GUST_SPEED: item["WindGustDay"][ATTR_SPEED][
                #     ATTR_VALUE
                # ],
                # ATTR_FORECAST_UV_INDEX: item["UVIndex"][ATTR_VALUE],
                # ATTR_FORECAST_WIND_BEARING: item["WindDay"][ATTR_DIRECTION]["Degrees"],
                # ATTR_FORECAST_CONDITION: CONDITION_MAP.get(item["IconDay"]),
            }
            for item in self.daily_coordinator.data
        ]


def is_daytime(dt: datetime.datetime) -> bool:
    """Check if it is currently daytime based on the sun position."""
    loc_info = LocationInfo("Bucharest", timezone="Europe/Bucharest")
    s = sun(loc_info.observer, date=dt)
    return s["sunrise"] <= dt <= s["sunset"]


def condition_to_night_time(
    condition: str, dt: datetime.datetime = datetime.datetime.now(datetime.UTC)
) -> str:
    """Convert condition to night time equivalent."""
    if condition == ATTR_CONDITION_SUNNY and not is_daytime(dt):
        return ATTR_CONDITION_CLEAR_NIGHT
    return condition
