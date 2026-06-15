"""Band API client — the coordination backbone.

All agent state, task handoffs, and artifacts flow through this client.
Band is the active coordination layer: agents post artifacts here and read
artifacts posted by upstream agents. No direct agent-to-agent communication.

Supports two modes:
  - Live: real Band API calls (set BAND_API_KEY env var)
  - Local simulation: in-process dict with file persistence (for demos/testing)
"""

import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import requests


BAND_API_BASE = os.getenv("BAND_API_BASE", "https://api.band.ai")


@dataclass
class BandMessage:
    """Structured artifact posted to a Band channel."""

    agent_id: str
    artifact_type: str  # "plan", "enriched_context", "implementation", "review"
    content: dict
    channel_id: str
    timestamp: float = field(default_factory=time.time)
    message_id: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "BandMessage":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class BandClient:
    """Band coordination client.

    Wraps Band's HTTP API for artifact-based agent coordination.
    Falls back to local file simulation when BAND_API_KEY is not set,
    making it fully functional for demos without Band credentials.

    Usage:
        band = BandClient()

        # Post an artifact (any agent)
        band.post_artifact("cohezion-orchestrator", "plan", {"phases": [...]})

        # Read latest artifact of a type (downstream agent)
        plan = band.get_artifact("plan")

        # Get full channel history
        history = band.get_channel_history()
    """

    _SIM_FILE = Path.home() / ".cohezion" / "band_sim_state.json"

    def __init__(self):
        self.api_key = os.getenv("BAND_API_KEY")
        self.workspace_id = os.getenv("BAND_WORKSPACE_ID", "cohezion-hackathon")
        self.channel_id = os.getenv("BAND_CHANNEL_ID", "enterprise-pipeline")
        self._local_state: dict[str, Any] = {}
        self._history: list[dict] = []
        self._mode = "live" if self.api_key else "local"

        if self._mode == "local":
            self._load_sim_state()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def post_artifact(self, agent_id: str, artifact_type: str, content: dict) -> bool:
        """Post an artifact to the Band channel.

        Args:
            agent_id: ID of the posting agent (e.g. "cohezion-orchestrator")
            artifact_type: Semantic type — "plan", "enriched_context", "implementation"
            content: The artifact payload (arbitrary dict, will be JSON-serialized)

        Returns:
            True on success, False on failure.
        """
        msg = BandMessage(
            agent_id=agent_id,
            artifact_type=artifact_type,
            content=content,
            channel_id=self.channel_id,
        )

        if self._mode == "live":
            return self._api_post(msg)
        else:
            return self._sim_post(msg)

    def get_artifact(self, artifact_type: str) -> dict | None:
        """Get the most recent artifact of the given type from the channel.

        Args:
            artifact_type: Type to fetch — "plan", "enriched_context", "implementation"

        Returns:
            The artifact content dict, or None if not yet posted.
        """
        if self._mode == "live":
            return self._api_get(artifact_type)
        else:
            return self._sim_get(artifact_type)

    def get_channel_history(self) -> list[dict]:
        """Return full channel history (all posted artifacts, in order)."""
        if self._mode == "live":
            return self._api_history()
        else:
            return list(self._history)

    def clear_channel(self) -> None:
        """Clear channel state (useful between demo runs)."""
        self._local_state = {}
        self._history = []
        self._persist_sim_state()

    @property
    def mode(self) -> str:
        """'live' (Band API) or 'local' (simulation)."""
        return self._mode

    # ------------------------------------------------------------------
    # Live API implementation
    # ------------------------------------------------------------------

    def _api_post(self, msg: BandMessage) -> bool:
        """POST artifact to Band channel via HTTP API."""
        url = f"{BAND_API_BASE}/v1/workspaces/{self.workspace_id}/channels/{self.channel_id}/artifacts"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "agent_id": msg.agent_id,
            "artifact_type": msg.artifact_type,
            "content": msg.content,
            "timestamp": msg.timestamp,
        }
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=15)
            resp.raise_for_status()
            return True
        except requests.RequestException as exc:
            print(f"[Band:error] POST failed: {exc}")
            return False

    def _api_get(self, artifact_type: str) -> dict | None:
        """GET latest artifact of type from Band channel."""
        url = (
            f"{BAND_API_BASE}/v1/workspaces/{self.workspace_id}"
            f"/channels/{self.channel_id}/artifacts/latest"
        )
        headers = {"Authorization": f"Bearer {self.api_key}"}
        params = {"artifact_type": artifact_type}
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return data.get("content")
        except requests.RequestException as exc:
            print(f"[Band:error] GET failed: {exc}")
            return None

    def _api_history(self) -> list[dict]:
        """GET full channel artifact history from Band API."""
        url = (
            f"{BAND_API_BASE}/v1/workspaces/{self.workspace_id}"
            f"/channels/{self.channel_id}/artifacts"
        )
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            return resp.json().get("artifacts", [])
        except requests.RequestException as exc:
            print(f"[Band:error] history GET failed: {exc}")
            return []

    # ------------------------------------------------------------------
    # Local simulation
    # ------------------------------------------------------------------

    def _sim_post(self, msg: BandMessage) -> bool:
        """Post to in-memory state + file persistence."""
        record = msg.to_dict()
        self._local_state[msg.artifact_type] = record
        self._history.append(record)
        self._persist_sim_state()
        print(
            f"  [Band:local] {msg.agent_id} → posted '{msg.artifact_type}' "
            f"to #{self.channel_id}"
        )
        return True

    def _sim_get(self, artifact_type: str) -> dict | None:
        """Read from in-memory state."""
        record = self._local_state.get(artifact_type)
        if record:
            return record.get("content")
        return None

    def _load_sim_state(self) -> None:
        """Load persisted simulation state from disk."""
        if self._SIM_FILE.exists():
            try:
                data = json.loads(self._SIM_FILE.read_text())
                self._local_state = data.get("state", {})
                self._history = data.get("history", [])
            except (json.JSONDecodeError, KeyError):
                pass

    def _persist_sim_state(self) -> None:
        """Persist simulation state to disk for cross-process visibility."""
        self._SIM_FILE.parent.mkdir(parents=True, exist_ok=True)
        self._SIM_FILE.write_text(
            json.dumps({"state": self._local_state, "history": self._history}, indent=2)
        )
