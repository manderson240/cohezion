"""Centralized inference configuration.

Single source of truth for the Lemonade inference endpoint. All Lemonade callers
should import LEMONADE_BASE_URL from here instead of hard-coding a port.

Override for the whole stack:
    export LEMONADE_BASE_URL="http://other-host:8080"
"""

from __future__ import annotations

import os

LEMONADE_BASE_URL: str = os.environ.get("LEMONADE_BASE_URL", "http://localhost:13305")
