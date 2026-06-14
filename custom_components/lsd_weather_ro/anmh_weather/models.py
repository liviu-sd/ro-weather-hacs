from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
from dataclasses_json import dataclass_json, config
from marshmallow import fields
from xml.etree.ElementTree import Element

from .helpers import (
    get_bearing,
    get_forecast_conditions,
    get_pressure,
    get_snow_depth,
    get_weather_conditions,
    get_wind,
    calc_dewpoint,
)


@dataclass_json
@dataclass
class Geometry:
    type: str
    coordinates: List[str]
    zoom: int


def my_str2float(val) -> float | None:
    return None if val == "indisponibil" else val


@dataclass_json
@dataclass
class Properties:
    umezeala: float = field(metadata=config(decoder=my_str2float))
    fenomen_e: str
    zapada: str  # 1 cm la ora 02,
    actualizat: str  # 29-12-2025&nbsp;ora&nbsp;03:00,
    nebulozitate: str  # indisponibil,
    presiunetext: str  # 998.9 mb, in scadere,
    icon: int  # 84,
    nume: str  # IASI,
    tempe: float = field(metadata=config(decoder=my_str2float))  # 1.7,
    vant: str  # 4.5 m/s, directia : NV,
    tempapa: str  # indisponibil


@dataclass_json
@dataclass
class Feature:
    type: str
    geometry: Geometry
    properties: Properties


@dataclass_json
@dataclass
class StareaVremiiData:
    success: bool
    type: str  # = "FeatureCollection"
    date: datetime = field(
        metadata=config(
            encoder=datetime.isoformat,
            decoder=datetime.fromisoformat,
            mm_field=fields.DateTime(format="iso"),
        )
    )
    features: List[Feature]


@dataclass
class WeatherData:
    condition: str
    condition_raw: str | None
    temperature: float
    relative_humidity_percent: float
    wind_speed: float | None
    wind_speed_unit: str | None
    wind_direction_degrees: float | None
    wind_direction_text: str | None
    pressure: float | None
    pressure_unit: str
    pressure_tendency_trend: str

    _stareaVremii: Properties

    # update_time: datetime

    def __init__(
        self, stareaVremii: Properties, last_check_time: datetime | None = None
    ):
        self._stareaVremii = stareaVremii
        self.last_checked = last_check_time if last_check_time else datetime.now()
        self.temperature = float(stareaVremii.tempe)
        self.relative_humidity_percent = float(stareaVremii.umezeala)
        p, p_um, trend = get_pressure(self._stareaVremii.presiunetext)

        self.pressure = p
        self.pressure_unit = (
            stareaVremii.presiunetext.split(" ")[1].split(",")[0].strip()
        )
        self.pressure_tendency_trend = trend

        wind, wind_um, wind_dir = get_wind(self._stareaVremii.vant)

        self.wind_speed = wind
        self.wind_speed_unit = wind_um
        self.wind_direction_text = wind_dir.replace("V", "W") if wind_dir else None
        self.wind_direction_degrees = get_bearing(wind_dir)

        c, c_e = get_weather_conditions(
            stareaVremii.nebulozitate, stareaVremii.fenomen_e
        )

        self.condition = c_e if c_e else c
        self.condition_raw = (
            stareaVremii.fenomen_e if c_e else stareaVremii.nebulozitate
        )

        self.extreme_phenomena = c_e
        self.nebulosity = c

    @property
    def snow_depth_cm(self) -> float | None:
        try:
            return get_snow_depth(self._stareaVremii.zapada)
        except:
            return None

    @property
    def water_temperature(self) -> float | None:
        try:
            return (
                float(self._stareaVremii.tempapa)
                if self._stareaVremii.tempapa not in ["indisponibil", None]
                else None
            )
        except:
            return None

    @property
    def itu_index(self) -> int | None:
        #  ((id(temperature).state * 1.8 + 32) - (0.55 - 0.55 * id(humidity).state / 100) * ((id(temperature).state * 1.8 + 32) - 58));
        try:
            return int(
                (self.temperature * 1.8 + 32)
                - (0.55 - 0.55 * self.relative_humidity_percent / 100)
                * ((self.temperature * 1.8 + 32) - 58)
            )
        except:
            return None

    @property
    def itu_perception(self) -> str:
        itu_class = "Unknown"
        
        if self.itu_index == None:
            return itu_class
        
        if self.itu_index <= 70:
            itu_class = "comfortable"
        elif self.itu_index > 70 and self.itu_index <= 75:
            itu_class = "discomfort alert"
        elif self.itu_index > 75 and self.itu_index <= 79.4:
            itu_class = "uncomfortable"
        elif self.itu_index > 79.4 and self.itu_index <= 80.0:
            itu_class = "very uncomfortable"
        elif self.itu_index > 80.0:
            itu_class = "very very uncomfortable"
        else:
            itu_class = "Unknown"

        return itu_class

    @property
    def raw_data(self) -> dict[str, any]:
        return self._stareaVremii.__dict__

    @property
    def dew_point(self) -> float:
        return calc_dewpoint(self.relative_humidity_percent, self.temperature)

    @property
    def last_updated(self) -> datetime:
        espected_format = "%d-%m-%Y&nbsp;ora&nbsp;%H:%M"
        dt = datetime.strptime(self._stareaVremii.actualizat, espected_format)

        return dt


@dataclass
class BaseTimelineEntry:
    data: datetime | None
    temp_max: Optional[float] = None
    temp_min: Optional[float] = None
    fenomen_descriere: Optional[str] = None
    fenomen_simbol: Optional[str] = None

    @property
    def hass_weather_condition(self) -> Optional[str]:
        return (
            get_forecast_conditions(self.fenomen_descriere)
            if self.fenomen_descriere != None
            else "unknown"
        )


def get_float(v: str | None):
    try:
        return float(v)
    except Exception:
        return None


@dataclass
class Forecast24hTimelineEntry(BaseTimelineEntry):
    def __init__(self, fd: Element):
        self.data = datetime.fromisoformat(d) if (d := fd.get("data")) != None else None
        self.temp_max = (
            get_float(d.text) if (d := fd.find("temp_max")) != None else None
        )
        self.temp_min = (
            get_float(d.text) if (d := fd.find("temp_min")) != None else None
        )
        self.fenomen_descriere = (
            d.text if (d := fd.find("fenomen_descriere")) != None else None
        )
        self.fenomen_simbol = (
            d.text if (d := fd.find("fenomen_simbol")) != None else None
        )


@dataclass(frozen=True)
class Location:
    name: str | None = None
    latitude: str | None = None
    longitude: str | None = None
