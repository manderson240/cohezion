#!/usr/bin/env python3
"""Test Lemonade CLI Management & Local Substrate Interrogation.

Executes direct `lemonade` CLI commands to query server status, model metadata,
and hardware acceleration parameters.
"""

import subprocess
import time

def run_cmd(cmd: list[str]):
    print(f"▶ Running: {' '.join(cmd)}")
    t0 = time.perf_counter()
    res = subprocess.run(cmd, capture_output=True, text=True)
    dt = time.perf_counter() - t0
    print(f"  Exit code: {res.returncode} (Duration: {dt:.2f}s)")
    if res.stdout:
        print("  Stdout:\n" + "\n".join(["    " + line for line in res.stdout.strip().split("\n")[:10]]))
    if res.stderr:
        print("  Stderr:\n" + "\n".join(["    " + line for line in res.stderr.strip().split("\n")[:5]]))
    print()

def main():
    print("=" * 80)
    print("🍋 TESTING LEMONADE CLI INTEGRATION ON PORT 13305")
    print("=" * 80)

    # 1. Lemonade status / version
    run_cmd(["lemonade", "--version"])
    
    # 2. Show active models on port 13305
    run_cmd(["lemonade", "list", "--downloaded-only"])

    # 3. Model inspection
    run_cmd(["lemonade", "show", "Gemma-4-E4B-it-GGUF"])

    print("=" * 80)

if __name__ == "__main__":
    main()
