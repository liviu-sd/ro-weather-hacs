import voluptuous as vol
import logging
from typing import Any, Dict
from aiohttp import ClientSession

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import callback
from homeassistant.const import (
    CONF_LOCATION,
    # CONF_LATITUDE,
    # CONF_LONGITUDE,
    CONF_CODE,
)

from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_FORECAST_LOCATION,
)
from .anmh_weather import AnmhWeather, Location

_LOGGER = logging.getLogger(__name__)


class AnmhWeatherConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for ANMH Weather."""

    VERSION = 1
    _input_data: dict[str, Any]
    _title: str

    _client_session: ClientSession | None = None
    _weather_client: AnmhWeather | None = None
    _weather_locations: list[Location] | None = None

    async def _async_get_user_step_data(
        self, errors: Dict[str, str]
    ) -> tuple[list[str] | None, list[str] | None]:
        if self._weather_locations is None:
            # Get the HA-managed session
            if self._weather_client is None and self._client_session is None:
                self._client_session = async_get_clientsession(self.hass)

                if self._weather_client is None:
                    self._weather_client = AnmhWeather(
                        session=self._client_session,
                    )

            try:
                # Fetch locations using the weather_client with the HA session
                locations_raw = (
                    await self._weather_client.get_available_weather_locations()
                )
                forecast_locations = (
                    await self._weather_client.get_available_forecast_locations()
                )

                # Basic validation on fetched data
                if isinstance(locations_raw, list) and all(
                    isinstance(loc, Location) for loc in locations_raw
                ):
                    self._weather_locations = locations_raw
                    self._forecast_locations = forecast_locations
                else:
                    _LOGGER.error(
                        "Fetched locations data is not a list of strings: %s",
                        locations_raw,
                    )
                    errors["base"] = "invalid_location_data"

                ## TO REVIEW:
                if (
                    not self._weather_locations and "base" not in errors
                ):  # Check if list is empty
                    _LOGGER.error("Fetched locations list is empty.")
                    errors["base"] = "no_locations_found"

            except Exception as exc:
                _LOGGER.exception("Error fetching locations: %s", exc)
                errors["base"] = "cannot_connect"

        return (
            sorted([l.name for l in self._weather_locations]),
            self._forecast_locations,
        )

    async def async_step_user(
        self, user_input: Dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: Dict[str, str] = {}

        locations, forecast_locations = await self._async_get_user_step_data(errors)

        # --- handle user input or show form ---
        if user_input is not None:
            selected_location = user_input[CONF_LOCATION]
            if selected_location not in locations:
                # This shouldn't happen if vol.In is working correctly
                errors["base"] = "invalid_selection"
                _LOGGER.error(
                    "Selected location '%s' not in fetched list.", selected_location
                )

            selected_forecast_location = user_input[CONF_FORECAST_LOCATION]
            if selected_forecast_location not in (["None"] + forecast_locations):
                errors["base"] = "invalid_location_selection"
                _LOGGER.error(
                    "selected forecast location '%s' not in available list",
                    selected_forecast_location,
                )

            if "base" not in errors:
                # _LOGGER.debug("Creating entry for location: %s", selected_location)
                if selected_forecast_location not in forecast_locations:
                    user_input[CONF_FORECAST_LOCATION] = None

                self._input_data = user_input

                return self.async_create_entry(title=selected_location, data=user_input)

        # If there were errors during fetch, prevent showing the form with bad data
        if locations is None or errors and errors.get("base") != "invalid_selection":
            return self.async_show_form(step_id="user", errors=errors)

        # Define schema using fetched locations (only if no fetch errors)
        schema = vol.Schema(
            {
                vol.Required(CONF_LOCATION): vol.In(locations),
                vol.Required(CONF_FORECAST_LOCATION): vol.In(
                    ["None"] + forecast_locations
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
