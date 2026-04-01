#!/usr/bin/env python3
"""
Monitor script for NVIDIA Nemotron Model Reasoning Challenge training progress.
"""

import asyncio
import os
from datetime import datetime

from cohezion.integrations.kaggle_api import KaggleAPI


async def check_notebook_status(notebook_id):
    username = os.getenv("KAGGLE_USERNAME") or "manderson240"
    api = KaggleAPI(username=username, key=os.getenv("KAGGLE_API_TOKEN"))

    print(f"🔍 Checking status for user: {username}")

    status = await api.get_notebook_status(notebook_id)

    print("\n" + "=" * 60)
    print(f"📋 NOTEBOOK STATUS: {notebook_id}")
    print("=" * 60)
    print(f"📊 Status: {status}")
    print(f"🔗 URL: https://www.kaggle.com/{username}/{notebook_id}")

    # Try to get logs
    print("\n📝 Retrieving most recent logs...")
    logs = await api.get_notebook_output(notebook_id)
    if logs and logs != "No logs found.":
        print("-" * 60)
        # Print last 20 lines of logs
        log_lines = logs.split("\n")
        for line in log_lines[-20:]:
            print(line)
        print("-" * 60)
    else:
        print("📝 No output logs available yet")

    print(f"\n⏰ Checked at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    print("\n💡 NEXT STEPS:")
    if status == "KernelWorkerStatus.RUNNING":
        print("  ⏳ Training in progress. Wait for completion.")
    elif status == "KernelWorkerStatus.COMPLETE":
        print("  ✅ Training complete! Run retrieve_nemotron_adapter.py to get weights.")
    elif status == "KernelWorkerStatus.ERROR":
        print("  ❌ Training failed. Check the full logs for debugging.")
    else:
        print("  ❓ Status unknown - check manually on Kaggle")

    print("  📊 Final: Submit adapter and check leaderboard position")
    print("-" * 50)

    return status


async def main():
    print("🚀 NEMOTRON TRAINING MONITOR")
    print("=" * 50)

    # Check all notebooks
    notebooks = [
        "nemotron-lora-blackwell-v14",
        "nemotron-lora-blackwell-v13",
        "nemotron-lora-baseline",
        "nemotron-lora-g4-v10",
        "nemotron-lora-g4-v7-manderson240",
        "nemotron-lora-g4-v6-manderson240",
        "nemotron-lora-g4-v5-manderson240",
        "nemotron-lora-g4-v4-manderson240",
        "nemotron-lora-g4-v3-manderson240",
        "nemotron-lora-g4-v2-manderson240",
        "nemotron-lora-g4-manderson240",
        "nemotron-lora-baseline-improved-manderson240",
        "nemotron-lora-baseline-manderson240",
    ]

    results = {}
    for notebook in notebooks:
        print(f"\n📋 Checking {notebook}")
        status = await check_notebook_status(notebook)
        results[notebook] = status

    print("\n📊 SUMMARY:")
    print("=" * 50)
    for notebook, status in results.items():
        status_display = status if status else "UNKNOWN"
        print(f"  {notebook}: {status_display}")


if __name__ == "__main__":
    asyncio.run(main())
