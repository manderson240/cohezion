"""SurrealDB execution trace writer — persister plugin for CompoundExecutor.

Wires into ExecutorFactory.create() as the `persister` callback. After each
execution it writes one row to `execution_trace`, which becomes the SkillOpt
trajectory corpus (read by surreal_trajectory_loader.py).

Schema (auto-created on first write):
    execution_trace {
        skill_name  string
        input       string   -- task description / prompt
        output      string   -- execution result text
        score       float    -- alignment/quality score (0.0–1.0)
        status      string   -- 'success' | 'failure' | 'partial'
        tokens_used int
        model_tier  string   -- 'npu' | 'igpu' | 'cpu' | 'cloud'
        created_at  datetime
    }
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_SURREAL_URL = "http://127.0.0.1:8001/sql"
_SURREAL_AUTH = ("root", "root")
_SURREAL_HEADERS = {
    "surreal-ns": "cohezion",
    "surreal-db": "main",
    "Content-Type": "text/plain",
    "Accept": "application/json",
}


def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


class SurrealTraceWriter:
    """Callable persister that writes execution traces to SurrealDB."""

    def __init__(self, base_url: str = _SURREAL_URL, timeout: float = 5.0) -> None:
        self._url = base_url
        self._timeout = timeout
        self._client = httpx.Client(timeout=timeout)
        self._ensure_table()

    def _ensure_table(self) -> None:
        """Define the table schema once (idempotent DEFINE TABLE IF NOT EXISTS)."""
        ddl = """
        DEFINE TABLE IF NOT EXISTS execution_trace SCHEMAFULL;
        DEFINE FIELD IF NOT EXISTS skill_name  ON execution_trace TYPE string;
        DEFINE FIELD IF NOT EXISTS input       ON execution_trace TYPE string;
        DEFINE FIELD IF NOT EXISTS output      ON execution_trace TYPE string;
        DEFINE FIELD IF NOT EXISTS score       ON execution_trace TYPE float;
        DEFINE FIELD IF NOT EXISTS status      ON execution_trace TYPE string;
        DEFINE FIELD IF NOT EXISTS tokens_used ON execution_trace TYPE int;
        DEFINE FIELD IF NOT EXISTS model_tier  ON execution_trace TYPE string;
        DEFINE FIELD IF NOT EXISTS created_at  ON execution_trace TYPE datetime VALUE time::now() READONLY;
        DEFINE INDEX IF NOT EXISTS idx_skill ON execution_trace FIELDS skill_name;
        """
        try:
            self._client.post(
                self._url,
                content=ddl,
                headers=_SURREAL_HEADERS,
                auth=_SURREAL_AUTH,
                timeout=10.0,
            )
        except Exception as exc:
            logger.debug("SurrealTraceWriter._ensure_table failed (non-fatal): %s", exc)

    def __call__(self, context: Any, result: Any) -> None:
        """Persister callback — called by CompoundExecutor after each task."""
        try:
            skill_name = _extract_skill_name(context)
            input_text = _extract_input(context)
            output_text = _extract_output(result)
            score = _extract_score(result)
            status = "success" if getattr(result, "success", False) else "failure"
            tokens = getattr(result, "tokens_used", 0) or 0
            tier = _extract_tier(result)

            sql = (
                f"CREATE execution_trace SET "
                f'skill_name = "{_escape(skill_name)}", '
                f'input = "{_escape(input_text[:2000])}", '
                f'output = "{_escape(output_text[:4000])}", '
                f"score = {score}, "
                f'status = "{status}", '
                f"tokens_used = {tokens}, "
                f'model_tier = "{tier}";'
            )
            self._client.post(
                self._url,
                content=sql,
                headers=_SURREAL_HEADERS,
                auth=_SURREAL_AUTH,
            )
            logger.debug("Wrote execution_trace for skill '%s' (score=%.2f)", skill_name, score)
        except Exception as exc:
            logger.debug("SurrealTraceWriter.__call__ failed (non-fatal): %s", exc)


# ------------------------------------------------------------------ #
# Field extractors — defensive, never raise                           #
# ------------------------------------------------------------------ #


def _extract_skill_name(context: Any) -> str:
    # Direct attributes (vault ExecutionContext: skill_name, task_description)
    direct = getattr(context, "skill_name", None)
    if direct:
        return direct
    # Nested task object (core ExecutionContext: task.skill_name / task.name)
    task = getattr(context, "task", None)
    if task:
        return (
            getattr(task, "skill_name", None)
            or getattr(task, "name", None)
            or getattr(task, "description", "")[:60]
        )
    return "unknown"


def _extract_input(context: Any) -> str:
    # Direct attribute (vault ExecutionContext)
    direct = getattr(context, "task_description", None)
    if direct:
        return direct
    # Nested task object (core ExecutionContext)
    task = getattr(context, "task", None)
    if task:
        return getattr(task, "description", "") or getattr(task, "prompt", "") or ""
    return ""


def _extract_output(result: Any) -> str:
    return (
        getattr(result, "output", None)
        or getattr(result, "response", None)
        or getattr(result, "text", None)
        or ""
    )


def _extract_score(result: Any) -> float:
    raw = (
        getattr(result, "alignment_score", None)
        or getattr(result, "compound_score", None)
        or getattr(result, "score", None)
        or getattr(result, "quality_score", None)
    )
    if raw is None:
        return 1.0 if getattr(result, "success", False) else 0.0
    try:
        v = float(raw)
        return v if v > 0.0 else (1.0 if getattr(result, "success", False) else 0.0)
    except (TypeError, ValueError):
        return 0.5


def _extract_tier(result: Any) -> str:
    metrics = getattr(result, "metrics", None)
    if metrics:
        # metrics may be a dict (CompoundExecutor) or an object (core executor)
        if isinstance(metrics, dict):
            return metrics.get("model_tier", metrics.get("tier", "cloud")) or "cloud"
        return getattr(metrics, "model_tier", None) or getattr(metrics, "tier", "cloud") or "cloud"
    # Fall back to token_metrics for model tier
    token_metrics = getattr(result, "token_metrics", None)
    if isinstance(token_metrics, dict):
        model = token_metrics.get("model", "")
        if "npu" in model.lower() or "flm" in model.lower():
            return "npu"
        if "igpu" in model.lower() or "e4b" in model.lower() or "e2b" in model.lower():
            return "igpu"
        if "cpu" in model.lower() or "31b" in model.lower() or "gguf" in model.lower():
            return "cpu"
    return "cloud"


def make_trace_writer() -> SurrealTraceWriter | None:
    """Factory — returns None if SurrealDB is unreachable."""
    try:
        writer = SurrealTraceWriter()
        logger.info("SurrealTraceWriter wired (execution_trace table ready)")
        return writer
    except Exception as exc:
        logger.debug("SurrealTraceWriter unavailable: %s", exc)
        return None
