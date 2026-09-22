"""VaultNeuron & VaultNeuronGraph — SurrealDB 3.x experiential substrate.

Every execution outcome is persisted as a vault_neuron / experiential_neuron record,
building the experiential substrate with HNSW vector indexing and Hebbian synaptic
plasticity for test-time prior conditioning and Mycelium skill synthesis.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any


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


@dataclass(frozen=True, slots=True)
class ExperientialPrior:
    """Prior experiential knowledge retrieved for test-time inference conditioning."""

    neuron_id: str
    category: str
    similarity: float
    success_rate: float
    action_ir: str
    quality_score: float
    delta_entropy: float = 0.0


class VaultNeuronGraph:
    """SurrealDB 3.x Experiential Hypergraph with HNSW Vector Search & Synaptic Plasticity."""

    def __init__(self, surreal_client: Any | None = None) -> None:
        if surreal_client is None:
            # Lazy: a module-level import of core.persistence closes an import cycle
            # (core -> ... -> compound.skill_refiner -> this module, still partially
            # initialised), which bound skill_refiner.VaultNeuronWriter to None and
            # silently pinned mgpo_weight() to 1.0 (regression from e9869f425).
            from cohezion.core.persistence.surreal_client import get_surreal_client

            surreal_client = get_surreal_client()
        self.surreal = surreal_client
        self._schema_initialized = False

    async def ensure_schema(self) -> None:
        """Provision SurrealDB 3.x Schemafull tables and HNSW vector index."""
        if self._schema_initialized:
            return
        ddl = """
        DEFINE TABLE IF NOT EXISTS experiential_neuron SCHEMAFULL;
        DEFINE FIELD IF NOT EXISTS task_id ON experiential_neuron TYPE string;
        DEFINE FIELD IF NOT EXISTS category ON experiential_neuron TYPE string;
        DEFINE FIELD IF NOT EXISTS success ON experiential_neuron TYPE bool;
        DEFINE FIELD IF NOT EXISTS tokens ON experiential_neuron TYPE int;
        DEFINE FIELD IF NOT EXISTS node ON experiential_neuron TYPE string;
        DEFINE FIELD IF NOT EXISTS model ON experiential_neuron TYPE string;
        DEFINE FIELD IF NOT EXISTS quality_score ON experiential_neuron TYPE float;
        DEFINE FIELD IF NOT EXISTS delta_entropy ON experiential_neuron TYPE float;
        DEFINE FIELD IF NOT EXISTS embedding ON experiential_neuron TYPE array<float, 256>;
        DEFINE FIELD IF NOT EXISTS recorded_at ON experiential_neuron TYPE datetime DEFAULT time::now();

        DEFINE INDEX IF NOT EXISTS neuron_vec_idx ON experiential_neuron
        FIELDS embedding HNSW DIST COSINE TYPE F32;

        DEFINE TABLE IF NOT EXISTS synapse SCHEMAFULL;
        DEFINE FIELD IF NOT EXISTS in ON synapse TYPE record<experiential_neuron>;
        DEFINE FIELD IF NOT EXISTS out ON synapse TYPE record<experiential_neuron>;
        DEFINE FIELD IF NOT EXISTS weight ON synapse TYPE float DEFAULT 1.0;
        DEFINE FIELD IF NOT EXISTS transitions ON synapse TYPE int DEFAULT 1;
        """
        try:
            await self.surreal.query(ddl)
            self._schema_initialized = True
        except Exception as exc:
            logger.debug("VaultNeuronGraph schema initialization skipped: %s", exc)

    async def record_neuron(
        self,
        *,
        task_id: str,
        category: str,
        success: bool,
        tokens: int,
        node: str,
        model: str,
        quality_score: float,
        delta_entropy: float,
        embedding: list[float],
        previous_neuron_id: str | None = None,
    ) -> str:
        """Persist an experiential neuron with 256D embedding and synaptic transitions."""
        await self.ensure_schema()
        safe_id = (
            f"neuron_{task_id}_{int(time.time() * 1000)}".replace(":", "_")
            .replace("-", "_")
            .replace("/", "_")
        )

        # Normalize or pad embedding to exactly 256 dimensions
        padded = list(embedding[:256])
        if len(padded) < 256:
            padded.extend([0.0] * (256 - len(padded)))

        neuron_data = {
            "task_id": task_id,
            "category": category,
            "success": bool(success),
            "tokens": int(tokens),
            "node": str(node),
            "model": str(model),
            "quality_score": float(quality_score),
            "delta_entropy": float(delta_entropy),
            "embedding": padded,
        }

        try:
            await self.surreal.query(
                "UPSERT type::record('experiential_neuron', $id) CONTENT $data;",
                {"id": safe_id, "data": neuron_data},
            )
        except Exception as exc:
            logger.debug("Failed to upsert experiential_neuron %s: %s", safe_id, exc)

        # Synaptic Plasticity: Hebbian connection with previous neuron in trajectory
        if previous_neuron_id:
            edge_query = """
            RELATE type::record('experiential_neuron', $prev) -> synapse -> type::record('experiential_neuron', $curr)
            SET weight = weight + $hebbian_delta, transitions = transitions + 1;
            """
            hebbian_delta = 0.1 if success else -0.05
            try:
                await self.surreal.query(
                    edge_query,
                    {
                        "prev": previous_neuron_id,
                        "curr": safe_id,
                        "hebbian_delta": hebbian_delta,
                    },
                )
            except Exception as exc:
                logger.debug("Synaptic update skipped: %s", exc)

        return safe_id

    async def retrieve_experiential_priors(
        self,
        query_embedding: list[float],
        category: str | None = None,
        k: int = 5,
    ) -> list[ExperientialPrior]:
        """Test-time compute prior conditioning: fetch nearest verified negentropic neurons."""
        await self.ensure_schema()
        padded = list(query_embedding[:256])
        if len(padded) < 256:
            padded.extend([0.0] * (256 - len(padded)))

        sql = """
        SELECT id, category, quality_score, delta_entropy,
               vector::similarity::cosine(embedding, $query_vec) AS sim
        FROM experiential_neuron
        WHERE success = true AND delta_entropy <= 0.0
        ORDER BY sim DESC
        LIMIT $k;
        """
        try:
            res = await self.surreal.query(sql, {"query_vec": padded, "k": k})
            records = res[0].get("result", []) if res else []
            return [
                ExperientialPrior(
                    neuron_id=str(r.get("id", "")),
                    category=str(r.get("category", "")),
                    similarity=float(r.get("sim", 0.0)),
                    success_rate=1.0,
                    action_ir="",
                    quality_score=float(r.get("quality_score", 0.0)),
                    delta_entropy=float(r.get("delta_entropy", 0.0)),
                )
                for r in records
            ]
        except Exception as exc:
            logger.debug("Experiential prior retrieval skipped: %s", exc)
            return []


class VaultNeuronWriter:
    """Persists task execution outcomes to SurrealDB vault_neuron table.

    Each record is one learned experience: task category, success/failure,
    token cost, silicon tier (node), model, quality score, and latency.
    The table self-provisions on first write (DEFINE TABLE IF NOT EXISTS).
    """

    def __init__(self) -> None:
        self._ddl_sent = False
        self._graph: VaultNeuronGraph | None = None

    @property
    def graph(self) -> VaultNeuronGraph:
        """Lazy-loaded VaultNeuronGraph."""
        if self._graph is None:
            self._graph = VaultNeuronGraph()
        return self._graph

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
        except Exception as exc:
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
        except Exception:
            return None
