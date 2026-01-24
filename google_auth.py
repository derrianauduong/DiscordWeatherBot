from __future__ import print_function

import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

def get_calendar_service():
    print("Starting get_calendar_service()")

    creds = None

    # token.json stores your access/refresh tokens
    if os.path.exists("token.json"):
        print("Found token.json, loading credentials...")
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    else:
        print("No token.json found")

    # If no valid credentials, log in
    if not creds or not creds.valid:
        print("No valid credentials, need to authenticate")

        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired credentials...")
            creds.refresh(Request())
        else:
            print("Starting OAuth flow...")
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
            print("OAuth flow completed")

        # Save the credentials for next time
        with open("token.json", "w") as token:
            print("Saving new token.json")
            token.write(creds.to_json())
    else:
        print("Credentials already valid")

    print("Building calendar service...")
    service = build("calendar", "v3", credentials=creds)
    print("Service built successfully")
    return service