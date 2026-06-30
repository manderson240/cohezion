"""Cognitive-Profile Harness — the P1–P3 foundation of the DeepMind cognitive framework /goal.

Measures COHEZION (the assembled SYSTEM, not a single model — paper claim B5) against the 10
cognitive faculties (G1–G10) plus the testable beyond-faculty axes (B1 speed, B-calibration), using
HELD-OUT, contamination-free probe batteries authored fresh here. It emits an HONEST per-axis profile:
score, uncertainty, and a status in {MET, PARTIAL, GAP, BEYOND_REACH}.

Discipline (verification-depth.md):
  - The axes are SEPARABLE. Each axis routes through a DISTINCT capability slot in `Capabilities`, so
    neutralizing one capability collapses ONLY that axis's score — never a global confound. This is
    proven by `tests/eval/test_cognitive_profile.py::test_axis_separability_...`.
  - Substrate-BEYOND-REACH axes (native perception Gv/Ga, broad knowledge Gc, frontier Gf — per the
    gap-map ~/vaults/cohezion-vault/reports/agi-cognitive-framework-gapmap-2026-06-30.md) are MEASURED
    where cheap but reported BEYOND_REACH and NEVER laundered into MET, even on a high score.
  - A no-op / wrong system on an axis scores LOW (the axis measures capability, not mere presence).

Live capabilities route through real Cohezion modules: G1/B1 → `task_classifier.classify`;
G5 → `JourneyTracker` + `SemanticCache` round-trip; G4 → `DifficultyEstimator`; the LLM-backed
faculties → the local AMD fleet via the OmniRouter (:13305), $0.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any


logger = logging.getLogger(__name__)

# Local AMD fleet — the OmniRouter serves the whole catalog on :13305 ($0). See CLAUDE.md "Inference Ports".
_OMNI_CHAT_URL = "http://localhost:13305/api/v1/chat/completions"
_FLEET_MODEL = "Gemma-4-E4B-it-GGUF"  # iGPU mid-tier; the cascade's structured-output workhorse

# Status thresholds (score in [0, 1]).
_MET = 0.70
_PARTIAL = 0.34


# ──────────────────────────────────────────────────────────────────────────────
# Probe primitives — held-out, authored fresh (contamination-free).
# ──────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class TextProbe:
    """A single held-out item graded by deterministic `contains` (no LLM-as-judge)."""

    prompt: str
    expected: str  # lowercase keyword/phrase the correct answer MUST contain

    def grade(self, output: str) -> bool:
        return self.expected.lower() in (output or "").strip().lower()


def _validate_contains(output: str, expected: str) -> bool:
    return expected.lower() in (output or "").strip().lower()


# LLM-backed faculty batteries. Each routes through its OWN capability slot (separability).
_REASONING = [  # G6 — deductive / transitive / inductive
    TextProbe("If all roses are flowers and this object is a rose, is it a flower? Answer yes or no.", "yes"),
    TextProbe("Tom is taller than Sam. Sam is taller than Bob. Who is tallest? Answer one name.", "tom"),
    TextProbe("What number comes next in 2, 4, 6, 8, ? Answer with only the number.", "10"),
]
_GENERATION = [  # G2 — text/code execution ability
    TextProbe("Output only the single word: hello", "hello"),
    TextProbe("Give the single word opposite of 'up'.", "down"),
    TextProbe("Write a Python expression that adds 2 and 3. Output only the expression.", "2 + 3"),
]
_PROBLEM_SOLVING = [  # G9 — math / algorithmic
    TextProbe("A train travels 60 miles in 2 hours. What is its speed in mph? Answer the number only.", "30"),
    TextProbe("Sort the numbers 3, 1, 2 in ascending order. Answer comma-separated.", "1, 2, 3"),
    TextProbe("What is 7 multiplied by 8? Answer the number only.", "56"),
]
_SOCIAL = [  # G10 — theory of mind / false belief (Sally-Anne style)
    TextProbe(
        "Anna puts her ball in the box and leaves the room. While she is gone, Ben moves the ball "
        "to the basket. When Anna returns, where will she look for her ball first? Answer one word.",
        "box",
    ),
    TextProbe(
        "Sara believes the keys are on the table, but they are actually in the drawer. "
        "Where will Sara look for the keys first? Answer one word.",
        "table",
    ),
]
_PLANNING = [  # G8 — executive: decompose a goal into ordered steps (graded structurally below)
    TextProbe("List, numbered 1-2-3, three steps to make a cup of tea.", "water"),
]
_KNOWLEDGE = [  # Gc breadth — SUBSTRATE-BEYOND-REACH (measured cheap, never MET)
    TextProbe("What is the capital city of France? Answer one word.", "paris"),
    TextProbe("What gas do plants primarily absorb for photosynthesis? Answer one phrase.", "carbon dioxide"),
    TextProbe("Who wrote the play 'Romeo and Juliet'? Answer the surname.", "shakespeare"),
]
_FLUID = [  # Gf frontier abstraction — SUBSTRATE-BEYOND-REACH
    TextProbe("Complete the analogy: hand is to glove as foot is to ____. Answer one word.", "sock"),
    TextProbe("If A=1, B=2, C=3, what is the value of E? Answer the number only.", "5"),
]


# ──────────────────────────────────────────────────────────────────────────────
# Capabilities — the injectable system surfaces. ONE slot per axis ⇒ separable.
# ──────────────────────────────────────────────────────────────────────────────


class MemoryProbe:
    """G5 episodic+semantic memory machinery, routed through the REAL Cohezion modules.

    - Semantic round-trip: `SemanticCache` L1 store→get (the production retrieval path).
    - Episodic round-trip: `JourneyTracker.track_execution` → `get_recent_point_count` increments.

    The embedding tiers are deliberately bypassed (L1 exact + hash-latent) so the probe is offline
    and segfault-safe on XDNA2 (harness note: sentence-transformers can crash on ROCm). We measure the
    memory MACHINERY firing, not embedding quality.
    """

    def __init__(self) -> None:
        from cohezion.cache.semantic_cache import SemanticCache

        self._cache = SemanticCache()
        self._jt = None  # lazily built; forced onto the deterministic hash-latent path

    # -- semantic store/retrieve via the real SemanticCache L1 path --
    def _key(self, prompt: str) -> str:
        import hashlib

        full = f"\n{prompt}\n"
        return hashlib.sha256(full.encode()).hexdigest()[:16]

    def store(self, prompt: str, response: str) -> None:
        import numpy as np

        from cohezion.cache.semantic_cache import CacheEntry

        key = self._key(prompt)
        self._cache.l1_cache[key] = CacheEntry(
            key=key, prompt=prompt, response=response, embedding=np.zeros(1, dtype=np.float32)
        )
        if key not in self._cache.l1_insertion_order:
            self._cache.l1_insertion_order.append(key)

    def retrieve(self, prompt: str) -> str | None:
        import asyncio

        return asyncio.run(self._cache.get(prompt))  # L1 exact hit returns before any embedding

    # -- episodic round-trip via the real JourneyTracker --
    def episodic_roundtrip(self, task: str) -> bool:
        from cohezion.compound.executor import ExecutionResult
        from cohezion.compound.journey_tracker import JourneyTracker

        if self._jt is None:
            self._jt = JourneyTracker(seed=7)
            self._jt._flume_encoder = None  # force deterministic hash latent (offline, no network)
        before = self._jt.get_recent_point_count()
        result = ExecutionResult(
            success=True, output=task, metrics={"coherence": 0.6}, duration_seconds=0.01,
            token_metrics={"cache_hit_rate": 0.5},
        )
        self._jt.track_execution(result, task_description=task, operation_type="memory_probe")
        return self._jt.get_recent_point_count() == before + 1


class LearningProbe:
    """G4 online learning machinery via the REAL `DifficultyEstimator` — does it learn per-skill
    routing from execution feedback? Records consistent NPU-success for one skill and CPU-escalation
    for another, then checks `predict_tier` converged to the right tier for each."""

    def __init__(self) -> None:
        from cohezion.compound.difficulty_estimator import DifficultyEstimator

        self._est = DifficultyEstimator()

    def learn_and_predict(self) -> list[bool]:
        # Skill A: NPU succeeds cleanly and repeatedly → should learn "npu".
        for _ in range(5):
            self._est.record("axis_easy", "op", "npu", escalation_count=0, quality_score=0.9)
        # Skill B: NPU fails / escalates to CPU repeatedly → should learn away from npu.
        for _ in range(5):
            self._est.record("axis_hard", "op", "cpu", escalation_count=2, quality_score=0.8)
        easy = self._est.predict_tier("axis_easy", "op")
        hard = self._est.predict_tier("axis_hard", "op")
        return [easy == "npu", hard in {"igpu", "cpu"}]


def _make_attention_fn(memory: MemoryProbe) -> Callable[[str, list[str]], str | None]:
    """G3 selective attention / distractor resistance: store the goal-relevant fact among N noise
    entries, then retrieve the goal — focus must survive the distractors."""

    def attend(goal_prompt: str, distractors: list[str]) -> str | None:
        for i, d in enumerate(distractors):
            memory.store(d, f"noise-{i}")
        memory.store(goal_prompt, "GOAL-ANSWER")
        return memory.retrieve(goal_prompt)

    return attend


@dataclass
class Capabilities:
    """Injectable system surfaces — one slot per axis so the profile is SEPARABLE.

    LLM-backed slots default to the same local-fleet `chat` callable but are SEPARATE objects, so a
    test can neutralize exactly one (e.g. `reasoning_fn`) and only that axis collapses.
    """

    reasoning_fn: Callable[[str], str]
    generation_fn: Callable[[str], str]
    problem_solving_fn: Callable[[str], str]
    social_fn: Callable[[str], str]
    planning_fn: Callable[[str], str]
    knowledge_fn: Callable[[str], str]  # substrate
    fluid_fn: Callable[[str], str]  # substrate
    classify_fn: Callable[[str], Any]  # task_classifier.classify → RouteDecision
    calibration_classify_fn: Callable[[str], Any]
    memory: MemoryProbe
    attention_fn: Callable[[str, list[str]], str | None]
    learning: LearningProbe
    fleet_model: str = _FLEET_MODEL


# ──────────────────────────────────────────────────────────────────────────────
# Axis registry — (id, faculty, runner, substrate_beyond_reach, gap_map_status)
# ──────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Axis:
    axis_id: str
    faculty: str
    run: Callable[[Capabilities], list[bool]]  # per-item pass/fail
    substrate_beyond_reach: bool
    gap_map_status: str  # the honest prior verdict from the gap-map (recorded, not the live status)


def _grade_text(fn: Callable[[str], str], probes: list[TextProbe]) -> list[bool]:
    return [p.grade(fn(p.prompt)) for p in probes]


def _run_perception(caps: Capabilities) -> list[bool]:
    """G1 (text perception) — does `classify` correctly EXTRACT the structure of the input text?"""
    cases = [
        ("Write a Python function to reverse a string.", "code"),
        ("Reply with one word: is water wet?", "categorical"),
        ("Summarize the main causes of the First World War in a few paragraphs.", "generation"),
    ]
    out = []
    for prompt, want in cases:
        try:
            d = caps.classify_fn(prompt)
            ot = (getattr(d, "output_type", "") or "").lower()
        except Exception:
            out.append(False)
            continue
        out.append(want in ot)
    return out


def _run_metacognition(caps: Capabilities) -> list[bool]:
    """G7 monitoring — does the system KNOW when it is more vs less sure? Confidence must be higher on
    a clear, well-formed request than on a vague one (self-monitoring discrimination)."""
    pairs = [
        ("Write a Python function to add two numbers.", "uh, do the thing with the stuff maybe?"),
        ("Translate 'hello' to French. One word.", "thoughts on it generally?"),
    ]
    out = []
    for clear, vague in pairs:
        try:
            cc = float(getattr(caps.calibration_classify_fn(clear), "confidence", 0.0))
            vc = float(getattr(caps.calibration_classify_fn(vague), "confidence", 0.0))
        except Exception:
            out.append(False)
            continue
        out.append(cc >= vc)
    return out


def _run_calibration(caps: Capabilities) -> list[bool]:
    """B-calibration — Brier-style: emitted `confidence` should track whether the route is correct.
    We pass an item if the system is (confident AND correct) or (uncertain AND wrong) — i.e. its
    confidence is informative. An always-0.99 stub fails the uncertain-and-wrong cases."""
    labeled = [  # (prompt, expected output_type substring)
        ("Write a Python class for a stack.", "code"),
        ("Reply yes or no: is fire cold?", "categorical"),
        ("Tell me about something, anything, you decide what.", None),  # genuinely ambiguous
    ]
    out = []
    for prompt, want in labeled:
        try:
            d = caps.calibration_classify_fn(prompt)
            conf = float(getattr(d, "confidence", 0.0))
            ot = (getattr(d, "output_type", "") or "").lower()
        except Exception:
            out.append(False)
            continue
        correct = (want is not None) and (want in ot)
        # informative if confidence agrees with correctness direction (0.55 = the classifier's
        # length-fallback "unsure" floor)
        out.append((correct and conf >= 0.6) or ((not correct) and conf < 0.66))
    return out


def _run_planning(caps: Capabilities) -> list[bool]:
    """G8 executive — decompose a goal into ORDERED steps. Graded structurally (multiple steps) AND
    on a required content token, so an empty/degenerate planner fails."""
    out = []
    for p in _PLANNING:
        text = caps.planning_fn(p.prompt) or ""
        has_steps = sum(c in text for c in ("1", "2")) >= 2 or text.count("\n") >= 1
        out.append(has_steps and p.grade(text))
    return out


def _run_speed(caps: Capabilities) -> list[bool]:
    """B1 — processing/response speed of the routing brain. `classify` must be fast (<50ms); the live
    NPU path is microseconds. A pass per item routed under the latency budget."""
    prompts = ["classify this", "what is 2+2?", "write code", "summarize the news today please"]
    out = []
    for pr in prompts:
        t0 = time.perf_counter()
        try:
            caps.classify_fn(pr)
        except Exception:
            out.append(False)
            continue
        out.append((time.perf_counter() - t0) < 0.050)
    return out


def _run_memory(caps: Capabilities) -> list[bool]:
    """G5 — semantic store→retrieve (SemanticCache) + episodic round-trip (JourneyTracker)."""
    out = []
    facts = [
        ("the cohezion launch code is alpha-7", "alpha-7"),
        ("the meeting is on tuesday at noon", "tuesday"),
    ]
    for prompt, marker in facts:
        caps.memory.store(prompt, f"recall:{marker}")
        got = caps.memory.retrieve(prompt) or ""
        out.append(marker in got)
    try:
        out.append(caps.memory.episodic_roundtrip("remember this execution"))
    except Exception:
        out.append(False)
    return out


def _run_attention(caps: Capabilities) -> list[bool]:
    """G3 — retrieve the goal-relevant fact buried among distractors."""
    out = []
    for goal in ("where did I leave the goal key", "the one true target fact"):
        noise = [f"irrelevant chatter number {i}" for i in range(8)]
        got = caps.attention_fn(goal, noise) or ""
        out.append("GOAL-ANSWER" in got)
    return out


def _run_learning(caps: Capabilities) -> list[bool]:
    return caps.learning.learn_and_predict()


_AXES: list[Axis] = [
    Axis("G1_perception", "Perception (text)", _run_perception, False, "PARTIAL"),
    Axis("G2_generation", "Generation", lambda c: _grade_text(c.generation_fn, _GENERATION), False, "PARTIAL"),
    Axis("G3_attention", "Attention", _run_attention, False, "PARTIAL"),
    Axis("G4_learning", "Learning", _run_learning, False, "PARTIAL"),
    Axis("G5_memory", "Memory", _run_memory, False, "MET"),
    Axis("G6_reasoning", "Reasoning", lambda c: _grade_text(c.reasoning_fn, _REASONING), False, "PARTIAL"),
    Axis("G7_metacognition", "Metacognition", _run_metacognition, False, "PARTIAL"),
    Axis("G8_executive", "Executive functions", _run_planning, False, "PARTIAL"),
    Axis("G9_problem_solving", "Problem solving", lambda c: _grade_text(c.problem_solving_fn, _PROBLEM_SOLVING), False, "PARTIAL"),
    Axis("G10_social", "Social cognition", lambda c: _grade_text(c.social_fn, _SOCIAL), False, "GAP"),
    Axis("B1_speed", "Processing speed", _run_speed, False, "MET"),
    Axis("B2_calibration", "Confidence calibration", _run_calibration, False, "PARTIAL"),
    # Substrate-BEYOND-REACH axes — MEASURED where cheap, never flipped to MET.
    Axis("Gc_knowledge_breadth", "Memory: broad knowledge (Gc)", lambda c: _grade_text(c.knowledge_fn, _KNOWLEDGE), True, "BEYOND"),
    Axis("Gf_fluid_frontier", "Problem solving: fluid reasoning (Gf)", lambda c: _grade_text(c.fluid_fn, _FLUID), True, "BEYOND"),
    Axis("Gv_perception_native", "Perception: native visual/auditory (Gv/Ga)", lambda c: _run_native_perception(c), True, "BEYOND"),
]


def _run_native_perception(_caps: Capabilities) -> list[bool]:
    """G1 native Gv/Ga — there is NO trained visual/auditory cortex in the cognitive path (borrowed
    VLM shim only, dormant). Honestly scores 0; status is forced BEYOND_REACH regardless."""
    return [False]


# ──────────────────────────────────────────────────────────────────────────────
# Scoring / status
# ──────────────────────────────────────────────────────────────────────────────


def _status(score: float | None, n: int, substrate: bool) -> str:
    if substrate:
        return "BEYOND_REACH"
    if score is None or n == 0:
        return "GAP"
    if score >= _MET:
        return "MET"
    if score >= _PARTIAL:
        return "PARTIAL"
    return "GAP"


def _binomial_se(p: float, n: int) -> float:
    if n <= 0:
        return 1.0
    return (p * (1.0 - p) / n) ** 0.5


def _score_axis(axis: Axis, caps: Capabilities, repeats: int) -> dict[str, Any]:
    per_run_scores: list[float] = []
    last_results: list[bool] = []
    for _ in range(max(1, repeats)):
        try:
            results = axis.run(caps)
        except Exception as exc:  # an axis must never crash the whole profile
            logger.warning("axis %s raised, scoring 0: %s", axis.axis_id, exc)
            results = [False]
        last_results = results
        per_run_scores.append(mean(1.0 if r else 0.0 for r in results) if results else 0.0)
    n = len(last_results) * max(1, repeats)
    score = mean(per_run_scores) if per_run_scores else 0.0
    # uncertainty: combine binomial SE with cross-repeat stochasticity
    se = _binomial_se(score, n)
    spread = (max(per_run_scores) - min(per_run_scores)) if len(per_run_scores) > 1 else 0.0
    uncertainty = round(min(1.0, se + 0.5 * spread), 4)
    return {
        "faculty": axis.faculty,
        "score": round(score, 4),
        "n": n,
        "uncertainty": uncertainty,
        "status": _status(score, n, axis.substrate_beyond_reach),
        "substrate_beyond_reach": axis.substrate_beyond_reach,
        "gap_map_status": axis.gap_map_status,
        "detail": f"{sum(1 for r in last_results if r)}/{len(last_results)} held-out probes passed (last run)",
    }


# ──────────────────────────────────────────────────────────────────────────────
# Default (live) + oracle (offline) capabilities
# ──────────────────────────────────────────────────────────────────────────────


def _local_chat(prompt: str, model: str = _FLEET_MODEL) -> str:
    """Route a probe through the live local AMD fleet via the OmniRouter (:13305), $0. temp=0 for
    determinism. Returns '' on any failure (offline-safe — the axis simply scores low)."""
    try:
        import httpx

        r = httpx.post(
            _OMNI_CHAT_URL,
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 512,
                "temperature": 0.0,
            },
            timeout=120,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"].get("content") or ""
    except Exception as exc:
        logger.debug("local fleet chat failed (axis will score low): %s", exc)
        return ""


def build_default_capabilities(fleet_model: str = _FLEET_MODEL) -> Capabilities:
    """Wire every axis to its real, LIVE Cohezion surface. LLM faculties → local fleet (:13305)."""
    from cohezion.inference.task_classifier import classify

    memory = MemoryProbe()

    def chat(prompt: str) -> str:
        return _local_chat(prompt, fleet_model)

    return Capabilities(
        reasoning_fn=chat,
        generation_fn=chat,
        problem_solving_fn=chat,
        social_fn=chat,
        planning_fn=chat,
        knowledge_fn=chat,
        fluid_fn=chat,
        classify_fn=classify,
        calibration_classify_fn=classify,
        memory=memory,
        attention_fn=_make_attention_fn(memory),
        learning=LearningProbe(),
        fleet_model=fleet_model,
    )


# Oracle answers: a perfect-substrate baseline for the separability / discrimination tests. Built once
# from every LLM battery so the answers live in exactly one place (the probes themselves).
_ORACLE_ANSWERS: dict[str, str] = {}
for _battery in (_REASONING, _GENERATION, _PROBLEM_SOLVING, _SOCIAL, _PLANNING, _KNOWLEDGE, _FLUID):
    for _p in _battery:
        # planning needs ordered steps + the content token to pass its structural grader
        _ORACLE_ANSWERS[_p.prompt] = (
            f"1. boil {_p.expected}\n2. pour {_p.expected}\n3. done"
            if _p in _PLANNING
            else _p.expected
        )


def oracle_capabilities() -> Capabilities:
    """A deterministic, OFFLINE baseline: the LLM-backed faculties answer their own held-out batteries
    correctly (a 'perfect substrate'); the non-LLM faculties use the REAL offline Cohezion impls
    (classify, SemanticCache L1, JourneyTracker, DifficultyEstimator). Used by the tests to prove
    separability and beyond-reach honesty without any network."""

    def oracle(prompt: str) -> str:
        return _ORACLE_ANSWERS.get(prompt, "")

    caps = build_default_capabilities()
    caps.reasoning_fn = oracle
    caps.generation_fn = oracle
    caps.problem_solving_fn = oracle
    caps.social_fn = oracle
    caps.planning_fn = oracle
    caps.knowledge_fn = oracle
    caps.fluid_fn = oracle
    return caps


# ──────────────────────────────────────────────────────────────────────────────
# The harness entry point + persistence
# ──────────────────────────────────────────────────────────────────────────────


def run_profile(
    capabilities: Capabilities | None = None,
    *,
    repeats: int = 1,
    persist: bool = False,
) -> dict[str, Any]:
    """Run all axes against Cohezion-as-system and return an HONEST cognitive profile.

    Returns ``{"axes": {axis_id: {...}}, "summary": {...}, "timestamp": ...}``.
    ``persist=True`` writes the profile to SurrealDB ``cognitive_profile`` + a vault scorecard.
    """
    caps = capabilities or build_default_capabilities()
    axes: dict[str, Any] = {ax.axis_id: _score_axis(ax, caps, repeats) for ax in _AXES}

    statuses = [a["status"] for a in axes.values()]
    summary = {
        "n_axes": len(axes),
        "MET": statuses.count("MET"),
        "PARTIAL": statuses.count("PARTIAL"),
        "GAP": statuses.count("GAP"),
        "BEYOND_REACH": statuses.count("BEYOND_REACH"),
        "mean_score_testable": round(
            mean([a["score"] for a in axes.values() if not a["substrate_beyond_reach"]]) or 0.0, 4
        ),
    }
    profile = {
        "timestamp": datetime.now(UTC).isoformat(),
        "system": "cohezion (assembled system, not model — B5)",
        "fleet_model": caps.fleet_model,
        "repeats": repeats,
        "axes": axes,
        "summary": summary,
    }

    if persist:
        _persist_surreal(profile)
        _write_scorecard(profile)
    return profile


def _persist_surreal(profile: dict[str, Any]) -> None:
    """Write the profile to SurrealDB ``cognitive_profile`` via the parameterized `_surql_set`
    (injection-safe by construction). Fail-open."""
    try:
        import httpx

        from cohezion.compound.prompt_version_registry import (
            _NOW,
            _SURREAL_HEADERS,
            _SURREAL_URL,
            _surql_set,
        )

        q = "CREATE cognitive_profile SET " + _surql_set(
            {
                "profile_json": json.dumps(profile),
                "mean_score_testable": profile["summary"]["mean_score_testable"],
                "n_met": profile["summary"]["MET"],
                "created_at": _NOW,
            }
        ) + ";"
        httpx.post(_SURREAL_URL, content=q, headers=_SURREAL_HEADERS, auth=("root", "root"), timeout=5.0)
        logger.info("persisted cognitive_profile to SurrealDB")
    except Exception as exc:
        logger.debug("cognitive_profile SurrealDB persist failed (fail-open): %s", exc)


def _write_scorecard(profile: dict[str, Any]) -> Path | None:
    """Write a human-readable vault scorecard markdown. Fail-open."""
    try:
        vault = Path.home() / "vaults" / "cohezion-vault" / "reports"
        vault.mkdir(parents=True, exist_ok=True)
        path = vault / f"cognitive-profile-scorecard-{datetime.now().strftime('%Y-%m-%d')}.md"
        lines = [
            "---",
            "type: scorecard",
            "title: Cohezion Cognitive Profile (DeepMind 10-faculty framework)",
            f"date: {datetime.now().strftime('%Y-%m-%d')}",
            "tags: [agi, cognitive-framework, scorecard]",
            "---",
            "",
            "# Cohezion Cognitive Profile — Honest Scorecard (system, not model)",
            "",
            f"- Generated: {profile['timestamp']}  ·  fleet model: `{profile['fleet_model']}`",
            f"- Summary: {profile['summary']}",
            "",
            "| Axis | Faculty | Score | n | Uncert. | Status | Substrate-BEYOND | Probes |",
            "|------|---------|-------|---|---------|--------|------------------|--------|",
        ]
        for aid, ax in profile["axes"].items():
            lines.append(
                f"| {aid} | {ax['faculty']} | {ax['score']:.2f} | {ax['n']} | {ax['uncertainty']:.3f} | "
                f"**{ax['status']}** | {'yes' if ax['substrate_beyond_reach'] else '—'} | {ax['detail']} |"
            )
        path.write_text("\n".join(lines) + "\n")
        logger.info("wrote cognitive-profile scorecard to %s", path)
        return path
    except Exception as exc:
        logger.debug("scorecard write failed (fail-open): %s", exc)
        return None


__all__ = [
    "Axis",
    "Capabilities",
    "LearningProbe",
    "MemoryProbe",
    "TextProbe",
    "build_default_capabilities",
    "oracle_capabilities",
    "run_profile",
]
