# tools/AuthenticationManager.py

import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from typing import Optional, Tuple
import logging

class AuthenticationManager:
    """Handles Google Drive API authentication and service creation."""
    
    SCOPES = [
        'https://www.googleapis.com/auth/drive.readonly',
        'https://www.googleapis.com/auth/drive.file'
    ]

    def __init__(self, credentials_path: str, token_path: str, logger: logging.Logger):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.logger = logger
        self.service = None

    def authenticate(self) -> Tuple[bool, Optional[object]]:
        """Authenticate with Google Drive API and return service object."""
        creds = None
        
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    self.logger.error(f"Token refresh failed: {str(e)}")
                    return False, None
            else:
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, self.SCOPES)
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    self.logger.error(f"Authentication failed: {str(e)}")
                    return False, None

            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())

        try:
            service = build('drive', 'v3', credentials=creds)
            self.service = service
            return True, service
        except Exception as e:
            self.logger.error(f"Service build failed: {str(e)}")
            return False, None

    def get_service(self) -> Optional[object]:
        """Get the current Drive service object."""
        return self.service