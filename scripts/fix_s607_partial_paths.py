#!/usr/bin/env python3
"""
S607 Partial Path Security Fixer
================================

Converts dangerous subprocess calls to use sys.executable.

Pattern: subprocess.run([sys.executable, ...]) -> subprocess.run([sys.executable, ...])
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def fix_s607_in_file(filepath: Path) -> tuple[int, list[str]]:
    """Fix S607 errors in a single file."""

    content = filepath.read_text()
    original = content
    fixes = []

    # Pattern 1: subprocess.run([sys.executable, ...])
    content, count1 = re.subn(
        r'(subprocess\.\w+\(\[)(["\'])python(["\'])', r"\1sys.executable", content
    )
    if count1 > 0:
        fixes.append(f"Replaced 'python' with sys.executable ({count1}x)")

    # Pattern 2: subprocess.call([sys.executable, ...])
    content, count2 = re.subn(
        r'(subprocess\.\w+\(\[)(["\'])python3(["\'])', r"\1sys.executable", content
    )
    if count2 > 0:
        fixes.append(f"Replaced 'python3' with sys.executable ({count2}x)")

    # Pattern 3: os.system("" + sys.executable + " ...")
    content, count3 = re.subn(
        r'(os\.system\(["\'])(python|python3)\s+', r'\1" + sys.executable + " ', content
    )
    if count3 > 0:
        fixes.append(f"Replaced os.system python calls ({count3}x)")

    # Check if sys is imported
    if (count1 + count2 + count3) > 0:
        if "import sys" not in content:
            # Add import sys at top
            lines = content.split("\n")
            import_idx = 0
            for i, line in enumerate(lines):
                if line.startswith("import ") or line.startswith("from "):
                    import_idx = i + 1
            lines.insert(import_idx, "import sys")
            content = "\n".join(lines)
            fixes.append("Added 'import sys'")

    if content != original:
        filepath.write_text(content)
        return (count1 + count2 + count3), fixes

    return 0, []


def find_and_fix_s607():
    """Find all S607 errors and fix them."""

    import subprocess

    # Get list of files with S607 errors
    result = subprocess.run(
        ["ruff", "check", ".", "--select", "S607", "--output-format", "json"],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print("No S607 errors found!")
        return

    try:
        import json

        errors = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("Failed to parse ruff output")
        return

    files_to_fix = set()
    for error in errors:
        filename = error.get("filename", "")
        if filename and not filename.startswith(".venv") and "__pycache__" not in filename:
            files_to_fix.add(filename)

    print(f"Found {len(files_to_fix)} files with S607 errors")

    total_fixes = 0
    for filepath_str in sorted(files_to_fix):
        filepath = Path(filepath_str)
        if not filepath.exists():
            continue

        count, fixes = fix_s607_in_file(filepath)
        if count > 0:
            print(f"✓ {filepath}: {count} fixes")
            for fix in fixes:
                print(f"  - {fix}")
            total_fixes += count

    print(f"\nTotal S607 fixes applied: {total_fixes}")


if __name__ == "__main__":
    find_and_fix_s607()
