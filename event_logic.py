import pytz
from datetime import datetime, timedelta
from weather import extract_suburb, geocode_suburb, get_weather, needs_umbrella

GOING_OUT_KEYWORDS = [ "dinner", "lunch", "gym", "hangout", "party", "appointment", "work", "coffee", "drinks" ]

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

    events_result = service.events().list(
        calendarId="primary",
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    return events_result.get("items", [])

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
    
    # 4. If event starts after 5pm
    start_str = event["start"].get("dateTime")
    if start_str:
        start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00")) 
        sydney = pytz.timezone("Australia/Sydney")
        local_start = start_dt.astimezone(sydney)
        
        if local_start.hour >= 17:
            return True
        
    return False

def get_weather_recommendations(events):
    recommendations = []

    for event in events:
        location = event.get("location", "")
        suburb = extract_suburb(location)

        # Default to Sydney CBD
        lat, lon = -33.8688, 151.2093

        if suburb:
            coords = geocode_suburb(suburb)
            if coords:
                lat, lon = coords

        weather = get_weather(lat, lon)
        umbrella = needs_umbrella(weather)

        recommendations.append({
            "event": event,
            "weather": weather,
            "umbrella": umbrella
        })

    return recommendations
