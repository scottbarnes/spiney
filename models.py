from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import os
from typing import Final

from sqlalchemy import Column, String, Float, Integer, DateTime, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from pydantic import BaseModel, model_validator

Base = declarative_base()

DB_URI: Final = os.getenv("DB_URI", "")


@dataclass
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


def get_session() -> Session:
    """Get a DB session."""
    engine = create_engine(DB_URI)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


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
            cls.get_datetime_from_timestamp(timestamp=json_data.get("dt"))
            if (json_data.get("dt") and json_data.get("timezone"))
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
            cls.get_datetime_from_timestamp(sys_data.get("sunrise"))
            if sys_data.get("sunrise") and json_data.get("timezone")
            else None
        )
        result["sunset"] = (
            cls.get_datetime_from_timestamp(sys_data.get("sunset"))
            if sys_data.get("sunset") and json_data.get("timezone")
            else None
        )
        result["country"] = sys_data.get("country")

        return cls.model_validate(result)

    @classmethod
    def get_datetime_from_timestamp(cls, timestamp: int) -> datetime:
        """
        Covert a UTC timestamp, along with its timezone offset (in seconds), to
        a datetime that reflects the local time.
        E.g., "1703967963" (2023-12-30 at 20:26:03) with offset -28800 (-8 hours)
        becomes atetime(2023, 12, 30, 12, 26, 3).
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
