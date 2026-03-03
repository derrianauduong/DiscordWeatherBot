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

    # Convert event time to local timezone of the forecast
    if event_datetime.tzinfo is None:
        event_datetime = pytz.timezone("Australia/Sydney").localize(event_datetime)
    else:
        event_datetime = event_datetime.astimezone(pytz.timezone("Australia/Sydney"))

    # Parse hourly timestamps
    hourly_times = [datetime.fromisoformat(t) for t in times]

    # Find closest hour
    closest_idx = min(
        range(len(hourly_times)),
        key=lambda i: abs(hourly_times[i] - event_datetime)
    )

    weather_code = hourly["weathercode"][closest_idx]
    temp = hourly["temperature_2m"][closest_idx]
    rain_chance = hourly["precipitation_probability"][closest_idx]
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
        "event_time": event_datetime,
        "matched_hour": hourly_times[closest_idx],
    }

def format_weather(weather):
    event_time = weather["event_time"].strftime("%I:%M %p")
    matched = weather["matched_hour"].strftime("%I:%M %p")

    return (
        f"{weather['emoji']} **Weather at {event_time}** "
        f"(closest forecast hour: {matched})\n"
        f"**Condition:** {weather['description']}\n"
        f"**Temperature:** {weather['temp']}°C\n"
        f"**Day Range:** {weather['temp_min']}°C – {weather['temp_max']}°C\n"
        f"**Rain Chance:** {weather['rain_chance']}%\n"
    )

def needs_umbrella(weather):
    code = weather["code"]
    rain = weather["rain_chance"]

    rainy_codes = {51, 53, 55, 61, 63, 65, 80, 81, 82}

    decision = False
    reason = "low rain + non-rainy code"

    if code in rainy_codes:
        decision = True
        reason = f"rainy code {code}"
    elif rain >= 50:
        decision = True
        reason = f"high rain chance {rain}%"

    print(
        f"[Umbrella debug] code={code}, rain={rain}%, "
        f"event_time={weather['event_time']}, matched_hour={weather['matched_hour']}, "
        f"decision={decision}, reason={reason}"
    )

    return decision
