#!/usr/bin/env python3
"""Quick compound engineering demo — dry-run cycle on 3 skills.

Demonstrates the full compound loop without requiring Ollama:
  PRIME skills -> expand -> execute (placeholder) -> retrospect -> report

Usage:
  uv run python scripts/compound_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from scripts.compound_driver import main


if __name__ == "__main__":
    main(["--skills", "3", "--dry-run", "--threshold", "0.0"])
