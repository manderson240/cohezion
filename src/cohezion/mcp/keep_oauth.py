"""
Google Keep OAuth Setup.

Uses Google's official OAuth flow for Keep access.
Run this script in browser to authenticate.
"""

import json
import os
from pathlib import Path

# OAuth credentials - you'll need to create these in Google Cloud Console
# 1. Go to https://console.cloud.google.com/apis/credentials
# 2. Create OAuth 2.0 Client ID (Desktop app)
# 3. Download JSON and save as .cohezion/google_oauth.json

SCOPES = [
    'https://www.googleapis.com/auth/keep',
    'https://www.googleapis.com/auth/keep.readonly',
]

TOKEN_PATH = Path('.cohezion/keep_token.json')
CREDS_PATH = Path('.cohezion/google_oauth.json')


def setup_oauth():
    """Run OAuth flow for Google Keep."""
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
    except ImportError:
        print("Installing required packages...")
        import subprocess
        subprocess.run(['uv', 'add', 'google-auth-oauthlib', 'google-api-python-client'])
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
    
    creds = None
    
    # Check for existing token
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    
    # Refresh or get new token
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing token...")
            creds.refresh(Request())
        else:
            if not CREDS_PATH.exists():
                print(f"""
OAuth Setup Required!

1. Go to https://console.cloud.google.com/apis/credentials
2. Create a new project (or use existing)
3. Enable the Google Keep API
4. Create OAuth 2.0 Client ID (Desktop app type)
5. Download the JSON credentials
6. Save as: {CREDS_PATH}
7. Run this script again

Note: The Google Keep API is only available for Google Workspace accounts,
not personal Gmail accounts. For personal accounts, use the local file queue.
""")
                return None
            
            print("Starting OAuth flow... A browser window will open.")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDS_PATH), SCOPES
            )
            creds = flow.run_local_server(port=0)
        
        # Save token
        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(TOKEN_PATH, 'w') as f:
            f.write(creds.to_json())
        print(f"Token saved to {TOKEN_PATH}")
    
    print("✅ OAuth setup complete!")
    return creds


def test_keep_api(creds):
    """Test Keep API access."""
    try:
        from googleapiclient.discovery import build
        
        service = build('keep', 'v1', credentials=creds)
        notes = service.notes().list().execute()
        print(f"Found {len(notes.get('notes', []))} notes")
        return True
    except Exception as e:
        print(f"Keep API error: {e}")
        print("\nNote: Google Keep API requires a Google Workspace account.")
        print("For personal Gmail, use the local file queue at .cohezion/tasks.md")
        return False


if __name__ == "__main__":
    creds = setup_oauth()
    if creds:
        test_keep_api(creds)
