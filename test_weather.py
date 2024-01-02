from dataclasses import dataclass
from typing import Final
from unittest.mock import patch

import aiohttp
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from errors import APISyntaxError, InvalidAPIKeyError
from models import Coords, CoordsDB, User
from test_json_data import (
    currentweather_expected_complete,
    currentweather_expected_minimal,
    owm_json_data_complete,
    owm_json_data_minimal,
)
from test_models import coords_google, coords_washington_dc, db_session
from weather import (
    WeatherResponse,
    get_coordinates_from_api,
    get_current_weather_from_owm,
    get_location_data,
    handle_checking_another_users_default,
    handle_user_sets_default_location,
    handle_users_default_location,
)


@pytest.fixture
def mock_response(request):
    """
    Mock response for aiohttp.ClientSession.get("https://whatever").json(),
    but with async. See e.g. weather.get_coordinates_from_api() for an example.

    Note: `request` is special and the name cannot change.
    See https://docs.pytest.org/en/7.1.x/example/parametrize.html#indirect-parametrization.
    """

    class MockResponse:
        async def json(self):
            return request.param

    async def mock_get(*args, **kwargs):
        return MockResponse()

    return mock_get


location_google = "1600 Amphitheatre Parkway, Mountain View, CA"
location_washingon_dc = "20001"

mock_api_response_google = {
    "results": [
        {
            "formatted_address": "1600 Amphitheatre Pkwy, Mountain View, CA 94043, USA",
            "geometry": {"location": {"lat": 37.4224053, "lng": -122.0842161}},
        }
    ],
    "status": "OK",
}

mock_api_response_washington_dc = {
    "results": [
        {
            "formatted_address": "Washington, DC 20001, USA",
            "geometry": {"location": {"lat": 38.912068, "lng": -77.0190228}},
        }
    ],
    "status": "OK",
}

coords_google = Coords(
    address="1600 Amphitheatre Pkwy, Mountain View, CA 94043, USA",
    latitude=37.4224053,
    longitude=-122.0842161,
    query="1600 Amphitheatre Parkway, Mountain View, CA",
)

coords_washington_dc = Coords(
    address="Washington, DC 20001, USA", latitude=38.912068, longitude=-77.0190228, query="20001"
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("location", "mock_response", "expected"),
    [
        (
            location_google,
            mock_api_response_google,
            coords_google,
        ),
        (
            location_washingon_dc,
            mock_api_response_washington_dc,
            coords_washington_dc,
        ),
    ],
    indirect=["mock_response"],
)
async def test_get_coordinates(location: str, mock_response: dict, expected: Coords) -> None:
    """
    Test that a location maps to coordinates.
    """
    with patch("aiohttp.ClientSession.get", new=mock_response):
        got = await get_coordinates_from_api(location)
        assert got == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_response, exception",
    [
        ({"error_message": "API key error", "results": [], "status": "REQUEST_DENIED"}, InvalidAPIKeyError),
        ({"status": "Mrs. Renfro's Salsa"}, ValueError),
    ],
    indirect=["mock_response"],
)
async def test_get_coordinates_error_handling(mock_response, exception) -> None:
    """
    Handle when there's an invalid API key or an unknown error.
    """
    TEST_LOCATION: Final = "1600 Amphitheatre Parkway, Mountain View, CA"
    with patch("aiohttp.ClientSession.get", new=mock_response):
        with pytest.raises(exception):
            await get_coordinates_from_api(TEST_LOCATION)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("query", "expected"),
    [
        (location_google, coords_google),
        (location_washingon_dc, coords_washington_dc),
    ],
)
async def test_get_location_data_doesnt_call_api_when_coords_in_db(
    db_session: Session, query: str, expected: Coords
) -> None:
    """
    The logic is that `get_location_data` should first attempt to get location
    data from the database, and if that fails, it should hit the API, and then
    store the information in the database (and return the data).
    """
    # Ensure DB is empty.
    assert db_session.query(CoordsDB).count() == 0

    db_session.add(coords_google.to_sqlalchemy())
    db_session.add(coords_washington_dc.to_sqlalchemy())
    db_session.commit()

    with patch("weather.get_coordinates_from_api") as mock_get_coordinates:
        got = await get_location_data(address=query, db_session=db_session)
        assert got == expected
        mock_get_coordinates.assert_not_called()


@pytest.mark.asyncio()
@pytest.mark.parametrize(
    ("query", "expected"),
    [
        (location_google, coords_google),
        (location_washingon_dc, coords_washington_dc),
    ],
)
async def test_get_location_data_updates_db_with_new_coordinates(
    db_session: Session, query: str, expected: Coords
) -> None:
    """
    When coordinates are pulled from the external geocoding API, the
    coordinates should be written to the database.

    This is just testing the business logic of `get_location_data`, hence the
    mocked respose for `weather.get_coordinates_from_api()`, which is unit
    tested elsewhere.
    """
    assert db_session.query(CoordsDB).count() == 0

    async def mock_get_coordinates(_):
        return expected

    with patch("weather.get_coordinates_from_api", new=mock_get_coordinates):
        # Verify over all result.
        got = await get_location_data(address=query, db_session=db_session)
        assert got == expected

        # Verify item from API is added to the DB correctly.
        assert db_session.query(CoordsDB).count() == 1
        db_query = select(CoordsDB).where(CoordsDB.query == query)
        got = db_session.execute(db_query).scalar_one_or_none()
        assert got
        assert got.to_dataclass() == expected


@pytest.mark.asyncio()
@pytest.mark.parametrize(
    ("latitude", "longitude", "mock_response", "validation_dict"),
    [
        (37.4224, -122.0842, owm_json_data_complete, currentweather_expected_complete),
        (37.4224, -122.0842, owm_json_data_minimal, currentweather_expected_minimal),
    ],
    indirect=["mock_response"],
)
async def test_get_current_weather_from_owm(
    latitude: float, longitude: float, mock_response: dict, validation_dict: dict
) -> None:
    """
    Given a mock API response from OpenWeatherMap, ensure we get the correct
    `CurrentWeather` object. Note: this is largely tested by `TestWeather` in
    `test_models.py`, as this function does little more than call an API and
    pass the JSON to `CurrentWeather.create_from_owm_json()`.
    """

    with patch("aiohttp.ClientSession.get", new=mock_response):
        model = await get_current_weather_from_owm(latitude=latitude, longitude=longitude)
        for attr, expected_value in validation_dict.items():
            assert (
                getattr(model, attr) == expected_value
            ), f"For key {attr}: found {getattr(model, attr)} but expected {expected_value}"


@pytest.mark.asyncio()
@pytest.mark.parametrize(
    ("latitude", "longitude", "mock_response", "error"),
    [
        (9999.9999, -122.0842, {"cod": "400", "message": "wrong latitude"}, APISyntaxError),
        (37.4224, 9999.9999, {"cod": "400", "message": "wrong longitude"}, APISyntaxError),
        (
            37.4224,
            -122.0842,
            {
                "cod": "401",
                "message": "Invalid API key. Please see https://openweathermap.org/faq#error401 for more info.",
            },
            InvalidAPIKeyError,
        ),
        (37.4224, -122.0842, {"cod": "999", "message": "Rubbish response"}, ValueError),
    ],
    indirect=["mock_response"],
)
async def test_get_current_weather_from_owm_errors(latitude: float, longitude: float, mock_response: dict, error):
    """Ensure get_current_weather_from_owm() raises the correct errors."""
    with patch("aiohttp.ClientSession.get", new=mock_response):
        with pytest.raises(error):
            await get_current_weather_from_owm(longitude, latitude)


@dataclass(slots=True)
class Author:
    """Stand-in for `discord.py`'s `Author`."""

    id: int
    name: str


@dataclass(slots=True)
class Message:
    """
    Stand-in for `discord.py`'s `message`.
    """

    author: Author
    no_prefix: str
    weather_prefix: str


class TestProcessWeatherCommand:
    author_1 = Author(id=1, name="Test User 1")
    author_2 = Author(id=2, name="Test User 2")

    @pytest.mark.asyncio
    async def test_handle_users_default_location(self, db_session: Session) -> None:
        """
        When a user checks their default weather location, they get that location or
        a message about setting a default.
        """
        discord_msg_1 = Message(author=self.author_1, no_prefix="", weather_prefix=".wz")
        discord_msg_2 = Message(author=self.author_2, no_prefix="", weather_prefix=".wz")
        py_user_with_location = User(name="Test User 1", discord_id=1, weather_location="20001")
        py_user_no_location = User(name="Test User 2", discord_id=2, weather_location=None)
        db_session.add(py_user_with_location)
        db_session.add(py_user_no_location)
        db_session.commit()

        assert await handle_users_default_location(db_session, discord_msg_1) == WeatherResponse(
            status="success", message="", location="20001"
        )
        assert await handle_users_default_location(db_session, discord_msg_2) == WeatherResponse(
            status="error", message="No location set. Set with `.wz -d location`", location=""
        )

    @pytest.mark.asyncio
    async def test_handle_user_sets_default_location(self, db_session: Session) -> None:
        """
        Users can set a default with `.wz -d location`, and we want to set it
        and pass the location along for an immediate weather report.
        """
        discord_msg_1 = Message(author=self.author_1, no_prefix="", weather_prefix=".wz")
        discord_msg_2 = Message(author=self.author_2, no_prefix="20001", weather_prefix=".wz")
        py_user_1 = User(name="Test User 1", discord_id=1, weather_location=None)
        py_user_2 = User(name="Test User 2", discord_id=2, weather_location=None)
        db_session.add(py_user_1)
        db_session.add(py_user_2)
        db_session.commit()

        assert await handle_user_sets_default_location(db_session, discord_msg_1) == WeatherResponse(
            status="error", message="Missing location. Set with `.wz -d location`", location=""
        )
        assert await handle_user_sets_default_location(db_session, discord_msg_2) == WeatherResponse(
            status="success", message="Default location set to: 20001", location="20001"
        )

    @pytest.mark.asyncio
    async def test_handle_checking_another_users_default(self, db_session: Session) -> None:
        """
        Users can check the default locations for one another.
        """
        discord_msg_1 = Message(author=self.author_1, no_prefix="<@not_an_id>", weather_prefix=".wz")
        discord_msg_2 = Message(author=self.author_2, no_prefix="<@2>", weather_prefix=".wz")
        py_user_1 = User(name="Test User 1", discord_id=1, weather_location=None)
        py_user_2 = User(name="Test User 2", discord_id=2, weather_location="20001")
        db_session.add(py_user_1)
        db_session.add(py_user_2)
        db_session.commit()

        assert await handle_checking_another_users_default(db_session, discord_msg_1) == WeatherResponse(
            status="error", message="User has no default set", location=""
        )
        assert await handle_checking_another_users_default(db_session, discord_msg_2) == WeatherResponse(
            status="success", message="", location="20001"
        )
