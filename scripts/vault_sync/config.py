"""Configuration constants for vault sync."""

import os
import re
import signal
import sys
from pathlib import Path

VAULT_ROOT = Path(__file__).resolve().parent.parent.parent
CHECKPOINT = VAULT_ROOT / ".vault-journal" / "checkpoint.json"
SURREAL_PORT = int(os.environ.get("SURREAL_PORT", "8001"))

SURREAL_NS = "cohezion"
SURREAL_DB = "vault"
SURREAL_USER = "root"
SURREAL_PASS = "root"

CONTENT_DIRS = [
    "cortex", "sensory", "memory", "genome", "research",
    "prefrontal", "laboratory", "cerebellum", "benchmarks",
    "motor", "hippocampus", "thalamus", "missions", "retrospectives", "Agents",
    "dreaming", "songlines", "subconscious", "metabolism", "visual-cortex",
    "docs", "teleport", "assessments", "meta",
]

SKIP_DIRS = {
    ".git", ".obsidian", ".claude", ".worktrees", ".entire", ".locks",
    ".pytest_cache", ".ruff_cache", ".github", ".vault-journal",
    "node_modules", "htmlcov", "logs", "telemetry", "tools",
    "obsidian-plugin", "mcp-server", "src", "tests", "scripts",
    "attachments", "templates", "skills_index", "checkpoints",
    "archived", "learnings", "data", "skills",
}

DIR_TO_ASPECT = {
    "cortex": "knower", "sensory": "knower", "memory": "knower",
    "genome": "knower", "research": "knower",
    "prefrontal": "thinker", "laboratory": "thinker",
    "cerebellum": "thinker", "benchmarks": "thinker",
    "motor": "doer", "hippocampus": "doer", "thalamus": "doer",
    "missions": "doer", "retrospectives": "doer", "Agents": "doer",
    "dreaming": "connective", "songlines": "connective",
    "subconscious": "connective", "metabolism": "connective",
    "visual-cortex": "connective", "docs": "connective",
    "meta": "connective", "assessments": "connective",
    "teleport": "connective",
}

WIKI_LINK_RE = re.compile(r"\[\[([^\]|#]+?)(?:[|#][^\]]*?)?\]\]")

# inotify event masks
IN_CLOSE_WRITE = 0x00000008
IN_MOVED_FROM = 0x00000040
IN_MOVED_TO = 0x00000080
IN_DELETE = 0x00000200
IN_CREATE = 0x00000100
IN_ISDIR = 0x40000000

DEBOUNCE_SECS = 0.5

alive = True


def stop_handler(signum, frame):
    global alive
    alive = False
    print("\nStopping vault-sync...", file=sys.stderr)


signal.signal(signal.SIGINT, stop_handler)
signal.signal(signal.SIGTERM, stop_handler)
