from datetime import datetime

# "Complete" Response from the Open Weather Map API.
# See https://openweathermap.org/current for more.
owm_json_data_complete = {
    "coord": {"lon": -122.0842, "lat": 37.4224},
    "weather": [
        {"id": 502, "main": "Rain", "description": "heavy intensity rain", "icon": "10n"},
        {"id": 701, "main": "Mist", "description": "mist", "icon": "50n"},
    ],
    "base": "stations",
    "main": {
        "temp": 13.1,
        "feels_like": 12.87,
        "temp_min": 11.77,
        "temp_max": 14.18,
        "pressure": 1014,
        "humidity": 92,
    },
    "visibility": 4828,
    "wind": {"speed": 3.6, "deg": 110, "gust": 5.6},
    "rain": {"1h": 5.31},
    "snow": {"1h": 1.2},
    "clouds": {"all": 100},
    "dt": 1703982775,
    "sys": {"type": 2, "id": 2010364, "country": "US", "sunrise": 1703949739, "sunset": 1703984341},
    "timezone": -28800,
    "id": 5375480,
    "name": "Mountain View",
    "cod": 200,
}


# The minimum accepted fields for a `CurrentWeather` object.
owm_json_data_minimal = {
    "main": {
        "temp": 15.8,
    },
    "dt": 1703918849,
    "timezone": -28800,
    "name": "Mountain View",
    "cod": 200,
}


# A dictionary used to check the values for each attribute of the above
# OWM API response, once it's processed by `CurrentWeather`.
currentweather_expected_complete = {
    "last_updated": datetime(2023, 12, 30, 16, 32, 55),
    "conditions": "heavy intensity rain",
    "icon": "10n",
    "temperature": 13.1,
    "feels_like": 12.87,
    "humidity": 92,
    "pressure": 1014,
    "visibility": 4828,
    "wind_speed": 3.6,
    "wind_gust": 5.6,
    "wind_direction": "ESE",
    "clouds": 100,
    "rain_last_hour": 5.31,
    "snow_last_hour": 1.2,
    "sunrise": datetime(2023, 12, 30, 7, 22, 19),
    "sunset": datetime(2023, 12, 30, 16, 59, 1),
    "name": "Mountain View",
    "country": "US",
}


# A dictionary for checking values of the minimum attributes needed to
# instantiate a `CurrentWeather` object.
currentweather_expected_minimal = {
    "name": "Mountain View",
    "temperature": 15.8,
    "last_updated": datetime(2023, 12, 29, 22, 47, 29),
}
