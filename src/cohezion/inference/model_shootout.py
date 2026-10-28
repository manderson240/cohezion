"""Quality-first local model shootout — event-driven data-mesh producer.

Answers "which local model is actually best on this Strix Halo box?" WITHOUT
defaulting to throughput — the mandate is QUALITY OVER SPEED. The adaptive
router already weights quality far above the size/speed proxy:

    fleet_roles._perf_scores() → reads SurrealDB `model_performance`, adds
    +25.0 * quality_score to rank, vs ±0.5/GB for size.

This module is a DataMesh producer per the agent-operated event-driven
architecture (AGENTS.md mandate #5):

1. HOT-SWAP each candidate under fleet lock + broadcast MODEL_LOADING /
   MODEL_LOADED / MODEL_LOAD_REFUSED — via the existing
   ``ModelSprintOrchestrator`` / ``hotswap`` / ``EventBus`` stack.
2. Run the SAME quality-discriminating task via ``LemonadeTransport``
   (the real inference primitive — NOT a made-up client).
3. Score quality with ``evaluate_quality_simple``.
4. Publish a ``DATA_PRODUCT_UPDATED`` event carrying the result — the
   existing ``DataMeshEventBridge`` subscribes and persists it, alongside
   the orchestrator's own lifecycle events, to SurrealDB
   ``data_product_event`` (durable audit trail).
5. Write ``model`` + ``quality_score`` (plus task/role/tps metadata) to
   SurrealDB ``model_performance`` — the table the router already reads —
   closing the adaptive loop so the router auto-prefers the winner.

Only composes existing primitives — no parallel infrastructure.

Why quality-first: a TPS benchmark crowns the fastest 1-4B draft model.
This shootout crowns the model whose reasoning output is most on-target;
because rank is quality-driven, the winner is what the router starts
forwarding real work to.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from cohezion.core.event_bus import Event, EventBus, EventType, get_event_bus
from cohezion.data_mesh.data_product import DataProductSchema, DataProductStatus, DataQualityTier
from cohezion.inference.evaluation_harness import evaluate_quality_simple
from cohezion.inference.model_sprint_orchestrator import (
    DEFAULT_BASE_URL,
    ModelSprintOrchestrator,
)
from cohezion.inference.transports.lemonade import LemonadeTransport


logger = logging.getLogger(__name__)

# ── SurrealDB target tables ------------------------------------------------
#   data_product_event  → durable audit trail written by DataMeshEventBridge
#   model_performance   → adaptive table the router (fleet_roles) reads
SURREAL_URL = "http://localhost:8001/sql"
SURREAL_NS = "cohezion"
SURREAL_DB = "main"
SURREAL_AUTH = base64.b64encode(b"root:root").decode()

# Default (quality-discriminating) reviewer task — the same shape used for the
# multi-perspective review lanes. Only a GOOD code review hits every token.
DEFAULT_TASK = (
    "Review this Python function and list concrete bugs, race conditions, "
    "or correctness issues. Be specific; cite line-level symptoms if possible."
    "\n\n```python\n"
    "def transfer(acct, to, amt):\n"
    "    if amt < 0: return\n"
    "    bal = acct.account.balance\n"
    "    to.balance += amt\n"
    "    acct.balance = bal - amt\n"
    "    return acct.balance\n"
    "```"
)
DEFAULT_EXPECTED = ["balance", "amt", "overdraft", "integer", "float"]


# Default candidate set derives from the DAEMON-MAINTAINED resident fleet so
# the shootout rides the work the fleet daemons already do (hot pre-warming,
# keeping models resident) instead of forcing its own cold loads through the
# safety gate. ``ensure_resident`` short-circuits to ``already_resident`` for
# anything resident, so comparing this list needs zero loads / zero refusals.
# A non-resident model (e.g. a candidate the user passes explicitly) falls
# back to the hotswap cold-load path with the RAM floor respected.
def default_candidates(min_resident: int = 2) -> list[str]:
    """Return the resident models worth comparing; resident first.

    Falls back to a curated quality list if fewer than ``min_resident``
    models are resident (e.g. fleet daemons not yet up).
    """
    from cohezion.inference import hotswap

    try:
        resident = [m.get("model_name", "") for m in hotswap.resident_models()]
        resident = [
            m
            for m in resident
            if m and not any(s in m.lower() for s in ("embed", "embedding", "nomic"))
        ]
    except Exception as exc:  # daemon fleet introspection unavailable
        logger.debug("shootout: could not read resident fleet: %s", exc)
        resident = []

    if len(resident) >= min_resident:
        return resident
    return list(_CURATED_FALLBACK)


# Curated fallback when the daemon fleet is empty/unknown (rare).
_CURATED_FALLBACK = [
    "Qwen3.8-27B-ThinkingCoder",  # reasoning/code star (resident)
    "Qwen3.6-35B-A3B-ThinkingCoder",  # MoE thinking coder (resident)
    "Qwen3.8-27B-GGUF",  # dense baseline (resident)
    "Bonsai-8B-gguf",  # fast baseline (resident)
]

PRODUCT_SCHEMA = DataProductSchema(
    fields={
        "model": "str — Lemonade model id",
        "quality_score": "float 0-1 — fraction of expected tokens matched",
        "latency_ms": "float — measured round-trip latency",
        "tps": "float — tokens per second (secondary, never the rank key)",
        "role": "str — router role this shootout targets",
        "task": "str — the quality-discriminating prompt used",
    },
    version="1.0.0",
)


@dataclass
class ShootoutResult:
    """Outcome for a single candidate model."""

    model: str
    ok: bool
    quality_score: float
    latency_ms: float = 0.0
    tps: float = 0.0
    output_tokens: int = 0
    output_preview: str = ""
    reason: str = ""
    loaded: bool = False


@dataclass
class ShootoutReport:
    """Full shootout: per-model results, quality-ranked."""

    task: str
    expected_contains: list[str]
    role: str
    results: list[ShootoutResult] = field(default_factory=list)

    def quality_ranked(self) -> list[ShootoutResult]:
        """Rank by quality_score DESC (latency is never the ranking key)."""
        return sorted(self.results, key=lambda r: r.quality_score, reverse=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "expected_contains": self.expected_contains,
            "role": self.role,
            "ranked_by": "quality_score",
            "results": [r.__dict__ for r in self.quality_ranked()],
        }


def _ok_quality(quality_score: float) -> bool:
    """Pass = matched at least half the expected tokens."""
    return quality_score >= 0.5


class ModelShootout:
    """Runs a quality-first comparison as a DataMesh producer.

    Args:
        candidates: model ids to compare (must be in the :13305 catalog).
        task: the prompt every candidate answers.
        expected_contains: tokens a GOOD answer must contain; score = fraction.
        role: router role label tied to this shootout (e.g. "code").
        runs: how many independent runs per model (quality mean when >1).
        min_free_gb: passed through to the hotswap safety gate.
        orchestrator: optional injected ModelSprintOrchestrator (test seam).
        bus: optional injected EventBus (test seam).
    """

    def __init__(
        self,
        candidates: list[str] | None = None,
        task: str = DEFAULT_TASK,
        expected_contains: list[str] | None = None,
        role: str = "code",
        runs: int = 1,
        min_free_gb: float = 20.0,
        base_url: str = DEFAULT_BASE_URL,
        orchestrator: ModelSprintOrchestrator | None = None,
        bus: EventBus | None = None,
    ) -> None:
        self.candidates = candidates or default_candidates()
        self.task = task
        self.expected_contains = expected_contains or list(DEFAULT_EXPECTED)
        self.role = role
        self.runs = max(1, runs)
        self.min_free_gb = min_free_gb
        self._orchestrator = orchestrator or ModelSprintOrchestrator(
            base_url=base_url, min_free_gb=min_free_gb
        )
        self._bus = bus
        self._transport = LemonadeTransport(port=int(base_url.rsplit(":", 1)[-1]))

    # ── Public API ─────────────────────────────────────────────────────────

    async def run(self) -> ShootoutReport:
        """Hot-swap each candidate, score quality, publish DataMesh events.

        Never raises on a per-model failure: a model that won't load is a
        ``ShootoutResult(ok=False, reason=...)`` whose refusal was already
        broadcast by the orchestrator; the shootout continues to the next.
        """
        report = ShootoutReport(self.task, self.expected_contains, self.role)

        for model in self.candidates:
            logger.info("shootout: candidate %s (role=%s)", model, self.role)

            # ALREADY-RESIDENT FAST PATH: the fleet daemons keep these hot, so
            # skip the load/gate entirely and just query. This is the
            # daemon-riding behavior — we reuse their pre-warmed state instead
            # of re-gating (pre_load_gate refuses at <20GiB free even for a
            # resident model, so running the full sprint here is wrong).
            if model in self._resident_ids():
                sprint_ok = True
                sprint_reason = "already resident (daemon-maintained fleet)"
                already_resident = True
                evicted: list[str] = []
            else:
                sprint = await self._orchestrator.ensure_model(
                    model, protect=(), load_timeout=300.0
                )
                sprint_ok = sprint.ok
                sprint_reason = sprint.reason
                already_resident = sprint.already_resident
                evicted = sprint.evicted

            if not sprint_ok:
                result = ShootoutResult(
                    model=model,
                    ok=False,
                    quality_score=0.0,
                    reason=sprint_reason or "not loadable",
                    loaded=False,
                )
                report.results.append(result)
                await self._emit_product_update(result)
                continue

            quality_scores: list[float] = []
            latency_ms = 0.0
            tps = 0.0
            tokens = 0
            preview = ""
            run_failures = 0

            for _ in range(self.runs):
                # Real inference primitive — not a fabricated client.
                resp = await self._transport.query(
                    self.task,
                    model,
                    params={"temperature": 0.1, "max_tokens": 512},
                )
                if resp is None or not resp.content.strip():
                    run_failures += 1
                    continue
                quality_scores.append(evaluate_quality_simple(resp.content, self.expected_contains))
                latency_ms = resp.latency_ms
                tokens = len(resp.content.split())
                tps = (tokens / max(resp.latency_ms, 1.0)) * 1000.0
                preview = resp.content[:200]

            if not quality_scores:
                result = ShootoutResult(
                    model=model,
                    ok=False,
                    quality_score=0.0,
                    reason="all runs failed to produce output",
                    loaded=sprint_ok,
                )
                report.results.append(result)
                await self._emit_product_update(result)
                continue

            quality = sum(quality_scores) / len(quality_scores)
            result = ShootoutResult(
                model=model,
                ok=sprint_ok and run_failures < self.runs,
                quality_score=round(quality, 4),
                latency_ms=round(latency_ms, 2),
                tps=round(tps, 1),
                output_tokens=tokens,
                output_preview=preview,
                reason=sprint_reason,
                loaded=True,
            )
            report.results.append(result)

            # Close the adaptive loop the router already reads.
            await asyncio.to_thread(
                write_model_performance,
                model=model,
                quality_score=result.quality_score,
                task=self.task[:200],
                role=self.role,
                tps=result.tps,
                outcome="pass" if _ok_quality(result.quality_score) else "low",
            )
            await self._emit_product_update(result)

        return report

    # ── DataMesh emission (agent-operated event bus) ───────────────────────

    def _resident_ids(self) -> set[str]:
        """Current resident model ids — the daemons' pre-warmed fleet state."""
        from cohezion.inference import hotswap

        try:
            return {m.get("model_name", "") for m in hotswap.resident_models()}
        except Exception as exc:
            logger.debug("shootout: could not read resident fleet: %s", exc)
            return set()

    async def _bus_ref(self) -> EventBus | None:
        if self._bus is not None:
            return self._bus
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return None
        try:
            return await get_event_bus()
        except Exception as exc:
            logger.debug("shootout: event bus unavailable: %s", exc)
            return None

    async def _emit_product_update(self, result: ShootoutResult) -> None:
        """Publish a DATA_PRODUCT_UPDATED event for this candidate.

        DataMeshEventBridge subscribes to this type and persists it to
        SurrealDB ``data_product_event`` — the durable, replayable audit trail
        for the agent-operated architecture. Downstream consumers (router,
        dashboard, monitor) react to it live and/or on replay.
        """
        bus = await self._bus_ref()
        if bus is None:
            return

        product_id = f"inference.shootout.{self.role}.{result.model.lower().replace('.', '-')}"
        status = (
            DataProductStatus.ACTIVE
            if result.ok and _ok_quality(result.quality_score)
            else DataProductStatus.DEPRECATED
        )
        event = Event(
            type=EventType.DATA_PRODUCT_UPDATED,
            source="inference.model_shootout",
            payload={
                "product_id": product_id,
                "name": result.model,
                "domain": "inference",
                "status": status,
                "quality_tier": (
                    DataQualityTier.GOLD
                    if _ok_quality(result.quality_score)
                    else DataQualityTier.BRONZE
                ),
                "schema_version": PRODUCT_SCHEMA.version,
                "role": self.role,
                "quality_score": result.quality_score,
                "latency_ms": result.latency_ms,
                "tps": result.tps,
                "tasks": 1,
                "ok": result.ok,
                "reason": result.reason,
                "task": self.task[:120],
            },
        )
        try:
            if bus._running:
                await bus.publish(event)
            else:
                bus.publish_sync(event)
        except Exception as exc:
            logger.warning("shootout: failed to publish product update: %s", exc)


# ── SurrealDB writer (feeds the router's adaptive table) ───────────────────


def write_model_performance(
    model: str,
    quality_score: float,
    task: str = "",
    role: str = "code",
    tps: float = 0.0,
    outcome: str = "pass",
    temp_arm: str = "0.1",
) -> bool:
    """Append one row to SurrealDB `model_performance` (router-adaptive).

    ``fleet_roles._perf_scores()`` reads this table as
    ``SELECT model, math::mean(quality_score) FROM model_performance GROUP BY
    model`` and adds +25.0 * mean to role ranking. Writing here makes the
    router prefer this model on future role selection.
    """
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    row = {
        "model": model,
        "quality_score": quality_score,
        "task": task,
        "role": role,
        "temp_arm": temp_arm,
        "tps": tps,
        "outcome": outcome,
        "ts": ts,
    }
    surql = f"CREATE model_performance CONTENT {json.dumps(row)};"
    try:
        req = urllib.request.Request(
            SURREAL_URL,
            data=surql.encode(),
            headers={
                "surreal-ns": SURREAL_NS,
                "surreal-db": SURREAL_DB,
                "Content-Type": "text/plain",
                "Authorization": f"Basic {SURREAL_AUTH}",
            },
        )
        with urllib.request.urlopen(req, timeout=5) as r:  # noqa: S310
            from cohezion.storage.surreal_http import checked_statements

            code = r.status
            if code == 200:
                checked_statements(json.loads(r.read()), status_code=code)
        if code == 200:
            logger.info(
                "shootout: wrote model_performance row for %s (q=%.3f)", model, quality_score
            )
            return True
        logger.warning("shootout: SurrealDB returned HTTP %s for %s", code, model)
    except Exception as exc:
        logger.warning("shootout: SurrealDB write failed for %s: %s", model, exc)
    return False


# ── Convenience / CLI entry points ─────────────────────────────────────────


async def run_model_shootout(
    candidates: list[str] | None = None,
    **kwargs: Any,
) -> ShootoutReport:
    """One-shot quality-first shootout (DataMesh producer)."""
    return await ModelShootout(candidates=candidates, **kwargs).run()


def main() -> None:
    """CLI entry point."""
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(
        description="Quality-first local model shootout (hotswaps + DataMesh events + adapts)"
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=default_candidates(),
        help="Candidate model ids (must be in the :13305 catalog).",
    )
    parser.add_argument("--role", default="code", help="Router role label.")
    parser.add_argument("--runs", type=int, default=1, help="Runs per model (mean quality).")
    parser.add_argument(
        "--task",
        default=None,
        help="Prompt every candidate answers (default: code-review task).",
    )
    parser.add_argument(
        "--expected",
        nargs="+",
        default=None,
        help="Tokens a good answer must contain (quality = matched fraction).",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON report to stdout.")
    args = parser.parse_args()

    report = asyncio.run(
        run_model_shootout(
            candidates=args.models,
            task=args.task if args.task is not None else DEFAULT_TASK,
            expected_contains=args.expected if args.expected is not None else DEFAULT_EXPECTED,
            role=args.role,
            runs=args.runs,
        )
    )

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
        return

    print("\n=== Model Shootout (quality-first) ===")
    print(f"Task: {report.task[:80]}...")
    print("Ranked by quality_score:")
    for i, r in enumerate(report.quality_ranked(), 1):
        status = "LOADED" if r.loaded else "NOT-LOADED"
        print(
            f"  {i}. {r.model:40s} q={r.quality_score:.3f} "
            f"lat={r.latency_ms:.0f}ms tps={r.tps:.0f} [{status}]"
        )
        if not r.ok:
            print(f"      ! {r.reason}")
    print()


if __name__ == "__main__":
    main()
