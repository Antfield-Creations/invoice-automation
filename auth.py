import os
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from config import Config


def get_credentials(config: Config) -> Credentials:
    # Start with empty credentials
    creds: Optional[Credentials] = None

    # Load token from previous session if present
    if os.path.exists(config['oauth']['token_path']):
        creds = Credentials.from_authorized_user_file(
            filename=config['oauth']['token_path'],
            scopes=config['oauth']['scopes']
        )

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Connect to the Google docs service
            flow = InstalledAppFlow.from_client_secrets_file(
                client_secrets_file=config['oauth']['credentials_path'],
                scopes=config['oauth']['scopes']
            )

            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open(config['oauth']['token_path'], 'w') as token:
            token.write(creds.to_json())

    return creds
