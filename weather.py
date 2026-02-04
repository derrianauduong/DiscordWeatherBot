import requests
import re

def extract_suburb(location: str) -> str | None:
    if not location:
        return None

    # If the location contains a comma, the suburb is usually after it
    if "," in location:
        parts = [p.strip() for p in location.split(",")]
        return parts[-1]  # last part is usually the suburb

    # Otherwise, take the last word or last two words
    words = location.split()
    if len(words) >= 2:
        return " ".join(words[-2:])  # e.g., "Bondi Junction"
    return words[-1]

def geocode_suburb(suburb: str):
    query = f"{suburb}, NSW, Australia"
    url = "https://nominatim.openstreetmap.org/search"
    params = {"format": "json", "q": query}

    response = requests.get(url, params=params, headers={"User-Agent": "DiscordBot"})
    data = response.json()

    if not data:
        return None

    lat = float(data[0]["lat"])
    lon = float(data[0]["lon"])
    return lat, lon


def get_weather(lat, lon, event_datetime):
    url = (
        "https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        "&hourly=weathercode,temperature_2m,precipitation_probability"
        "&daily=temperature_2m_max,temperature_2m_min"
        "&timezone=auto"
    )
    response = requests.get(url).json()

    hourly = response["hourly"]
    times = hourly["time"]

    target = event_datetime.strftime("%Y-%m-%dT%H:00")

    if target not in times:
        return None

    idx = times.index(target)

    weather_code = hourly["weathercode"][idx]
    temp = hourly["temperature_2m"][idx]
    rain_chance = hourly["precipitation_probability"][idx]
    temp_max = response["daily"]["temperature_2m_max"][0]
    temp_min = response["daily"]["temperature_2m_min"][0]

    weather_types = {
        0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Fog", 48: "Depositing rime fog",
        51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
        61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
        80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
        71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
        95: "Thunderstorm", 96: "Thunderstorm w/ slight hail", 99: "Thunderstorm w/ heavy hail"
    }

    emoji_icons = {
        0: "☀️", 1: "☀️",
        2: "🌤️",
        3: "☁️",
        45: "🌫️", 48: "🌫️",
        51: "🌦️", 53: "🌦️", 55: "🌦️",
        61: "🌧️", 63: "🌧️", 65: "🌧️",
        80: "🌧️", 81: "🌧️", 82: "🌧️",
        71: "❄️", 73: "❄️", 75: "❄️",
        95: "⛈️", 96: "⛈️", 99: "⛈️",
    }

    return {
        "code": weather_code,
        "description": weather_types.get(weather_code, "Unknown"),
        "emoji": emoji_icons.get(weather_code, "❓"),
        "temp": temp,
        "temp_min": temp_min,
        "temp_max": temp_max,
        "rain_chance": rain_chance,
        "event_time": event_datetime
    }

def format_weather(weather):
    dt = weather["event_time"].strftime("%I:%M %p")

    return (
        f"{weather['emoji']} **Weather at {dt}**\n"
        f"**Condition:** {weather['description']}\n"
        f"**Current Temperature:** {weather['temp']}°C\n"
        f"**Today's Min:** {weather['temp_min']}°C\n"
        f"**Today's Max:** {weather['temp_max']}°C\n"
        f"**Rain Chance:** {weather['rain_chance']}%\n"
    )

def needs_umbrella(weather):
    code = weather["code"]
    rain = weather["rain_chance"]

    rainy_codes = {51, 53, 55, 61, 63, 65, 80, 81, 82}

    if code in rainy_codes:
        return True

    if rain >= 50:
        return True

    return False
