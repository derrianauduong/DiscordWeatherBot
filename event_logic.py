from datetime import datetime, timedelta

import pytz

from weather import extract_suburb, geocode_suburb, get_weather, needs_umbrella

SYDNEY_TZ = pytz.timezone("Australia/Sydney")
GOING_OUT_KEYWORDS = {
    "dinner", "lunch", "gym", "hangout", "party", "appointment",
    "work", "coffee", "drinks", "exam", "class", "lecture", "tutorial",
}


# Banana, lavender, amethyst
GOING_OUT_COLOUR_IDS = {"12", "17", "24"}


def get_todays_events(service):
    now = datetime.now(SYDNEY_TZ)
    start_of_day = SYDNEY_TZ.localize(datetime(now.year, now.month, now.day))
    end_of_day = start_of_day + timedelta(days=1)
    result = service.events().list(
        calendarId="primary",
        timeMin=start_of_day.isoformat(),
        timeMax=end_of_day.isoformat(),
        singleEvents=True,
        orderBy="startTime",
    ).execute()
    return result.get("items", [])


def get_going_out_events(service):
    return [event for event in get_todays_events(service) if is_going_out_event(event)]


def is_going_out_event(event):
    summary = event.get("summary", "").lower()

    if "tutoring" or "alchemy" in summary:
        return False

    if event.get("location", "").strip():
        return True

    if any(keyword in summary for keyword in GOING_OUT_KEYWORDS):
        return True

    colour_id = event.get("eventLabelId") or event.get("colorId")
    if colour_id in GOING_OUT_COLOUR_IDS:
        return True

    start_str = event.get("start", {}).get("dateTime")
    if start_str:
        start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        if start.astimezone(SYDNEY_TZ).hour >= 17:
            return True

    return False


def _event_times(event):
    start_data = event.get("start", {})
    end_data = event.get("end", {})

    if start_data.get("dateTime"):
        start = datetime.fromisoformat(start_data["dateTime"].replace("Z", "+00:00"))
        start = start.astimezone(SYDNEY_TZ)
    else:
        start = SYDNEY_TZ.localize(datetime.fromisoformat(start_data["date"]))

    if end_data.get("dateTime"):
        end = datetime.fromisoformat(end_data["dateTime"].replace("Z", "+00:00"))
        end = end.astimezone(SYDNEY_TZ)
    elif end_data.get("date"):
        end = SYDNEY_TZ.localize(datetime.fromisoformat(end_data["date"]))
    else:
        end = start + timedelta(hours=2)
    return start, end


def get_weather_recommendations(events):
    recommendations = []
    for event in events:
        lat, lon = -33.8688, 151.2093  # Sydney CBD fallback
        suburb = extract_suburb(event.get("location", ""))
        if suburb:
            try:
                coordinates = geocode_suburb(suburb)
                if coordinates:
                    lat, lon = coordinates
            except Exception as error:
                print(f"Could not geocode {suburb!r}; using Sydney CBD: {error}")

        start, end = _event_times(event)
        try:
            weather = get_weather(lat, lon, start, end)
            recommendations.append({
                "event": event,
                "weather": weather,
                "umbrella": needs_umbrella(weather),
            })
        except Exception as error:
            print(f"Could not get weather for {event.get('summary', 'event')!r}: {error}")
            recommendations.append({
                "event": event,
                "weather": None,
                "umbrella": None,
                "error": "Forecast unavailable",
            })
    return recommendations
