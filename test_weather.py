from typing import Final
from unittest.mock import MagicMock, Mock

import pytest

from errors import InvalidAPIKeyError
from models import Coords
from weather import get_coordinates


@pytest.fixture
def session_mock():
    session = Mock()
    session.get = MagicMock()
    return session


def setup_mock_response(session_mock, response_data):
    """Helper function to set up mock response."""
    session_mock.get.return_value.__aenter__.return_value.json.return_value = response_data


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("location", "mock_response", "expected"),
    [
        (
            "1600 Amphitheatre Parkway, Mountain View, CA",
            {
                "results": [
                    {
                        "formatted_address": "1600 Amphitheatre Pkwy, Mountain View, CA 94043, USA",
                        "geometry": {"location": {"lat": 37.4224053, "lng": -122.0842161}},
                    }
                ],
                "status": "OK",
            },
            Coords(
                address="1600 Amphitheatre Pkwy, Mountain View, CA 94043, USA",
                latitude=37.4224053,
                longitude=-122.0842161,
                query="1600 Amphitheatre Parkway, Mountain View, CA",
            ),
        ),
        (
            "20001",
            {
                "results": [
                    {
                        "formatted_address": "Washington, DC 20001, USA",
                        "geometry": {"location": {"lat": 38.912068, "lng": -77.0190228}},
                    }
                ],
                "status": "OK",
            },
            Coords(address="Washington, DC 20001, USA", latitude=38.912068, longitude=-77.0190228, query="20001"),
        ),
    ],
)
async def test_get_coordinates(location, mock_response, expected, session_mock) -> None:
    setup_mock_response(session_mock, mock_response)

    location = await get_coordinates(session_mock, location)
    assert location == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response, exception",
    [
        ({"error_message": "API key error", "results": [], "status": "REQUEST_DENIED"}, InvalidAPIKeyError),
        ({"status": "Mrs. Renfro's Salsa"}, ValueError),
    ],
)
async def test_get_coordinates_error_handling(response, exception, session_mock) -> None:
    TEST_LOCATION: Final = "1600 Amphitheatre Parkway, Mountain View, CA"
    setup_mock_response(session_mock, response)

    with pytest.raises(exception):
        await get_coordinates(session_mock, TEST_LOCATION)
