import logging
from datetime import datetime
from typing import Optional, Dict, Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
    SensorStateClass,
    EntityCategory,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import (
    CONF_LOCATION,
    UnitOfTemperature,
    UnitOfSpeed,
    UnitOfPressure,
    UnitOfLength,
    PERCENTAGE,
    DEGREE,
    UnitOfIrradiance,
    UnitOfPrecipitationDepth,
    UnitOfVolumetricFlux,
)
from homeassistant.components.weather import (
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_TIME,
    ATTR_FORECAST_TEMP_LOW,
    ATTR_FORECAST_TEMP,
    ATTR_CONDITION_CLEAR_NIGHT,
    ATTR_CONDITION_SUNNY,
    Forecast,
)
from homeassistant.helpers.device_registry import DeviceInfo
import homeassistant.util.dt as dt_util  # For timezone conversion

from .coordinator import (
    ANMHWeatherData,
    ANMHCurrentConditionsUpdateCoordinator,
    ANMHDailyForecastDataUpdateCoordinator,
)
from .const import DOMAIN
from .helpers import get_device_info, get__attr_unique_id

# Import your library's model
from .anmh_weather import WeatherData, BaseTimelineEntry

_LOGGER = logging.getLogger(__name__)

# Define Sensor Descriptions using the field names as keys
# We will filter this list based on available data later
SENSOR_DESCRIPTIONS: tuple[SensorEntityDescription, ...] = (
    # --- Fields from BaseTimelineEntry ---
    SensorEntityDescription(
        key="temperature",
        name="Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="relative_humidity_percent",
        name="Relative Humidity",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="pressure",  # "mean_sea_level_pressure_hpa",
        name="Pressure",
        native_unit_of_measurement=UnitOfPressure.MBAR,  # .HPA,
        device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,  # Often has decimals, e.g. 1022.6
    ),
    SensorEntityDescription(
        key="wind_speed",
        name="Wind Speed",
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,  # .KILOMETERS_PER_HOUR,
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:weather-windy",
    ),
    SensorEntityDescription(
        key="wind_direction_text",
        name="Wind Direction",
        icon="mdi:compass-outline",
        # No unit, device_class, or state_class for textual direction
    ),
    SensorEntityDescription(
        key="max_wind_gust_kmh",
        name="Wind Gust",
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:weather-windy-variant",
    ),
    # --- Fields specific to WeatherData ---
    SensorEntityDescription(
        key="dew_point",
        name="Dew Point",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="wind_direction_degrees",
        name="Wind Direction Degrees",
        native_unit_of_measurement=DEGREE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:compass",
    ),
    SensorEntityDescription(
        key="wind_direction_max_gust_degrees",
        name="Wind Gust Direction Degrees",
        native_unit_of_measurement=DEGREE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:compass-rose",
        entity_registry_enabled_default=False,
    ),
    # wind_direction_max_gust_text covered by wind_direction_text generally
    SensorEntityDescription(
        key="wind_speed_average_kmh",
        name="Wind Speed Average",
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:weather-windy",
        entity_registry_enabled_default=False,  # Often less critical than current speed/gust
    ),
    SensorEntityDescription(
        key="station_pressure_hpa",
        name="Station Pressure",
        native_unit_of_measurement=UnitOfPressure.MBAR,
        device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="precipitation_accumulated_mm",  # 10 minute accumulated rainfall
        name="Precipitation 10 minutes",
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.TOTAL,  # represents a total over a period that might reset (e.g., daily)
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="precipitation_rate",
        name="Precipitation Rate",
        native_unit_of_measurement=UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
        device_class=SensorDeviceClass.PRECIPITATION_INTENSITY,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:weather-pouring",
        suggested_display_precision=2,
    ),
    SensorEntityDescription(
        key="snow_depth_cm",
        name="Snow Depth",
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:weather-snowy",
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="precipitation_1h_accumulated_mm",
        name="Precipitation 1h",
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.TOTAL_INCREASING,  # Total over the last hour
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="precipitation_12h_accumulated_mm",
        name="Precipitation 12h",
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.TOTAL_INCREASING,  # Total over the last 12 hours
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="precipitation_24h_accumulated_mm",
        name="Precipitation 24h",
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.TOTAL_INCREASING,  # Total over the last 24 hours
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="water_temperature",
        name="Water Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:thermometer-water",
        suggested_display_precision=1,
        entity_registry_enabled_default=False,  # Often specific to certain locations
    ),
    SensorEntityDescription(
        key="global_solar_radiation_wm2",
        name="Global Solar Radiation",
        native_unit_of_measurement=UnitOfIrradiance.WATTS_PER_SQUARE_METER,
        device_class=SensorDeviceClass.IRRADIANCE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:solar-power-variant-outline",
    ),
    SensorEntityDescription(
        key="global_solar_radiation_average_wm2",
        name="Global Solar Radiation Average",
        native_unit_of_measurement=UnitOfIrradiance.WATTS_PER_SQUARE_METER,
        device_class=SensorDeviceClass.IRRADIANCE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:solar-power-variant",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="diffuse_solar_radiation_wm2",
        name="Diffuse Solar Radiation",
        native_unit_of_measurement=UnitOfIrradiance.WATTS_PER_SQUARE_METER,
        device_class=SensorDeviceClass.IRRADIANCE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:weather-partly-cloudy",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="diffuse_solar_radiation_average_wm2",
        name="Diffuse Solar Radiation Average",
        native_unit_of_measurement=UnitOfIrradiance.WATTS_PER_SQUARE_METER,
        device_class=SensorDeviceClass.IRRADIANCE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:weather-partly-cloudy",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="visibility_km",
        name="Visibility",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:eye-outline",
    ),
    SensorEntityDescription(
        key="temperature_at_5cm",
        name="Temperature at 5cm",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:thermometer-low",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="temperature_average_at_5cm",
        name="Temperature Average at 5cm",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:thermometer-low",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="ground_temperature_at_5cm",
        name="Ground Temperature at 5cm",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:thermometer-lines",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="ground_temperature_average_at_5cm",
        name="Ground Temperature Average at 5cm",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:thermometer-lines",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="ground_temperature_at_10cm",
        name="Ground Temperature at 10cm",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:thermometer-lines",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="ground_temperature_average_at_10cm",
        name="Ground Temperature Average at 10cm",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:thermometer-lines",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="ground_temperature_at_20cm",
        name="Ground Temperature at 20cm",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:thermometer-lines",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="ground_temperature_average_at_20cm",
        name="Ground Temperature Average at 20cm",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:thermometer-lines",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="ground_temperature_at_30cm",
        name="Ground Temperature at 30cm",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:thermometer-lines",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="ground_temperature_average_at_30cm",
        name="Ground Temperature Average at 30cm",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:thermometer-lines",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="ground_temperature_at_50cm",
        name="Ground Temperature at 50cm",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:thermometer-lines",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="ground_temperature_average_at_50cm",
        name="Ground Temperature Average at 50cm",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:thermometer-lines",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="condition_raw",
        name="Raw Conditions",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    # SensorEntityDescription(
    #     key="itu_index",
    #     name="ITU",
    #     icon="mdi:checkbox-marked-circle",
    #     state_class=SensorStateClass.MEASUREMENT,
    #     entity_category=EntityCategory.DIAGNOSTIC,
    # ),
    SensorEntityDescription(
        key="itu_perception",
        name="ITU Perception",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="pressure_tendency_trend",
        icon="mdi:gauge",
        name="Pressure Tendency Trend",
    ),
    SensorEntityDescription(
        key="nebulosity",
        name="Nebulosity",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="extreme_phenomena",
        name="Extreme Phenomena",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="condition",
        icon="mdi:gauge",
        name="Weather",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(key="nebulozitate", icon="mdi:cloudy", name="Nebulozity"),
    SensorEntityDescription(
        key="last_updated",
        name="Last Updated",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="last_checked",
        name="Last checked",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ANMH weather sensor entities based on a config entry."""
    coordinator: ANMHCurrentConditionsUpdateCoordinator = (
        entry.runtime_data.coordinator_current_conditions
    )
    # hass.data[DOMAIN][entry.entry_id]
    location_name = entry.data[CONF_LOCATION]  # Get location name from config entry

    if not coordinator.last_update_success or not coordinator.data:
        _LOGGER.warning(
            "Initial ANMH data fetch failed or missing, cannot set up sensors yet."
        )
        if not coordinator.data:  # Strict check if no data object exists
            _LOGGER.error(
                "No initial data object from coordinator. Cannot create sensors."
            )
            return  # Cannot proceed without initial data structure

    current_data: WeatherData = coordinator.data
    _LOGGER.debug(f"DATA IS {current_data}")
    entities_to_add = []

    device_info = get_device_info(DOMAIN, location_name)

    # Create entities for standard descriptions if data is available
    for description in SENSOR_DESCRIPTIONS:
        # Check if the key exists in the model
        if hasattr(current_data, description.key):  # value is not None:
            _LOGGER.debug(f"Creating entity for {description.key}")
            entities_to_add.append(
                AnmhWeatherSensor(
                    entry.runtime_data.coordinator_current_conditions,
                    entry.runtime_data.coordinator_daily_forecast,
                    description,
                    device_info,
                    entry,
                )
            )
        else:
            _LOGGER.debug(
                f"Skipping entity creation for {description.key} (unknown attribute)"
            )

    if entities_to_add:
        _LOGGER.info(
            f"Adding {len(entities_to_add)} ANMH weather sensors for {location_name}"
        )
        async_add_entities(entities_to_add)
    else:
        _LOGGER.warning(
            f"No valid sensors found to add for {location_name} based on initial data."
        )


class AnmhWeatherSensor(
    CoordinatorEntity[ANMHCurrentConditionsUpdateCoordinator], SensorEntity
):
    """Implementation of an ANMH weather sensor."""

    _attr_has_entity_name = True  # Use entity description name as the base
    # _attr_attribution = ATTRIBUTION

    def __init__(
        self,
        conditions_coordinator: ANMHCurrentConditionsUpdateCoordinator,
        forecast_coordinator: ANMHDailyForecastDataUpdateCoordinator,
        description: SensorEntityDescription,
        device_info: DeviceInfo,
        # config_entry_id: str,
        cfg_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(conditions_coordinator)
        self.forecast_coordinator = forecast_coordinator
        self.entity_description = description
        self._attr_device_info = device_info
        # Construct unique ID: domain_configentryid_sensorkey
        # self._attr_unique_id = f"{DOMAIN}_{config_entry_id}_{description.key}"
        config_entry_id = cfg_entry.entry_id
        self._attr_unique_id = get__attr_unique_id(
            DOMAIN, config_entry_id, description.key
        )

    @property
    def icon(self):
        icon = None
        if self.entity_description.key in ["condition_raw", "condition"]:
            icon = "mdi:cloud-question-outline"
            c = getattr(self.coordinator.data, "condition", None)
            if c and c != "indisponibil":
                icon = f"mdi:weather-{c}"

        if self.entity_description.key in ["extreme_phenomena", "nebulosity"]:
            icon = "mdi:crosshairs-question"  # cloud-question-outline
            value = getattr(self.coordinator.data, self.entity_description.key, None)
            # self.coordinator.data.getattr(self.entity_description.key)
            if value and value != "indisponibil":
                icon = f"mdi:weather-{value}"

        if icon:
            return icon

    @property
    def native_value(self) -> Optional[Any]:
        """Return the state of the sensor."""
        if not self.coordinator.last_update_success or not self.coordinator.data:
            return None  # Let HA handle unavailability

        # current_data: WeatherData = self.coordinator.data.get("current")[0]

        # Default handling: get value directly using the key
        value = getattr(self.coordinator.data, self.entity_description.key, None)

        # Apply suggested precision if available and value is numeric
        precision = self.entity_description.suggested_display_precision
        if precision is not None and isinstance(value, (int, float)):
            return round(value, precision)

        if self.entity_description.device_class == SensorDeviceClass.TIMESTAMP:
            return dt_util.as_local(value)

        return (
            value  # Return string as is (e.g., cardinal direction) or None if missing
        )

    def get_forecast(self) -> list[Forecast] | None:
        """Return the daily forecast."""
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
            for item in self.forecast_coordinator.data
        ]

    def get_condition_attributes(self) -> Optional[Dict[str, Any]]:
        return {
            "temperature": self.coordinator.data.temperature,
            "dew_point": self.coordinator.data.dew_point,
            "temperature_unit": UnitOfTemperature.CELSIUS,
            "humidity": self.coordinator.data.relative_humidity_percent,
            "pressure": self.coordinator.data.pressure,
            "pressure_unit": self.coordinator.data.pressure_unit,
            "wind_bearing": self.coordinator.data.wind_direction_text,
            "wind_speed": self.coordinator.data.wind_speed,
            "wind_speed_unit": self.coordinator.data.wind_speed_unit,
            "visibility_unit": UnitOfLength.KILOMETERS,
            "precipitation_unit": UnitOfPrecipitationDepth.MILLIMETERS,
            "supported_features": 1,
            "forecast": self.get_forecast(),
        }

    @property
    def extra_state_attributes(self) -> Optional[Dict[str, Any]]:
        """Return entity specific state attributes."""
        if not self.coordinator.last_update_success or not self.coordinator.data:
            return None  # Let HA handle unavailability

        # current_data: WeatherData = self.coordinator.data.get("current")[0]

        extra_state_attributes = None

        if "condition_raw" == self.entity_description.key:
            extra_state_attributes = self.coordinator.data.raw_data

        if "condition" == self.entity_description.key:
            extra_state_attributes = self.get_condition_attributes()

        if "itu_perception" == self.entity_description.key:
            index, txt, t, h = self.coordinator.data.itu_index
            if index:
                extra_state_attributes = {
                    "itu_index": index,
                    "temperature": t,
                    "humidity": h,
                }

        valid_utc: Optional[datetime] = getattr(self.coordinator.data, "valid", None)

        if valid_utc:
            # Convert the UTC datetime object from the API to local time
            local_valid_time = dt_util.as_local(valid_utc)
            return (extra_state_attributes if extra_state_attributes else {}) | {
                "last_updated": local_valid_time.isoformat()
            }

        if extra_state_attributes:
            return extra_state_attributes
        # else:
        #     return None

    # @property
    # def available(self) -> bool:
    #     """Return True if entity is available."""
    #     # Available if the conditions_coordinator is successful and the specific value is not None
    #     # (or if it's the special rate sensor and its ingredients are available)
    #     base_available = super().available and self.coordinator.data is not None

    #     if not base_available:
    #         return False

    #     return (
    #         getattr(
    #             self.coordinator.data.get("current")[0],
    #             self.entity_description.key,
    #             None,
    #         )
    #         is not None
    #     )
