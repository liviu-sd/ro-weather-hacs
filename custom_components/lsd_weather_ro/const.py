from __future__ import annotations
from typing import TYPE_CHECKING, Final
from datetime import timedelta

from homeassistant.const import Platform

DOMAIN: Final = "lsd_weather_ro"
DEFAULT_NAME: Final = "LSD: Weather RO"
DEFAULT_PLATFORMS: Final[list[Platform]] = [
    Platform.WEATHER,
    Platform.SENSOR,
]

CONF_FORECAST_LOCATION: Final = "conf_forecast_location"

CURRENT_CONDITIONS_UPDATE_INTERVAL: Final[timedelta] = timedelta(minutes=15)
FORECAST_DAILY_UPDATE_INTERVAL: Final[timedelta] = timedelta(minutes=1)  # hours=1)
SERVICE_GET_WATHER: Final = "get_weather"
