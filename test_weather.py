from typing import Final
from unittest.mock import patch

import aiohttp
import pytest

from errors import InvalidAPIKeyError
from models import Coords, CoordsDB
from weather import get_coordinates_from_api, get_location_data
from test_models import get_db


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


def setup_mock_api_response(aiohttp_session_mock, response_data):
    """Helper function to set up mock response."""
    aiohttp_session_mock.get.return_value.__aenter__.return_value.json.return_value = response_data


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
async def test_get_coordinates(location, mock_response, expected) -> None:
    """
    Test that a location maps to coordinates.
    """
    with patch("aiohttp.ClientSession.get", new=mock_response):
        location = await get_coordinates_from_api(location)
        assert location == expected


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
    TEST_LOCATION: Final = "1600 Amphitheatre Parkway, Mountain View, CA"
    with patch("aiohttp.ClientSession.get", new=mock_response):
        with pytest.raises(exception):
            await get_coordinates_from_api(TEST_LOCATION)


# @pytest.mark.asyncio
# @pytest.mark.parametrize(
#     ("query", "expected"),
#     [
#         (location_google, coords_google),
#         (location_washingon_dc, coords_washington_dc),
#         ("blah blah xyz rubbish", None),
#     ],
# )
# async def test_get_location_data_calls_external_api_if_necessary(get_db, aiohttp_session_mock, query, expected, monkeypatch) -> None:
#     """
#     The logic is that `get_location_data` should first attempt to get location
#     data from the database, and if that fails, it should hit the API, and then
#     store the information in the database (and return the data).
#     """
#     from aiohttp.test_utils import TestClient

#     db_session = get_db
#     # setup_mock_api_response(aiohttp_session_mock, mock_api_response_google)

#     # api_session = AsyncMock()
#     # api_session.get = AsyncMock()

#     # monkeypatch.setattr(aiohttp, "ClientSession", lambda: api_session)
#     # Need to:
#     # ensure database is checked.
#     # ensure API is called
#     # ensure DB is updated
#     # ensure data is returned

#     with aioresponses() as mocked_api_session:
#         # mocked_api_session.get
#         mocked_api_session.get("http://httpbin.org/get", status=200, body='{"test": true}')

#         # Ensure database is new.
#         assert len(db_session.query(CoordsDB).all()) == 0
#         got = await get_location_data(query)
#         assert got == expected
