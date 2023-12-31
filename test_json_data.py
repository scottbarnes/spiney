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

# A timezone offset of 0 caused a bug because `some_truthy_time and 0` is False.
owm_json_utc_location = {
    "coord": {"lon": -1.8287, "lat": 51.1788},
    "weather": [{"id": 801, "main": "Clouds", "description": "few clouds", "icon": "02n"}],
    "base": "stations",
    "main": {"temp": 5.13, "feels_like": -1.43, "temp_min": -4.56, "temp_max": 6.04, "pressure": 985, "humidity": 91},
    "visibility": 10000,
    "wind": {"speed": 5.14, "deg": 220},
    "clouds": {"all": 20},
    "dt": 1704001975,
    "sys": {"type": 2, "id": 2003051, "country": "GB", "sunrise": 1704010285, "sunset": 1704038910},
    "timezone": 0,
    "id": 2657355,
    "name": "Amesbury",
    "cod": 200,
}

currentweather_expected_utc_location = {
    "last_updated": datetime(2023, 12, 30, 21, 52, 55),
    "conditions": "few clouds",
    "icon": "02n",
    "temperature": 5.13,
    "feels_like": -1.43,
    "humidity": 91,
    "pressure": 985,
    "visibility": 10000,
    "wind_speed": 5.14,
    "wind_direction": "SW",
    "clouds": 20,
    "sunrise": datetime(2023, 12, 31, 0, 11, 25),
    "sunset": datetime(2023, 12, 31, 8, 8, 30),
    "name": "Amesbury",
    "country": "GB",
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
    "last_updated": datetime(2023, 12, 30, 8, 32, 55),
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
    "sunrise": datetime(2023, 12, 29, 23, 22, 19),
    "sunset": datetime(2023, 12, 30, 8, 59, 1),
    "name": "Mountain View",
    "country": "US",
}


# A dictionary for checking values of the minimum attributes needed to
# instantiate a `CurrentWeather` object.
currentweather_expected_minimal = {
    "name": "Mountain View",
    "temperature": 15.8,
    "last_updated": datetime(2023, 12, 29, 14, 47, 29),
}
