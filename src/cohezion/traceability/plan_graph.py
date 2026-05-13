"""Async client for plan traceability graph stored in SurrealDB.

Wraps SurrealDB operations for plan -> task -> file -> commit graph edges.
Uses httpx HTTP fallback (POST /sql) when the websocket client has issues,
following the same pattern as ``cohezion.core.persistence.surreal_client``.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import httpx


logger = logging.getLogger(__name__)

_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "knowledge_graph" / "plan_traceability_schema.surql"

# SurrealDB connection defaults
_DEFAULT_URLS = [
    os.environ.get("SURREAL_URL", "http://localhost:8001"),
    "http://localhost:8001",
]
_NS = "cohezion"
_DB = "traceability"
_USER = os.environ.get("SURREAL_USER", "root")
_PASS = os.environ.get("SURREAL_PASSWORD", "root")


class PlanGraph:
    """Thin async wrapper around SurrealDB for plan traceability queries."""

    def __init__(
        self,
        url: str | None = None,
        namespace: str = _NS,
        database: str = _DB,
        username: str = _USER,
        password: str = _PASS,
    ) -> None:
        self._urls = [url] if url else list(_DEFAULT_URLS)
        self.namespace = namespace
        self.database = database
        self._username = username
        self._password = password
        self._base_url: str | None = None

    # ------------------------------------------------------------------
    # Low-level HTTP transport
    # ------------------------------------------------------------------

    async def _resolve_url(self) -> str:
        """Find the first reachable SurrealDB endpoint."""
        if self._base_url:
            return self._base_url
        for url in self._urls:
            try:
                async with httpx.AsyncClient(timeout=2.0) as c:
                    r = await c.get(f"{url}/health")
                    if r.status_code == 200:
                        self._base_url = url
                        return url
            except Exception:
                logger.debug("SurrealDB not reachable at %s, trying next.", url)
                continue
        # Fall back to the first URL even if unreachable
        self._base_url = self._urls[0]
        return self._base_url

    async def _sql(self, query: str, params: dict[str, Any] | None = None) -> list[dict]:
        """Execute a SurrealQL statement via HTTP POST /sql."""
        url = await self._resolve_url()
        headers = {
            "Accept": "application/json",
            "NS": self.namespace,
            "DB": self.database,
        }
        auth = (self._username, self._password)

        # SurrealDB HTTP endpoint accepts raw SurrealQL in the body.
        # Variables are interpolated via $name placeholders in the query;
        # we pass them as JSON body when using the /sql endpoint by
        # embedding them directly in the query for simplicity (the HTTP
        # /sql endpoint doesn't support a separate vars payload in older
        # versions).  To stay safe we use string interpolation only for
        # values we control (slugs, paths, hashes) and never for
        # user-generated free text -- plan data goes through parameterised
        # CREATE statements.
        body = query
        if params:
            # SurrealDB HTTP /sql supports LET $var = <value> preambles.
            preamble_parts: list[str] = []
            for k, v in params.items():
                preamble_parts.append(f"LET ${k} = {_surreal_literal(v)};")
            body = "\n".join(preamble_parts) + "\n" + query

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{url}/sql", content=body, headers=headers, auth=auth)
            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    async def initialize_schema(self) -> None:
        """Run the .surql schema file against SurrealDB."""
        schema_text = _SCHEMA_PATH.read_text()
        await self._sql(schema_text)
        logger.info("Plan traceability schema initialized.")

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    async def create_plan(
        self,
        slug: str,
        name: str,
        source_file: str,
        tasks: list[dict[str, str]],
    ) -> str:
        """Create a plan and its tasks, returning the plan record id.

        *tasks* is a list of dicts each containing ``step_number`` and ``title``.
        """
        plan_id = f"plan:{slug}"
        await self._sql(
            f"CREATE plan:{slug} SET "
            "slug = $slug, "
            "name = $name, "
            "status = 'draft', "
            "source_file = $source_file, "
            "tasks_total = $total, "
            "tasks_completed = 0;",
            {
                "slug": slug,
                "name": name,
                "source_file": source_file,
                "total": len(tasks),
            },
        )

        for task in tasks:
            step = task["step_number"]
            title = task["title"]
            # Replace dots in step number for safe record id
            safe_step = step.replace(".", "_")
            task_id = f"{slug}__{safe_step}"
            await self._sql(
                f"CREATE task:{task_id} SET title = $title, status = 'pending', step_number = $step;",
                {"title": title, "step": step},
            )
            # Edge: plan -> task
            await self._sql(
                f"RELATE plan:{slug}->plan_has_task->task:{task_id};",
            )

        logger.info("Created plan %s with %d tasks.", slug, len(tasks))
        return plan_id

    async def update_plan_status(self, slug: str, status: str) -> None:
        """Update plan status (draft/approved/in_progress/completed/abandoned)."""
        extra = ""
        if status == "completed":
            extra = ", completed_at = time::now()"
        await self._sql(
            f"UPDATE plan:{slug} SET status = $status{extra};",
            {"status": status},
        )

    async def complete_task(self, plan_slug: str, step_number: str) -> None:
        """Mark a task as completed and bump the plan's tasks_completed counter."""
        task_id = f"{plan_slug}__{step_number}"
        await self._sql(f"UPDATE task:{task_id} SET status = 'completed', completed_at = time::now();")
        await self._sql(f"UPDATE plan:{plan_slug} SET tasks_completed += 1;")

    async def record_file_touch(self, plan_slug: str, step_number: str, file_path: str) -> None:
        """Record that a task modified a file (upsert file, create edge)."""
        safe_file_id = _path_to_id(file_path)
        task_id = f"{plan_slug}__{step_number}"

        # Upsert the file record
        await self._sql(
            "CREATE file SET path = $path, last_modified = time::now();",
            {"path": file_path},
        )
        # Edge: task -> file
        await self._sql(f"RELATE task:{task_id}->task_modifies->file:{safe_file_id};")

    async def record_commit(
        self,
        commit_hash: str,
        message: str,
        task_steps: list[str],
        plan_slug: str | None = None,
    ) -> None:
        """Record a git commit and link it to tasks + touched files."""
        short = commit_hash[:12]
        await self._sql(
            f"CREATE commit:{short} SET hash = $hash, message = $message, timestamp = time::now();",
            {"hash": commit_hash, "message": message},
        )

        for step in task_steps:
            slug = plan_slug or ""
            task_id = f"{slug}__{step}" if slug else step
            await self._sql(f"RELATE commit:{short}->commit_implements->task:{task_id};")

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    async def plan_completeness(self, slug: str) -> dict[str, Any]:
        """Return {total, completed, pct} for a plan."""
        result = await self._sql(f"SELECT tasks_total, tasks_completed FROM plan:{slug};")
        row = _first_result(result)
        if not row:
            return {"total": 0, "completed": 0, "pct": 0.0}
        total = row.get("tasks_total", 0)
        completed = row.get("tasks_completed", 0)
        pct = (completed / total * 100) if total else 0.0
        return {"total": total, "completed": completed, "pct": round(pct, 1)}

    async def files_for_plan(self, slug: str) -> list[str]:
        """Return all file paths linked to a plan's tasks."""
        result = await self._sql(f"SELECT ->plan_has_task->task->task_modifies->file.path AS paths FROM plan:{slug};")
        row = _first_result(result)
        if not row:
            return []
        paths = row.get("paths", [])
        # Flatten nested lists if needed
        flat: list[str] = []
        for p in paths:
            if isinstance(p, list):
                flat.extend(p)
            else:
                flat.append(p)
        return sorted(set(flat))

    async def plans_for_file(self, path: str) -> list[str]:
        """Return plan slugs that touched a given file path."""
        result = await self._sql(
            "SELECT <-task_modifies<-task<-plan_has_task<-plan.slug AS slugs FROM file WHERE path = $path;",
            {"path": path},
        )
        row = _first_result(result)
        if not row:
            return []
        slugs = row.get("slugs", [])
        flat: list[str] = []
        for s in slugs:
            if isinstance(s, list):
                flat.extend(s)
            else:
                flat.append(s)
        return sorted(set(flat))

    async def orphan_files(self) -> list[str]:
        """Return file paths not linked to any plan via task_modifies edges."""
        result = await self._sql("SELECT path FROM file WHERE count(<-task_modifies) = 0;")
        rows = _all_results(result)
        return sorted(r["path"] for r in rows if "path" in r)

    async def plan_graph(self, slug: str) -> dict[str, Any]:
        """Return the full plan with nested tasks, files, and commits."""
        # Plan record
        plan_result = await self._sql(f"SELECT * FROM plan:{slug};")
        plan = _first_result(plan_result)
        if not plan:
            return {}

        # Tasks with their edges
        tasks_result = await self._sql(
            f"SELECT *, "
            f"->task_modifies->file.path AS files, "
            f"<-commit_implements<-commit.hash AS commits "
            f"FROM task WHERE <-plan_has_task<-plan CONTAINS plan:{slug};"
        )
        tasks = _all_results(tasks_result)

        plan["tasks"] = tasks
        return plan


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _surreal_literal(value: Any) -> str:
    """Convert a Python value to a SurrealQL literal for LET statements."""
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace("'", "\\'")
        return f"'{escaped}'"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    if value is None:
        return "NONE"
    if isinstance(value, list):
        items = ", ".join(_surreal_literal(v) for v in value)
        return f"[{items}]"
    # Fallback: stringify
    escaped = str(value).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"


def _path_to_id(file_path: str) -> str:
    """Convert a file path to a safe SurrealDB record id.

    Replaces ``/`` and ``.`` with underscores, strips leading underscores.
    """
    safe = file_path.replace("/", "_").replace(".", "_").replace("-", "_").strip("_")
    return safe


def _first_result(response: list[dict]) -> dict[str, Any] | None:
    """Extract the first record from a SurrealDB HTTP response."""
    for envelope in response:
        result = envelope.get("result")
        if isinstance(result, list) and result:
            return result[0]  # type: ignore[no-any-return]
        if isinstance(result, dict):
            return result  # type: ignore[no-any-return]
    return None


def _all_results(response: list[dict]) -> list[dict[str, Any]]:
    """Extract all records from a SurrealDB HTTP response."""
    for envelope in response:
        result = envelope.get("result")
        if isinstance(result, list):
            return result  # type: ignore[no-any-return]
    return []
