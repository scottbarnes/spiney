import asyncio
import os
from typing import Final

import aiohttp

from errors import InvalidAPIKeyError
from models import Coords

GOOGLE_MAPS_API_KEY: Final = os.getenv("GOOGLE_MAPS_API_KEY", "")


async def get_coordinates(session: aiohttp.ClientSession, address: str) -> Coords | None:
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={GOOGLE_MAPS_API_KEY}"
    async with session.get(url) as response:
        result = await response.json()

        match result:
            case {"status": "REQUEST_DENIED", "error_message": message}:
                raise InvalidAPIKeyError(message=message)
            case {"status": "ZERO_RESULTS", "results": []}:
                return None
            case {"status": "OK", "results": results}:
                coordinates = results[0]["geometry"]["location"]
                return Coords(latitude=coordinates["lat"], longitude=coordinates["lng"])
            case _:
                raise ValueError(f"Got unexpected result from get_coordinates: {result}")


async def get_location_data(address):
    async with aiohttp.ClientSession() as session:
        coordinates = await get_coordinates(session, address)
        if not coordinates:
            return "No geocode results found"

        return coordinates


if __name__ == "__main__":
    address = " "
    location_data = asyncio.run(get_location_data(address))
    print(location_data)
