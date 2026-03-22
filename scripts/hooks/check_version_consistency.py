#!/usr/bin/env python3
"""Pre-commit hook: verify version strings match across pyproject.toml and package.json."""

import json
import re
import sys
from pathlib import Path


def get_pyproject_version() -> str | None:
    path = Path("pyproject.toml")
    if not path.exists():
        return None
    for line in path.read_text().splitlines():
        m = re.match(r'^version\s*=\s*"([^"]+)"', line)
        if m:
            return m.group(1)
    return None


def get_package_json_version(pkg_path: str) -> str | None:
    path = Path(pkg_path)
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return data.get("version")


def main() -> int:
    expected = get_pyproject_version()
    if not expected:
        print("WARNING: Could not read version from pyproject.toml")
        return 0

    pkg_paths = ["src/web/anima_dashboard/package.json"]
    errors = 0

    for pkg_path in pkg_paths:
        ver = get_package_json_version(pkg_path)
        if ver and ver != expected:
            print(f"ERROR: {pkg_path} version ({ver}) != pyproject.toml ({expected})")
            errors += 1

    if errors == 0:
        print(f"Versions consistent: {expected}")
    return errors


if __name__ == "__main__":
    sys.exit(main())
