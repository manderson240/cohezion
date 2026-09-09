#!/usr/bin/env python3
"""Lemonade CLI Fleet Manager & Hardware Allocation Orchestrator.

Provides direct programmatic access to `/usr/bin/lemonade` CLI commands:
- `lemonade status`
- `lemonade list --downloaded`
- `lemonade load <model>` (under SystemWideFleetLock)
- `lemonade unload <model>`
- `lemonade pin <model>`
"""

import subprocess
import json
import logging
from typing import List, Dict, Any, Optional

from cohezion.reliability.system_wide_fleet_lock import SystemWideFleetLock
from cohezion.reliability.oom_guard import OOMGuard

logger = logging.getLogger(__name__)

class LemonadeFleetManager:
    """Manages Lemonade Server models and execution via the official CLI."""

    LEMONADE_BIN = "/usr/bin/lemonade"

    @classmethod
    def get_status(cls) -> str:
        """Returns the output of `lemonade status`."""
        res = subprocess.run([cls.LEMONADE_BIN, "status"], capture_output=True, text=True)
        return res.stdout.strip()

    @classmethod
    def list_downloaded_models(cls) -> List[str]:
        """Lists all downloaded models ready for immediate instantiation."""
        res = subprocess.run([cls.LEMONADE_BIN, "list", "--downloaded"], capture_output=True, text=True)
        lines = res.stdout.strip().split("\n")[3:] # skip header
        models = []
        for line in lines:
            parts = line.split()
            if parts and parts[0] != "----------------------------------------------------------------------------------------------------":
                models.append(parts[0])
        return models

    @classmethod
    def load_model(cls, model_name: str) -> bool:
        """Loads a model via `lemonade load` under SystemWideFleetLock."""
        lock = SystemWideFleetLock(resource_name="modelload")
        with lock.hold(timeout=45.0) as acquired:
            if not acquired:
                logger.error(f"Failed to acquire lock for loading {model_name}")
                return False
            
            mem = OOMGuard.get_memory_state()
            if not mem.is_safe:
                logger.warning(f"Memory unsafe for loading {model_name}: {mem.available_gb} GiB Avail")
                return False

            res = subprocess.run([cls.LEMONADE_BIN, "load", model_name], capture_output=True, text=True)
            return res.returncode == 0

    @classmethod
    def unload_model(cls, model_name: str) -> bool:
        """Unloads a model from Lemonade memory."""
        res = subprocess.run([cls.LEMONADE_BIN, "unload", model_name], capture_output=True, text=True)
        return res.returncode == 0

if __name__ == "__main__":
    print("=" * 80)
    print("🍋 LEMONADE CLI FLEET MANAGER AUDIT")
    print("=" * 80)
    print("Server Status:")
    print(LemonadeFleetManager.get_status())
    print("\nDownloaded Models:")
    for m in LemonadeFleetManager.list_downloaded_models():
        print(f"  • {m}")
    print("=" * 80)
