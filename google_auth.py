import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

def get_calendar_service():
    creds = None

    creds_json_str = os.getenv("GOOGLE_CREDENTIALS_JSON")
    token_json_str = os.getenv("GOOGLE_TOKEN_JSON")

    # Try loading token if it exists
    if token_json_str:
        try:
            creds = Credentials.from_authorized_user_info(json.loads(token_json_str), SCOPES)
        except Exception:
            creds = None

    # If no valid creds, run OAuth flow
    if not creds or not creds.valid:
        creds_json = json.loads(creds_json_str)
        flow = InstalledAppFlow.from_client_config(creds_json, SCOPES)
        creds = flow.run_local_server(port=0)

        print("PASTE THIS INTO GOOGLE_TOKEN_JSON:")
        print(creds.to_json())

    service = build("calendar", "v3", credentials=creds)
    return service
