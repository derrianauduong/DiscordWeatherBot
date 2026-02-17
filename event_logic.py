import pytz
from datetime import datetime, timedelta
from weather import extract_suburb, geocode_suburb, get_weather, needs_umbrella

GOING_OUT_KEYWORDS = [ "dinner", "lunch", "gym", "hangout", "party", "appointment", "work", "coffee", "drinks", "tutorial" ]

def get_todays_events(service):
    """
    Fetches all events happening today (local time) from the user's primary calendar.
    Returns a list of event dictionaries.
    """

    # Use your local timezone (Sydney)
    tz = pytz.timezone("Australia/Sydney")
    now = datetime.now(tz)

    # Start of today
    start_of_day = tz.localize(datetime(now.year, now.month, now.day, 0, 0, 0))
    # End of today
    end_of_day = start_of_day + timedelta(days=1)

    # Convert to RFC3339 format for Google Calendar API
    time_min = start_of_day.isoformat()
    time_max = end_of_day.isoformat()

    all_events = []

    # 1. Fetch all calendars the user has access to
    calendars = service.calendarList().list().execute().get("items", [])

    for cal in calendars:
        cal_id = cal["id"]

        events_result = service.events().list(
            calendarId=cal_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        events = events_result.get("items", [])
        all_events.extend(events)

    return all_events

def get_going_out_events(service):
    events = get_todays_events(service)
    return [event for event in events if is_going_out_event(event)]

def is_going_out_event(event): 
    """ Returns True if the event is likely a 'going out' event. """ 
    # 1. If event has a location
    if "location" in event and event["location"].strip(): 
        return True
    
    # # 2. If event summary contains keywords
    summary = event.get("summary", "").lower()
    if any(keyword in summary for keyword in GOING_OUT_KEYWORDS):
        return True
    
    # 3. If event is coloured lavendar (colourId = 1)
    colour = event.get("colorId")
    if colour == "1":
        return True
        
    return False

def get_weather_recommendations(events):
    recommendations = []

    for event in events:
        summary = event.get("summary", "Untitled Event")
        location = event.get("location", "")
        suburb = extract_suburb(location)

        # 1. Handle coordinates (Default to Sydney CBD)
        lat, lon = -33.8688, 151.2093
        if suburb:
            coords = geocode_suburb(suburb)
            if coords:
                lat, lon = coords

        # 2. Fix the Parser Error & Handle All-Day events
        start_info = event.get("start", {})
        start_str = start_info.get("dateTime") or start_info.get("date")

        if not start_str:
            continue # Skip if no date info found

        if "T" in start_str:
            # Timed event: 2026-02-02T11:00:00Z
            event_time = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        else:
            # All-day event: 2026-02-02
            event_time = datetime.strptime(start_str, "%Y-%m-%d")

        # 3. Get weather (Now including Min/Max)
        # Ensure your get_weather function returns a dict with 'max' and 'min'
        weather = get_weather(lat, lon, event_time)
        
        # 4. Check for umbrella
        umbrella = needs_umbrella(weather)

        recommendations.append({
            "event": event,
            "weather": weather,
            "umbrella": umbrella
        })

    return recommendations



