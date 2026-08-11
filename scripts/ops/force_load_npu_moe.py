#!/usr/bin/env python3
"""
Explicit NPU MoE Model Loader & Fleet Lock Controller
=====================================================
Acquires `fleet_lock:modelload`, unloads any active model from Lemonade,
loads `qwen3.6-moe-35b-a3b-FLM` explicitly on the AMD XDNA2 NPU (`recipe: flm`),
and waits for readiness before releasing lock.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "src"))

from cohezion.researcher.daily_researcher import FleetLock

LEMONADE_BASE = "http://localhost:13305"


def check_loaded_models() -> list[str]:
    req = urllib.request.Request(f"{LEMONADE_BASE}/v1/models")
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            res = json.loads(r.read().decode())
            return [m["id"] for m in res.get("data", [])]
    except Exception:
        return []


def unload_active_models():
    print("🧹 Unloading active Lemonade models...")
    req = urllib.request.Request(
        f"{LEMONADE_BASE}/api/v1/unload",
        data=b"{}",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            print("  ✓ Unload request sent:", r.status)
    except Exception as e:
        print("  ! Unload note:", e)


async def load_npu_moe_model(model_name: str = "qwen3.6-moe-35b-a3b-FLM") -> bool:
    fleet_lock = FleetLock()
    async with fleet_lock.acquire("modelload", timeout=60.0):
        print(f"🔒 Fleet lock acquired. Preparing to load `{model_name}`...")

        unload_active_models()
        time.sleep(2)

        print(f"⚡ Dispatching load request for `{model_name}` to Lemonade...")
        payload = {"model": model_name}
        req = urllib.request.Request(
            f"{LEMONADE_BASE}/api/v1/load",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                res = json.loads(r.read().decode())
                print("  ✓ Load response:", res)
        except Exception as e:
            print("  ! Load API call returned:", e)

        print("⏳ Waiting for model readiness in `/v1/models`...")
        for attempt in range(20):
            models = check_loaded_models()
            print(f"  • Active models ({attempt+1}/20): {models}")
            if model_name in models:
                print(f"🎉 `{model_name}` is FULLY LOADED AND READY on NPU!")
                return True
            time.sleep(3)

        return False


def main():
    print("=== Cohezion Fleet Lock & NPU MoE Dedicated Loader ===")
    success = asyncio.run(load_npu_moe_model("qwen3.6-moe-35b-a3b-FLM"))
    if not success:
        print("❌ Failed to verify model readiness within timeout.")
        sys.exit(1)


if __name__ == "__main__":
    main()
