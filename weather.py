import asyncio
import os
from typing import Final
from urllib.parse import quote_plus

from sqlalchemy.orm import Session

import aiohttp

from errors import InvalidAPIKeyError
from models import Coords, CoordsDB

GOOGLE_MAPS_API_KEY: Final = os.getenv("GOOGLE_MAPS_API_KEY", "")


async def get_coordinates_from_api(location: str) -> Coords | None:
    """
    Get the coordinates for `location`. The API parameter says `address`, but
    this can be an address, a name (e.g. "Mount Whitney"), a zip code, etc.
    """
    url_encoded_location = quote_plus(location)
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={url_encoded_location}&key={GOOGLE_MAPS_API_KEY}"
    async with aiohttp.ClientSession() as session:
        response = await session.get(url)
        result = await response.json()

        match result:
            case {"status": "REQUEST_DENIED", "error_message": message}:
                raise InvalidAPIKeyError(message=message)
            case {"status": "ZERO_RESULTS", "results": []}:
                return None
            case {"status": "OK", "results": results}:
                coordinates = results[0]["geometry"]["location"]
                address = results[0]["formatted_address"]
                return Coords(
                    address=address, query=location, latitude=coordinates["lat"], longitude=coordinates["lng"]
                )
            case _:
                raise ValueError(f"Got unexpected result from get_coordinates: {result}")


async def get_location_data(address, db_session: Session) -> Coords | None:
    """
    TODO:
    1. Check database if entry exists; if it does, use it.
    2. If not, query API, update DB, then use that data.
    """
    # Get coordinates from DB if available.
    if coordinates := db_session.query(CoordsDB).filter(CoordsDB.query == address).first():
        return coordinates.to_dataclass()

    # Get coordinates from API if necessary.
    coordinates = await get_coordinates_from_api(address)
    if not coordinates:
        return None

    return coordinates


# if __name__ == "__main__":
#     address = "20001"
#     location_data = asyncio.run(get_location_data(address))
#     print(location_data)
