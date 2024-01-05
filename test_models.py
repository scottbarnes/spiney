from typing import Final, Generator

import pytest
from pydantic_core import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from models import Base, Coords, CoordsDB, CurrentWeather, Url, User
from test_json_data import (
    currentweather_expected_complete,
    currentweather_expected_minimal,
    currentweather_expected_utc_location,
    owm_json_data_complete,
    owm_json_data_minimal,
    owm_json_utc_location,
)

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


def test_insert_coords_db_item(db_session: Session) -> None:
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


def test_covert_from_coords_db_to_coords(db_session: Session) -> None:
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
            (owm_json_utc_location, currentweather_expected_utc_location),
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

    @pytest.mark.asyncio()
    async def test_currentweather_get_cardinal_degrees(self) -> None:
        """
        Check for edge cases, such as degrees = 360
        """
        assert CurrentWeather.get_cardinal_from_degrees(360) == "N"


#######################################
# General database models and relations
#######################################


@pytest.mark.asyncio()
async def test_user_instantiation(db_session: Session):
    """Ensure a user can be created."""
    user = User(name="12345")
    db_session.add(user)
    db_session.commit()
    assert user.id is not None


@pytest.mark.asyncio()
async def test_user_names_are_unique(db_session: Session):
    """
    The `name` field is unique because it represents one IRC nick or one
    Discord user ID.
    """
    user = User(name="123")
    db_session.add(user)
    db_session.commit()
    new_user = User(name="456")
    db_session.add(user)
    db_session.add(new_user)
    db_session.commit()
    assert db_session.query(User).count() == 2


@pytest.mark.asyncio()
async def test_url_instantiation(db_session: Session):
    """Ensure a Url can be created."""
    user = User(name="123")
    url = Url(user=user, url="https://example.com")
    db_session.add(url)
    db_session.commit()
    assert url.id is not None


@pytest.mark.asyncio()
async def test_url_user_relationship(db_session: Session):
    """Test the relationship between User and Url."""
    user = User(name="123")
    url = Url(user=user, url="https://example.com")
    db_session.add(user)
    db_session.add(url)
    db_session.commit()

    retrieved_user = db_session.query(User).first()
    assert retrieved_user is not None
    assert len(retrieved_user.urls) == 1
    assert retrieved_user.urls[0].url == "https://example.com"

    retrieved_url = db_session.query(Url).first()
    assert retrieved_url is not None
    assert retrieved_url.user.name == "123"


@pytest.mark.asyncio
async def test_set_user_weather_location(db_session: Session) -> None:
    """Ensure users can set `User.weather_location` with `wz -d location`."""
    user = User(name="Test User", discord_id=1)
    assert user.weather_location is None
    user.set_weather_location("20001")
    db_session.commit()
    assert user.weather_location is "20001"
