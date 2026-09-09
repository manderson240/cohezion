#!/usr/bin/env python3
import os
from pathlib import Path

env_file = Path(".env")
api_key = os.environ.get("BLUEQUBIT_API_KEY")

print("Checking BlueQubit API Key status:")
if api_key:
    print(f"✓ BLUEQUBIT_API_KEY found in environment (prefix: {api_key[:6]}...)")
else:
    print("❌ BLUEQUBIT_API_KEY not found in environment.")

if env_file.exists():
    content = env_file.read_text()
    if "BLUEQUBIT" in content:
        print("✓ BLUEQUBIT entry found in .env file")
    else:
        print("ℹ️ No BLUEQUBIT entry in .env yet.")
else:
    print("ℹ️ No .env file present.")
