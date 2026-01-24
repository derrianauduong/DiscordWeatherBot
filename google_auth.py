import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

def get_calendar_service():
    creds = None

    # Load JSON strings from Railway environment variables
    creds_json_str = os.getenv("GOOGLE_CREDENTIALS_JSON")
    token_json_str = os.getenv("GOOGLE_TOKEN_JSON")

    # If token exists, load it
    if token_json_str:
        creds = Credentials.from_authorized_user_info(json.loads(token_json_str), SCOPES)

    # If no valid credentials, start OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Load credentials.json from environment variable
            creds_json = json.loads(creds_json_str)
            flow = InstalledAppFlow.from_client_config(creds_json, SCOPES)
            creds = flow.run_local_server(port=0)

        # Print token so you can paste it into Railway
        print("PASTE THIS INTO GOOGLE_TOKEN_JSON:")
        print(creds.to_json())

    service = build("calendar", "v3", credentials=creds)
    return service
