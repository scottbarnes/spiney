import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Final

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


##########
# Database
##########


class User(Base):
    """SQLAlchemy representation of a user."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    discord_id = Column(Integer, unique=True)
    name = Column(String, nullable=False)

    urls = relationship("Url", back_populates="user")


class CoordsDB(Base):
    """SQLAlchemy representation of Coords."""

    __tablename__ = "coords"

    id = Column(Integer, primary_key=True, autoincrement=True)
    address = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    query = Column(String, nullable=False, index=True, unique=True)
    created = Column(DateTime, default=datetime.now(timezone.utc))
    modified = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

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
    """SQLAlchemy representation of the A URL"""

    __tablename__ = "urls"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    created = Column(DateTime, default=datetime.now(timezone.utc))
    url = Column(String, nullable=False)
    title = Column(String)

    user = relationship("User", back_populates="urls")

    def __str__(self):
        return f"Url(id={self.id}, mentioned='{self.mentioned}', nick='{self.nick}', url='{self.url}', title='{self.title}')"


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
        result["wind_direction"] = cls.get_cardinal_from_degrees(wind_data.get("deg")) if wind_data.get("deg") else None
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

    @classmethod
    def get_cardinal_from_degrees(cls, degrees: int) -> str:
        """
        Take a degree in int and get the cardinal abbreviation.

        get_cardinal_from_degrees(110)
        >>> "ESE"
        """
        directions = [
            "N",
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
        ]
        dir_index = round(degrees / (360 / len(directions)))
        return directions[dir_index]

    def format_weather_report(self):
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


############
# URL parser
############


@dataclass(slots=True)
class UrlTitle:
    url: str
    title: str
