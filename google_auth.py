import os
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

def get_calendar_service():
    token_json = os.getenv("GOOGLE_TOKEN_JSON")
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")

    if not token_json or not creds_json:
        raise Exception("Missing GOOGLE_TOKEN_JSON or GOOGLE_CREDENTIALS_JSON")

    creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
    return build("calendar", "v3", credentials=creds)
