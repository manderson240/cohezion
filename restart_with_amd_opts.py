#!/usr/bin/env python3
"""Restart Lemonade server with AMD optimizations."""

import os

import requests


# Set AMD optimizations BEFORE starting server
os.environ["RADV_PERFTEST"] = "aco,gpl,rt,nggc"
os.environ["RADV_COOPERATIVE_MATRIX"] = "1"
os.environ["MESA_SHADER_CACHE_DISABLE"] = "0"
os.environ["MESA_SHADER_CACHE_MAX_SIZE"] = "4GB"
os.environ["HSA_OVERRIDE_GFX_VERSION"] = "11.0.0"
os.environ["HIP_VISIBLE_DEVICES"] = "0"

print("=" * 70)
print("RESTARTING LEMONADE SERVER WITH AMD OPTIMIZATIONS")
print("=" * 70)
print()

# Check current state
try:
    r = requests.get("http://localhost:8002/health", timeout=2)
    print(f"Server currently: {r.json().get('status', 'unknown')}")
    print("Server already running - optimization will take effect after restart")
    print("(Environment vars need to be set before server start)")
except:
    print("Server not responding - starting fresh...")

print()
print("Environment set:")
for k, v in os.environ.items():
    if "RADV" in k or "HIP" in k or "HSA" in k or "MESA" in k:
        print(f"  {k}={v}")

print()
print("To restart server, run:")
print("  python3 scripts/lemonade_amd_optimized_launcher.py gpu")
