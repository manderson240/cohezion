"""
Heartbeat utility for background daemons.
"""

import json
import time
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Default heartbeat file location
HEARTBEAT_FILE = Path("data/system/heartbeats.json")

def update_heartbeat(daemon_name: str) -> None:
    """Updates the heartbeat timestamp for a given daemon."""
    try:
        HEARTBEAT_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        heartbeats = {}
        if HEARTBEAT_FILE.exists():
            try:
                with open(HEARTBEAT_FILE, "r") as f:
                    heartbeats = json.load(f)
            except json.JSONDecodeError:
                pass
        
        heartbeats[daemon_name] = time.time()
        
        with open(HEARTBEAT_FILE, "w") as f:
            json.dump(heartbeats, f, indent=2)
            
    except Exception as e:
        logger.error(f"Failed to update heartbeat for {daemon_name}: {e}")

def get_heartbeats() -> dict[str, float]:
    """Returns all current heartbeats."""
    if not HEARTBEAT_FILE.exists():
        return {}
    try:
        with open(HEARTBEAT_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}
