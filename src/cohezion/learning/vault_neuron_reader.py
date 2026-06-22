"""VaultNeuron — SurrealDB persistence for task execution outcomes.

Every execution outcome from LoopCoordinator is persisted as a vault_neuron
record, building the experiential substrate for Mycelium skill synthesis.
"""

from __future__ import annotations

import logging
import time

try:
    import httpx as _httpx
except ImportError:  # pragma: no cover
    _httpx = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

_SURREAL_URL = "http://localhost:8001/sql"
_SURREAL_HEADERS = {
    "surreal-ns": "cohezion",
    "surreal-db": "main",
    "Content-Type": "text/plain",
    "Accept": "application/json",
}
_SURREAL_AUTH = ("root", "root")

_singleton: VaultNeuronWriter | None = None


class VaultNeuronWriter:
    """Persists task execution outcomes to SurrealDB vault_neuron table.

    Each record is one learned experience: task category, success/failure,
    token cost, silicon tier (node), model, quality score, and latency.
    The table self-provisions on first write (DEFINE TABLE IF NOT EXISTS).
    """

    def __init__(self) -> None:
        self._ddl_sent = False

    @classmethod
    def get_instance(cls) -> VaultNeuronWriter:
        global _singleton
        if _singleton is None:
            _singleton = cls()
        return _singleton

    @classmethod
    def reset_instance(cls) -> None:
        global _singleton
        _singleton = None

    def _ensure_table(self, client: object) -> None:
        if self._ddl_sent:
            return
        ddl = "DEFINE TABLE IF NOT EXISTS vault_neuron SCHEMALESS;"
        try:
            client.post(  # type: ignore[union-attr]
                _SURREAL_URL, headers=_SURREAL_HEADERS, auth=_SURREAL_AUTH, content=ddl
            )
        except Exception:
            return
        self._ddl_sent = True

    def write_outcome(
        self,
        *,
        task_id: str,
        category: str,
        success: bool,
        tokens: int,
        node: str,
        model: str,
        quality_score: float | None,
        elapsed_ms: float = 0.0,
    ) -> None:
        """Persist one execution outcome. Fail-open if SurrealDB is unreachable."""
        if _httpx is None:
            return
        try:
            client = _httpx.Client(timeout=2.0)
            self._ensure_table(client)
            ts = time.time()
            # Build a stable but unique record ID from task + timestamp millis
            safe_id = f"{task_id}_{int(ts * 1000)}".replace(":", "_").replace("/", "_")
            qs_field = str(quality_score) if quality_score is not None else "NONE"
            sql = (
                f"CREATE vault_neuron:`{safe_id}` SET "
                f'task_id = "{task_id}", '
                f'category = "{category}", '
                f"success = {str(success).lower()}, "
                f"tokens = {int(tokens)}, "
                f'node = "{node}", '
                f'model = "{model}", '
                f"quality_score = {qs_field}, "
                f"elapsed_ms = {float(elapsed_ms)}, "
                f"recorded_at = {ts};"
            )
            resp = client.post(
                _SURREAL_URL, headers=_SURREAL_HEADERS, auth=_SURREAL_AUTH, content=sql
            )
            if resp.status_code >= 400:
                logger.debug(
                    "VaultNeuronWriter.write_outcome HTTP %s: %s", resp.status_code, resp.text[:200]
                )
        except Exception as exc:  # noqa: BLE001
            logger.debug("VaultNeuronWriter.write_outcome skipped: %s", exc)

    def query_category_success_rate(self, category: str, limit: int = 100) -> float | None:
        """Recent success rate for a task category (0.0–1.0). None if no data."""
        if _httpx is None:
            return None
        try:
            sql = (
                f"SELECT success FROM vault_neuron "
                f'WHERE category = "{category}" '
                f"ORDER BY recorded_at DESC LIMIT {limit};"
            )
            resp = _httpx.post(
                _SURREAL_URL,
                headers=_SURREAL_HEADERS,
                auth=_SURREAL_AUTH,
                content=sql,
                timeout=2.0,
            )
            if resp.status_code >= 400:
                return None
            rows = resp.json()
            records = (rows[0].get("result") or []) if rows else []
            if not records:
                return None
            return sum(1 for r in records if r.get("success")) / len(records)
        except Exception:  # noqa: BLE001
            return None
