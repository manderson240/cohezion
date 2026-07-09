"""OmniGauntlet — empirical V-model benchmark harness for the local model fleet.

Party mode: runs multiple challenger models CONCURRENTLY against the same task
(asyncio.gather = wall-clock = slowest, not sum).

Score formula:
  quality_ratio = keyword_hits / keyword_total   (0..1 proxy for output quality)
  score = quality_ratio * tps_actual             (quality-weighted throughput)

V-model tier alignment:
  Specify  → task suite (TASK_SUITE constant, 7 capability domains)
  Design   → model × role matrix (from local_fleet.FleetRole)
  Build    → parallel benchmark execution (run_gauntlet)
  Test     → 3-run mean ± σ (test_repeatability in gauntlet_test_hooks)
  Validate → champion vs. challenger (promote if ≥5% improvement)

Results are stored in ~/.cohezion/gauntlet_scores.json.
Champion promotion threshold: PROMOTION_THRESHOLD = 0.05 (5%).

Usage:
    import asyncio
    from cohezion.inference.gauntlet import run_gauntlet
    asyncio.run(run_gauntlet())  # benchmarks all roles, updates champions
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


logger = logging.getLogger(__name__)

OMNI_URL = "http://localhost:13305"
GAUNTLET_PATH = Path.home() / ".cohezion" / "gauntlet_scores.json"
PROMOTION_THRESHOLD = 0.05  # 5% required for champion replacement
BENCH_RUNS = 3  # mean over N runs for repeatability (V-model Test tier)


@dataclass
class BenchTask:
    name: str
    role: str  # FleetRole value (e.g. "code", "generation")
    prompt: str
    expected_keywords: list[str]  # presence check (case-insensitive)
    max_tokens: int = 60


@dataclass
class BenchResult:
    model_id: str
    task_name: str
    role: str
    ttft_seconds: float
    tps_actual: float
    keyword_hits: int
    keyword_total: int
    quality_ratio: float  # keyword_hits / keyword_total
    score: float  # quality_ratio * tps_actual
    run_id: int = 0


# ── Canonical 7-domain task suite ────────────────────────────────────────────
TASK_SUITE: list[BenchTask] = [
    BenchTask(
        name="code_fibonacci",
        role="code",
        prompt="Write a compact Python function that returns a list of Fibonacci numbers up to n.",
        expected_keywords=["def", "fibonacci", "return"],
        max_tokens=80,
    ),
    BenchTask(
        name="math_proof",
        role="code",
        prompt="Prove sqrt(2) is irrational. One paragraph.",
        expected_keywords=["assume", "rational", "contradiction"],
        max_tokens=80,
    ),
    BenchTask(
        name="short_route",
        role="router",
        prompt="Reply with one word only: is Python interpreted?",
        expected_keywords=["yes"],
        max_tokens=5,
    ),
    BenchTask(
        name="generation_summary",
        role="generation",
        prompt="In two sentences, explain why attention is O(n^2) in transformers.",
        expected_keywords=["attention", "token", "quadratic"],
        max_tokens=60,
    ),
    BenchTask(
        name="reasoning_transitive",
        role="reasoning",
        prompt="Step by step: if A→B and B→C, does A→C? Answer yes/no first.",
        expected_keywords=["yes", "transitive"],
        max_tokens=60,
    ),
    BenchTask(
        name="synthesis_brief",
        role="synthesis",
        prompt="In one sentence: what does the FLUME encoder do?",
        expected_keywords=["latent", "encode"],
        max_tokens=30,
    ),
    BenchTask(
        name="triage_label",
        role="triage",
        prompt="Label as code/text/math: 'x = sorted([3,1,2])'. One word only.",
        expected_keywords=["code"],
        max_tokens=5,
    ),
]


# ── HTTP helpers ──────────────────────────────────────────────────────────────


async def _call_model(
    model_id: str,
    prompt: str,
    max_tokens: int,
) -> tuple[float, float, str]:
    """POST to OmniRouter /api/v1/chat and return (ttft_s, tps, text).

    Returns ("", 0, 0) on error rather than raising so the gauntlet keeps running.
    """
    try:
        import httpx  # lazy import — test mocks replace this

        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "stream": False,
        }
        t0 = time.monotonic()
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{OMNI_URL}/api/v1/chat", json=payload)
            resp.raise_for_status()
        elapsed = time.monotonic() - t0
        data = resp.json()
        text: str = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        n_tokens = data.get("usage", {}).get("completion_tokens", max(1, len(text.split())))
        tps = n_tokens / max(elapsed, 0.001)
        # TTFT: for non-streaming we approximate as half the elapsed time
        ttft = elapsed / 2.0
        return ttft, tps, text
    except Exception as exc:
        logger.debug("gauntlet._call_model(%s) failed: %s", model_id, exc)
        return 0.0, 0.0, ""


def _score_result(task: BenchTask, ttft: float, tps: float, text: str) -> BenchResult:
    lower = text.lower()
    hits = sum(1 for kw in task.expected_keywords if kw.lower() in lower)
    total = max(1, len(task.expected_keywords))
    quality = hits / total
    return BenchResult(
        model_id="",  # filled by caller
        task_name=task.name,
        role=task.role,
        ttft_seconds=round(ttft, 3),
        tps_actual=round(tps, 1),
        keyword_hits=hits,
        keyword_total=total,
        quality_ratio=round(quality, 3),
        score=round(quality * tps, 2),
    )


# ── Core benchmark logic ──────────────────────────────────────────────────────


async def _bench_model_on_task(
    model_id: str,
    task: BenchTask,
    run_id: int = 0,
) -> BenchResult:
    ttft, tps, text = await _call_model(model_id, task.prompt, task.max_tokens)
    result = _score_result(task, ttft, tps, text)
    result.model_id = model_id
    result.run_id = run_id
    return result


async def _bench_role(
    role: str,
    challengers: list[str],
    tasks: list[BenchTask],
    runs: int = BENCH_RUNS,
) -> dict[str, float]:
    """Benchmark all challengers for a role across all matching tasks.

    Returns {model_id: mean_score} sorted descending.
    Party mode: all (model, task, run) combos run concurrently.
    """
    role_tasks = [t for t in tasks if t.role == role]
    if not role_tasks:
        return {}

    coros = [
        _bench_model_on_task(mid, task, run_id=r)
        for mid in challengers
        for task in role_tasks
        for r in range(runs)
    ]
    results: list[BenchResult] = await asyncio.gather(*coros)

    # Aggregate: mean score per model
    scores: dict[str, list[float]] = {mid: [] for mid in challengers}
    for r in results:
        if r.tps_actual > 0:  # skip error runs
            scores[r.model_id].append(r.score)

    return {mid: round(sum(s) / len(s), 3) if s else 0.0 for mid, s in scores.items()}


# ── Champion tracking ─────────────────────────────────────────────────────────


def _load_scores() -> dict:
    if GAUNTLET_PATH.exists():
        try:
            return json.loads(GAUNTLET_PATH.read_text())
        except Exception:
            pass
    return {}


def _save_scores(scores: dict) -> None:
    GAUNTLET_PATH.parent.mkdir(parents=True, exist_ok=True)
    GAUNTLET_PATH.write_text(json.dumps(scores, indent=2))


def _promote_if_better(
    scores: dict,
    role: str,
    new_scores: dict[str, float],
) -> tuple[str, bool]:
    """Return (champion_model_id, was_promoted).

    Promotion requires ≥5% improvement over the current champion score.
    """
    best_new = max(new_scores.items(), key=lambda kv: kv[1], default=(None, 0.0))
    best_model, best_score = best_new

    current = scores.get("champions", {}).get(role, {})
    current_score = current.get("score", 0.0)

    promoted = False
    if best_model and best_score > current_score * (1 + PROMOTION_THRESHOLD):
        scores.setdefault("champions", {})[role] = {
            "model_id": best_model,
            "score": best_score,
        }
        promoted = True
        logger.info(
            "Gauntlet: NEW CHAMPION role=%s model=%s score=%.2f (prev=%.2f)",
            role,
            best_model,
            best_score,
            current_score,
        )

    champion = scores.get("champions", {}).get(role, {}).get("model_id", best_model)
    return champion or "", promoted


# ── Public entry point ────────────────────────────────────────────────────────


async def run_gauntlet(
    roles: Sequence[str] | None = None,
    task_suite: list[BenchTask] | None = None,
    challengers_by_role: dict[str, list[str]] | None = None,
) -> dict[str, str]:
    """Run the full (or partial) gauntlet and return {role: champion_model_id}.

    Args:
        roles: Subset of FleetRole values to benchmark.  None = all roles.
        task_suite: Override the default TASK_SUITE.
        challengers_by_role: {role: [model_ids]}.  If None, uses fleet defaults.
    """
    from cohezion.inference.local_fleet import FleetRole, get_fleet

    fleet = get_fleet()
    suite = task_suite or TASK_SUITE
    scores = _load_scores()
    scores.setdefault("champions", {})
    scores.setdefault("history", [])

    active_roles = [r.value for r in FleetRole] if roles is None else list(roles)
    champions: dict[str, str] = {}

    for role in active_roles:
        # Default challengers: the canonical fleet model for this role,
        # plus any overrides from challengers_by_role.
        if challengers_by_role and role in challengers_by_role:
            challenger_ids = challengers_by_role[role]
        else:
            try:
                model = fleet.get(FleetRole(role))
                challenger_ids = [model.model_id]
            except (ValueError, KeyError):
                continue

        role_scores = await _bench_role(role, challenger_ids, suite)
        if not role_scores:
            continue

        champion, promoted = _promote_if_better(scores, role, role_scores)
        champions[role] = champion

        # History entry for trending
        scores["history"].append(
            {
                "role": role,
                "scores": role_scores,
                "promoted": promoted,
            }
        )

    _save_scores(scores)
    return champions


def get_champion(role: str) -> str | None:
    """Return the current champion model_id for a role (None if never benchmarked)."""
    scores = _load_scores()
    entry = scores.get("champions", {}).get(role)
    return entry.get("model_id") if entry else None
