"""
TODO Scanner Script.

Scans the codebase for:
- TODO
- FIXME
- HACK
- "Next Steps" sections in Markdown

Outputs a formatted list of tasks.
"""

import os
import re
from pathlib import Path


def scan_codebase():
    base_path = Path(".")
    # Patterns to search for
    patterns = {
        "TODO": re.compile(r"(TODO|FIXME|HACK|XXX):\s*(.*)", re.IGNORECASE),
        "Next Step": re.compile(r"(?:##|\*\*|[\-\*])\s*(?:Proposed )?Next Steps?:?\s*(.*)", re.IGNORECASE),
        "Option": re.compile(r"(?:##|\*\*|[\-\*])\s*Option\s*(\d+|[A-Z])?:?\s*(.*)", re.IGNORECASE),
        "Future Work": re.compile(r"(?:##|\*\*|[\-\*])\s*Future Work:?\s*(.*)", re.IGNORECASE),
    }

    tasks = []

    # Exclude these dirs
    excludes = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        ".cohezion",
        "node_modules",
    }

    for root, dirs, files in os.walk(base_path):
        # Modify dirs in-place to exclude
        dirs[:] = [d for d in dirs if d not in excludes]

        for file in files:
            if not file.endswith((".py", ".md", ".json", ".js", ".ts")):
                continue

            path = Path(root) / file

            try:
                content = path.read_text(errors="ignore")
                lines = content.splitlines()

                for i, line in enumerate(lines):
                    line_strip = line.strip()
                    if not line_strip:
                        continue

                    # Check all patterns
                    for label, pattern in patterns.items():
                        match = pattern.search(line)
                        if match:
                            # If it's a header (starts with #), we might want to capture subsequent bullet points
                            # But for now, let's just capture the line itself if it has content
                            text = match.group(match.lastindex or 0).strip()
                            if len(text) > 3 and not text.startswith("#"):
                                tasks.append(f"- [ ] {label} ({path.name}:{i + 1}): {text}")

                            # Logic for "Next Steps" or "Option" headers to capture list items below could go here
                            # This is a simple improvement for now

            except Exception:
                pass

    return tasks


if __name__ == "__main__":
    found_tasks = scan_codebase()

    print("# Refined Codebase Tasks\n")
    for task in found_tasks:
        print(task)

    # Append to .cohezion/tasks.md logic would go here, but printing first for review
