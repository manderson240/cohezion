"""UiPath Maestro Case Management Client.

Two modes:
  live  — UIPATH_ACCESS_TOKEN + UIPATH_URL set; hits Maestro REST API
  local — file-backed simulation at ~/.cohezion/uipath_sim_state.json

Case lifecycle state machine:
  OPEN → PLANNING → ANALYSIS → IMPLEMENTATION → COMPLETE
"""

import json
import os
import time
import uuid
from pathlib import Path
from typing import Optional

import requests


_SIM_STATE_PATH = Path.home() / ".cohezion" / "uipath_sim_state.json"


# ─── Local simulation ─────────────────────────────────────────────────────────

def _load_sim_state() -> dict:
    if _SIM_STATE_PATH.exists():
        try:
            return json.loads(_SIM_STATE_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"cases": {}}


def _save_sim_state(state: dict) -> None:
    _SIM_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _SIM_STATE_PATH.write_text(json.dumps(state, indent=2, default=str))


# ─── UiPathMaestroClient ──────────────────────────────────────────────────────

class UiPathMaestroClient:
    """Client for UiPath Maestro Case Management.

    Connects to UiPath Automation Cloud when credentials are present,
    otherwise falls back to local file simulation with identical semantics.

    The local simulation persists state to ~/.cohezion/uipath_sim_state.json
    so cases survive across runs and the demo can be re-entered mid-flight.
    """

    _VALID_STATUSES = ("OPEN", "PLANNING", "ANALYSIS", "IMPLEMENTATION", "COMPLETE")

    def __init__(self) -> None:
        self._url = os.getenv("UIPATH_URL", "").rstrip("/")
        self._token = os.getenv("UIPATH_ACCESS_TOKEN", "")
        self._tenant = os.getenv("UIPATH_TENANT_NAME", "DefaultTenant")
        self._live = bool(self._url and self._token)

        if self._live:
            self._headers = {
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
                "X-UIPATH-TenantName": self._tenant,
            }

    @property
    def mode(self) -> str:
        return "live" if self._live else "local"

    # ------------------------------------------------------------------
    # Case lifecycle
    # ------------------------------------------------------------------

    def create_case(self, task: str) -> str:
        """Open a new Maestro case for the given task. Returns case_id."""
        case_id = f"case-{uuid.uuid4().hex[:8]}"
        entry = {
            "id": case_id,
            "task": task,
            "status": "OPEN",
            "artifacts": {},
            "history": [
                {"event": "CASE_OPENED", "status": "OPEN", "timestamp": time.time()}
            ],
        }
        if self._live:
            self._api_post("/cases", {"title": task[:200], "externalId": case_id, "status": "OPEN"})
        else:
            state = _load_sim_state()
            state["cases"][case_id] = entry
            _save_sim_state(state)
        print(f"  [UiPath:{self.mode}] Case created: #{case_id}")
        return case_id

    def update_case_status(self, case_id: str, status: str) -> None:
        """Transition case to a new status."""
        if status not in self._VALID_STATUSES:
            raise ValueError(f"Invalid status {status!r}. Must be one of {self._VALID_STATUSES}")
        event = {
            "event": f"STATUS_CHANGE → {status}",
            "status": status,
            "timestamp": time.time(),
        }
        if self._live:
            self._api_patch(f"/cases/{case_id}", {"status": status})
        else:
            state = _load_sim_state()
            if case_id not in state["cases"]:
                raise KeyError(f"Case {case_id} not found")
            state["cases"][case_id]["status"] = status
            state["cases"][case_id]["history"].append(event)
            _save_sim_state(state)
        print(f"  [UiPath:{self.mode}] Case #{case_id} → {status}")

    def post_artifact(self, case_id: str, artifact_type: str, data: dict) -> None:
        """Attach a typed artifact to the case (plan / enriched_context / implementation)."""
        entry = {
            "artifact_type": artifact_type,
            "data": data,
            "timestamp": time.time(),
        }
        history_event = {
            "event": f"ARTIFACT_POSTED:{artifact_type}",
            "artifact_type": artifact_type,
            "timestamp": time.time(),
        }
        if self._live:
            self._api_post(f"/cases/{case_id}/artifacts", {
                "type": artifact_type,
                "content": json.dumps(data, default=str),
            })
        else:
            state = _load_sim_state()
            if case_id not in state["cases"]:
                raise KeyError(f"Case {case_id} not found")
            state["cases"][case_id]["artifacts"][artifact_type] = entry
            state["cases"][case_id]["history"].append(history_event)
            _save_sim_state(state)
        print(f"  [UiPath:{self.mode}] Artifact '{artifact_type}' posted to case #{case_id}")

    def get_artifact(self, case_id: str, artifact_type: str) -> Optional[dict]:
        """Retrieve a typed artifact from the case. Returns None if not found."""
        if self._live:
            try:
                resp = self._api_get(f"/cases/{case_id}/artifacts?type={artifact_type}")
                items = resp.get("value", [])
                if items:
                    return json.loads(items[0].get("content", "{}"))
            except (requests.RequestException, json.JSONDecodeError, KeyError):
                return None
        else:
            state = _load_sim_state()
            case = state.get("cases", {}).get(case_id)
            if not case:
                return None
            entry = case.get("artifacts", {}).get(artifact_type)
            return entry.get("data") if entry else None

    def get_case(self, case_id: str) -> dict:
        """Return full case metadata."""
        if self._live:
            return self._api_get(f"/cases/{case_id}")
        state = _load_sim_state()
        return state.get("cases", {}).get(case_id, {})

    def get_case_history(self, case_id: str) -> list:
        """Return ordered event history for the case."""
        if self._live:
            resp = self._api_get(f"/cases/{case_id}/history")
            return resp.get("value", [])
        state = _load_sim_state()
        case = state.get("cases", {}).get(case_id, {})
        return case.get("history", [])

    def close_case(self, case_id: str, outcome: str = "SUCCESS") -> None:
        """Close the case with a final outcome."""
        self.update_case_status(case_id, "COMPLETE")
        if not self._live:
            state = _load_sim_state()
            if case_id in state["cases"]:
                state["cases"][case_id]["outcome"] = outcome
                state["cases"][case_id]["closed_at"] = time.time()
                state["cases"][case_id]["history"].append({
                    "event": f"CASE_CLOSED:{outcome}",
                    "status": "COMPLETE",
                    "timestamp": time.time(),
                })
                _save_sim_state(state)
        print(f"  [UiPath:{self.mode}] Case #{case_id} CLOSED ({outcome})")

    def clear_state(self) -> None:
        """Reset local simulation state (for demo re-runs)."""
        if not self._live and _SIM_STATE_PATH.exists():
            _SIM_STATE_PATH.write_text(json.dumps({"cases": {}}, indent=2))

    # ------------------------------------------------------------------
    # REST helpers (live mode only)
    # ------------------------------------------------------------------

    def _api_get(self, path: str) -> dict:
        resp = requests.get(
            f"{self._url}/orchestrator_/api/v2{path}",
            headers=self._headers,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    def _api_post(self, path: str, body: dict) -> dict:
        resp = requests.post(
            f"{self._url}/orchestrator_/api/v2{path}",
            headers=self._headers,
            json=body,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json() if resp.content else {}

    def _api_patch(self, path: str, body: dict) -> dict:
        resp = requests.patch(
            f"{self._url}/orchestrator_/api/v2{path}",
            headers=self._headers,
            json=body,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json() if resp.content else {}
