import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Final

from discord.message import Message
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker

Base = declarative_base()

DB_URI: Final = os.getenv("DB_URI", "")

##################
# Helper functions
##################


def get_db_session() -> Session:
    """Get a DB session."""
    engine = create_engine(DB_URI)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


@dataclass(slots=True)
class Coords:
    """Represents latitude and longitude coordinates."""

    address: str
    latitude: float
    longitude: float
    query: str

    def to_sqlalchemy(self) -> "CoordsDB":
        return CoordsDB(
            address=self.address,
            latitude=self.latitude,
            longitude=self.longitude,
            query=self.query,
        )


class CustomMessage:
    """Wrap the Discord message class with some additional attributes."""

    def __init__(self, message: Message):
        self._message = message
        self.no_prefix: str | None = None
        self.weather_prefix: str | None = None

    def __getattr__(self, item):
        return getattr(self._message, item)


##########
# Database
##########


class User(Base):
    """SQLAlchemy representation of a user."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    discord_id = Column(Integer, unique=True)
    name = Column(String, nullable=False)
    weather_location = Column(String, nullable=True)

    attachments = relationship("Attachment", back_populates="user")
    urls = relationship("Url", back_populates="user")

    def set_weather_location(self, location: str) -> None:
        """Set `self.weather_location to `location`."""
        self.weather_location = location


class CoordsDB(Base):
    """SQLAlchemy representation of Coords."""

    __tablename__ = "coords"

    id = Column(Integer, primary_key=True, autoincrement=True)
    address = Column(String, nullable=False)
    created = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    modified = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    query = Column(String, nullable=False, index=True, unique=True)

    def to_dataclass(self) -> Coords:
        """
        Convert the SQLAlchemy model instance to a Coords dataclass
        """
        return Coords(
            address=str(self.address),
            latitude=float(str(self.latitude)),
            longitude=float(str(self.longitude)),
            query=str(self.query),
        )

    def __str__(self) -> str:
        return f"CoordsDB(id={self.id}, query={self.query}, latitude={self.latitude}, longitude={self.longitude})"


class Url(Base):
    """SQLAlchemy representation of a Discord URL."""

    __tablename__ = "urls"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    created = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    url = Column(String, nullable=False)
    title = Column(String)

    user = relationship("User", back_populates="urls")

    def __str__(self):
        return f"Url(id={self.id}, user='{self.user}', url='{self.url}', title='{self.title}')"


class Attachment(Base):
    """SQLAlchemy representation of a Discord attachment."""

    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    discord_filename = Column(String, nullable=False)
    discord_id = Column(String, nullable=False)
    emoji = Column(String)
    filename = Column(String, nullable=False)
    url = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))

    user = relationship("User", back_populates="attachments")

    def __str__(self):
        return f"Attachment(id={self.id}, user='{self.user}', filename='{self.filename}')"


#########
# Weather
#########


class CurrentWeather(BaseModel):
    """
    Represent the current weather conditions for a specific place.

    See https://openweathermap.org/current for the full API response.
    """

    name: str
    temperature: float
    last_updated: datetime
    conditions: str | None = None
    icon: str | None = None
    feels_like: float | None = None
    humidity: int | None = None
    pressure: int | None = None
    visibility: int | None = None
    wind_speed: float | None = None
    wind_gust: float | None = None
    wind_direction: str | None = None
    clouds: int | None = None
    rain_last_hour: float | None = None
    snow_last_hour: float | None = None
    sunrise: datetime | None = None
    sunset: datetime | None = None
    country: str | None = None

    @classmethod
    def create_from_owm_json(cls, json_data) -> "CurrentWeather":
        """
        Flatten and otherwise process data from the OpenWeatherMap API so it's
        ready for model_validate().
        """
        cloud_data = json_data.get("clouds", {})
        main_data = json_data.get("main", {})
        rain_data = json_data.get("rain", {})
        snow_data = json_data.get("snow", {})
        sys_data = json_data.get("sys", {})
        # For some reason the weather key has multiple IDs. Pick the first I guess.
        weather_data = json_data.get("weather")[0] if json_data.get("weather") else {}
        wind_data = json_data.get("wind", {})

        # Extract and otherwise pre-process the data.
        result = {}
        result["name"] = json_data.get("name")
        result["temperature"] = main_data.get("temp")
        result["last_updated"] = (
            cls.get_datetime_from_timestamp(timestamp=json_data.get("dt") + json_data.get("timezone"))
            if (json_data.get("dt"))
            else None
        )
        result["conditions"] = weather_data.get("description")
        result["icon"] = weather_data.get("icon")
        result["feels_like"] = main_data.get("feels_like")
        result["humidity"] = main_data.get("humidity")
        result["pressure"] = main_data.get("pressure")
        result["visibility"] = json_data.get("visibility")
        result["wind_speed"] = wind_data.get("speed")
        result["wind_gust"] = wind_data.get("gust")
        result["wind_direction"] = (
            CurrentWeather.get_cardinal_from_degrees(wind_data.get("deg")) if wind_data.get("deg") else None
        )
        result["clouds"] = cloud_data.get("all")
        result["rain_last_hour"] = rain_data.get("1h")
        result["snow_last_hour"] = snow_data.get("1h")
        result["sunrise"] = (
            cls.get_datetime_from_timestamp(sys_data.get("sunrise") + json_data.get("timezone"))
            if sys_data.get("sunrise")
            else None
        )
        result["sunset"] = (
            cls.get_datetime_from_timestamp(sys_data.get("sunset") + json_data.get("timezone"))
            if sys_data.get("sunset")
            else None
        )
        result["country"] = sys_data.get("country")

        return cls.model_validate(result)

    @classmethod
    def get_datetime_from_timestamp(cls, timestamp: int) -> datetime:
        """
        Covert a UTC timestamp (e.g. `1703999757` to a `datetime`.
        """
        return datetime.fromtimestamp(timestamp)

    @staticmethod
    def get_cardinal_from_degrees(degrees: int) -> str:
        """
        Take a degree in int and get the cardinal abbreviation.

        get_cardinal_from_degrees(110)
        >>> "ESE"
        """
        directions = [
            "NNE",
            "NE",
            "ENE",
            "E",
            "ESE",
            "SE",
            "SSE",
            "S",
            "SSW",
            "SW",
            "WSW",
            "W",
            "WNW",
            "NW",
            "NNW",
            "N",
        ]
        dir_index = round((degrees / (360 / len(directions))) - 1)
        return directions[dir_index]

    def format_weather_report(self) -> str:
        """
        Create a formatted weather report.
        """

        def format_datetime(dt):
            return dt.strftime("%H:%M") if dt else ""

        def celsius_to_fahrenheit(c):
            return c * 9.0 / 5.0 + 32 if c is not None else None

        def kph_to_mph(kph):
            return kph * 0.621371 if kph is not None else None

        def meters_to_miles(meters):
            return meters * 0.000621371 if meters is not None else None

        elements = [
            f"Current weather for {self.name}, {self.country or 'Unknown'}",
            f"(Last Update: {self.last_updated.strftime('%a %b %d %H:%M:%S')})" if self.last_updated else "",
            f"Conditions: {self.conditions}" if self.conditions else "",
            f"Temperature: {self.temperature:.1f}°C ({celsius_to_fahrenheit(self.temperature):.1f}°F)"
            if self.temperature
            else "",
            f"Feels Like: {self.feels_like:.1f}°C ({celsius_to_fahrenheit(self.feels_like):.1f}°F)"
            if self.feels_like
            else "",
            f"Wind: {self.wind_speed}kph ({kph_to_mph(self.wind_speed):.1f}mph)" if self.wind_speed else "",
            f"Direction: {self.wind_direction}" if self.wind_direction else "",
            f"Humidity: {self.humidity}%" if self.humidity else "",
            f"Pressure: {self.pressure}hPa" if self.pressure else "",
            f"Visibility: {self.visibility} meters ({meters_to_miles(self.visibility):.2f} miles)"
            if self.visibility
            else "",
            f"Clouds: {self.clouds}%" if self.clouds else "",
            f"Rain Last Hour: {self.rain_last_hour} mm" if self.rain_last_hour else "",
            f"Snow Last Hour: {self.snow_last_hour} mm" if self.snow_last_hour else "",
            f"Sunrise: {format_datetime(self.sunrise)}" if self.sunrise else "",
            f"Sunset: {format_datetime(self.sunset)}" if self.sunset else "",
        ]

        report = ", ".join(element for element in elements if element)

        return report


@dataclass(slots=True)
class Grid:
    """
    Representation of an NWS weather grid.

    See, e.g.: https://api.weather.gov/points/39.7456,-97.0892
    """

    grid_id: str
    grid_x: int
    grid_y: int


class ForecastPeriod(BaseModel):
    name: str
    startTime: datetime
    endTime: datetime
    probabilityOfPrecipitation: int | None
    windSpeed: str
    windDirection: str
    icon: str
    shortForecast: str
    detailedForecast: str


class ForecastWeather(BaseModel):
    elevation: float | None
    updateTime: datetime
    forecastPeriods: list[ForecastPeriod]

    @classmethod
    def create_from_json(cls, json_data) -> "ForecastWeather":
        elevation_data = json_data["properties"].get("elevation", [])
        update_time = json_data["properties"]["updateTime"]
        periods_data = json_data["properties"]["periods"]
        now = datetime.now(tz=timezone(timedelta(days=-1, seconds=64800)))

        # Parse each period into a ForecastPeriod model (next ~3 days only).
        periods = [
            ForecastPeriod(
                name=period["name"],
                startTime=datetime.fromisoformat(period["startTime"]),
                endTime=datetime.fromisoformat(period["endTime"]),
                probabilityOfPrecipitation=period["probabilityOfPrecipitation"]["value"],
                windSpeed=period["windSpeed"],
                windDirection=period["windDirection"],
                icon=period["icon"],
                shortForecast=period["shortForecast"],
                detailedForecast=period["detailedForecast"],
            )
            for period in periods_data
            if datetime.fromisoformat(period["startTime"]) - now <= timedelta(days=2)
        ]

        return cls(
            elevation=elevation_data.get("value"), updateTime=datetime.fromisoformat(update_time), forecastPeriods=periods
        )

    def format_forecast_report(self) -> str:
        """
        Create a formatted forecast weather report.
        """

        def mph_to_kph(mph):
            return mph * 1.60934

        def fahrenheit_to_celsius(f):
            return (f - 32) * 5.0 / 9.0

        def extract_and_convert_temperature(details):
            # Assuming temperature is mentioned in Fahrenheit in the details
            temp_f = extract_temperature_in_fahrenheit(details)
            if temp_f is not None:
                temp_c = fahrenheit_to_celsius(temp_f)
                return f"{temp_c:.1f}°C ({temp_f:.1f}°F)"
            return ""

        def extract_temperature_in_fahrenheit(details):
            # Implement a method to extract the temperature in Fahrenheit from the details string
            pass

        def extract_wind_speed_in_mph(wind_speed_str):
            # Assuming wind speed is in the format '10 mph' or '5 to 10 mph'
            # Extract and return the average wind speed in mph
            pass

        report_lines = [
            f"Forecast at Elevation: {self.elevation:.2f} meters. Last Updated: {self.updateTime.strftime('%a %b %d %H:%M:%S %Z')}"
            if self.updateTime
            else "",
        ]

        for period in self.forecastPeriods:
            wind_speed_mph = extract_wind_speed_in_mph(period.windSpeed)
            wind_speed_kph = mph_to_kph(wind_speed_mph)
            temperature = extract_and_convert_temperature(period.detailedForecast)

            period_details = [
                f"**{period.name}**",
                f"Probability of Precipitation: {period.probabilityOfPrecipitation}%"
                if period.probabilityOfPrecipitation is not None
                else "",
                f"Wind: {period.windSpeed} from the {period.windDirection}",
                f"Details: {period.detailedForecast}",
            ]
            report_lines.append(", ".join(detail for detail in period_details if detail))

        return "\n".join(report_lines)

    def format_forecast_report(self) -> str:
        """
        Create a formatted forecast weather report.
        """
        report_lines = [
            f"Forecast at Elevation: {self.elevation:.2f} meters. Last Updated: {self.updateTime.strftime('%a %b %d %H:%M:%S %Z')}"
            if self.updateTime
            else "",
        ]

        for period in self.forecastPeriods:
            period_details = [
                f"**{period.name}**",
                f"Probability of Precipitation: {period.probabilityOfPrecipitation}%"
                if period.probabilityOfPrecipitation is not None
                else "",
                f"Wind: {period.windSpeed} from the {period.windDirection}",
                f"Details: {period.detailedForecast}",
            ]
            report_lines.append(", ".join(detail for detail in period_details if detail))

        return "\n".join(report_lines)


@dataclass(slots=True)
class WeatherResponse:
    """A class for holding responses for .wz when parsing the input from Discord."""

    status: str
    message: str
    location: str


############
# URL parser
############


@dataclass(slots=True)
class UrlTitle:
    url: str
    title: str
