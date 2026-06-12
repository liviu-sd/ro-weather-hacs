import re
import math

from .weather_mapings import (
    WEATHER_NEBULOSITY_CONDITIONS_MAPPING,
    WEATHER_EXTREME_CONDITIONS_MAPPING,
    WIND_DIRECTIONS,
    FORECAST_CONDITIONS_MAPPING,
)


def get_bearing(dir) -> float:
    if dir in WIND_DIRECTIONS:
        dir_idx = WIND_DIRECTIONS.index(dir)
        # { (dir_idx + 1) * 22.5 - 11.25 } #}
        return dir_idx * 22.5

    return dir


def get_snow_depth(s: str) -> float | None:
    if not (d := re.search(r"(\d*(\.\d*)?)\s*cm", s)) is None:
        return float(d[1])

    return None


def get_pressure(s: str) -> tuple[float | None, str, str]:
    if not (d := re.search(r"(\d*(\.\d*)?)\s+([a-y]+),\s+([1-z\s]+)", s)) is None:
        trend = {
            "in scadere": "falling",
            "in crestere": "rising",
            "variabila": "variable",
            "stationara": "stationary",
        }.get(d[4])
        return float(d[1]), d[3], trend if trend else d[4]

    return None, "", ""


def get_wind(s: str) -> tuple[float | None, str | None, str | None]:
    if (
        not (
            d := re.search(
                r"(\d*(\.\d*)?)\s+([a-y]/[a-y]),\s*directia\s*:\s*([A-Y]+)", s
            )
        )
        is None
    ):
        return float(d[1]), d[3], d[4]

    return None, None, None


def get_weather_conditions(nebulozitate: str, fenomen_e: str) -> tuple[str, str]:
    s = []

    s.append(
        WEATHER_NEBULOSITY_CONDITIONS_MAPPING[nebulozitate]
        if nebulozitate in WEATHER_NEBULOSITY_CONDITIONS_MAPPING.keys()
        else None
    )

    s.append(
        WEATHER_EXTREME_CONDITIONS_MAPPING[fenomen_e]
        if fenomen_e in WEATHER_EXTREME_CONDITIONS_MAPPING.keys()
        else None
    )

    return tuple(s)
    # return s[0] if len(s) > 0 else fenomen_e + ", " + nebulozitate


def get_forecast_conditions(cond: str) -> str:
    c = [
        k
        for k in FORECAST_CONDITIONS_MAPPING.keys()
        if cond in FORECAST_CONDITIONS_MAPPING[k]
    ]
    return cond if len(c) <= 0 else c[0]


def calc_dewpoint(humidity, temp_c):
    a = 17.625
    b = 243.04
    alpha = math.log(humidity / 100.0) + ((a * temp_c) / (b + temp_c))
    return (b * alpha) / (a - alpha)
