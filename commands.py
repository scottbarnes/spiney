from models import get_db_session
from weather import get_current_weather_from_owm, get_location_data


async def get_current_weather(location: str) -> str:
    """
    Geocode `location` to GPS coordinates and return a report of the current weather.
    """
    db_session = get_db_session()
    if not (coordinates := await get_location_data(address=location, db_session=db_session)):
        return f"Could not geocode input: {location}."

    current_weather = await get_current_weather_from_owm(coordinates.latitude, coordinates.longitude)
    return current_weather.format_weather_report()
