#!/usr/bin/env python3
"""Git hook or pre-flight check to block commits when code duplication exceeds threshold."""

import os
import subprocess
import sys


def main():
    if os.environ.get("JSCPD_GUARD_DISABLE") == "1":
        print("✓ jscpd duplication gate disabled via JSCPD_GUARD_DISABLE=1")
        return 0

    print("Running jscpd duplication gate check...")
    # Check if npx is available
    try:
        subprocess.run(
            ["npx", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
        )
    except Exception:
        print("⚠ npx command not found. Skipping duplication gate.")
        return 0

    # Run jscpd duplication scan
    cmd = ["npx", "-y", "jscpd", "src/cohezion", "--threshold", "5.0"]
    print(f"Executing: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print("\n❌ [FAIL] Code duplication exceeds allowed threshold (5.0%):")
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return 1

    print("✓ Duplication check passed cleanly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
