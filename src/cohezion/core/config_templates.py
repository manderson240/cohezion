"""
Adaptive Configuration Template Engine for Cohezion.

Generates and manages configuration templates that adapt based on
the skill registry, hardware profile, local model roster, and
session state. Supports Claude <-> Gemini agent handoff manifests.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_REGISTRY_PATH = _PROJECT_ROOT / "src" / "cohezion" / "registry" / "skill_registry.json"

# Default model parameters per task type (aligned with LocalExpertRouter elite roster)
_TASK_DEFAULTS: dict[str, dict[str, Any]] = {
    "general": {"model": "gpt-oss-256k:latest", "temperature": 0.7, "max_tokens": 512},
    "coding": {"model": "qwen3-coder-next:latest", "temperature": 0.3, "max_tokens": 1024},
    "analysis": {"model": "phi4-256k:latest", "temperature": 0.5, "max_tokens": 768},
    "creative": {"model": "gpt-oss-256k:latest", "temperature": 0.9, "max_tokens": 512},
    "critique": {"model": "phi4-256k:latest", "temperature": 0.4, "max_tokens": 768},
    "synthesis": {"model": "qwen3-coder-next:latest", "temperature": 0.5, "max_tokens": 1024},
    "vision": {"model": "glm-ocr:latest", "temperature": 0.5, "max_tokens": 512},
    "routing": {"model": "phi4-256k:latest", "temperature": 0.3, "max_tokens": 256},
    "reasoning": {"model": "phi4-256k:latest", "temperature": 0.5, "max_tokens": 768},
}

# Named configuration templates
_TEMPLATES: dict[str, dict[str, Any]] = {
    "fast": {"model": "gemma3-4b-256k:latest", "temperature": 0.5, "max_tokens": 256},
    "balanced": {"model": "phi4-256k:latest", "temperature": 0.7, "max_tokens": 512},
    "quality": {"model": "qwen3-coder-next:q8_0", "temperature": 0.4, "max_tokens": 1024},
    "large_context": {
        "model": "qwen3-coder-256k:latest",
        "temperature": 0.5,
        "max_tokens": 1024,
    },
}


class ConfigTemplateManager:
    """Adaptive configuration template engine for Cohezion.

    Generates and manages configuration templates that adapt based on:
    - Available skills in the registry
    - Current hardware profile
    - Active agent roster
    - Session state and handoff requirements

    Parameters
    ----------
    registry_path : Path | None
        Path to skill_registry.json.  Defaults to the project's
        ``src/cohezion/registry/skill_registry.json``.
    """

    def __init__(self, registry_path: Path | None = None) -> None:
        self._registry_path = registry_path or _REGISTRY_PATH
        self._registry: dict[str, Any] = {}
        self._session_start = datetime.now(UTC).isoformat()
        self._generated_configs: list[dict[str, Any]] = []
        self._load_registry()

    def _load_registry(self) -> None:
        """Load the skill registry from disk."""
        if self._registry_path.exists():
            try:
                self._registry = json.loads(self._registry_path.read_text())
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to load skill registry: %s", exc)
                self._registry = {}
        else:
            logger.info("No skill registry at %s; starting empty", self._registry_path)
            self._registry = {}

    def generate_agent_config(
        self,
        agent_name: str,
        task_type: str = "general",
    ) -> dict[str, Any]:
        """Generate an adaptive config for an agent based on its task.

        Parameters
        ----------
        agent_name : str
            Identifier for the agent (e.g. ``"scout"``, ``"strategist"``).
        task_type : str
            One of the recognised task types (general, coding, analysis,
            creative, critique, synthesis, vision).

        Returns
        -------
        dict
            Configuration dict with model, temperature, max_tokens, and
            metadata about the agent and available skills.
        """
        defaults = _TASK_DEFAULTS.get(task_type, _TASK_DEFAULTS["general"])
        config: dict[str, Any] = {
            "agent_name": agent_name,
            "task_type": task_type,
            "model": defaults["model"],
            "temperature": defaults["temperature"],
            "max_tokens": defaults["max_tokens"],
            "stream": False,
            "available_skills": len(self._registry),
            "generated_at": datetime.now(UTC).isoformat(),
        }
        self._generated_configs.append(config)
        return config

    def generate_session_manifest(self) -> dict[str, Any]:
        """Generate a manifest of the current session state for handoff.

        Returns
        -------
        dict
            Manifest suitable for passing between AI agents during
            Claude <-> Gemini handoff.
        """
        skill_names = sorted(self._registry.keys())
        return {
            "session_start": self._session_start,
            "snapshot_at": datetime.now(UTC).isoformat(),
            "skills_loaded": len(skill_names),
            "skill_names": skill_names,
            "configs_generated": len(self._generated_configs),
            "agents_configured": [c["agent_name"] for c in self._generated_configs],
            "task_types_used": sorted(
                {c["task_type"] for c in self._generated_configs}
            ),
        }

    def update_all_timestamps(self) -> str:
        """Update timestamps across all config templates.

        Returns
        -------
        str
            The ISO-8601 timestamp applied.
        """
        now = datetime.now(UTC).isoformat()
        for config in self._generated_configs:
            config["generated_at"] = now
        logger.info(
            "Updated %d config timestamps to %s", len(self._generated_configs), now
        )
        return now

    def create_git_safe_handoff_commit(
        self,
        session_data: dict[str, Any] | None = None,
    ) -> str:
        """Create a commit message suitable for agent session handoff.

        Parameters
        ----------
        session_data : dict | None
            Optional session metrics (duration, velocity, features).

        Returns
        -------
        str
            Formatted commit message string.
        """
        manifest = self.generate_session_manifest()
        lines = [
            f"agent-handoff: {manifest['configs_generated']} configs, "
            f"{manifest['skills_loaded']} skills",
            "",
            f"Session start : {manifest['session_start']}",
            f"Snapshot      : {manifest['snapshot_at']}",
            f"Skills loaded : {manifest['skills_loaded']}",
            f"Agents        : {', '.join(manifest['agents_configured']) or 'none'}",
        ]
        if session_data:
            if "duration_hours" in session_data:
                lines.append(f"Duration      : {session_data['duration_hours']}h")
            if "major_features" in session_data:
                lines.append(
                    f"Features      : {', '.join(session_data['major_features'])}"
                )
        return "\n".join(lines)

    def get_template(self, template_name: str) -> dict[str, Any]:
        """Retrieve a named configuration template.

        Parameters
        ----------
        template_name : str
            One of ``fast``, ``balanced``, ``quality``, ``large_context``.

        Returns
        -------
        dict
            Configuration dict for the requested template.

        Raises
        ------
        KeyError
            If the template name is not recognised.
        """
        if template_name not in _TEMPLATES:
            available = ", ".join(sorted(_TEMPLATES))
            raise KeyError(
                f"Unknown template {template_name!r}. Available: {available}"
            )
        return {**_TEMPLATES[template_name], "template": template_name}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    manager = ConfigTemplateManager()

    # Generate configs for a few agents
    scout_cfg = manager.generate_agent_config("scout", "analysis")
    coder_cfg = manager.generate_agent_config("coder", "coding")
    print("Scout config:", json.dumps(scout_cfg, indent=2))
    print("Coder config:", json.dumps(coder_cfg, indent=2))

    # Session manifest
    manifest = manager.generate_session_manifest()
    print("Session manifest:", json.dumps(manifest, indent=2))

    # Handoff commit message
    session_data = {
        "duration_hours": 2.5,
        "major_features": [
            "adaptive_framework_config",
            "dynamic_timestamp_system",
            "git_safe_handoff_automation",
        ],
    }
    commit_msg = manager.create_git_safe_handoff_commit(session_data)
    print("Handoff commit message:")
    print(commit_msg)

    # Named template
    print("Balanced template:", manager.get_template("balanced"))

    print("\nAll imports successful")
