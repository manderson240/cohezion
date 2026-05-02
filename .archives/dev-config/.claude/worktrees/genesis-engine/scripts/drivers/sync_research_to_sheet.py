#!/usr/bin/env python3
"""
Sync Research to Sheet
Updates the 'Cohezion_Research' Google Sheet with findings for Rows 214-223.
"""

import logging

import gspread


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SheetSync")

import json
import os

from dotenv import load_dotenv
from google.oauth2.credentials import Credentials


# Load environment variables
load_dotenv("/home/mike-anderson/dev/cohezion/.env")

# Scopes are required for gspread
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_NAME = "Cohezion_Research"


def get_creds():
    try:
        # Load Secure Token from Environment
        token_json = os.getenv("GOOGLE_SHEETS_TOKEN_JSON")
        if not token_json:
            logger.error("❌ GOOGLE_SHEETS_TOKEN_JSON not found in .env")
            return None

        logger.info("Loading credentials from secure .env...")
        info = json.loads(token_json)

        # Helper to convert JSON dict to Credentials object
        creds = Credentials.from_authorized_user_info(info, scopes=SCOPES)
        return creds

    except Exception as e:
        logger.error(f"Auth load failed: {e}")
        return None


# Data to sync (Row Index is 1-based in Sheet)
# Based on previous extraction, last 10 rows were 214-223.
UPDATES = {
    214: {
        "Status": "Abstracted",
        "Key Abstractions": "12D [eff:1.0, sta:0.9, b:0.8], Model Selection, Roster Strategy",
        "Integration": "Validates model_manager.py dynamic routing.",
    },
    215: {
        "Status": "Abstracted",
        "Key Abstractions": "12D [con:0.95, res:0.9, b:11], Quantum Error Correction, Swarm Reliability",
        "Integration": "Metaphor for 12-Agent Consensus.",
    },
    216: {
        "Status": "Abstracted",
        "Key Abstractions": "12D [nov:0.98, fric:0.85, b:7], Plasma Physics, High-I Interaction",
        "Integration": "Supports 'Strong Interaction' theory.",
    },
    217: {
        "Status": "Abstracted",
        "Key Abstractions": "12D [nov:0.95, eff:0.92, b:7], Propulsion Physics, Electromagnetic Drive",
        "Integration": "Metaphor for 'Plasma-Driven Execution'.",
    },
    218: {
        "Status": "Abstracted",
        "Key Abstractions": "12D [sta:0.9, com:0.85, b:3], Paleolithic Math, Pattern Recognition",
        "Integration": "Validates 'Geometric Logic' (Metatron's Cube).",
    },
    219: {
        "Status": "Abstracted",
        "Key Abstractions": "12D [nov:0.98, flo:0.95, b:10], Biological Dynamics, Swarm Movement",
        "Integration": "'Negative Viscosity' = Swarms moving faster against resistance.",
    },
    220: {
        "Status": "Abstracted",
        "Key Abstractions": "12D [com:0.92, con:0.9, b:1], Latent Space Topology, Stratified Learning",
        "Integration": "Direct validation of FLUME's 'Manifold Stratification'.",
    },
    221: {
        "Status": "Abstracted",
        "Key Abstractions": "12D [eff:0.9, sta:0.8, b:5], Hardware Bottlenecks, Memory-Centric Design",
        "Integration": "Reinforces ResourceMonitor focus on VRAM/RAM bandwidth.",
    },
    222: {
        "Status": "Abstracted",
        "Key Abstractions": "12D [eff:1.0, sta:0.95, b:2], Performance Optimization, Native Tooling",
        "Integration": "Suggests migrating markdown rendering to WASM/Native.",
    },
    223: {
        "Status": "Abstracted",
        "Key Abstractions": "12D [eff:1.0, nov:0.9, b:1], Agentic Modeling, Velocity",
        "Integration": "Benchmark for 'AnalystAgent' capabilities.",
    },
}


def sync():
    try:
        creds = get_creds()
        if not creds:
            logger.error("Could not obtain credentials.")
            return

        gc = gspread.authorize(creds)
        sh = gc.open(SHEET_NAME)
        ws = sh.sheet1

        # Column Indices (approximate based on standard layout, usually B=2, C=3, D=4)
        # We need to find the column headers to be safe, or assume.
        # Browser check showed: A: Link, B: Status, C: Key Abstractions, D: Integration
        headers = ws.row_values(1)
        try:
            col_status = headers.index("Status") + 1
            col_abs = headers.index("Key Abstractions") + 1
            col_int = headers.index("Integration") + 1
        except ValueError:
            logger.warning("Headers not found exactly, assuming B=Status, C=Abstractions, D=Integration")
            col_status = 2
            col_abs = 3
            col_int = 4

        logger.info(f"Columns determined: Status={col_status}, Abs={col_abs}, Int={col_int}")

        # Batch update logic or cell-by-cell
        for row_num, data in UPDATES.items():
            logger.info(f"Updating Row {row_num}...")
            # Update cells
            ws.update_cell(row_num, col_status, data["Status"])
            ws.update_cell(row_num, col_abs, data["Key Abstractions"])
            ws.update_cell(row_num, col_int, data["Integration"])

        logger.info("✅ Sync Complete.")

    except Exception as e:
        logger.error(f"Sync failed: {e}")


if __name__ == "__main__":
    sync()
