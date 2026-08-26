from datetime import datetime, timedelta
import re

import pytz
import requests

SYDNEY_TZ = pytz.timezone("Australia/Sydney")

WEATHER_TYPES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog", 51: "Light drizzle",
    53: "Moderate drizzle", 55: "Dense drizzle", 56: "Light freezing drizzle",
    57: "Dense freezing drizzle", 61: "Slight rain", 63: "Moderate rain",
    65: "Heavy rain", 66: "Light freezing rain", 67: "Heavy freezing rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    77: "Snow grains", 80: "Slight rain showers", 81: "Moderate rain showers",
    82: "Violent rain showers", 85: "Slight snow showers",
    86: "Heavy snow showers", 95: "Thunderstorm",
    96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail",
}

EMOJI_ICONS = {
    0: "☀️", 1: "☀️", 2: "🌤️", 3: "☁️", 45: "🌫️", 48: "🌫️",
    51: "🌦️", 53: "🌦️", 55: "🌦️", 56: "🌦️", 57: "🌦️",
    61: "🌦️", 63: "🌧️", 65: "🌧️", 66: "🌧️", 67: "🌧️",
    71: "❄️", 73: "❄️", 75: "❄️", 77: "❄️",
    80: "🌧️", 81: "🌧️", 82: "🌧️", 85: "❄️", 86: "❄️",
    95: "⛈️", 96: "⛈️", 99: "⛈️",
}

RAINY_CODES = {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99}


def extract_suburb(location: str) -> str | None:
    if not location:
        return None
    cleaned = re.sub(r"\b\d{4}\b", "", location).strip(" ,")
    parts = [part.strip() for part in cleaned.split(",") if part.strip()]
    ignored = {"australia", "nsw", "new south wales"}
    useful_parts = [part for part in parts if part.lower() not in ignored]
    if useful_parts:
        return useful_parts[-1]
    words = cleaned.split()
    return " ".join(words[-2:]) if len(words) >= 2 else cleaned or None


def geocode_suburb(suburb: str):
    response = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"format": "json", "q": f"{suburb}, NSW, Australia", "limit": 1},
        headers={"User-Agent": "DiscordWeatherBot/1.0"},
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    if not data:
        return None
    return float(data[0]["lat"]), float(data[0]["lon"])


def _as_sydney_time(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None:
        return SYDNEY_TZ.localize(value)
    return value.astimezone(SYDNEY_TZ)


def get_weather(lat, lon, event_start=None, event_end=None):
    """Return hourly weather covering an event, or the next two hours by default."""
    start = _as_sydney_time(event_start) or datetime.now(SYDNEY_TZ)
    end = _as_sydney_time(event_end) or (start + timedelta(hours=2))
    if end <= start:
        end = start + timedelta(hours=2)

    response = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "hourly": (
                "temperature_2m,apparent_temperature,precipitation_probability,"
                "weather_code,wind_speed_10m"
            ),
            "timezone": "Australia/Sydney",
            "start_date": start.date().isoformat(),
            "end_date": end.date().isoformat(),
        },
        timeout=15,
    )
    response.raise_for_status()
    hourly = response.json()["hourly"]
    forecast_times = [
        SYDNEY_TZ.localize(datetime.fromisoformat(value)) for value in hourly["time"]
    ]
    indices = [
        i for i, forecast_time in enumerate(forecast_times)
        if forecast_time < end and forecast_time + timedelta(hours=1) > start
    ]
    if not indices:
        raise ValueError("No hourly forecast is available for this event time.")

    temperatures = [hourly["temperature_2m"][i] for i in indices]
    feels_like = [hourly["apparent_temperature"][i] for i in indices]
    rain_chances = [hourly["precipitation_probability"][i] or 0 for i in indices]
    winds = [hourly["wind_speed_10m"][i] for i in indices]
    representative_index = indices[rain_chances.index(max(rain_chances))]
    code = hourly["weather_code"][representative_index]

    return {
        "code": code,
        "description": WEATHER_TYPES.get(code, "Unknown conditions"),
        "emoji": EMOJI_ICONS.get(code, "❓"),
        "min_temp": min(temperatures),
        "max_temp": max(temperatures),
        "min_feels_like": min(feels_like),
        "max_feels_like": max(feels_like),
        "rain_chance": max(rain_chances),
        "wind_speed": max(winds),
        "forecast_start": start,
        "forecast_end": end,
    }


def needs_umbrella(weather):
    return weather["code"] in RAINY_CODES or weather["rain_chance"] >= 40
