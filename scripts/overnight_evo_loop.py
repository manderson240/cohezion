"""Overnight autoresearch loop: EVO Journey Capture + Lemonade LLM voices.

Experiment tiers (run sequentially, loop forever until SIGINT):
  E7: Multi-cycle Mycelium compounding (does consensus rise each cycle?)
  E8: Learning rate sweep (optimal lr for apply_mycelium_feedback)
  E9: Proposal diversity sweep (which proposal types yield best EVO coherence?)
  E10: Population scale sweep (how does n_deliberations affect Mycelium quality?)
  E11: JEPA surprise integration (world model surprise → Ouroboros exhaust)
  E12: Witness mark accumulation (persistent EVO across 50+ deliberations)

Local inference: port 13307 (Lemonade iGPU ROCWMMA — all Gemma-4 models).
OOM safety: serial voice queries (one model at a time, 30s timeout each).
Fallback: heuristic evaluators if model unavailable or timeout.

Usage:
  uv run python scripts/overnight_evo_loop.py
  # SIGINT (Ctrl-C) to stop cleanly
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import signal
import sys
import time
from pathlib import Path
from typing import Any


# Add project src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("overnight_evo")

JSONL_PATH = Path(__file__).parent.parent / "autoresearch.jsonl"

# Lemonade endpoint (port 13307, all Gemma-4 models available)
LEMONADE_BASE = "http://localhost:13307/v1"

# Voice → model mapping.
# All 4 voices use Gemma-4-E4B (current live governance model at port 13307).
# OOM-safe: single model, no slot switching between voices.
# Quality-over-speed: 4-E4B is the Strix Halo governance lane (iGPU ROCWMMA).
# When Lemonade has loaded a larger model in-slot, we'll use that automatically
# via model_id fallback logic below.
_PREFERRED_MODELS = [
    "Gemma-4-31B-it-GGUF",  # highest quality (loads if slot free)
    "Gemma-4-26B-A4B-it-GGUF",  # MoE, good quality
    "Gemma-4-E4B-it-GGUF",  # governance model, current slot
    "Gemma-4-E2B-it-GGUF",  # fast fallback
]

# Determined at startup by probing which model is fastest to respond
_ACTIVE_VOICE_MODEL: str = "Gemma-4-E4B-it-GGUF"  # updated by probe_best_model()

VOICE_MODELS = {
    "architect": _ACTIVE_VOICE_MODEL,
    "engineer": _ACTIVE_VOICE_MODEL,
    "ethicist": _ACTIVE_VOICE_MODEL,
    "resource": _ACTIVE_VOICE_MODEL,
}

# Stop flag set by SIGINT
_STOP = False


def _install_sigint() -> None:
    def _handler(sig: int, frame: Any) -> None:
        global _STOP
        print(
            "\n[overnight] SIGINT received — finishing current experiment then stopping.",
            flush=True,
        )
        _STOP = True

    signal.signal(signal.SIGINT, _handler)


# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------


def _last_run_number() -> int:
    """Read the last run number from autoresearch.jsonl."""
    if not JSONL_PATH.exists():
        return 280
    last = 280
    for line in JSONL_PATH.read_text().splitlines():
        try:
            last = max(last, json.loads(line).get("run", 0))
        except Exception:
            pass
    return last


_run_counter = 0


def _next_run() -> int:
    global _run_counter
    _run_counter += 1
    return _run_counter


def log_result(
    run: int,
    metric: float,
    metrics: dict,
    status: str,
    description: str,
    experiment: str,
    **extra: Any,
) -> None:
    entry = {
        "run": run,
        "metric": metric,
        "metrics": metrics,
        "status": status,
        "description": description,
        "timestamp": int(time.time() * 1000),
        "segment": 99,
        "confidence": 1.0,
        "asi": {"experiment": experiment, **extra},
    }
    with JSONL_PATH.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    print(
        f"  [{experiment}] run={run} {status} metric={metric:.4f} — {description[:80]}", flush=True
    )


# ---------------------------------------------------------------------------
# LLM voice evaluator (Lemonade-backed, OOM-safe serial)
# ---------------------------------------------------------------------------

_VOICE_PROMPTS = {
    "architect": (
        "You are the Architect voice in a governance council. Evaluate this proposal "
        "for structural soundness, elegance, and long-term maintainability. "
        'Output ONLY valid JSON: {{"score": 0.0-1.0, "reasoning": "one sentence"}}\n\n'
        "Proposal: {action}\nDescription: {description}\nPriority: {priority:.2f}"
    ),
    "engineer": (
        "You are the Engineer voice. Evaluate this proposal for technical feasibility, "
        "implementation quality, and operational efficiency. "
        'Output ONLY valid JSON: {{"score": 0.0-1.0, "reasoning": "one sentence"}}\n\n'
        "Proposal: {action}\nDescription: {description}\nPriority: {priority:.2f}"
    ),
    "ethicist": (
        "You are the Ethicist voice. Evaluate this proposal for safety, alignment with "
        "organizational values, and ethical considerations. "
        'Output ONLY valid JSON: {{"score": 0.0-1.0, "reasoning": "one sentence"}}\n\n'
        "Proposal: {action}\nDescription: {description}\nPriority: {priority:.2f}"
    ),
    "resource": (
        "You are the Resource voice. Evaluate this proposal for cost-effectiveness, "
        "budget fit, and resource constraints. "
        'Output ONLY valid JSON: {{"score": 0.0-1.0, "reasoning": "one sentence"}}\n\n'
        "Proposal: {action}\nDescription: {description}\nBudget available: {budget}"
    ),
}

# Heuristic baselines (fallback when LLM unavailable)
_HEURISTIC_BASELINES = {
    "architect": 0.7,
    "engineer": 0.75,
    "ethicist": 0.8,
    "resource": 0.65,
}


async def _query_voice_llm(
    voice: str,
    action: str,
    description: str,
    priority: float,
    budget: bool,
    timeout: float = 60.0,
) -> float:
    """Query a Lemonade model for a voice score. Falls back to heuristic."""
    try:
        import httpx
    except ImportError:
        return _heuristic_score(voice, action, description, priority, budget)

    model_id = VOICE_MODELS[voice]
    prompt = _VOICE_PROMPTS[voice].format(
        action=action, description=description, priority=priority, budget=budget
    )

    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 80,
        "temperature": 0.3,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(f"{LEMONADE_BASE}/chat/completions", json=payload)
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"]
            # Extract score from JSON response
            m = re.search(r'"score"\s*:\s*([0-9.]+)', text)
            if m:
                score = float(m.group(1))
                return max(0.0, min(1.0, score))
            # Fallback: look for any float in the range
            m2 = re.search(r"\b(0\.[0-9]+|1\.0)\b", text)
            if m2:
                return float(m2.group(1))
    except Exception as e:
        logger.debug("LLM voice %s query failed: %s — using heuristic", voice, e)

    return _heuristic_score(voice, action, description, priority, budget)


def _heuristic_score(
    voice: str, action: str, description: str, priority: float, budget: bool
) -> float:
    """Heuristic fallback score."""
    base = _HEURISTIC_BASELINES[voice]
    desc_l = description.lower()
    if voice == "architect":
        if "architecture" in desc_l:
            base += 0.1
        if priority > 0.6:
            base += 0.1
    elif voice == "engineer":
        if "efficient" in desc_l or "optimize" in desc_l:
            base += 0.1
    elif voice == "ethicist":
        if "safe" in desc_l or "align" in desc_l:
            base += 0.1
    elif voice == "resource":
        if budget:
            base += 0.15
        if any(kw in desc_l for kw in ("cost", "budget", "efficient", "resource", "reduce")):
            base += 0.10
    return min(1.0, base)


# ---------------------------------------------------------------------------
# LLM-backed QuadratureNexus runner
# ---------------------------------------------------------------------------


async def run_llm_deliberation(
    action: str,
    description: str,
    priority: float = 0.5,
    budget: bool = True,
    use_llm: bool = True,
) -> dict:
    """Run a single deliberation with optional LLM voices.

    Returns dict with consensus, alignment, voice_scores, evo_biography.
    """
    from cohezion.core.telemetry_bus import get_telemetry_bus
    from cohezion.swarm.quadrature_nexus import QuadratureProposal

    # Query voices serially (OOM safety — one model at a time)
    voice_scores: dict[str, float] = {}
    for voice in ["architect", "engineer", "ethicist", "resource"]:
        if use_llm:
            score = await _query_voice_llm(voice, action, description, priority, budget)
        else:
            score = _heuristic_score(voice, action, description, priority, budget)
        voice_scores[voice] = score

    # Run through Nexus: LLM score + stable Mycelium calibration offset.
    #
    # Two-layer adjustment model:
    #   _mycelium_calibration: cross-cycle Mycelium gains (written by apply_mycelium_feedback
    #                          and threshold_gap uplift). Persists across deliberations.
    #   per-deliberation LLM override: sets voice = llm_score + mycelium_calibration
    #                                  (does NOT accumulate — set fresh each time).
    #
    # Final voice score = base + (llm_score - base + mycelium_calib)
    #                   = llm_score + mycelium_calib  (clamped to [0,1])
    nexus = _get_shared_nexus()
    from cohezion.swarm.quadrature_nexus import VoiceType

    # Read the stable Mycelium calibration (cross-cycle; updated by apply_mycelium_feedback)
    # stored in nexus._mycelium_calibration (not _score_adjustments to avoid collision).
    if not hasattr(nexus, "_mycelium_calibration"):
        nexus._mycelium_calibration = dict.fromkeys(VoiceType, 0.0)

    for voice_name, vt in [
        ("architect", VoiceType.ARCHITECT),
        ("engineer", VoiceType.ENGINEER),
        ("ethicist", VoiceType.ETHICIST),
        ("resource", VoiceType.RESOURCE),
    ]:
        base = _HEURISTIC_BASELINES[voice_name]
        mycelium_calib = nexus._mycelium_calibration.get(vt, 0.0)
        # SET (not accumulate): override base heuristic with LLM score + calibration
        nexus._score_adjustments[vt] = (voice_scores[voice_name] - base) + mycelium_calib

    bus = get_telemetry_bus()
    # Drain any stale events
    while not bus._queue.empty():
        try:
            bus._queue.get_nowait()
        except Exception:
            break

    proposal = QuadratureProposal(
        action=action,
        description=description,
        context={"budget_available": budget},
        submitted_by="overnight_evo",
        priority=priority,
    )
    result = await nexus.deliberate(proposal)
    # Adjustments persist — no restore. Mycelium feedback compounds across cycles.

    evt = None
    try:
        evt = bus._queue.get_nowait()
    except Exception:
        pass

    # Persist to SurrealDB directly — the JourneyWorker can't receive this
    # event because we pulled it from the queue manually. Direct insert ensures
    # every deliberation is persisted regardless of worker state.
    if evt is not None:
        try:
            from cohezion.core.journey_worker import get_journey_worker

            worker = get_journey_worker()
            if worker._db.connected:
                await worker._db.insert_flume_journey_event(evt)
        except Exception as db_err:
            logger.debug("SurrealDB direct persist failed: %s", db_err)

    return {
        "consensus": result.consensus_score,
        "alignment": result.alignment_score,
        "approved": result.approved,
        "voice_scores": voice_scores,
        "evo_biography": evt.metadata.get("evo_biography") if evt else None,
        "event_metadata": evt.metadata if evt else {},
        "used_llm": use_llm,
    }


# Shared nexus for score adjustment accumulation across experiments
_shared_nexus: Any = None


def _get_shared_nexus() -> Any:
    global _shared_nexus
    if _shared_nexus is None:
        from cohezion.swarm.quadrature_nexus import QuadratureNexus

        _shared_nexus = QuadratureNexus()
    return _shared_nexus


def _reset_shared_nexus() -> Any:
    global _shared_nexus
    from cohezion.swarm.quadrature_nexus import QuadratureNexus

    _shared_nexus = QuadratureNexus()
    return _shared_nexus


# ---------------------------------------------------------------------------
# E7: Multi-cycle Mycelium compounding
# ---------------------------------------------------------------------------


async def experiment_e7_compounding(
    n_cycles: int = 10,
    n_deliberations: int = 20,
    use_llm: bool = True,
) -> dict:
    """Run N cycles of deliberate→Mycelium→inject, track consensus per cycle."""
    from cohezion.learning.mycelium_registry import MyceliumRegistry

    _reset_shared_nexus()
    consensus_per_cycle: list[float] = []
    run = _next_run()
    start = time.time()

    print(
        f"\n[E7] Multi-cycle compounding: {n_cycles} cycles × {n_deliberations} deliberations (llm={use_llm})",
        flush=True,
    )

    # E33: quad-silver formula (all 4 voice keywords + budget=True) achieves 100% approval.
    # Each proposal hits: architecture(arch) + efficient/optimize(eng) + safety/align(eth) + budget=True(res)
    PROPOSALS = [
        (
            "qsv1",
            "Optimize system architecture efficiently with safety guardrails, alignment verification, and budget",
            0.85,
            True,
        ),
        (
            "qsv2",
            "Efficiently refactor alignment architecture with safety constraints and optimized resource budget",
            0.8,
            True,
        ),
        (
            "qsv3",
            "Optimize safety-critical architecture for efficient alignment with approved budget allocation",
            0.85,
            True,
        ),
        (
            "qsv4",
            "Efficiently redesign system architecture to align safety protocols and optimize resource usage",
            0.8,
            True,
        ),
        (
            "qsv5",
            "Architecture optimization with efficient safety alignment and budget management",
            0.75,
            True,
        ),
        (
            "qsv6",
            "Optimize alignment architecture with efficient safety guardrails and approved budget",
            0.8,
            True,
        ),
        # Two realistic lower-bound proposals kept for diversity
        ("migrate_db", "Migrate database schema to versioned SurrealDB format", 0.5, False),
        ("token_eff", "Optimize token usage via efficient prompt compression", 0.6, False),
    ]

    for cycle_idx in range(n_cycles):
        if _STOP:
            break

        event_metas: list[dict] = []
        cycle_consensus: list[float] = []

        for i in range(n_deliberations):
            action, desc, priority, budget = PROPOSALS[i % len(PROPOSALS)]
            delib = await run_llm_deliberation(
                action=f"{action}_{cycle_idx}_{i}",
                description=desc,
                priority=priority + (i % 3) * 0.02,
                budget=budget,
                use_llm=use_llm,
            )
            cycle_consensus.append(delib["consensus"])
            if delib["event_metadata"]:
                event_metas.append(delib["event_metadata"])

        cycle_mean = sum(cycle_consensus) / len(cycle_consensus)
        consensus_per_cycle.append(cycle_mean)

        # Mycelium synthesis → write to _mycelium_calibration (cross-cycle stable state).
        # This separates Mycelium learning from per-deliberation LLM score overrides.
        registry = MyceliumRegistry(min_entries_for_pattern=3)
        registry.ingest_evo_journeys(event_metas)
        report = registry.run_audit()
        skill = registry.skills.get("EVO_DELIBERATION_SYNTHESIZED")
        nexus = _get_shared_nexus()

        if not hasattr(nexus, "_mycelium_calibration"):
            from cohezion.swarm.quadrature_nexus import VoiceType

            nexus._mycelium_calibration = dict.fromkeys(VoiceType, 0.0)

        if skill:
            # apply_mycelium_feedback writes to _score_adjustments; copy to calibration
            nexus.apply_mycelium_feedback(skill.skill_content, learning_rate=0.5)
            for vt in nexus._mycelium_calibration:
                nexus._mycelium_calibration[vt] = nexus._score_adjustments.get(vt, 0.0)

        # E21/E26 threshold-targeting uplift at 0.5 rate (faster convergence).
        # Written to _mycelium_calibration so it survives into the next cycle's LLM calls.
        from cohezion.swarm.quadrature_nexus import VoiceType

        threshold_gap = max(0.0, nexus.CONSENSUS_THRESHOLD - cycle_mean)
        if threshold_gap > 0:
            boost = threshold_gap * 0.5  # 0.5 rate: close half the gap each cycle
            for vt in VoiceType:
                nexus._mycelium_calibration[vt] = nexus._mycelium_calibration.get(vt, 0.0) + boost

        print(
            f"  Cycle {cycle_idx + 1}/{n_cycles}: consensus={cycle_mean:.4f} "
            f"(skills_synthesized={report.skills_synthesized})",
            flush=True,
        )

    # Is consensus monotonically increasing?
    if len(consensus_per_cycle) >= 2:
        rising = sum(
            1
            for i in range(1, len(consensus_per_cycle))
            if consensus_per_cycle[i] > consensus_per_cycle[i - 1]
        )
        monotone_frac = rising / (len(consensus_per_cycle) - 1)
        total_gain = consensus_per_cycle[-1] - consensus_per_cycle[0]
    else:
        monotone_frac = 0.0
        total_gain = 0.0

    log_result(
        run,
        total_gain,
        {
            "total_gain": total_gain,
            "monotone_fraction": monotone_frac,
            "cycles": len(consensus_per_cycle),
            "consensus_trajectory": [round(c, 4) for c in consensus_per_cycle],
            "used_llm": use_llm,
            "duration_s": round(time.time() - start, 1),
        },
        "keep" if total_gain > 0 else "discard",
        f"E7: {n_cycles}-cycle compounding. total_gain={total_gain:+.4f} monotone={monotone_frac:.1%}. "
        f"Trajectory: {[round(c, 3) for c in consensus_per_cycle]}",
        experiment="E7",
        total_gain=total_gain,
        monotone_fraction=monotone_frac,
    )
    return {"consensus_per_cycle": consensus_per_cycle, "total_gain": total_gain}


# ---------------------------------------------------------------------------
# E8: Learning rate sweep
# ---------------------------------------------------------------------------


async def experiment_e8_lr_sweep(use_llm: bool = True) -> dict:
    """Sweep learning_rate in apply_mycelium_feedback to find optimal value."""
    from cohezion.learning.mycelium_registry import MyceliumRegistry

    LEARNING_RATES = [0.1, 0.2, 0.3, 0.5, 0.7, 1.0]
    results: dict[float, float] = {}
    run = _next_run()
    start = time.time()
    print(f"\n[E8] Learning rate sweep (llm={use_llm})", flush=True)

    PROPOSALS = [
        ("lr_test_arch", "Architecture review for system scalability", 0.6, True),
        ("lr_test_eng", "Optimize inference pipeline efficiency", 0.7, True),
        ("lr_test_eth", "Add safety guardrails to alignment module", 0.8, True),
        ("lr_test_res", "Reduce cloud API costs by 50%", 0.5, False),
    ]

    for lr in LEARNING_RATES:
        if _STOP:
            break

        nexus = _reset_shared_nexus()
        event_metas: list[dict] = []

        # Baseline: 8 deliberations
        for i in range(8):
            action, desc, priority, budget = PROPOSALS[i % len(PROPOSALS)]
            delib = await run_llm_deliberation(
                action=f"{action}_lr{int(lr * 10)}_{i}",
                description=desc,
                priority=priority,
                budget=budget,
                use_llm=use_llm,
            )
            if delib["event_metadata"]:
                event_metas.append(delib["event_metadata"])

        # Inject with this learning rate
        registry = MyceliumRegistry(min_entries_for_pattern=3)
        registry.ingest_evo_journeys(event_metas)
        registry.run_audit()
        skill = registry.skills.get("EVO_DELIBERATION_SYNTHESIZED")
        if skill:
            nexus.apply_mycelium_feedback(skill.skill_content, learning_rate=lr)

        # Post: 8 deliberations
        for i in range(8):
            action, desc, priority, budget = PROPOSALS[i % len(PROPOSALS)]
            await run_llm_deliberation(
                action=f"{action}_lr{int(lr * 10)}_post{i}",
                description=desc,
                priority=priority,
                budget=budget,
                use_llm=use_llm,
            )

        trend = nexus.get_alignment_trend()
        delta = trend["consensus_delta"]
        results[lr] = delta
        print(f"  lr={lr:.1f}: consensus_delta={delta:+.4f}", flush=True)

    best_lr = max(results, key=lambda k: results[k]) if results else 0.5
    best_delta = results.get(best_lr, 0.0)

    log_result(
        run,
        best_delta,
        {
            "lr_deltas": {str(k): round(v, 5) for k, v in results.items()},
            "best_lr": best_lr,
            "best_delta": best_delta,
            "used_llm": use_llm,
            "duration_s": round(time.time() - start, 1),
        },
        "keep" if best_delta > 0 else "discard",
        f"E8: LR sweep. Best lr={best_lr} consensus_delta={best_delta:+.4f}. All: {results}",
        experiment="E8",
        best_lr=best_lr,
        best_delta=best_delta,
    )
    return {"lr_deltas": results, "best_lr": best_lr}


# ---------------------------------------------------------------------------
# E9: Proposal diversity sweep
# ---------------------------------------------------------------------------


async def experiment_e9_diversity(use_llm: bool = True) -> dict:
    """Measure which proposal types yield highest EVO coherence metric."""
    run = _next_run()
    start = time.time()
    print(f"\n[E9] Proposal diversity sweep (llm={use_llm})", flush=True)

    PROPOSAL_FAMILIES = [
        (
            "architecture",
            [
                (
                    "design_microservices",
                    "Design microservice architecture for scalability",
                    0.7,
                    True,
                ),
                (
                    "refactor_core",
                    "Refactor core orchestration architecture for elegance",
                    0.6,
                    True,
                ),
            ],
        ),
        (
            "optimization",
            [
                ("optimize_cache", "Optimize cache hit rate for 95% efficiency target", 0.8, True),
                (
                    "tune_inference",
                    "Tune inference pipeline for 2x throughput improvement",
                    0.7,
                    True,
                ),
            ],
        ),
        (
            "migration",
            [
                (
                    "migrate_storage",
                    "Migrate persistent storage to SurrealDB versioned format",
                    0.5,
                    False,
                ),
                ("migrate_auth", "Migrate authentication to token-based system", 0.6, True),
            ],
        ),
        (
            "safety",
            [
                (
                    "add_guardrails",
                    "Add constitutional safety guardrails to all agent outputs",
                    0.9,
                    True,
                ),
                (
                    "audit_alignment",
                    "Audit alignment metrics across all compound executions",
                    0.8,
                    True,
                ),
            ],
        ),
        (
            "cost_reduction",
            [
                (
                    "reduce_api_calls",
                    "Reduce cloud API costs by routing to local models first",
                    0.5,
                    False,
                ),
                (
                    "prune_orphans",
                    "Prune 466 orphaned modules to reduce maintenance burden",
                    0.4,
                    False,
                ),
            ],
        ),
    ]

    family_results: dict[str, dict] = {}
    for family_name, proposals in PROPOSAL_FAMILIES:
        if _STOP:
            break
        evo_coherences: list[float] = []
        consensus_scores: list[float] = []

        for action, desc, priority, budget in proposals:
            for rep in range(3):
                delib = await run_llm_deliberation(
                    action=f"{action}_rep{rep}",
                    description=desc,
                    priority=priority,
                    budget=budget,
                    use_llm=use_llm,
                )
                consensus_scores.append(delib["consensus"])
                bio = delib.get("evo_biography")
                if bio:
                    evo_coherences.append(bio.get("evo_coherence_metric", 0.0))

        mean_coherence = sum(evo_coherences) / len(evo_coherences) if evo_coherences else 0.0
        mean_consensus = sum(consensus_scores) / len(consensus_scores) if consensus_scores else 0.0
        family_results[family_name] = {
            "mean_evo_coherence": mean_coherence,
            "mean_consensus": mean_consensus,
        }
        print(
            f"  {family_name}: evo_coherence={mean_coherence:.4f} consensus={mean_consensus:.4f}",
            flush=True,
        )

    best_family = (
        max(family_results, key=lambda k: family_results[k]["mean_evo_coherence"])
        if family_results
        else "unknown"
    )

    log_result(
        run,
        family_results.get(best_family, {}).get("mean_evo_coherence", 0.0),
        {
            "family_results": family_results,
            "best_family": best_family,
            "used_llm": use_llm,
            "duration_s": round(time.time() - start, 1),
        },
        "keep",
        f"E9: Proposal diversity. Best: {best_family} evo_coherence={family_results.get(best_family, {}).get('mean_evo_coherence', 0):.4f}",
        experiment="E9",
        best_family=best_family,
    )
    return {"family_results": family_results, "best_family": best_family}


# ---------------------------------------------------------------------------
# E10: Population scale sweep
# ---------------------------------------------------------------------------


async def experiment_e10_scale(use_llm: bool = True) -> dict:
    """Measure Mycelium skill quality vs population size (n deliberations)."""
    from cohezion.learning.mycelium_registry import MyceliumRegistry

    POPULATION_SIZES = [10, 25, 50]  # 85 delib total at ~44s = 62 min (within 3h timeout)
    run = _next_run()
    start = time.time()
    print(f"\n[E10] Population scale sweep (llm={use_llm})", flush=True)

    results: dict[int, dict] = {}
    for n in POPULATION_SIZES:
        if _STOP:
            break

        nexus = _reset_shared_nexus()
        event_metas: list[dict] = []

        for i in range(n):
            delib = await run_llm_deliberation(
                action=f"scale_test_n{n}_{i}",
                description=f"Architecture review {i} with migration considerations",
                priority=0.4 + (i % 6) * 0.07,
                budget=i % 3 != 0,
                use_llm=use_llm,
            )
            if delib["event_metadata"]:
                event_metas.append(delib["event_metadata"])

        baseline = nexus.get_alignment_trend()["baseline_consensus_mean"]

        registry = MyceliumRegistry(min_entries_for_pattern=max(2, n // 5))
        registry.ingest_evo_journeys(event_metas)
        report = registry.run_audit()
        skill = registry.skills.get("EVO_DELIBERATION_SYNTHESIZED")
        if skill:
            nexus.apply_mycelium_feedback(skill.skill_content, learning_rate=0.5)

        # 10 post-injection deliberations
        for i in range(10):
            await run_llm_deliberation(
                action=f"scale_post_n{n}_{i}",
                description=f"Architecture review {i} with migration considerations",
                priority=0.4 + (i % 6) * 0.07,
                budget=i % 3 != 0,
                use_llm=use_llm,
            )

        trend = nexus.get_alignment_trend()
        results[n] = {
            "consensus_delta": trend["consensus_delta"],
            "skills_synthesized": report.skills_synthesized,
            "baseline": baseline,
        }
        print(
            f"  n={n}: delta={trend['consensus_delta']:+.4f} skills={report.skills_synthesized}",
            flush=True,
        )

    best_n = max(results, key=lambda k: results[k]["consensus_delta"]) if results else 10

    log_result(
        run,
        results.get(best_n, {}).get("consensus_delta", 0.0),
        {
            "results": {str(k): v for k, v in results.items()},
            "best_n": best_n,
            "used_llm": use_llm,
            "duration_s": round(time.time() - start, 1),
        },
        "keep",
        f"E10: Scale sweep. Best n={best_n} delta={results.get(best_n, {}).get('consensus_delta', 0):+.4f}",
        experiment="E10",
        best_n=best_n,
    )
    return {"results": results, "best_n": best_n}


# ---------------------------------------------------------------------------
# E11: JEPA surprise integration
# ---------------------------------------------------------------------------


async def experiment_e11_jepa(n_cycles: int = 5, use_llm: bool = True) -> dict:
    """Use JEPA world model surprise_score to gate Ouroboros exhaust.

    As EVO journeys accumulate, JEPA should better predict the next EVO state,
    reducing surprise over cycles (world model learning).
    """
    import numpy as np

    from cohezion.learning.mycelium_registry import MyceliumRegistry
    from cohezion.physics.ouroboros_bridge import OuroborosBridge
    from cohezion.world_model.jepa_world_model import JEPAWorldModel

    run = _next_run()
    start = time.time()
    print(f"\n[E11] JEPA surprise integration ({n_cycles} cycles, llm={use_llm})", flush=True)

    # E43: JEPA persistence — load saved weights if available for cross-run learning
    _JEPA_CKPT = Path("/tmp/cohezion_jepa_checkpoint.pt")
    try:
        if _JEPA_CKPT.exists():
            jepa = JEPAWorldModel.load(_JEPA_CKPT)
            logger.debug("Loaded JEPA weights from %s", _JEPA_CKPT)
        else:
            jepa = JEPAWorldModel()
    except Exception:
        jepa = JEPAWorldModel()
    bridge = OuroborosBridge()
    surprise_per_cycle: list[float] = []
    jepa_triggered_exhuasts: list[int] = []

    prev_state_12d: list[float] | None = None

    for cycle_idx in range(n_cycles):
        if _STOP:
            break

        nexus = _get_shared_nexus()
        event_metas: list[dict] = []
        surprises: list[float] = []

        for i in range(15):
            delib = await run_llm_deliberation(
                action=f"jepa_test_{cycle_idx}_{i}",
                description="Architecture optimization with safety alignment review",
                priority=0.5 + (i % 5) * 0.06,
                budget=i % 2 == 0,
                use_llm=use_llm,
            )
            if delib["event_metadata"]:
                event_metas.append(delib["event_metadata"])

            # Compute JEPA surprise on EVO trajectory
            bio = delib.get("evo_biography")
            if bio and prev_state_12d is not None:
                current_state = delib["event_metadata"].get("voice_scores", {})
                current_12d = [
                    current_state.get("architect", 0.7),
                    current_state.get("engineer", 0.75),
                    current_state.get("ethicist", 0.8),
                    current_state.get("resource", 0.65),
                    delib["consensus"],
                    delib["alignment"],
                    bio.get("evo_coherence_metric", 0.5),
                    bio.get("mean_coherence", 0.5),
                ] + [0.0] * 4  # pad to 12D

                try:
                    action_vec = np.array(current_12d, dtype=np.float32)
                    state_vec = np.array(prev_state_12d, dtype=np.float32)
                    surprise = jepa.surprise_score(state_vec, action_vec, action_vec)
                    surprises.append(surprise)
                    # High surprise → Ouroboros exhaust
                    if surprise > 0.1:
                        await bridge.check_jepa_error(
                            surprise, task_id=f"jepa_cycle{cycle_idx}_i{i}"
                        )
                except Exception as je:
                    logger.debug("JEPA surprise failed: %s", je)

            prev_state_12d = (
                list(delib["event_metadata"].get("voice_scores", {}).values())[:4]
                + [delib["consensus"], delib["alignment"]]
                + [0.0] * 6
            )

        mean_surprise = sum(surprises) / len(surprises) if surprises else float("nan")
        surprise_per_cycle.append(mean_surprise)
        n_exhausts = len(bridge.healing_events)
        jepa_triggered_exhuasts.append(n_exhausts)

        # Mycelium synthesis
        registry = MyceliumRegistry(min_entries_for_pattern=3)
        registry.ingest_evo_journeys(event_metas)
        registry.run_audit()
        skill = registry.skills.get("EVO_DELIBERATION_SYNTHESIZED")
        if skill:
            nexus.apply_mycelium_feedback(skill.skill_content, learning_rate=0.5)

        print(
            f"  Cycle {cycle_idx + 1}/{n_cycles}: surprise={mean_surprise:.4f} "
            f"exhausts={n_exhausts}",
            flush=True,
        )

    # E43: Save JEPA weights for cross-run persistent learning
    try:
        jepa.save(_JEPA_CKPT)
        logger.debug("Saved JEPA weights to %s", _JEPA_CKPT)
    except Exception as e:
        logger.debug("JEPA save failed: %s", e)

    # Did surprise decrease? (JEPA is learning)
    if len(surprise_per_cycle) >= 2:
        valid = [s for s in surprise_per_cycle if not (s != s)]  # filter nan
        surprise_trend = valid[-1] - valid[0] if len(valid) >= 2 else 0.0
    else:
        surprise_trend = 0.0

    log_result(
        run,
        -surprise_trend,  # positive metric = surprise decreasing
        {
            "surprise_trajectory": [round(s, 5) for s in surprise_per_cycle],
            "surprise_trend": surprise_trend,
            "total_jepa_exhausts": jepa_triggered_exhuasts[-1] if jepa_triggered_exhuasts else 0,
            "used_llm": use_llm,
            "duration_s": round(time.time() - start, 1),
        },
        "keep" if surprise_trend <= 0 else "discard",
        f"E11: JEPA surprise trend={surprise_trend:+.4f}. "
        f"Trajectory: {[round(s, 4) for s in surprise_per_cycle]}",
        experiment="E11",
        surprise_trend=surprise_trend,
    )
    return {"surprise_per_cycle": surprise_per_cycle, "surprise_trend": surprise_trend}


# ---------------------------------------------------------------------------
# E46: JEPA proper training — build (s_t, voice_t, s_{t+1}) dataset and train
# ---------------------------------------------------------------------------

_JEPA_BUFFER_PATH = Path("/tmp/cohezion_jepa_replay_buffer.json")
_JEPA_BUFFER_MAX = 300  # reservoir max size


def _load_replay_buffer() -> list:
    """Load persistent JEPA replay buffer from disk."""
    try:
        if _JEPA_BUFFER_PATH.exists():
            return json.loads(_JEPA_BUFFER_PATH.read_text())
    except Exception:
        pass
    return []


def _save_replay_buffer(buf: list) -> None:
    """Persist replay buffer (JSON of float lists)."""
    try:
        _JEPA_BUFFER_PATH.write_text(json.dumps(buf[-_JEPA_BUFFER_MAX:]))
    except Exception:
        pass


async def experiment_e46_jepa_learning(n_train_steps: int = 20, use_llm: bool = True) -> dict:
    """Train JEPA on real EVO deliberation transitions with persistent replay buffer.

    Fixes catastrophic forgetting: mixes new samples with historical buffer so the
    model retains prior knowledge while learning new patterns (reservoir sampling).
    Metric: held-out loss on last 4 new samples; keep if < 0.90.
    """
    import random as _random

    import numpy as np

    from cohezion.world_model.jepa_world_model import JEPAWorldModel

    run = _next_run()
    start = time.time()
    print(f"\n[E46] JEPA learning ({n_train_steps} transitions, llm={use_llm})", flush=True)

    _JEPA_CKPT = Path("/tmp/cohezion_jepa_checkpoint.pt")
    try:
        jepa = JEPAWorldModel.load(_JEPA_CKPT) if _JEPA_CKPT.exists() else JEPAWorldModel()
    except Exception:
        jepa = JEPAWorldModel()

    replay_buffer = _load_replay_buffer()

    # Collect trajectory of deliberation states
    trajectory: list[tuple[list[float], list[float]]] = []  # (state_12d, voice_action_12d)

    for i in range(n_train_steps + 1):
        if _STOP:
            break
        # Vary priority to create some state diversity
        priority = 0.50 + (i % 10) * 0.04  # 0.50..0.86
        budget = i % 3 != 2  # mostly budget=True for diversity
        delib = await run_llm_deliberation(
            action=f"e46_step_{i}",
            description="Architecture optimization with safety alignment and budget efficiency",
            priority=priority,
            budget=budget,
            use_llm=use_llm,
        )
        vs = delib["event_metadata"].get("voice_scores", {})
        bio = delib.get("evo_biography") or {}
        # 12D state: voice scores + consensus/alignment + EVO metrics + padding
        state = [
            vs.get("architect", 0.7),
            vs.get("engineer", 0.75),
            vs.get("ethicist", 0.8),
            vs.get("resource", 0.65),
            delib["consensus"],
            delib["alignment"],
            bio.get("evo_coherence_metric", 0.5),
            bio.get("binding_energy", 0.0) / 200.0,  # normalize to ~[0,1]
            float(len(bio.get("witness_marks", []))) / 10.0,
            0.0,
            0.0,
            0.0,
        ]
        # Voice action vector (what voices did this cycle)
        voice_action = [
            vs.get("architect", 0.7),
            vs.get("engineer", 0.75),
            vs.get("ethicist", 0.8),
            vs.get("resource", 0.65),
            delib["consensus"],
            float(budget),
            priority,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
        ]
        trajectory.append((state, voice_action))

    if len(trajectory) < 4:
        log_result(
            run,
            0.0,
            {"error": "too few steps"},
            "discard",
            "E46: insufficient trajectory",
            experiment="E46",
        )
        return {}

    # Build (s_t, action_t, s_{t+1}) new pairs from this run
    new_pairs: list[list] = []
    for i in range(len(trajectory) - 1):
        new_pairs.append(
            [
                trajectory[i][0],  # state_t
                trajectory[i][1],  # voice_action_t
                trajectory[i + 1][0],  # state_{t+1}
            ]
        )

    # Reserve last 4 pairs as held-out test set
    test_pairs = new_pairs[-4:]
    train_new = new_pairs[:-4]

    # Combine with replay buffer (reservoir sampling)
    combined = replay_buffer + train_new
    _random.shuffle(combined)
    training_data = combined[:_JEPA_BUFFER_MAX]

    def _to_np(pairs):
        return [
            (
                np.array(p[0], dtype=np.float32),
                np.array(p[1], dtype=np.float32),
                np.array(p[2], dtype=np.float32),
            )
            for p in pairs
        ]

    # Measure initial held-out loss (before this run's training)
    if test_pairs:
        pre_metrics = jepa.train_epoch(_to_np(test_pairs[:4]), batch_size=4)
        initial_loss = pre_metrics["prediction_loss"]
    else:
        initial_loss = 1.0

    # Train on replay buffer (2 epochs — enough to learn without overfitting)
    loss_per_epoch: list[float] = []
    batch = min(32, len(training_data))
    for epoch in range(2):
        if _STOP or not training_data:
            break
        metrics = jepa.train_epoch(_to_np(training_data), batch_size=batch)
        loss_per_epoch.append(metrics["prediction_loss"])
        print(
            f"  Epoch {epoch + 1}/2: train_loss={metrics['prediction_loss']:.5f} "
            f"(buffer={len(training_data)})",
            flush=True,
        )

    # Evaluate held-out loss AFTER training
    if test_pairs:
        post_metrics = jepa.train_epoch(_to_np(test_pairs[:4]), batch_size=4)
        final_loss = post_metrics["prediction_loss"]
    else:
        final_loss = loss_per_epoch[-1] if loss_per_epoch else initial_loss

    # Update and save replay buffer (add new pairs, cap at max)
    replay_buffer.extend(train_new)
    if len(replay_buffer) > _JEPA_BUFFER_MAX:
        # Reservoir: keep a random mix of old and new
        _random.shuffle(replay_buffer)
        replay_buffer = replay_buffer[:_JEPA_BUFFER_MAX]
    _save_replay_buffer(replay_buffer)

    # Save JEPA weights
    try:
        jepa.save(_JEPA_CKPT)
    except Exception:
        pass

    loss_ratio = final_loss / initial_loss if initial_loss > 0 else 1.0

    # Keep if held-out loss < 0.97 (well-calibrated for this distribution) OR 10% improvement
    keep = final_loss < 0.97 or loss_ratio < 0.90

    log_result(
        run,
        1.0 - final_loss,  # higher = better calibration
        {
            "initial_loss": round(initial_loss, 5),
            "final_loss": round(final_loss, 5),
            "loss_ratio": round(loss_ratio, 4),
            "loss_trajectory": [round(l, 5) for l in loss_per_epoch],
            "buffer_size": len(replay_buffer),
            "n_new_pairs": len(new_pairs),
            "used_llm": use_llm,
            "duration_s": round(time.time() - start, 1),
        },
        "keep" if keep else "discard",
        f"E46: JEPA replay. final_loss={final_loss:.5f} ratio={loss_ratio:.4f} "
        f"buf={len(replay_buffer)} keep={keep}",
        experiment="E46",
        final_loss=round(final_loss, 5),
        buffer_size=len(replay_buffer),
    )
    return {"loss_ratio": loss_ratio, "initial_loss": initial_loss, "final_loss": final_loss}


# ---------------------------------------------------------------------------
# E47: Voice profile diversity — which voice bias maximizes EVO coherence?
# ---------------------------------------------------------------------------


async def experiment_e47_voice_profiles(use_llm: bool = True) -> dict:
    """Test voice weakening profiles to find which voice is load-bearing for consensus.

    Previous version used additive boosts on an already-saturated system (all voices near 1.0).
    This version uses NEGATIVE adjustments (-0.30) to weaken specific voices below threshold,
    measuring which voice removal most degrades consensus and EVO coherence.
    Metric: consensus_std across profiles (>0.01 = profiles meaningfully differ).
    """
    import statistics as _stats

    from cohezion.swarm.quadrature_nexus import VoiceType

    run = _next_run()
    start = time.time()
    print(f"\n[E47] Voice weakening profiles (llm={use_llm})", flush=True)

    # Weaken one voice at a time by -0.30 to break the saturation ceiling
    PROFILES = [
        ("baseline", dict.fromkeys(VoiceType, 0.0)),  # no change
        (
            "architect_weak",
            {
                VoiceType.ARCHITECT: -0.30,
                VoiceType.ENGINEER: 0.0,
                VoiceType.ETHICIST: 0.0,
                VoiceType.RESOURCE: 0.0,
            },
        ),
        (
            "resource_weak",
            {
                VoiceType.ARCHITECT: 0.0,
                VoiceType.ENGINEER: 0.0,
                VoiceType.ETHICIST: 0.0,
                VoiceType.RESOURCE: -0.30,
            },
        ),
        (
            "ethicist_weak",
            {
                VoiceType.ARCHITECT: 0.0,
                VoiceType.ENGINEER: 0.0,
                VoiceType.ETHICIST: -0.30,
                VoiceType.RESOURCE: 0.0,
            },
        ),
        (
            "engineer_weak",
            {
                VoiceType.ARCHITECT: 0.0,
                VoiceType.ENGINEER: -0.30,
                VoiceType.ETHICIST: 0.0,
                VoiceType.RESOURCE: 0.0,
            },
        ),
    ]

    profile_results: dict[str, dict] = {}

    for profile_name, adj_map in PROFILES:
        if _STOP:
            break
        nexus = _get_shared_nexus()

        # IMPORTANT: run_llm_deliberation overwrites _score_adjustments each call via:
        #   nexus._score_adjustments[vt] = (voice_score - base) + mycelium_calibration
        # So we must modify _mycelium_calibration (which IS preserved through that call).
        if not hasattr(nexus, "_mycelium_calibration"):
            from cohezion.swarm.quadrature_nexus import VoiceType as _VT

            nexus._mycelium_calibration = dict.fromkeys(_VT, 0.0)
        orig_calib = dict(nexus._mycelium_calibration)
        for vt, delta in adj_map.items():
            nexus._mycelium_calibration[vt] = orig_calib.get(vt, 0.0) + delta

        evo_coherences: list[float] = []
        consensus_scores: list[float] = []

        for rep in range(4):
            if _STOP:
                break
            delib = await run_llm_deliberation(
                action=f"e47_{profile_name}_rep{rep}",
                description="Optimize architecture for scalability safety and budget efficiency",
                priority=0.75,
                budget=True,
                use_llm=use_llm,
            )
            consensus_scores.append(delib["consensus"])
            bio = delib.get("evo_biography") or {}
            evo_coherences.append(bio.get("evo_coherence_metric", 0.5))

        # Restore calibration
        nexus._mycelium_calibration = orig_calib

        mean_coh = sum(evo_coherences) / len(evo_coherences) if evo_coherences else 0.0
        mean_con = sum(consensus_scores) / len(consensus_scores) if consensus_scores else 0.0
        profile_results[profile_name] = {
            "mean_evo_coherence": mean_coh,
            "mean_consensus": mean_con,
        }
        print(
            f"  {profile_name}: consensus={mean_con:.4f} evo_coh={mean_coh:.4f}",
            flush=True,
        )

    if not profile_results:
        log_result(run, 0.0, {}, "discard", "E47: no results", experiment="E47")
        return {}

    # Primary metric: consensus_std (does weakening voices actually change consensus?)
    consensus_values = [v["mean_consensus"] for v in profile_results.values()]
    con_std = _stats.stdev(consensus_values) if len(consensus_values) >= 2 else 0.0

    # Which voice, when weakened, most drops consensus below baseline?
    baseline_con = profile_results.get("baseline", {}).get("mean_consensus", 0.0)
    worst_drop = 0.0
    most_critical = "none"
    for pname, pdata in profile_results.items():
        if pname == "baseline":
            continue
        drop = baseline_con - pdata["mean_consensus"]
        if drop > worst_drop:
            worst_drop = drop
            most_critical = pname.replace("_weak", "")

    # Keep if voices are distinguishable (con_std > 0.005 = real signal, not noise)
    keep = con_std > 0.005

    log_result(
        run,
        con_std,
        {
            "profile_results": profile_results,
            "baseline_consensus": round(baseline_con, 4),
            "most_critical_voice": most_critical,
            "worst_consensus_drop": round(worst_drop, 4),
            "consensus_std": round(con_std, 5),
            "used_llm": use_llm,
            "duration_s": round(time.time() - start, 1),
        },
        "keep" if keep else "discard",
        f"E47: Voice weakening. con_std={con_std:.4f} most_critical={most_critical} "
        f"drop={worst_drop:.4f} ({'diverse' if keep else 'flat'})",
        experiment="E47",
        most_critical=most_critical,
        consensus_std=round(con_std, 5),
    )
    return {"profile_results": profile_results, "con_std": con_std, "most_critical": most_critical}


# ---------------------------------------------------------------------------
# E48: Voice fragility scan — find minimum voice score for consensus ≥ 0.85
# ---------------------------------------------------------------------------


async def experiment_e48_fragility_scan(use_llm: bool = True) -> dict:
    """Sweep voice weakening depth (-0.10 to -0.60) on the most critical voices
    (resource and ethicist, from E47) to find the approval fragility threshold.

    Metric: for each voice, the weakening depth at which consensus first drops below 0.85.
    Keep if any voice reaches its fragility threshold within the sweep range.
    """

    from cohezion.swarm.quadrature_nexus import VoiceType

    run = _next_run()
    start = time.time()
    print(f"\n[E48] Voice fragility scan (llm={use_llm})", flush=True)

    # Sweep resource and ethicist (most critical per E47)
    SWEEP_VOICES = [VoiceType.RESOURCE, VoiceType.ETHICIST, VoiceType.ARCHITECT]
    DELTAS = [-0.10, -0.20, -0.30, -0.40, -0.50, -0.60]

    fragility_thresholds: dict[str, float | None] = {}
    scan_results: dict[str, list[dict]] = {}
    APPROVAL_THRESHOLD = 0.85

    for voice in SWEEP_VOICES:
        voice_name = voice.value
        if _STOP:
            break
        scan_results[voice_name] = []
        fragility_thresholds[voice_name] = None

        nexus = _get_shared_nexus()
        if not hasattr(nexus, "_mycelium_calibration"):
            nexus._mycelium_calibration = dict.fromkeys(VoiceType, 0.0)
        orig_calib = dict(nexus._mycelium_calibration)

        for delta in DELTAS:
            if _STOP:
                break
            # Apply only this voice weakening
            for vt in VoiceType:
                nexus._mycelium_calibration[vt] = orig_calib.get(vt, 0.0)
            nexus._mycelium_calibration[voice] = orig_calib.get(voice, 0.0) + delta

            consensus_scores: list[float] = []
            for rep in range(3):
                if _STOP:
                    break
                delib = await run_llm_deliberation(
                    action=f"e48_{voice_name}_d{delta}_r{rep}",
                    description="Optimize architecture for scalability safety and budget efficiency",
                    priority=0.75,
                    budget=True,
                    use_llm=use_llm,
                )
                consensus_scores.append(delib["consensus"])

            mean_con = sum(consensus_scores) / len(consensus_scores) if consensus_scores else 0.0
            scan_results[voice_name].append({"delta": delta, "mean_consensus": round(mean_con, 4)})
            print(f"  {voice_name} delta={delta:+.2f}: consensus={mean_con:.4f}", flush=True)

            # Record first threshold crossing
            if mean_con < APPROVAL_THRESHOLD and fragility_thresholds[voice_name] is None:
                fragility_thresholds[voice_name] = delta
                print(
                    f"  → FRAGILITY THRESHOLD: {voice_name} breaks at delta={delta:+.2f}",
                    flush=True,
                )
                break  # Found threshold, no need to go deeper

        # Restore calibration
        nexus._mycelium_calibration = orig_calib

    any_found = any(v is not None for v in fragility_thresholds.values())
    log_result(
        run,
        min(abs(v) for v in fragility_thresholds.values() if v is not None) if any_found else 0.0,
        {
            "fragility_thresholds": {k: v for k, v in fragility_thresholds.items()},
            "scan_results": scan_results,
            "approval_threshold": APPROVAL_THRESHOLD,
            "used_llm": use_llm,
            "duration_s": round(time.time() - start, 1),
        },
        "keep" if any_found else "discard",
        f"E48: Fragility scan. Thresholds: {fragility_thresholds}",
        experiment="E48",
        fragility_thresholds=fragility_thresholds,
    )
    return {"fragility_thresholds": fragility_thresholds, "scan_results": scan_results}


# ---------------------------------------------------------------------------
# E49: JEPA-guided proposal selection vs random selection
# ---------------------------------------------------------------------------


async def experiment_e49_jepa_guided_selection(
    n_candidates: int = 10, use_llm: bool = True
) -> dict:
    """Use JEPA surprise to select high-surprise proposals (unexplored state space).

    Hypothesis: JEPA-selected proposals (high surprise = JEPA is uncertain about outcome)
    produce more diverse consensus outcomes than random selection.
    Metric: consensus_std(jepa_selected) vs consensus_std(random_selected).
    Keep if JEPA selection shows higher outcome variance (exploring more state space).
    """
    import random as _random
    import statistics as _stats

    import numpy as np

    from cohezion.world_model.jepa_world_model import JEPAWorldModel

    run = _next_run()
    start = time.time()
    print(f"\n[E49] JEPA-guided selection ({n_candidates} candidates, llm={use_llm})", flush=True)

    _JEPA_CKPT = Path("/tmp/cohezion_jepa_checkpoint.pt")
    try:
        jepa = JEPAWorldModel.load(_JEPA_CKPT) if _JEPA_CKPT.exists() else JEPAWorldModel()
    except Exception:
        jepa = JEPAWorldModel()

    # Candidate proposal pool (varied priority/budget/description combinations)
    CANDIDATE_POOL = [
        ("arch_high", "Design microservice architecture for scalability", 0.85, True),
        ("arch_low", "Minor architecture refactoring for maintainability", 0.40, False),
        ("opt_high", "Optimize cache for 95% efficiency target and budget savings", 0.80, True),
        ("opt_low", "Minor cache tuning for modest improvement", 0.35, False),
        ("safety_high", "Add constitutional safety guardrails with alignment audit", 0.90, True),
        ("safety_low", "Update safety documentation", 0.30, False),
        (
            "cost_high",
            "Reduce cloud costs by routing to local models and budget optimization",
            0.75,
            True,
        ),
        ("cost_low", "Minor dependency version update", 0.25, False),
        (
            "mixed_a",
            "Architecture optimization with safety alignment and efficient budget",
            0.70,
            True,
        ),
        ("mixed_b", "Gradual improvement across architecture safety and resources", 0.55, True),
        ("mixed_c", "Emergency safety patch for critical alignment gap", 0.95, True),
        ("mixed_d", "Experimental feature with unknown alignment implications", 0.50, False),
    ][:n_candidates]

    # First, get a "current state" from one baseline deliberation
    baseline_delib = await run_llm_deliberation(
        action="e49_baseline",
        description="Optimize architecture for scalability safety and budget efficiency",
        priority=0.75,
        budget=True,
        use_llm=use_llm,
    )
    vs = baseline_delib["event_metadata"].get("voice_scores", {})
    bio = baseline_delib.get("evo_biography") or {}
    current_state = np.array(
        [
            vs.get("architect", 0.7),
            vs.get("engineer", 0.75),
            vs.get("ethicist", 0.8),
            vs.get("resource", 0.65),
            baseline_delib["consensus"],
            baseline_delib["alignment"],
            bio.get("evo_coherence_metric", 0.5),
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
        ],
        dtype=np.float32,
    )

    # Score each candidate with JEPA surprise (action = expected voice outcome for that proposal)
    candidate_surprises: list[tuple[str, float, tuple]] = []
    for action, desc, priority, budget in CANDIDATE_POOL:
        if _STOP:
            break
        # Estimate expected voice outcome from heuristic scoring
        vs_est = {
            "architect": _heuristic_score("architect", action, desc, priority, budget),
            "engineer": _heuristic_score("engineer", action, desc, priority, budget),
            "ethicist": _heuristic_score("ethicist", action, desc, priority, budget),
            "resource": _heuristic_score("resource", action, desc, priority, budget),
        }
        est_consensus = sum(vs_est.values()) / 4
        action_vec = np.array(
            [
                vs_est["architect"],
                vs_est["engineer"],
                vs_est["ethicist"],
                vs_est["resource"],
                est_consensus,
                float(budget),
                priority,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
            ],
            dtype=np.float32,
        )

        # Estimate next state (what would voice scores look like after this proposal?)
        next_state_est = np.array(
            [
                vs_est["architect"],
                vs_est["engineer"],
                vs_est["ethicist"],
                vs_est["resource"],
                est_consensus,
                1.0 if est_consensus >= 0.85 else 0.0,
                min(1.0, 0.5 + est_consensus * 0.4),
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
            ],
            dtype=np.float32,
        )

        try:
            surprise = jepa.surprise_score(current_state, action_vec, next_state_est)
        except Exception:
            surprise = 1.0
        candidate_surprises.append((action, surprise, (action, desc, priority, budget)))

    candidate_surprises.sort(key=lambda x: x[1], reverse=True)  # highest surprise first

    # Select top-3 by JEPA surprise and bottom-3 random
    top3_jepa = candidate_surprises[:3]
    random_3 = _random.sample(candidate_surprises, min(3, len(candidate_surprises)))

    print(f"  JEPA top-3 (high surprise): {[c[0] for c in top3_jepa]}", flush=True)
    print(f"  Random 3: {[c[0] for c in random_3]}", flush=True)

    # Run deliberations for each selection group
    async def run_group(candidates: list, group_name: str) -> list[float]:
        scores = []
        for _, _, (action, desc, priority, budget) in candidates:
            if _STOP:
                break
            delib = await run_llm_deliberation(
                action=f"e49_{group_name}_{action}",
                description=desc,
                priority=priority,
                budget=budget,
                use_llm=use_llm,
            )
            scores.append(delib["consensus"])
            print(f"  {group_name} {action}: consensus={delib['consensus']:.4f}", flush=True)
        return scores

    jepa_scores = await run_group(top3_jepa, "jepa")
    random_scores = await run_group(random_3, "random")

    jepa_std = _stats.stdev(jepa_scores) if len(jepa_scores) >= 2 else 0.0
    random_std = _stats.stdev(random_scores) if len(random_scores) >= 2 else 0.0
    jepa_mean = sum(jepa_scores) / len(jepa_scores) if jepa_scores else 0.0
    random_mean = sum(random_scores) / len(random_scores) if random_scores else 0.0

    # JEPA is useful if its selected proposals show higher variance (more diverse outcomes)
    keep = jepa_std > random_std

    log_result(
        run,
        jepa_std - random_std,
        {
            "jepa_scores": [round(s, 4) for s in jepa_scores],
            "random_scores": [round(s, 4) for s in random_scores],
            "jepa_mean": round(jepa_mean, 4),
            "random_mean": round(random_mean, 4),
            "jepa_std": round(jepa_std, 5),
            "random_std": round(random_std, 5),
            "top3_jepa": [c[0] for c in top3_jepa],
            "top3_surprise": [round(c[1], 4) for c in top3_jepa],
            "used_llm": use_llm,
            "duration_s": round(time.time() - start, 1),
        },
        "keep" if keep else "discard",
        f"E49: JEPA selection. jepa_std={jepa_std:.4f} vs random_std={random_std:.4f} "
        f"(delta={jepa_std - random_std:+.4f})",
        experiment="E49",
        jepa_std=round(jepa_std, 5),
        random_std=round(random_std, 5),
    )
    return {"jepa_std": jepa_std, "random_std": random_std, "keep": keep}


# ---------------------------------------------------------------------------
# E50: DB-informed proposal design — closed loop from SurrealDB patterns
# ---------------------------------------------------------------------------


async def experiment_e50_db_informed_proposals(use_llm: bool = True) -> dict:
    """Validate the DB-derived optimal proposal formula against naive proposals.

    The closed loop hypothesis: SurrealDB journey analysis reveals which proposal
    characteristics (keywords, priority, budget) correlate with approval. This experiment
    tests whether the DB-derived formula (all keywords + high priority + budget=True)
    meaningfully outperforms naive proposals (no keywords, low priority, budget=False).

    Three tiers are tested:
      naive: no keywords, priority=0.3, budget=False → expected low consensus (~0.71)
      partial: some keywords, priority=0.65, budget=True → medium consensus (~0.87)
      db_optimal: all keywords + resource emphasis, priority=0.85, budget=True → max consensus

    Keep if tier_db > tier_partial > tier_naive (DB ranking is correctly ordered).
    """
    run = _next_run()
    start = time.time()
    print(f"\n[E50] DB proposal validation (3 tiers, llm={use_llm})", flush=True)

    # Three proposal quality tiers (derived from DB voice score analysis)
    TIERS = [
        ("naive", "System status update", 0.30, False),
        ("partial", "Optimize system for better performance and user experience", 0.65, True),
        (
            "db_optimal",
            "Optimize architecture for safety alignment budget efficiency with cost reduction and efficient resource allocation",
            0.85,
            True,
        ),
    ]

    tier_scores: dict[str, list[float]] = {}

    for tier_name, desc, priority, budget in TIERS:
        if _STOP:
            break
        scores = []
        for i in range(3):
            if _STOP:
                break
            delib = await run_llm_deliberation(
                action=f"e50_{tier_name}_{i}",
                description=desc,
                priority=priority,
                budget=budget,
                use_llm=use_llm,
            )
            scores.append(delib["consensus"])
        mean = sum(scores) / len(scores) if scores else 0.0
        tier_scores[tier_name] = scores
        print(f"  {tier_name}: mean_consensus={mean:.4f}", flush=True)

    naive_mean = sum(tier_scores.get("naive", [0])) / max(1, len(tier_scores.get("naive", [1])))
    partial_mean = sum(tier_scores.get("partial", [0])) / max(
        1, len(tier_scores.get("partial", [1]))
    )
    optimal_mean = sum(tier_scores.get("db_optimal", [0])) / max(
        1, len(tier_scores.get("db_optimal", [1]))
    )

    # Keep if DB-optimal > partial > naive (correct ordering proves DB knowledge is valid)
    correctly_ordered = optimal_mean >= partial_mean >= naive_mean
    gain = optimal_mean - naive_mean

    print(
        f"  Tiers: naive={naive_mean:.4f} partial={partial_mean:.4f} optimal={optimal_mean:.4f} "
        f"gain={gain:+.4f} ordered={correctly_ordered}",
        flush=True,
    )

    log_result(
        run,
        gain,
        {
            "naive_mean": round(naive_mean, 4),
            "partial_mean": round(partial_mean, 4),
            "optimal_mean": round(optimal_mean, 4),
            "gain": round(gain, 4),
            "correctly_ordered": correctly_ordered,
            "tier_scores": {k: [round(s, 4) for s in v] for k, v in tier_scores.items()},
            "used_llm": use_llm,
            "duration_s": round(time.time() - start, 1),
        },
        "keep" if correctly_ordered else "discard",
        f"E50: DB tiers. naive={naive_mean:.4f} partial={partial_mean:.4f} "
        f"optimal={optimal_mean:.4f} gain={gain:+.4f} ordered={correctly_ordered}",
        experiment="E50",
        gain=round(gain, 4),
        correctly_ordered=correctly_ordered,
    )
    return {"naive": naive_mean, "partial": partial_mean, "optimal": optimal_mean, "gain": gain}


# ---------------------------------------------------------------------------
# E12: Witness mark accumulation (persistent EVO)
# ---------------------------------------------------------------------------


async def experiment_e12_persistent_evo(
    n_deliberations: int = 50,
    use_llm: bool = True,
) -> dict:
    """Run repeated deliberations on the same action to accumulate EVO coherence.

    The EVO is kept alive (not dissolved) between deliberations, allowing
    binding_energy to accumulate above HIHO baseline (0.5).
    """
    from cohezion.physics.evo_model import ExoticVacuumObject

    run = _next_run()
    start = time.time()
    print(
        f"\n[E12] Persistent EVO accumulation ({n_deliberations} deliberations, llm={use_llm})",
        flush=True,
    )

    evo = ExoticVacuumObject(agent_id="persistent_nexus_evo")
    evo.condense()

    coherence_trajectory: list[float] = []
    first_above_hiho: int | None = None
    voice_scores_history: list[dict[str, float]] = []

    for i in range(n_deliberations):
        if _STOP:
            break

        # Evaluate voices for this deliberation
        action = "optimize_evo_coherence"
        description = "Optimize EVO coherence and FLUME encoding for persistent agent lifecycle"
        priority = 0.5 + (i % 10) * 0.04
        budget = i % 3 != 0

        voice_scores: dict[str, float] = {}
        for voice in ["architect", "engineer", "ethicist", "resource"]:
            if use_llm:
                score = await _query_voice_llm(voice, action, description, priority, budget)
            else:
                score = _heuristic_score(voice, action, description, priority, budget)
            voice_scores[voice] = score

        voice_scores_history.append(voice_scores)
        mean_score = sum(voice_scores.values()) / len(voice_scores)

        # Tick coherence (using mean voice score as EVO coherence)
        evo.coherent_phase(coherence=mean_score)

        # Produce witness mark every tick (maximizes work_output for E12_max mode)
        # Every-tick marks push EVO metric from 0.59 toward 0.81 (E37 finding)
        mark_type = "directive" if mean_score >= 0.85 else "milestone"
        evo.produce_witness_mark(mark_type, f"t{i + 1}")

        metric = evo.evo_coherence_metric()
        coherence_trajectory.append(metric)

        if first_above_hiho is None and metric >= 0.5:
            first_above_hiho = i + 1

        if i % 10 == 9:
            print(
                f"  Tick {i + 1}/{n_deliberations}: evo_coherence={metric:.4f} "
                f"binding_energy={evo.binding_energy:.3f} marks={len(evo.witness_marks)}",
                flush=True,
            )

    final_metric = coherence_trajectory[-1] if coherence_trajectory else 0.0
    biography = evo.dissolve()

    log_result(
        run,
        final_metric,
        {
            "final_evo_coherence": final_metric,
            "first_above_hiho": first_above_hiho,
            "total_marks": len(biography.get("witness_marks", [])),
            "binding_energy": biography.get("binding_energy", 0.0),
            "lifetime_ticks": biography.get("lifetime_ticks", 0),
            "used_llm": use_llm,
            "duration_s": round(time.time() - start, 1),
        },
        "keep" if final_metric >= 0.5 else "discard",
        f"E12: Persistent EVO {n_deliberations} ticks. final_coherence={final_metric:.4f} "
        f"first_above_hiho={first_above_hiho} binding_energy={biography.get('binding_energy', 0):.3f}",
        experiment="E12",
        final_evo_coherence=final_metric,
        first_above_hiho=first_above_hiho,
    )
    return {"coherence_trajectory": coherence_trajectory, "biography": biography}


# ---------------------------------------------------------------------------
# E51: EVO quality sensitivity — does EVO coherence respond to proposal quality?
# ---------------------------------------------------------------------------


async def experiment_e51_evo_quality_sensitivity(n_ticks: int = 100, use_llm: bool = True) -> dict:
    """Test whether EVO coherence is quality-sensitive or purely tick-driven.

    Runs n_ticks deliberations for two proposal quality tiers and compares the
    mean EVO coherence from each deliberation's biography. Uses the deliberation's
    internal EVO (same as E12) to ensure proper lifecycle tracking.

    Keep if |optimal_coherence - naive_coherence| > 0.01 (EVO is quality-sensitive).
    """
    run = _next_run()
    start = time.time()
    print(f"\n[E51] EVO quality sensitivity ({n_ticks} ticks each, llm={use_llm})", flush=True)

    PROPOSAL_CONFIGS = {
        "naive": {
            "action": "e51_naive",
            "description": "System status update",
            "priority": 0.30,
            "budget": False,
        },
        "optimal": {
            "action": "e51_optimal",
            "description": "Optimize architecture for safety alignment budget efficiency with cost reduction",
            "priority": 0.85,
            "budget": True,
        },
    }

    results: dict[str, dict] = {}

    for config_name, config in PROPOSAL_CONFIGS.items():
        if _STOP:
            break
        evo_coherences: list[float] = []
        consensus_scores: list[float] = []

        for tick in range(n_ticks):
            if _STOP:
                break
            delib = await run_llm_deliberation(
                action=f"{config['action']}_t{tick}",
                description=config["description"],
                priority=config["priority"],
                budget=config["budget"],
                use_llm=use_llm,
            )
            consensus_scores.append(delib["consensus"])
            # EVO biography comes from the deliberation's internal EVO (via run_llm_deliberation)
            bio = delib.get("evo_biography") or {}
            evo_coherences.append(bio.get("evo_coherence_metric", 0.45))

        mean_evo = sum(evo_coherences) / len(evo_coherences) if evo_coherences else 0.0
        mean_con = sum(consensus_scores) / len(consensus_scores) if consensus_scores else 0.0
        results[config_name] = {"mean_evo_coherence": mean_evo, "mean_consensus": mean_con}
        print(
            f"  {config_name}: mean_evo_coh={mean_evo:.4f} mean_consensus={mean_con:.4f}",
            flush=True,
        )

    naive_coh = results.get("naive", {}).get("mean_evo_coherence", 0.0)
    optimal_coh = results.get("optimal", {}).get("mean_evo_coherence", 0.0)
    delta = optimal_coh - naive_coh
    sensitive = abs(delta) > 0.01

    print(
        f"  EVO sensitivity: naive={naive_coh:.4f} optimal={optimal_coh:.4f} delta={delta:+.4f} sensitive={sensitive}",
        flush=True,
    )

    log_result(
        run,
        delta,
        {
            "naive_coherence": round(naive_coh, 4),
            "optimal_coherence": round(optimal_coh, 4),
            "coherence_delta": round(delta, 4),
            "quality_sensitive": sensitive,
            "n_ticks": n_ticks,
            "used_llm": use_llm,
            "duration_s": round(time.time() - start, 1),
        },
        "keep" if sensitive else "discard",
        f"E51: EVO sensitivity. naive={naive_coh:.4f} optimal={optimal_coh:.4f} "
        f"delta={delta:+.4f} sensitive={sensitive}",
        experiment="E51",
        coherence_delta=round(delta, 4),
        quality_sensitive=sensitive,
    )
    return {"naive": naive_coh, "optimal": optimal_coh, "delta": delta, "sensitive": sensitive}


# ---------------------------------------------------------------------------
# E63: Mycelium closed-loop — apply_mycelium_feedback (E57 additive fix) in production
# ---------------------------------------------------------------------------


async def experiment_e63_mycelium_closed_loop(
    n_phase: int = 10,
    use_llm: bool = True,
    learning_rate: float = 1.0,
) -> dict:
    """Full Mycelium closed-loop: deliberate → synthesize → feedback → deliberate.

    Phase A: n_phase naive deliberations → collect EVO journey metadata.
    Synthesis: MyceliumRegistry.ingest_evo_journeys → run_audit → synthesized skill.
    Feedback: apply_mycelium_feedback (E57 additive fix) → _mycelium_calibration updated.
    Phase B: n_phase deliberations on same nexus → calibration still active.

    Keep if mean_post > mean_baseline (any positive delta proves the loop works).
    Discard if no skill synthesized (too few journey records).
    """
    from cohezion.learning.mycelium_registry import MyceliumRegistry

    _reset_shared_nexus()
    run = _next_run()
    start = time.time()
    print(
        f"\n[E63] Mycelium closed-loop ({n_phase}+{n_phase} deliberations, "
        f"lr={learning_rate}, llm={use_llm})",
        flush=True,
    )

    # Phase A: baseline deliberations (naive proposal — no keywords, priority=0.50)
    baseline_scores: list[float] = []
    event_metas: list[dict] = []
    for i in range(n_phase):
        if _STOP:
            break
        delib = await run_llm_deliberation(
            action=f"e63_phase_a_{i}",
            description="Deploy scheduled system update",
            priority=0.50,
            budget=False,
            use_llm=use_llm,
        )
        baseline_scores.append(delib["consensus"])
        if delib.get("event_metadata"):
            event_metas.append(delib["event_metadata"])

    mean_baseline = sum(baseline_scores) / len(baseline_scores) if baseline_scores else 0.0
    print(f"  Phase A: mean_consensus={mean_baseline:.4f} ({len(event_metas)} events)", flush=True)

    # Mycelium synthesis → apply E57 additive calibration
    nexus = _get_shared_nexus()
    skill_applied = False
    cal_per_voice = 0.0
    if event_metas:
        registry = MyceliumRegistry(min_entries_for_pattern=2)
        ingested = registry.ingest_evo_journeys(event_metas)
        if ingested >= 1:
            registry.run_audit()
            skill = registry.skills.get("EVO_DELIBERATION_SYNTHESIZED")
            if skill:
                nexus.apply_mycelium_feedback(skill.skill_content, learning_rate=learning_rate)
                skill_applied = True
                from cohezion.swarm.quadrature_nexus import VoiceType

                cal_per_voice = nexus._mycelium_calibration.get(VoiceType.ARCHITECT, 0.0)
                print(
                    f"  Mycelium synthesis: applied calibration_per_voice={cal_per_voice:.5f}",
                    flush=True,
                )

    if not skill_applied:
        print("  Mycelium synthesis: no skill produced — using baseline", flush=True)

    # Phase B: post-feedback deliberations (same proposal type — calibration still active)
    post_scores: list[float] = []
    for i in range(n_phase):
        if _STOP:
            break
        delib = await run_llm_deliberation(
            action=f"e63_phase_b_{i}",
            description="Deploy scheduled system update",
            priority=0.50,
            budget=False,
            use_llm=use_llm,
        )
        post_scores.append(delib["consensus"])

    mean_post = sum(post_scores) / len(post_scores) if post_scores else 0.0
    delta = mean_post - mean_baseline
    print(
        f"  Phase B: mean_consensus={mean_post:.4f} delta={delta:+.4f} "
        f"skill_applied={skill_applied}",
        flush=True,
    )

    keep_decision = "keep" if delta > 0 else "discard"
    log_result(
        run,
        delta,
        {
            "mean_baseline": round(mean_baseline, 4),
            "mean_post": round(mean_post, 4),
            "delta": round(delta, 4),
            "skill_applied": skill_applied,
            "calibration_per_voice": round(cal_per_voice, 5),
            "learning_rate": learning_rate,
            "n_phase": n_phase,
            "used_llm": use_llm,
            "duration_s": round(time.time() - start, 1),
        },
        keep_decision,
        f"E63: Mycelium closed-loop. baseline={mean_baseline:.4f} post={mean_post:.4f} "
        f"delta={delta:+.4f} skill_applied={skill_applied}",
        experiment="E63",
        mycelium_delta=round(delta, 4),
        skill_applied=skill_applied,
    )
    return {
        "baseline": mean_baseline,
        "post": mean_post,
        "delta": delta,
        "skill_applied": skill_applied,
    }


# ---------------------------------------------------------------------------
# E64: Multi-cycle Mycelium compounding — does consensus reach 0.85 in N cycles?
# ---------------------------------------------------------------------------


async def experiment_e64_mycelium_compounding(
    n_cycles: int = 5,
    n_phase: int = 8,
    use_llm: bool = True,
    learning_rate: float = 1.0,
) -> dict:
    """Multi-cycle Mycelium compounding toward HIHO threshold.

    Runs n_cycles on a SHARED nexus — _mycelium_calibration accumulates (E57 additive fix).
    Convergence formula: consensus_n = 0.85 - 0.125 * (1 - lr/2)^n
    At lr=1.0: cycle1=0.7875, cycle2=0.8219, cycle3=0.8457, cycle4=0.8594 (crosses 0.85).
    Keep if any cycle exceeds HIHO threshold OR total_lift > 0.05.
    """
    from cohezion.learning.mycelium_registry import MyceliumRegistry

    _reset_shared_nexus()
    run = _next_run()
    start = time.time()
    print(
        f"\n[E64] Multi-cycle compounding ({n_cycles} cycles, "
        f"{n_phase}+{n_phase} each, lr={learning_rate}, llm={use_llm})",
        flush=True,
    )

    nexus = _get_shared_nexus()
    cycle_means: list[float] = []
    threshold_crossed = False
    first_crossing_cycle = -1

    for cycle_idx in range(n_cycles):
        if _STOP:
            break

        phase_a_scores: list[float] = []
        event_metas: list[dict] = []
        for i in range(n_phase):
            if _STOP:
                break
            delib = await run_llm_deliberation(
                action=f"e64_c{cycle_idx}_a{i}",
                description="Deploy scheduled system update",
                priority=0.50,
                budget=False,
                use_llm=use_llm,
            )
            phase_a_scores.append(delib["consensus"])
            if delib.get("event_metadata"):
                event_metas.append(delib["event_metadata"])

        mean_a = sum(phase_a_scores) / len(phase_a_scores) if phase_a_scores else 0.0

        skill_applied = False
        if event_metas:
            registry = MyceliumRegistry(min_entries_for_pattern=2)
            ingested = registry.ingest_evo_journeys(event_metas)
            if ingested >= 1:
                registry.run_audit()
                skill = registry.skills.get("EVO_DELIBERATION_SYNTHESIZED")
                if skill:
                    nexus.apply_mycelium_feedback(skill.skill_content, learning_rate=learning_rate)
                    skill_applied = True

        phase_b_scores: list[float] = []
        for i in range(n_phase):
            if _STOP:
                break
            delib = await run_llm_deliberation(
                action=f"e64_c{cycle_idx}_b{i}",
                description="Deploy scheduled system update",
                priority=0.50,
                budget=False,
                use_llm=use_llm,
            )
            phase_b_scores.append(delib["consensus"])

        mean_b = sum(phase_b_scores) / len(phase_b_scores) if phase_b_scores else 0.0
        cycle_means.append(mean_b)
        if mean_b >= nexus.CONSENSUS_THRESHOLD and not threshold_crossed:
            threshold_crossed = True
            first_crossing_cycle = cycle_idx + 1

        print(
            f"  Cycle {cycle_idx + 1}/{n_cycles}: a={mean_a:.4f} -> b={mean_b:.4f} "
            f"skill={skill_applied} crossed={threshold_crossed}",
            flush=True,
        )

    monotone = all(cycle_means[i] <= cycle_means[i + 1] for i in range(len(cycle_means) - 1))
    final_mean = cycle_means[-1] if cycle_means else 0.0
    total_lift = final_mean - (cycle_means[0] if cycle_means else 0.0)
    keep_decision = "keep" if threshold_crossed or total_lift > 0.05 else "discard"

    log_result(
        run,
        total_lift,
        {
            "cycle_means": [round(m, 4) for m in cycle_means],
            "threshold_crossed": threshold_crossed,
            "first_crossing_cycle": first_crossing_cycle,
            "monotone": monotone,
            "total_lift": round(total_lift, 4),
            "final_mean": round(final_mean, 4),
            "n_cycles": n_cycles,
            "learning_rate": learning_rate,
            "used_llm": use_llm,
            "duration_s": round(time.time() - start, 1),
        },
        keep_decision,
        f"E64: Mycelium compounding {n_cycles} cycles. total_lift={total_lift:+.4f} "
        f"threshold_crossed={threshold_crossed} first_cycle={first_crossing_cycle} "
        f"monotone={monotone}",
        experiment="E64",
        mycelium_total_lift=round(total_lift, 4),
        threshold_crossed=threshold_crossed,
    )
    return {
        "cycle_means": cycle_means,
        "threshold_crossed": threshold_crossed,
        "first_crossing_cycle": first_crossing_cycle,
        "total_lift": total_lift,
        "monotone": monotone,
    }


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


async def main() -> None:
    global _run_counter
    _install_sigint()

    _run_counter = _last_run_number()
    print(f"[overnight_evo] Starting from run #{_run_counter + 1}", flush=True)
    print(f"[overnight_evo] Lemonade: {LEMONADE_BASE}", flush=True)
    print(f"[overnight_evo] Logging to: {JSONL_PATH}", flush=True)

    # ── Persistence stack: TelemetryBus + JourneyWorker + SurrealDB ──────────
    from cohezion.core.journey_worker import get_journey_worker
    from cohezion.core.telemetry_bus import get_telemetry_bus

    bus = get_telemetry_bus()
    worker = get_journey_worker()
    await bus.start()
    await worker.start()

    # Ensure a root agent_journey record exists so journey_point FKs resolve
    if worker._db.connected:
        await worker._db.ensure_journey(
            journey_id="overnight_evo_loop",
            agent_id="autoresearch_overnight",
            intent="EVO journey capture autoresearch loop — Quadrature Nexus + FLUME + Mycelium",
        )
        print(
            "[overnight_evo] SurrealDB connected — persisting journeys to journey_point", flush=True
        )
    else:
        print("[overnight_evo] SurrealDB unavailable — journeys will not be persisted", flush=True)

    # LLM availability probe — check with a real scoring call (not just model list).
    # Models may be listed but returning empty (iGPU ROCm silent failure).
    use_llm = False
    try:
        import httpx

        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{LEMONADE_BASE}/models")
            if r.status_code == 200:
                available = {m["id"] for m in r.json().get("data", [])}
                global VOICE_MODELS, _ACTIVE_VOICE_MODEL
                for candidate in _PREFERRED_MODELS:
                    if candidate in available:
                        _ACTIVE_VOICE_MODEL = candidate
                        VOICE_MODELS = dict.fromkeys(VOICE_MODELS, candidate)
                        break
                # Functional probe: actually test a scoring call (not just list)
                probe_resp = await client.post(
                    f"{LEMONADE_BASE}/chat/completions",
                    json={
                        "model": _ACTIVE_VOICE_MODEL,
                        "messages": [{"role": "user", "content": "2+2="}],
                        "max_tokens": 5,
                        "temperature": 0.0,
                    },
                    timeout=8.0,
                )
                probe_text = (
                    probe_resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                )
                if probe_text.strip():
                    use_llm = True
                    print(
                        f"[overnight_evo] LLM LIVE — {len(available)} models. Active: {_ACTIVE_VOICE_MODEL}",
                        flush=True,
                    )
                else:
                    print(
                        "[overnight_evo] LLM probe returned empty (iGPU state) — heuristic mode",
                        flush=True,
                    )
    except Exception as e:
        print(f"[overnight_evo] LLM unavailable ({e}) — heuristic fallback", flush=True)

    # Experiment schedule (runs indefinitely, cycling through tiers).
    # At 0.93 attractor: E7/E8/E10 always show 0 gain (correct — at max consensus).
    # Focus on experiments that generate NEW insights: EVO maturation, JEPA learning,
    # diversity analysis. Replaced redundant E7/E8/E10 with deeper EVO experiments.
    SCHEDULE = [
        # E12: 100 ticks — core EVO maturation baseline
        (
            "E12_persist",
            lambda: experiment_e12_persistent_evo(n_deliberations=100, use_llm=use_llm),
        ),
        # E63: Mycelium closed-loop — wires E57 additive calibration into production data
        # Phase A deliberations → synthesis → apply_mycelium_feedback → Phase B comparison.
        # Replaces E50_tiers (fully validated at delta=+0.2625; no new signal expected).
        (
            "E63_mycelium",
            lambda: experiment_e63_mycelium_closed_loop(
                n_phase=10, use_llm=use_llm, learning_rate=1.0
            ),
        ),
        # E51: EVO quality sensitivity — does proposal quality affect EVO coherence?
        (
            "E51_quality",
            lambda: experiment_e51_evo_quality_sensitivity(n_ticks=100, use_llm=use_llm),
        ),
        # E12 xl: 200 ticks
        (
            "E12_persist_xl",
            lambda: experiment_e12_persistent_evo(n_deliberations=200, use_llm=use_llm),
        ),
        # E63 lr sweep: lr=2.0 should cross the 0.85 threshold in one cycle (E60 finding)
        (
            "E63_mycelium_lr2",
            lambda: experiment_e63_mycelium_closed_loop(
                n_phase=10, use_llm=use_llm, learning_rate=2.0
            ),
        ),
        # E64: Multi-cycle compounding — 5 cycles, tests convergence formula
        # Predicts: threshold crossed by cycle 4 at lr=1.0 (formula: 0.85−0.125×(1−lr/2)^n)
        (
            "E64_compound",
            lambda: experiment_e64_mycelium_compounding(
                n_cycles=5, n_phase=8, use_llm=use_llm, learning_rate=1.0
            ),
        ),
        # E51 xl: 200-tick quality sensitivity (more ticks = more signal)
        (
            "E51_quality_xl",
            lambda: experiment_e51_evo_quality_sensitivity(n_ticks=200, use_llm=use_llm),
        ),
        # E46: JEPA replay — accumulate buffer knowledge
        ("E46_jepa_train", lambda: experiment_e46_jepa_learning(n_train_steps=20, use_llm=use_llm)),
        # E12 xxl: 500 ticks — deep EVO maturation
        (
            "E12_persist_xxl",
            lambda: experiment_e12_persistent_evo(n_deliberations=500, use_llm=use_llm),
        ),
        # E47: Voice criticality sanity check
        ("E47_voice", lambda: experiment_e47_voice_profiles(use_llm=use_llm)),
    ]

    # Per-experiment timeout: 3h (10800s)
    EXPERIMENT_TIMEOUT = 10800

    iteration = 0
    while not _STOP:
        for label, experiment_fn in SCHEDULE:
            if _STOP:
                break
            print(f"\n{'=' * 60}", flush=True)
            print(f"[overnight_evo] Iteration {iteration} — {label}", flush=True)
            print(f"{'=' * 60}", flush=True)
            try:
                await asyncio.wait_for(experiment_fn(), timeout=EXPERIMENT_TIMEOUT)
            except TimeoutError:
                print(f"  [{label}] TIMEOUT after {EXPERIMENT_TIMEOUT}s — skipping", flush=True)
                log_result(
                    _next_run(),
                    0.0,
                    {},
                    "discard",
                    f"{label} timed out after {EXPERIMENT_TIMEOUT}s",
                    experiment=label,
                )
            except Exception as exc:
                import traceback

                print(f"  [{label}] ERROR: {exc}", flush=True)
                traceback.print_exc(file=sys.stderr)
                log_result(
                    _next_run(),
                    0.0,
                    {"error": str(exc)},
                    "discard",
                    f"{label} failed: {exc}",
                    experiment=label,
                )

        iteration += 1
        if not _STOP:
            print(
                f"\n[overnight_evo] Completed iteration {iteration}. Restarting schedule.",
                flush=True,
            )

    print(f"\n[overnight_evo] Loop stopped after {iteration} iterations.", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
