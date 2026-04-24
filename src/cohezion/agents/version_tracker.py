"""Version tracker for generated agents.

Tracks skill version to generated agent version mapping in
``agents/generated/versions.json`` to detect stale agents that
need regeneration after skill refinement.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)

_VERSIONS_PATH = Path("src/cohezion/agents/generated/versions.json")


class VersionTracker:
    """Track generated agent versions against source skill versions.

    Parameters
    ----------
    versions_path : Path | None
        Override path to the versions JSON file.
    """

    def __init__(self, versions_path: Path | None = None) -> None:
        self.versions_path = versions_path or _VERSIONS_PATH

    def record_generation(
        self,
        skill_name: str,
        version: str,
        agent_path: str,
    ) -> None:
        """Record that an agent was generated for a skill version.

        Parameters
        ----------
        skill_name : str
            PRIME skill identifier.
        version : str
            Skill version at time of generation.
        agent_path : str
            Path to the generated agent file.
        """
        data = self._read()
        data[skill_name] = {
            "version": version,
            "agent_path": agent_path,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        self._write(data)
        logger.debug(
            "Recorded generation: %s v%s -> %s",
            skill_name,
            version,
            agent_path,
        )

    def needs_regeneration(self, skill_name: str, current_version: str) -> bool:
        """Check if an agent is stale and needs regeneration.

        Parameters
        ----------
        skill_name : str
            PRIME skill identifier.
        current_version : str
            Current version from the skill ``.md`` file.

        Returns
        -------
        bool
            ``True`` if the agent was generated from an older version.
        """
        entry = self.get_version(skill_name)
        if entry is None:
            return True
        return bool(entry.get("version", "") != current_version)

    def get_all_versions(self) -> dict[str, Any]:
        """Return the full version map.

        Returns
        -------
        dict[str, Any]
            Mapping of skill name to version info.
        """
        return self._read()

    def get_version(self, skill_name: str) -> dict[str, Any] | None:
        """Get version info for a specific skill.

        Parameters
        ----------
        skill_name : str
            PRIME skill identifier.

        Returns
        -------
        dict[str, Any] | None
            Version info dict if found, else ``None``.
        """
        data = self._read()
        result = data.get(skill_name)
        return dict(result) if isinstance(result, dict) else None

    def _read(self) -> dict[str, Any]:
        """Read the versions file with optional file locking."""
        try:
            from cohezion.concurrency.file_lock import LockedFileOperation

            with LockedFileOperation(self.versions_path) as locked:
                try:
                    data = locked.read_json(default={})
                    return dict(data) if isinstance(data, dict) else {}
                except json.JSONDecodeError:
                    logger.warning("Corrupt versions file: %s", self.versions_path)
                    return {}
        except ImportError:
            if not self.versions_path.exists():
                return {}
            try:
                text = self.versions_path.read_text(encoding="utf-8").strip()
                if not text:
                    return {}
                data = json.loads(text)
                return dict(data) if isinstance(data, dict) else {}
            except (json.JSONDecodeError, OSError):
                logger.warning("Could not read versions file: %s", self.versions_path)
                return {}

    def _write(self, data: dict[str, Any]) -> None:
        """Write the versions file with optional file locking."""
        try:
            from cohezion.concurrency.file_lock import LockedFileOperation

            with LockedFileOperation(self.versions_path) as locked:
                locked.write_json(data)
        except ImportError:
            self.versions_path.parent.mkdir(parents=True, exist_ok=True)
            self.versions_path.write_text(
                json.dumps(data, indent=2) + "\n",
                encoding="utf-8",
            )
