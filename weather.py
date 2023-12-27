import asyncio
import os
from typing import Final

import aiohttp

from errors import InvalidAPIKeyError
from models import Coords

GOOGLE_MAPS_API_KEY: Final = os.getenv("GOOGLE_MAPS_API_KEY", "")


async def get_coordinates(session: aiohttp.ClientSession, location: str) -> Coords | None:
    """
    Get the coordinates for `location`. the API parameter says `address`, but
    this can be an address, a name (e.g. "Mount Whitney"), a zip code, etc.
    """
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={location}&key={GOOGLE_MAPS_API_KEY}"
    async with session.get(url) as response:
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


async def get_location_data(address):
    """
    TODO:
    1. Check database if entry exists; if it does, use it.
    2. If not, query API, update DB, then use that data.
    """
    async with aiohttp.ClientSession() as session:
        coordinates = await get_coordinates(session, address)
        if not coordinates:
            return "No geocode results found"

        return coordinates


if __name__ == "__main__":
    address = "20001"
    location_data = asyncio.run(get_location_data(address))
    print(location_data)
