"""Card-aligned execute_fn for the compound executor (PR 1, datamesh-native).

This is the seam that wires the WS1+WS2 card-aligned local-fleet surface
into the compound loop. It also feeds evidence back into the datamesh
on every execution (Connections A, D, E from the plan).

Lifecycle of a single call:

  1. ResourceGuard pre-flight (soft gate; 0-MB estimate skips).
  2. FleetLock acquired for the duration of the dispatch.
  3. route_by_capability picks the (entry, params) pair.
  4. extend_claude_aligned dispatches to params.model_id (NOT a
     registry alternative).
  5. WITNESS_MARK precipitation event emitted with a 12D point
     derived from the card. Per-(task, model) 1/hour cooldown.
  6. Vault note EXEC-<timestamp>-<slug>.md written.
  7. SurrealDB row upserted fire-and-forget.
  8. Lock released; (text, metrics) returned.

Never raises: a failure path returns (error_text, metrics) with
card_aligned=False so the compound loop sees a consistent shape.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cohezion.inference.fleet import extend_claude_aligned
from cohezion.inference.model_card_harness import InferenceParams
from cohezion.inference.recipe_guard import RecipeGuard
from cohezion.inference.registry import Task

# Module-level imports so tests can patch them with
# `patch("cohezion.compound.execute_fn_aligned.<name>")`.
# The test surface requires attributes the patcher can find; lazy
# imports inside the function would prevent patching.
from cohezion.inference.route_by_capability import route_by_capability
from cohezion.precipitation import bus
from cohezion.precipitation.events import PrecipitationEvent, PrecipitationKind
from cohezion.reliability.resource_guard import ResourceGuard
from cohezion.researcher.daily_researcher import FleetLock


logger = logging.getLogger(__name__)


# ── Per-(task, model) cooldown for the bus ──────────────────────────────────


_witness_cooldown: dict[tuple[str, str], float] = {}
_WITNESS_COOLDOWN_SECONDS = 3600.0  # 1 hour


def _cooldown_key(guidance: dict[str, Any], params: InferenceParams) -> tuple[str, str]:
    """The (task, model) pair that gates the bus emission."""
    task = (guidance.get("operation_type") or guidance.get("task_description") or "unknown")[:80]
    return (task, params.model_id)


def _within_cooldown(key: tuple[str, str]) -> bool:
    last = _witness_cooldown.get(key)
    if last is None:
        return False
    return (time.time() - last) < _WITNESS_COOLDOWN_SECONDS


def _mark_emitted(key: tuple[str, str]) -> None:
    _witness_cooldown[key] = time.time()


# ── 12D point from the card (Connection A) ──────────────────────────────────


# Family → dimension mapping. Coarse, but the bus doesn't need
# high-fidelity 12D points; Mycelium clusters by proximity, so
# even a coarse signal is enough to detect card-aligned patterns.
_FAMILY_TO_DIM: dict[str, str] = {
    "gemma4": "logic",
    "qwen3": "physics",
    "deepseek": "logic",
    "phi4": "biology",
    "claude": "field",
    "gemini": "control",
    "llama3": "control",
    "test": "novelty",
}


def _twelve_d_from_card(
    *, family: str, task: str, escalated: bool, cache_hit: bool, errored: bool
) -> dict[str, float]:
    """A 12D point derived from the card + outcome.

    The family fingerprint is one dimension; the task is another.
    The base coherence is the HIHO baseline (0.5); family and
    novelty dimensions are lifted to indicate the card was used.
    All 12 dims must be in TWELVE_D_DIMS (enforced by the bus's
    __post_init__ which fills missing dims with 0.5).
    """
    twelve_d = {
        "x": 0.5, "y": 0.5, "z": 0.5, "time": 0.5,
        "physics": 0.5, "biology": 0.5, "logic": 0.5, "quantum": 0.5,
        "field": 0.5, "control": 0.5, "novelty": 0.5, "precipitation": 0.5,
    }
    # Family fingerprint: lift the relevant dimension to 0.7
    dim = _FAMILY_TO_DIM.get(family)
    if dim is not None:
        twelve_d[dim] = 0.7
    # Task fingerprint: a small lift on "novelty" for non-routine ops
    if task in ("generate", "architect", "research"):
        twelve_d["novelty"] = 0.65
    # Cache hits / escalations are recorded in the event payload
    # (coherence value), not the 12D point. The 12D point is the
    # *card* fingerprint, not the outcome.
    return twelve_d


# ── WITNESS_MARK emission (Connection A) ─────────────────────────────────────


def _emit_witness_mark(
    *, params: InferenceParams, task: str, twelve_d: dict[str, float],
    coherence: float, payload: dict[str, Any],
) -> None:
    """Emit a WITNESS_MARK precipitation event. Never raises."""
    try:
        event = PrecipitationEvent(
            kind=PrecipitationKind.WITNESS_MARK,
            universe_id="cohezion_compound_executor",
            coherence=coherence,
            twelve_d=twelve_d,
            payload={
                "source": "compound.execute_fn_aligned",
                "model_id": params.model_id,
                "task": task,
                **payload,
            },
        )
        bus.emit(event)
    except Exception as e:
        logger.debug("WITNESS_MARK emission failed (non-blocking): %s", e)


# ── Vault note (Connection E) ──────────────────────────────────────────────


def _vault_root() -> Path:
    return Path(
        os.environ.get(
            "COHEZION_VAULT_ROOT",
            str(Path.home() / "vaults" / "cohezion-vault" / "01-Learnings"),
        )
    )


def _slugify(s: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "-" for c in s)[:60].strip("-")


def _write_vault_note(
    *, params: InferenceParams, task: str, text: str, metrics: dict[str, Any],
    family: str,
) -> Path:
    """Write a vault note for the execution. Best-effort; never raises."""
    root = _vault_root() / "EXEC" / datetime.now(UTC).strftime("%Y-%m-%d")
    try:
        root.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).strftime("%H%M%S")
        slug = _slugify(task)
        out = root / f"EXEC-{ts}-{slug}.md"
        body = (
            f"# Aligned execution — {datetime.now(UTC).isoformat()}\n\n"
            f"**Model**: `{params.model_id}` ({family})\n"
            f"**Task**: `{task}`\n"
            f"**Lane**: {metrics.get('lane', '?')}\n"
            f"**Card-aligned**: {metrics.get('card_aligned', False)}\n"
            f"**Recipe params**: `{params.model_id}` "
            f"max_tokens={params.max_tokens} prefix={params.prompt_prefix!r}\n\n"
            f"## Output\n\n{text}\n\n"
            f"## Metrics\n\n```\n{metrics}\n```\n"
        )
        out.write_text(body)
        return out
    except Exception as e:
        logger.debug("vault note write failed (non-blocking): %s", e)
        return Path("(write failed)")


# ── SurrealDB upsert (Connection D, fire-and-forget) ───────────────────────


async def _upsert_surreal_execution(
    *, params: InferenceParams, task: str, metrics: dict[str, Any], text: str
) -> None:
    """Upsert a `fleet_research:execution` row in SurrealDB.

    Best-effort, async, never raises. Uses the same HTTP-direct-ingest
    pattern that the daily researcher's bus writes use.
    """
    try:
        import json
        import os
        import urllib.request

        url = os.environ.get("SURREAL_URL", "http://localhost:8001/sql")
        user = os.environ.get("SURREAL_USER", "root")
        password = os.environ.get("SURREAL_PASSWORD", "root")
        body = {
            "query": (
                "UPSERT fleet_research:execution CONTENT { "
                f"model_id: '{params.model_id}', "
                f"task: '{task}', "
                f"card_aligned: {str(metrics.get('card_aligned', False)).lower()}, "
                f"recipe_params_id: '{params.model_id}', "
                f"lane: '{metrics.get('lane', '?')}', "
                f"text_len: {len(text)} "
                "};"
            )
        }
        req = urllib.request.Request(  # noqa: S310 — SurrealDB URL is env-controlled, not user input
            url,
            data=json.dumps(body).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Basic " + _b64(f"{user}:{password}"),
            },
            method="POST",
        )
        urllib.request.urlopen(req, timeout=2.0).read()  # noqa: S310 — see above
    except Exception as e:
        logger.debug("SurrealDB upsert failed (non-blocking): %s", e)


def _b64(s: str) -> str:
    import base64
    return base64.b64encode(s.encode()).decode()


# ── The function ────────────────────────────────────────────────────────────


async def execute_fn_aligned(guidance: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """The card-aligned execute_fn for the CompoundExecutor.

    Args:
        guidance: The dict the CompoundExecutor passes to execute_fn.
            Has at least `task_description` and `operation_type`.

    Returns:
        (text, metrics) where metrics carries `card_aligned`,
        `recipe_params_id`, `lane`, `datamesh` (the witness/vault/surreal
        pointers), and on failure, `error`.
    """
    task = (guidance.get("task_description") or "unknown")[:200]
    operation = guidance.get("operation_type", "general")

    # 1. ResourceGuard pre-flight (soft gate; 0-MB estimate is allowed)
    try:
        ok, reason = ResourceGuard().can_load_model(0)
        if not ok:
            logger.warning("ResourceGuard refused aligned execute_fn: %s", reason)
            return (
                f"Error: preflight refused: {reason}",
                {
                    "card_aligned": False,
                    "error": reason,
                    "preflight": "refused",
                },
            )
    except Exception as e:
        logger.debug("ResourceGuard unavailable (non-blocking): %s", e)

    # 2. Pick the (entry, params) pair
    try:
        op_to_task = {
            "generate": Task.GENERAL,
            "analyze": Task.REASONING,
            "search": Task.SENSING,
            "transform": Task.CODE_GEN,
            "persist": Task.SUMMARIZATION,
            "summarize": Task.SUMMARIZATION,
        }
        task_enum = op_to_task.get(operation, Task.GENERAL)

        # The compound loop doesn't tell us how big the prompt is; we
        # estimate from the guidance. The router uses prompt_estimate
        # only to filter cards whose optimal_ctx can't hold it.
        prompt_estimate = len(task) + sum(
            len(str(v)) for v in guidance.values() if isinstance(v, (str, int, float))
        )
        prompt_estimate = max(512, min(prompt_estimate, 32_000))
        prompt_estimate_tokens = prompt_estimate // 4

        result = route_by_capability(
            task=task_enum,
            prompt_estimate_tokens=prompt_estimate_tokens,
        )
        if result is None:
            return (
                f"Error: route_by_capability found no capable model for task {task_enum!r}",
                {"card_aligned": False, "error": "no_capable_model"},
            )
        entry, params = result
        RecipeGuard.assert_card_present(entry)
        RecipeGuard.assert_aligned(params)
    except Exception as e:
        logger.warning("route_by_capability failed: %s", e, exc_info=True)
        return (
            f"Error: routing failed: {e}",
            {"card_aligned": False, "error": f"routing: {e}"},
        )

    family = entry.profile.family if entry.profile is not None else "unknown"
    lock_key = f"fleet_lock:modelload:execute_fn:{params.model_id}"

    # 3. FleetLock + dispatch
    text = ""
    errored = False
    escalated = False
    try:
        async with FleetLock().acquire(lock_key, timeout=30.0):
            try:
                result_obj = await extend_claude_aligned(
                    task, params=params, timeout=60.0
                )
                text = result_obj.text
                escalated = bool(getattr(result_obj, "escalated_to_cloud", False))
                if result_obj.error:
                    errored = True
            except Exception as e:
                logger.error("extend_claude_aligned dispatch failed: %s", e, exc_info=True)
                errored = True
                text = f"Error: dispatch failed: {e}"
    except Exception as e:
        # LockTimeout etc.
        logger.error("FleetLock failed: %s", e, exc_info=True)
        errored = True
        text = f"Error: lock failed: {e}"

    metrics: dict[str, Any] = {
        "card_aligned": not errored,
        "recipe_params_id": params.model_id,
        "lane": getattr(entry, "lane", "?").value if hasattr(entry, "lane") else "?",
        "escalated_to_cloud": escalated,
        "task": task,
        "operation": operation,
        "family": family,
    }
    if errored:
        metrics["error"] = text

    # 4. WITNESS_MARK (Connection A) — with 1/hour cooldown
    cd_key = _cooldown_key(guidance, params)
    if not _within_cooldown(cd_key):
        # Coherence: 0.5 baseline; lift to 0.6 on local success, 0.4 on
        # escalation, 0.3 on error. These are the bus signals Ouroboros
        # and Mycelium consume.
        if errored:
            coherence = 0.3
        elif escalated:
            coherence = 0.4
        else:
            coherence = 0.6
        twelve_d = _twelve_d_from_card(
            family=family,
            task=operation,
            escalated=escalated,
            cache_hit=False,
            errored=errored,
        )
        _emit_witness_mark(
            params=params,
            task=task,
            twelve_d=twelve_d,
            coherence=coherence,
            payload={
                "card_aligned": metrics["card_aligned"],
                "escalated": escalated,
                "errored": errored,
            },
        )
        _mark_emitted(cd_key)
        metrics["witness_mark_emitted"] = True
    else:
        metrics["witness_mark_emitted"] = False
        metrics["witness_mark_suppressed"] = "1h_cooldown"

    # 5. Vault note (Connection E)
    vault_path = _write_vault_note(
        params=params, task=task, text=text, metrics=metrics, family=family
    )
    metrics["vault_note_path"] = str(vault_path)

    # 6. SurrealDB upsert (Connection D) — fire-and-forget
    asyncio.create_task(
        _upsert_surreal_execution(params=params, task=task, metrics=metrics, text=text)
    )
    metrics["surreal_upsert_scheduled"] = True

    return text, metrics
