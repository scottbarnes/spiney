from datetime import datetime, timezone
from typing import Final, Generator

from pydantic_core import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from models import Base, Coords, CoordsDB, CurrentWeather
from test_json_data import (
    currentweather_expected_complete,
    currentweather_expected_minimal,
    owm_json_data_complete,
    owm_json_data_minimal,
)

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
    @pytest.mark.asyncio()
    @pytest.mark.parametrize(
        ("json_data", "expected"),
        [
            (owm_json_data_complete, currentweather_expected_complete),
            (owm_json_data_minimal, currentweather_expected_minimal),
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
