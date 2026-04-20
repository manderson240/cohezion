#!/usr/bin/env python3
"""
SheetCommandWatcher - Monitors 'Cohezion_Research' Google Sheet for new inputs.
Part of the 'Sheet-as-Control' Protocol (Learning 61).
"""

import json
import logging
import os
import time

import gspread
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials


# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [SHEET_WATCHER] - %(message)s")
logger = logging.getLogger("SheetWatcher")

# Configuration
SHEET_NAME = "Cohezion_Research"

# --- FREE TIER GUARDRAILS ---
# Google Sheets API Limit: 300 requests per minute per project.
# Safe Usage: 1 request every 5 minutes = 288 requests/day.
# This ensures we are <1% of the daily quota and avoids rate limits.
POLL_INTERVAL = 300  # seconds (5 min)

# Load environment variables
load_dotenv("/home/mike-anderson/dev/cohezion/.env")


def connect_to_sheet():
    """Authenticate and connect to the Google Sheet."""
    try:
        # Load Secure Token from Environment
        token_json = os.getenv("GOOGLE_SHEETS_TOKEN_JSON")
        if not token_json:
            logger.error("❌ GOOGLE_SHEETS_TOKEN_JSON not found in .env")
            return None

        info = json.loads(token_json)
        # Scopes are implicit in the token but good to be explicit if needed
        # Warning: For authorized_user, passing scopes to construction might trigger re-auth/errors
        # relying on the token's baked-in scopes is safer for this specific token type.
        creds = Credentials.from_authorized_user_info(info)

        gc = gspread.authorize(creds)
        sh = gc.open(SHEET_NAME)
        # Assuming the first sheet is the one we want
        worksheet = sh.sheet1
        return worksheet
    except Exception as e:
        logger.error(f"Failed to connect to sheet: {e}")
        return None


def check_for_new_items(worksheet):
    """Scan for rows with empty 'Status' column."""
    try:
        # Use get_all_values() to avoid DuplicateHeaderError
        rows = worksheet.get_all_values()

        if not rows:
            return []

        headers = rows[0]
        # Find column indices (fallback to B=Status, A=Link if not found)
        try:
            col_status = headers.index("Status")
            col_link = headers.index("Link")
        except ValueError:
            # Fallback: A=Link(0), B=Status(1)
            col_link = 0
            col_status = 1

        new_items = []
        # Iterate skipping header
        for i, row in enumerate(rows[1:], start=2):
            # Safe access
            status = row[col_status].strip() if len(row) > col_status else ""
            link = row[col_link].strip() if len(row) > col_link else ""

            if not status and link:
                logger.info(f"✨ NEW RESEARCH ITEM DETECTED: {link} (Row {i})")
                new_items.append({"row": i, "link": link})

        return new_items
    except Exception as e:
        logger.error(f"Error scanning sheet: {e}")
        return []


def main():
    logger.info("📡 SheetWatcher initialized. Watching 'Cohezion_Research'...")

    # Check for Env Var instead of File
    if not os.getenv("GOOGLE_SHEETS_TOKEN_JSON"):
        logger.error("❌ GOOGLE_SHEETS_TOKEN_JSON not found in .env")
        return

    while True:
        worksheet = connect_to_sheet()
        if worksheet:
            new_items = check_for_new_items(worksheet)
            if new_items:
                logger.info(f"Found {len(new_items)} new items. User notification triggered.")
                # Here we could integrate with the Immune System or specialized Agent
                # For now, we log visibly.
            else:
                logger.debug("No new items found.")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
