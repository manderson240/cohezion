"""SurrealDB-backed vector store for mem0 — unify memory onto the canonical engine.

mem0 2.0.4 ships 24 vector providers but NOT SurrealDB. This module adds one by
subclassing ``VectorStoreBase`` and registering it into mem0's three lookup points
(config map, injected config module, factory map). It lets mem0 persist its
embeddings into SurrealDB — the same multi-model engine Cohezion already uses for
bi-temporal records and the Entity-Relation knowledge graph — instead of a stray
embedded qdrant/SQLite. Search uses SurrealDB's native ``vector::similarity::cosine``.

Dependency-free transport: talks to SurrealDB over HTTP /sql via stdlib urllib, so
the provider adds no packages and can't fail to import under load.
"""

from __future__ import annotations

import base64
import json
import logging
import urllib.request
from typing import TYPE_CHECKING, Any

from mem0.vector_stores.base import VectorStoreBase
from pydantic import BaseModel


if TYPE_CHECKING:  # pragma: no cover - typing only
    from collections.abc import Sequence


logger = logging.getLogger(__name__)


class OutputData(BaseModel):
    """mem0's expected search/get result shape."""

    id: str | None = None
    score: float | None = None
    payload: dict | None = None


class SurrealVectorStore(VectorStoreBase):
    """mem0 vector store backed by SurrealDB (HTTP /sql, cosine similarity)."""

    def __init__(
        self,
        collection_name: str = "cohezion_memory",
        embedding_model_dims: int = 768,
        url: str = "http://localhost:8001/sql",
        namespace: str = "cohezion",
        database: str = "main",
        user: str = "root",
        password: str = "root",  # noqa: S107 - local SurrealDB dev default; override in prod
        **_: Any,
    ) -> None:
        self.collection_name = collection_name
        self.dims = embedding_model_dims
        self.url = url
        self.namespace = namespace
        self.database = database
        self._auth = base64.b64encode(f"{user}:{password}".encode()).decode()
        self.create_col(collection_name, embedding_model_dims, "cosine")

    # ── transport ────────────────────────────────────────────────────────────
    def _sql(self, query: str) -> list[dict]:
        req = urllib.request.Request(  # noqa: S310 - fixed localhost SurrealDB URL
            self.url,
            data=query.encode(),
            headers={
                "Accept": "application/json",
                "Content-Type": "text/plain",
                "surreal-ns": self.namespace,
                "surreal-db": self.database,
                "Authorization": f"Basic {self._auth}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            return json.loads(resp.read().decode())

    @staticmethod
    def _last_result(resp: list[dict]) -> list:
        if not resp:
            return []
        tail = resp[-1]
        res = tail.get("result", []) if isinstance(tail, dict) else []
        return res if isinstance(res, list) else [res]

    def _record(self, vid: str) -> str:
        """Backtick record reference `collection`:`id` (handles UUID hyphens)."""
        col = self.collection_name.replace("`", "")
        rid = str(vid).replace("`", "")
        return f"`{col}`:`{rid}`"

    def _where(self, filters: dict | None) -> str:
        if not filters:
            return ""
        clauses = [f"payload.{k} = {json.dumps(v)}" for k, v in filters.items()]
        return " WHERE " + " AND ".join(clauses)

    # ── VectorStoreBase contract ─────────────────────────────────────────────
    def create_col(self, name: str, vector_size: int, distance: str = "cosine") -> None:
        self._sql(f"DEFINE TABLE IF NOT EXISTS `{name}` SCHEMALESS;")

    def insert(
        self,
        vectors: Sequence[Sequence[float]],
        payloads: list[dict] | None = None,
        ids: list[str] | None = None,
    ) -> None:
        payloads = payloads or [{} for _ in vectors]
        ids = ids or [str(i) for i in range(len(vectors))]
        stmts = []
        for vec, payload, vid in zip(vectors, payloads, ids, strict=False):
            stmts.append(
                f"CREATE {self._record(vid)} "
                f"CONTENT {{ vec: {json.dumps(list(vec))}, payload: {json.dumps(payload)} }};"
            )
        if stmts:
            self._sql("\n".join(stmts))

    def search(
        self, query: str, vectors: Sequence[float], top_k: int = 5, filters: dict | None = None
    ) -> list[OutputData]:
        q = (
            f"SELECT meta::id(id) AS id, payload, "
            f"vector::similarity::cosine(vec, {json.dumps(list(vectors))}) AS score "
            f"FROM `{self.collection_name}`{self._where(filters)} "
            f"ORDER BY score DESC LIMIT {int(top_k)};"
        )
        rows = self._last_result(self._sql(q))
        return [
            OutputData(id=r.get("id"), score=r.get("score"), payload=r.get("payload")) for r in rows
        ]

    def get(self, vector_id: str) -> OutputData | None:
        q = f"SELECT meta::id(id) AS id, payload FROM {self._record(vector_id)};"
        rows = self._last_result(self._sql(q))
        if not rows:
            return None
        return OutputData(id=rows[0].get("id"), payload=rows[0].get("payload"), score=None)

    def update(
        self, vector_id: str, vector: Sequence[float] | None = None, payload: dict | None = None
    ) -> None:
        sets = []
        if vector is not None:
            sets.append(f"vec = {json.dumps(list(vector))}")
        if payload is not None:
            sets.append(f"payload = {json.dumps(payload)}")
        if sets:
            self._sql(f"UPDATE {self._record(vector_id)} SET {', '.join(sets)};")

    def delete(self, vector_id: str) -> None:
        self._sql(f"DELETE {self._record(vector_id)};")

    def list(self, filters: dict | None = None, top_k: int | None = 100) -> list[list[OutputData]]:
        limit = f" LIMIT {int(top_k)}" if top_k else ""
        q = (
            f"SELECT meta::id(id) AS id, payload FROM "
            f"`{self.collection_name}`{self._where(filters)}{limit};"
        )
        rows = self._last_result(self._sql(q))
        return [[OutputData(id=r.get("id"), payload=r.get("payload"), score=None) for r in rows]]

    def list_cols(self) -> list[str]:
        resp = self._sql("INFO FOR DB;")
        res = self._last_result(resp)
        tables = res[0].get("tables", {}) if res and isinstance(res[0], dict) else {}
        return list(tables.keys())

    def delete_col(self) -> None:
        self._sql(f"REMOVE TABLE IF EXISTS `{self.collection_name}`;")

    def col_info(self) -> dict:
        rows = self._last_result(
            self._sql(f"SELECT count() FROM `{self.collection_name}` GROUP ALL;")
        )
        count = rows[0].get("count", 0) if rows else 0
        return {"name": self.collection_name, "count": count}

    def reset(self) -> None:
        self.delete_col()
        self.create_col(self.collection_name, self.dims, "cosine")


def register_surreal_provider() -> None:
    """Register 'surrealdb' into mem0's three lookup points (idempotent)."""
    import sys
    import types

    from mem0.utils.factory import VectorStoreFactory
    from mem0.vector_stores.configs import VectorStoreConfig

    # 1. config-class map (validator rejects unknown providers without this).
    #    _provider_configs is a pydantic PRIVATE attr, not a plain class dict — mutate
    #    its underlying default dict, which instances share at init.
    VectorStoreConfig.__private_attributes__["_provider_configs"].default["surrealdb"] = (
        "SurrealDBConfig"
    )

    # 2. inject the config module the validator imports: mem0.configs.vector_stores.surrealdb
    mod_name = "mem0.configs.vector_stores.surrealdb"
    if mod_name not in sys.modules:

        class SurrealDBConfig(BaseModel):
            collection_name: str = "cohezion_memory"
            embedding_model_dims: int = 768
            url: str = "http://localhost:8001/sql"
            namespace: str = "cohezion"
            database: str = "main"
            user: str = "root"
            password: str = "root"  # noqa: S105 - local SurrealDB dev default

            model_config = {"extra": "allow"}

        module = types.ModuleType(mod_name)
        module.SurrealDBConfig = SurrealDBConfig
        sys.modules[mod_name] = module

    # 3. factory class map
    VectorStoreFactory.provider_to_class["surrealdb"] = (
        "cohezion.memory.surreal_vector_store.SurrealVectorStore"
    )
