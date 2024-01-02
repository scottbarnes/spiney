import os
from typing import Final
from urllib.parse import quote_plus

import aiohttp
from discord.message import Message
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from errors import APISyntaxError, InvalidAPIKeyError
from models import Coords, CoordsDB, CurrentWeather, CustomMessage, WeatherResponse
from utilities import get_or_create_user, get_user

GOOGLE_MAPS_API_KEY: Final = os.getenv("GOOGLE_MAPS_API_KEY", "")
OPENWEATHER_API_KEY: Final = os.getenv("OPENWEATHER_API_KEY", "")


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
                raise ValueError(f"Got unexpected result from get_coordinates_from_api(): {result}")


async def get_location_data(address: str, db_session: Session) -> Coords | None:
    """
    Turn an address into Coords, if geocoded coordinates can be found.

    1. Check database if entry exists; if it does, use it.
    2. If not, query API, update DB, then use that data.
    """
    # Get coordinates from DB if available.
    db_query = select(CoordsDB).where(func.lower(CoordsDB.query) == func.lower(address))
    if coordinates := db_session.execute(db_query).scalar_one_or_none():
        return coordinates.to_dataclass()

    # Get coordinates from API if necessary.
    if coordinates := await get_coordinates_from_api(address):
        db_session.add(coordinates.to_sqlalchemy())
        db_session.commit()
        return coordinates

    return None


async def get_current_weather_from_owm(latitude: float, longitude: float) -> CurrentWeather:
    """
    Fetch weather from the OpenWeatherMap API and return the CurrentWeather.
    1. get weather from API with async aiohttp.ClientSession()
    2. call the static method on CurrentWeather() to get class object to return.
    """
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={latitude}&lon={longitude}&units=metric&appid={OPENWEATHER_API_KEY}"

    async with aiohttp.ClientSession() as session:
        response = await session.get(url)
        result = await response.json()

        match result:
            case {"cod": "401", "message": message}:
                raise InvalidAPIKeyError(message=message)
            case {"cod": "400", "message": message}:
                raise APISyntaxError(message=message)
            # Note a 200 response is an `int` rather than a `str`, as with the others.
            case {"cod": 200}:
                return CurrentWeather.create_from_owm_json(result)
            case _:
                raise ValueError(f"Got unexpected result from get_current_weather_from_owm(): {result}")


async def get_current_weather(db_session: Session, location: str) -> str:
    """
    Geocode `location` to GPS coordinates and return a report of the current weather.
    """
    if not (coordinates := await get_location_data(address=location, db_session=db_session)):
        return f"Could not geocode input: {location}"

    current_weather = await get_current_weather_from_owm(coordinates.latitude, coordinates.longitude)
    return current_weather.format_weather_report()


async def handle_users_default_location(db_session: Session, message: Message) -> WeatherResponse:
    """
    Handle the response when a user requests their default weather location.

    If there `user` has `weather_location` set, then `status` will be `success` and
    a `location` is returned, but if not, `status` is `error`.

    The caller determines what to do based on the `status`.
    """
    user = get_or_create_user(db_session=db_session, name=message.author.name, discord_id=message.author.id)
    if user.weather_location is None:
        error_message = f"No location set. Set with `{message.weather_prefix} -d location`"
        return WeatherResponse(status="error", message=error_message, location="")
    else:
        return WeatherResponse(status="success", message="", location=str(user.weather_location))


async def handle_user_sets_default_location(db_session: Session, message) -> WeatherResponse:
    """
    Handle when a user sets a default location.

    The caller determines what to do based on the `status`.
    """
    user = get_or_create_user(db_session=db_session, name=message.author.name, discord_id=message.author.id)
    if len(message.no_prefix) == 0:
        error_message = f"Missing location. Set with `{message.weather_prefix} -d location`"
        return WeatherResponse(status="error", message=error_message, location="")
    else:
        user.weather_location = message.no_prefix
        db_session.commit()
        return WeatherResponse(
            status="success",
            message=f"Default location set to: {user.weather_location}",
            location=user.weather_location,
        )


async def handle_checking_another_users_default(db_session: Session, message) -> WeatherResponse:
    """
    Handle checking another user's default weather location.

    The caller determines what to do based on the `status`.
    """
    discord_id = message.no_prefix.strip("><@ ")
    user = get_user(db_session=db_session, discord_id=discord_id)
    if not user or user.weather_location is None:
        return WeatherResponse(status="error", message="User has no default set", location="")
    else:
        return WeatherResponse(status="success", message="", location=str(user.weather_location))


async def process_weather_command(db_session: Session, message: CustomMessage, weather_prefix: str) -> WeatherResponse:
    message.no_prefix = message.content[len(weather_prefix) + 1 :]
    message.weather_prefix = weather_prefix
    weather_response = WeatherResponse(status="", message="", location="")

    # Handle default locations
    if len(message.no_prefix) == 0:
        weather_response = await handle_users_default_location(db_session=db_session, message=message)
    # Handle setting a default.
    elif message.no_prefix.startswith("-d"):
        message.no_prefix = message.no_prefix[3:].strip()
        weather_response = await handle_user_sets_default_location(db_session=db_session, message=message)
    # Handle checking another user's default.
    elif message.no_prefix.startswith("<"):
        weather_response = await handle_checking_another_users_default(db_session=db_session, message=message)

    # Run the actual weather check.
    if weather_response.status == "error":
        return weather_response
    elif weather_response.status == "success":
        current_weather = await get_current_weather(db_session=db_session, location=weather_response.location)
        weather_response.message = current_weather
        return weather_response
    else:
        current_weather = await get_current_weather(db_session=db_session, location=message.no_prefix)
        weather_response.message = current_weather
        return weather_response
