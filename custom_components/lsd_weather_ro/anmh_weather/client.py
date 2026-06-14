import aiohttp
import logging
from typing import Optional, Type
import xml.etree.ElementTree as ET
from datetime import datetime

from .const import FORECAST_5_DAYS_URL, WEATHER_URL
from .models import (
    StareaVremiiData,
    WeatherData,
    Forecast24hTimelineEntry,
    Location,
)
from .station_map import FORECAST_LOCALITIES

_LOGGER = logging.getLogger(__name__)


class AnmhWeather:
    """Client to fetch weather data from ANMH."""

    available_locations: list[Location] | None = None

    def __init__(
        self,
        location_name: str | None = None,
        forecast_location: str | None = None,
        session: Optional[aiohttp.ClientSession] = None,
    ):
        self.location_name = location_name
        self.forecast_location = forecast_location

        if session is None:
            self._session = aiohttp.ClientSession()
            self._owns_session = True
        else:
            self._session = session
            self._owns_session = False

        _LOGGER.debug(f"Initialized AnmhWeather for location '{location_name}'")

    async def get_available_weather_locations(self) -> list[Location]:
        "Returns list of all locations provided by ANMH"
        locations: dict

        if self.available_locations is None:
            locations = await self.fetch_weather_data()
            self.available_locations = [
                Location(
                    name=loc["properties"]["nume"],
                    latitude=loc["geometry"]["coordinates"][0],
                    longitude=loc["geometry"]["coordinates"][1],
                )
                for loc in locations["features"]
            ]

        return self.available_locations

    async def get_available_forecast_locations(self) -> list[str]:
        "Returns list of all locations provided by ANMH"
        return FORECAST_LOCALITIES

    async def get_weather(self) -> WeatherData:
        starea_vremii_data = await self.fetch_weather_data()

        if not starea_vremii_data:
            return {}

        starea_vremii_data_parsed = StareaVremiiData.from_dict(starea_vremii_data)

        observation = list(
            filter(
                lambda f: f.properties.nume == self.location_name,
                starea_vremii_data_parsed.features,
            )
        )

        return WeatherData(
            observation[0].properties,
            last_check_time=datetime.now(),
        )  # is list for consistency with forecast data

    async def get_forecast(self) -> list[Forecast24hTimelineEntry]:
        prognoze_orase_data = await self.fetch_forecast_data()

        if not prognoze_orase_data:
            return []

        tree = ET.ElementTree(ET.fromstring(prognoze_orase_data))

        tree_root = tree.getroot()

        prognoze_oras_data_parsed = None
        if tree_root != None:
            prognoze_oras_data_parsed = tree_root.find(
                ".//prognoza/..[@nume='{location}']".format(
                    location=self.forecast_location
                )
            )

        forecasts = {}
        if (
            prognoze_oras_data_parsed
            and (dp := prognoze_oras_data_parsed.find("DataPrognozei")) != None
        ):
            # forecasts = {
            #     "forecast24h": [
            #         Forecast24hTimelineEntry(prognoza)
            #         for prognoza in prognoze_oras_data_parsed.findall("prognoza")
            #     ]
            # }
            forecasts = [
                Forecast24hTimelineEntry(prognoza)
                for prognoza in prognoze_oras_data_parsed.findall("prognoza")
            ]

        return forecasts

    async def fetch_weather_data(
        self,
    ) -> dict:
        _LOGGER.debug(f"Requesting weather data from {WEATHER_URL}")

        try:
            async with self._session.get(WEATHER_URL) as response:
                response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
                data = await response.json(content_type=None)
                _LOGGER.debug("Successfully received API response.")
                return data
        except aiohttp.ClientResponseError as e:
            _LOGGER.error(f"API request failed: {e.status} {e.message}")
            return {}
        except aiohttp.ClientError as e:
            _LOGGER.error(f"Client error during API request: {e}")
            return {}

    async def fetch_forecast_data(self) -> str:
        _LOGGER.debug(f"Requesting forecast data from {FORECAST_5_DAYS_URL}")

        try:
            async with self._session.get(FORECAST_5_DAYS_URL) as response:
                response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
                data = await response.text()
                _LOGGER.debug("Successfully received API response.")
                return data
        except aiohttp.ClientResponseError as e:
            _LOGGER.error(f"API request failed: {e.status} {e.message}")
            return {}
        except aiohttp.ClientError as e:
            _LOGGER.error(f"Client error during API request: {e}")
            return {}

    async def close(self):
        """Close the underlying aiohttp session if it was created internally."""
        if self._owns_session and self._session and not self._session.closed:
            await self._session.close()
            _LOGGER.debug("Closed internally managed aiohttp session.")

    async def __aenter__(self):
        """Async context manager enter."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
