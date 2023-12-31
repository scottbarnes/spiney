from datetime import datetime, timezone
from typing import Final, Generator

from pydantic_core import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from models import Base, Coords, CoordsDB, CurrentWeather

import pytest

DB_URI: Final = "sqlite:///:memory:"

coords_google = Coords(
    address="1600 Amphitheatre Pkwy, Mountain View, CA 94043, USA",
    latitude=37.4224053,
    longitude=-122.0842161,
    query="1600 Amphitheatre Parkway, Mountain View, CA",
)

coords_washington_dc = Coords(
    address="Washington, DC 20001, USA", latitude=38.912068, longitude=-77.0190228, query="20001"
)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    test_engine = create_engine(DB_URI)
    TestSession = sessionmaker(bind=test_engine)
    Base.metadata.create_all(test_engine)
    db_session = TestSession()

    yield db_session

    db_session.rollback()
    db_session.close()


def test_insert_coords_db_item(db_session) -> None:
    """
    These tests are fairly pointless and mostly test functionality already
    tested by SQLAlchemy's own tests.
    """
    location_google = coords_google.to_sqlalchemy()
    location_washington_dc = coords_washington_dc.to_sqlalchemy()

    db_session.add(location_google)
    db_session.add(location_washington_dc)
    db_session.commit()

    all_items = db_session.query(CoordsDB).all()
    assert all_items[0] == location_google
    assert all_items[1] == location_washington_dc


def test_covert_from_coords_db_to_coords(db_session) -> None:
    """
    The `CoordsDB` objects have a `.to_dataclass()` method to dump the instance
    to a `Coords` dataclass.
    """
    location_google = coords_google.to_sqlalchemy()
    # Add the SQLAlchemy item to a session so it can be managed:
    # See https://sqlalche.me/e/20/bhk3.
    db_session.add(location_google)
    assert location_google.to_dataclass() == coords_google


class TestCurrentWeather:
    json_data_complete = {
        "coord": {"lon": -122.0842, "lat": 37.4224},
        "weather": [
            {"id": 502, "main": "Rain", "description": "heavy intensity rain", "icon": "10n"},
            {"id": 701, "main": "Mist", "description": "mist", "icon": "50n"},
        ],
        "base": "stations",
        "main": {
            "temp": 13.1,
            "feels_like": 12.87,
            "temp_min": 11.77,
            "temp_max": 14.18,
            "pressure": 1014,
            "humidity": 92,
        },
        "visibility": 4828,
        "wind": {"speed": 3.6, "deg": 110, "gust": 5.6},
        "rain": {"1h": 5.31},
        "snow": {"1h": 1.2},
        "clouds": {"all": 100},
        "dt": 1703982775,
        "sys": {"type": 2, "id": 2010364, "country": "US", "sunrise": 1703949739, "sunset": 1703984341},
        "timezone": -28800,
        "id": 5375480,
        "name": "Mountain View",
        "cod": 200,
    }

    json_data_minimal = {
        "main": {
            "temp": 15.8,
        },
        "dt": 1703918849,
        "timezone": -28800,
        "name": "Mountain View",
    }

    # TODO: This should raise an error
    json_data_invalid = {}

    expected_complete = {
        "last_updated": datetime(2023, 12, 30, 16, 32, 55),
        "conditions": "heavy intensity rain",
        "icon": "10n",
        "temperature": 13.1,
        "feels_like": 12.87,
        "humidity": 92,
        "pressure": 1014,
        "visibility": 4828,
        "wind_speed": 3.6,
        "wind_gust": 5.6,
        "wind_direction": "ESE",
        "clouds": 100,
        "rain_last_hour": 5.31,
        "snow_last_hour": 1.2,
        "sunrise": datetime(2023, 12, 30, 7, 22, 19),
        "sunset": datetime(2023, 12, 30, 16, 59, 1),
        "name": "Mountain View",
        "country": "US",
    }

    expected_minimal = {
        "name": "Mountain View",
        "temperature": 15.8,
        "last_updated": datetime(2023, 12, 29, 22, 47, 29),
    }

    @pytest.mark.asyncio()
    @pytest.mark.parametrize(
        ("json_data", "expected"),
        [
            (json_data_complete, expected_complete),
            (json_data_minimal, expected_minimal),
        ],
    )
    async def test_currentweather_attributes(self, json_data: dict, expected: dict) -> None:
        """
        Use a dictionary of the expected keys and values to ensure the
        instaniated object has them all, both for every key, and for
        minimal keys.
        """
        model = CurrentWeather.create_from_owm_json(json_data)
        for attr, expected_value in expected.items():
            assert (
                getattr(model, attr) == expected_value
            ), f"For key {attr}: found {getattr(model, attr)} but expected {expected_value}"

    @pytest.mark.asyncio()
    async def test_currentweather_invalid_attributes(self) -> None:
        """
        If the JSON from the API lacks the required fields, raise a
        ValidationError.
        """
        with pytest.raises(ValidationError):
            json_data = {}
            CurrentWeather.create_from_owm_json(json_data)
