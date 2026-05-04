"""Filesystem path resolution and JSON loading helpers for the Cohezion MCP server.

These utilities are shared by every tool module so that registry locations
(skills, workflows, models, compound config) are computed in exactly one place.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any


def cohezion_root() -> str:
    """Return the absolute path to the Cohezion repo root (env-overridable)."""
    return os.environ.get("COHEZION_ROOT", "/home/mike-anderson/dev/cohezion")


def skill_registry_path() -> str:
    """Path to ``skill_registry.json`` (the canonical skill index)."""
    return cohezion_root() + "/src/cohezion/registry/skill_registry.json"


def workflow_registry_path() -> str:
    """Path to ``workflow_registry.json`` (the canonical workflow index)."""
    return cohezion_root() + "/src/cohezion/registry/workflow_registry.json"


def knowledge_graph_path() -> str:
    """Path to the knowledge-graph directory used by reliability tooling."""
    return cohezion_root() + "/src/cohezion/knowledge_graph"


def model_registry_path() -> str:
    """Path to the top-level ``model_registry.json``."""
    return cohezion_root() + "/model_registry.json"


def compound_config_path() -> str:
    """Path to the user-level ``compound_engineering.json`` settings file."""
    return "/home/mike-anderson/.config/opencode/compound_engineering.json"


def load_json(path: str) -> dict[str, Any]:
    """Load JSON from ``path``, stripping ``#`` and ``//`` comment lines.

    Returns ``{}`` for missing files or any decode/IO failure (with a stderr
    diagnostic). Designed for best-effort loading of optional registries.
    """
    try:
        if not os.path.exists(path):
            return {}
        with open(path) as f:
            content = f.read()
            # Simple comment stripping
            lines = content.splitlines()
            clean_lines = [ln for ln in lines if not ln.strip().startswith(("#", "//"))]
            return json.loads("\n".join(clean_lines))
    except (OSError, ValueError) as e:
        sys.stderr.write(f"Error loading {path}: {e}\n")
        return {}
