"""Coherence v3 — ADDITIVE, OFF-by-default per-cycle quality scalar.

This module lands the v3 coherence MACHINERY without flipping production behavior.
It is opt-in: gated on ``enable_coherence_v3`` (or ``coherence_version == 2``). When
disabled — the default — :func:`compute_coherence` reproduces the executor's current
**Step 5.8** coherence formula byte-for-byte, so wiring this module in with the flag
off cannot change any persisted value.

Design + review contract (both are the spec):
  * ``research/2026-07-10-coherence-redesign.md`` — the v3 design (§3 base, §6 formula v3).
  * ``research/2026-07-10-coherence-v3-redteam.md`` — Opus ADOPT-WITH-CHANGES; its
    change-set is MANDATORY. This module honors:
      F1  spine grader runs on the **iGPU lane** (Gemma-4-E4B via :13305), INTEGER
          0–100 scale ÷100 (the [0,1] float prompt mode-collapses to 0.00 on the 1B NPU
          model). Gate 0 = :func:`spine_liveness_ok`.
      F2  rubric prompt forbids rewarding fluency/verbosity and penalizes unsupported
          claims (see :func:`default_igpu_grader`); the scalar is *surface* quality, not
          correctness, for ground-truth-free tasks — read it that way.
      F3  **depth-weighting is REMOVED from the scalar** (comparability-critical). The
          scalar's ``verbal = entail`` unconditionally; task ``depth`` is exposed only as
          a returned diagnostic covariate, never folded in. Enforced in code, not by a
          default — there is deliberately no toggle to fold depth back in.
      F5  grader + entailment run on the iGPU lane with tiny token caps; never deepseek.
          Card-inherit sampling (NO ``temperature`` field) per F0/F1.
      F6  :func:`workspace_occupancy` ships here as topical-entropy (the design §6
          NPU/$0 form); FLUME latent sparsity is the documented, more-stable alternative.

The final multiplicative form (Opus F4 — variance-preserving, not re-saturating):

    coherence = clamp01(base * (0.5 + 0.5*health) * (0.5 + 0.5*verbal))

``verbal`` reuses the CB14 citation-gate machinery
(:meth:`SkillRefiner._lm_signal_cites_metrics`) as a cheap floor — a self-report that
cites no real metric cannot be faithful — layered under an injectable entailment judge.

Note on scope: the executor's **Step 5.9** natural-capital blend
(``coherence*0.9 + habitat_quality*0.1``) is a *separate, later* executor-layer step and
is intentionally NOT reproduced here; this module reproduces Step 5.8 only, which is what
the activation spec targets. The 5.9 blend, if present, still applies at the executor.
"""

from __future__ import annotations

import logging
import math
import re
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any


logger = logging.getLogger(__name__)

# Injectable grader/entailment callables. Defaults live in factory funcs
# (:func:`default_igpu_grader` / :func:`default_igpu_entailment`) used only at wiring
# time; the pure scoring functions REQUIRE these to be passed so a forgotten mock in a
# test fails loudly instead of hitting the network.
GraderFn = Callable[[str, str], float]  # (task, output_text) -> spine in [0,1]
EntailFn = Callable[[str, Mapping[str, Any]], float]  # (insight, metrics) -> [0,1]

_IGPU_MODEL = "Gemma-4-E4B-it-GGUF"  # F1: iGPU grader lane, NOT the 1B NPU model
_LEMONADE_PORT = 13305  # the router serves the whole catalog on demand


def clamp01(x: object, default: float = 0.0) -> float:
    """Coerce to a finite float clamped to [0, 1]; non-finite/uncoercible → ``default``."""
    try:
        f = float(x)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    if not math.isfinite(f):
        return default
    return max(0.0, min(1.0, f))


def logprob_to_quality(mean_logprob: float) -> float:
    """Monotone map mean token log-prob → quality proxy in (0, 1].

    Simple, documented, deterministic — ``exp(mean_logprob)`` (log-probs are ≤ 0, so the
    result is in (0, 1]). Deliberately NOT coupled to escalation_gate's IsotonicCalibrator:
    this is off-by-default corroboration, and a self-contained monotone map keeps the
    machinery testable without pulling in a calibration dependency.
    """
    try:
        lp = float(mean_logprob)
    except (TypeError, ValueError):
        return 0.5
    if not math.isfinite(lp):
        return 0.5
    return clamp01(math.exp(min(0.0, lp)))


# --------------------------------------------------------------------------------------
# v1 reproduction — the OFF path (executor.py Step 5.8, verbatim semantics)
# --------------------------------------------------------------------------------------
def coherence_v1(success: bool, metrics: Mapping[str, Any]) -> float:
    """Reproduce executor Step 5.8 exactly: ``mean`` of the cohesion components.

    Mirrors ``executor.py`` lines 1286-1300 with identical component order and defaults:
      * ``0.7 if success else 0.2`` (precipitation success)
      * ``metrics["anomaly_score"]`` (HEALTH score, default 1.0, used directly — NOT
        clamped, matching the current code)
      * ``alignment["intent_match"]`` (default 0.5) — appended ONLY when a truthy
        ``metrics["alignment"]`` dict is present (the current ``:=`` walrus + truthiness).

    This is the byte-for-byte OFF-by-default behavior. It does NOT include the separate
    Step 5.9 natural-capital blend (that stays at the executor layer).
    """
    components: list[float] = [0.7 if success else 0.2]
    components.append(metrics.get("anomaly_score", 1.0))
    alignment_data = metrics.get("alignment", {})
    if alignment_data:
        components.append(alignment_data.get("intent_match", 0.5))
    return sum(components) / len(components)


# --------------------------------------------------------------------------------------
# v3 components
# --------------------------------------------------------------------------------------
def base_quality(
    task: str,
    output_text: str,
    metrics: Mapping[str, Any],
    alignment: Mapping[str, Any] | None,
    execfn: Mapping[str, Any] | None,
    success: bool,
    grader: GraderFn,
) -> float:
    """Design §3 base: tier-independent spine + bounded corroboration + weak success anchor.

    ``grader`` is REQUIRED (no default) — the spine must vary or every downstream gate is
    meaningless (F1). Corroboration signals (logprob / quality_score / intent_match) only
    nudge the spine when present, each bounded so the spine stays the anchor; corroboration
    shifts the spine by at most ±50%.
    """
    spine = clamp01(grader(task, output_text))
    adj, w = 0.0, 0.0
    lp = metrics.get("mean_logprob")
    if lp is not None:
        adj += 0.6 * (logprob_to_quality(lp) - spine)
        w += 0.6
    qs = (execfn or {}).get("quality_score")
    if qs is not None:
        adj += 0.5 * (clamp01(qs) - spine)
        w += 0.5
    im = (alignment or {}).get("intent_match")
    if im is not None:
        adj += 0.4 * (clamp01(im) - spine)
        w += 0.4
    base = clamp01(spine + (adj / max(w, 1.0)) * 0.5)
    # Weak success anchor — NOT dominant (it was the whole story in v1).
    base = 0.9 * base + 0.1 * (1.0 if success else 0.0)
    return clamp01(base)


def _cb14_cites_metrics(insight: str, metrics: Mapping[str, Any]) -> bool:
    """Reuse CB14 without duplicating it: call ``SkillRefiner._lm_signal_cites_metrics``.

    That method ignores ``self`` (verified — it references only ``text``/``metrics``), so we
    invoke it with ``self=None`` on a real :class:`ExecutionMetrics` built from the cycle's
    metrics dict. Fail-open (True) on any import/build error so a missing dependency never
    silently zeroes the verbal gate.
    """
    try:
        from cohezion.compound.skill_refiner import ExecutionMetrics, SkillRefiner

        em = ExecutionMetrics(
            success=bool(metrics.get("success", True)),
            duration_seconds=float(metrics.get("duration_seconds", 0.0) or 0.0),
            tokens_used=int(metrics.get("tokens_used", 0) or 0),
            token_efficiency=float(metrics.get("token_efficiency", 0.0) or 0.0),
            quality_score=float(metrics.get("quality_score", 0.0) or 0.0),
            anomaly_score=float(metrics.get("anomaly_score", 1.0) or 1.0),
            cached_hits=int(metrics.get("cached_hits", 0) or 0),
        )
        return bool(SkillRefiner._lm_signal_cites_metrics(None, insight, em))  # type: ignore[arg-type]
    except (ImportError, AttributeError, TypeError, ValueError, KeyError) as e:
        logger.debug("CB14 citation reuse failed (fail-open): %s", e)
        return True


def verbal_score(
    insight: str,
    metrics: Mapping[str, Any],
    entail_fn: EntailFn,
) -> float:
    """Verbalizability / faithfulness gate — DEPTH-UNIFORM (F3).

    ``verbal = entail`` for the scalar; task depth is NOT folded in here (see
    :func:`compute_coherence_v3` which returns ``depth`` as a diagnostic covariate).
    ``entail_fn`` is REQUIRED. CB14 acts as a hard floor: a self-report that cites no real
    metric value cannot be faithful, so its entailment is forced to 0.
    """
    entail = clamp01(entail_fn(insight, metrics))
    if not _cb14_cites_metrics(insight, metrics):
        entail = 0.0
    return entail


def reasoning_depth(task: str) -> float:
    """Task reasoning-depth in [0,1] from ``task_classifier`` — DIAGNOSTIC ONLY (F3).

    ``reasoning``/``math_reasoning`` → ~1.0, ``short_categorical`` → ~0.2, else ~0.5.
    Returned as a covariate so cross-skill consumers can control for it; it is NEVER
    multiplied into ``final_coherence`` (that would re-introduce the F3 confound).
    """
    try:
        from cohezion.inference.task_classifier import classify

        otype = classify(task or "").output_type
    except (ImportError, AttributeError, ValueError, TypeError) as e:
        logger.debug("reasoning_depth classify failed (neutral 0.5): %s", e)
        return 0.5
    if otype in ("reasoning", "math_reasoning"):
        return 1.0
    if otype in ("short_categorical", "short_answer"):
        return 0.2
    return 0.5


@dataclass
class CoherenceV3Result:
    """Structured v3 output — the scalar plus its factors and the depth covariate."""

    final_coherence: float
    base: float
    health: float
    verbal: float
    spine: float
    depth: float  # F3 diagnostic covariate — NOT folded into final_coherence
    coherence_version: int = 2


def compute_coherence_v3(
    *,
    task: str,
    output_text: str,
    learning: str,
    metrics: Mapping[str, Any],
    success: bool,
    grader: GraderFn,
    entail_fn: EntailFn,
    alignment: Mapping[str, Any] | None = None,
    execfn: Mapping[str, Any] | None = None,
) -> CoherenceV3Result:
    """Full v3 computation. ``grader`` and ``entail_fn`` are REQUIRED (no network default).

    ``final = clamp01(base * (0.5 + 0.5*health) * (0.5 + 0.5*verbal))``.
    """
    base = base_quality(task, output_text, metrics, alignment, execfn, success, grader)
    health = clamp01(metrics.get("anomaly_score", 1.0), default=1.0)
    verbal = verbal_score(learning, metrics, entail_fn)
    spine = clamp01(grader(task, output_text))
    final = clamp01(base * (0.5 + 0.5 * health) * (0.5 + 0.5 * verbal))
    return CoherenceV3Result(
        final_coherence=final,
        base=base,
        health=health,
        verbal=verbal,
        spine=spine,
        depth=reasoning_depth(task),
    )


def compute_coherence(
    *,
    success: bool,
    metrics: Mapping[str, Any],
    task: str = "",
    output_text: str = "",
    learning: str = "",
    alignment: Mapping[str, Any] | None = None,
    execfn: Mapping[str, Any] | None = None,
    enable_coherence_v3: bool = False,
    coherence_version: int | None = None,
    grader: GraderFn | None = None,
    entail_fn: EntailFn | None = None,
) -> float:
    """Dispatcher — the proof-of-equivalence for OFF-by-default.

    OFF (``enable_coherence_v3=False`` and ``coherence_version != 2``): returns
    :func:`coherence_v1` — byte-for-byte the executor Step 5.8 value. ON: returns the v3
    scalar; ``grader`` and ``entail_fn`` must be provided (a v3 request without them is a
    caller error, raised loudly rather than silently falling back).
    """
    use_v3 = enable_coherence_v3 or coherence_version == 2
    if not use_v3:
        return coherence_v1(success, metrics)
    if grader is None or entail_fn is None:
        raise ValueError(
            "coherence v3 requires both `grader` and `entail_fn` (use "
            "default_igpu_grader()/default_igpu_entailment() at wiring time)."
        )
    return compute_coherence_v3(
        task=task,
        output_text=output_text,
        learning=learning,
        metrics=metrics,
        success=success,
        grader=grader,
        entail_fn=entail_fn,
        alignment=alignment,
        execfn=execfn,
    ).final_coherence


# --------------------------------------------------------------------------------------
# Gate 0 — spine liveness (Opus F1)
# --------------------------------------------------------------------------------------
def spine_liveness_ok(
    samples: Sequence[float],
    *,
    min_count: int = 30,
    min_distinct: int = 8,
    max_share: float = 0.30,
) -> bool:
    """Opus gate-0: is the spine a LIVE signal, not a mode-collapsed constant?

    Over ``samples`` (spine values from varied real outputs) require: at least
    ``min_count`` samples, at least ``min_distinct`` distinct 3-decimal values, and no
    single 3-decimal value taking more than ``max_share`` of the sample. Returns False on a
    degenerate/constant set (the 1B-collapse or a stuck grader) — a callable the lead runs
    empirically before activation.
    """
    vals: list[float] = []
    for s in samples:
        try:
            f = float(s)
        except (TypeError, ValueError):
            continue
        if math.isfinite(f):
            vals.append(round(f, 3))
    if len(vals) < min_count:
        return False
    counts = Counter(vals)
    if len(counts) < min_distinct:
        return False
    return max(counts.values()) / len(vals) <= max_share


# --------------------------------------------------------------------------------------
# Sibling balance scalar — workspace occupancy (design §6; NOT part of final_coherence)
# --------------------------------------------------------------------------------------
def workspace_occupancy(text: str) -> float:
    """Normalized topical entropy of ``text`` → [0,1] — the SEPARATE balance series.

    This is the design §6 NPU/$0 sibling scalar (Gurnee et al. 2026 global-workspace
    occupancy). It is deliberately independent of ``final_coherence``: its consumer is
    ``fractal_metrics`` (the hiho path), where ``hiho_fixed_point_deviation`` /
    ``hiho_engaged`` relocate onto THIS series. It is wired as an additive field and is
    NEVER folded into the quality scalar.

    Shannon entropy of the word distribution ÷ log(distinct-words) → 1.0 for maximally
    varied text, → 0.0 for a single repeated token. (Opus F6 flags text entropy as noisy on
    short strings and prefers FLUME latent sparsity as the more-stable definition; that is
    the documented upgrade path — the signature here stays ``(text) -> float`` per spec.)
    """
    tokens = re.findall(r"[a-z0-9]+", (text or "").lower())
    if len(tokens) < 2:
        return 0.0
    counts = Counter(tokens)
    total = sum(counts.values())
    entropy = -sum((c / total) * math.log(c / total) for c in counts.values())
    max_entropy = math.log(len(counts))
    if max_entropy <= 0:  # all tokens identical → one distinct word → no occupancy
        return 0.0
    return clamp01(entropy / max_entropy)


# --------------------------------------------------------------------------------------
# Default iGPU clients (wiring-time only; tests mock these). NO temperature field
# (card-inherit sampling, F0/F1). Small token caps (F5). Never deepseek.
# --------------------------------------------------------------------------------------
def _lemonade_score(
    prompt: str, *, max_tokens: int, port: int, model: str, timeout: float
) -> float:
    """POST an OpenAI-compatible chat request to the :13305 router; parse an int 0–100 ÷100.

    Card-inherit sampling: the body carries NO ``temperature`` (the summarizer bug we hit
    twice — the server applies the model card's sampling; mirroring it client-side broke it).
    Fail-open to neutral 0.5 on any network/parse error so a grader outage never aborts a
    cycle (off-by-default machinery; the lead tunes fail behavior at activation).
    """
    import httpx

    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        # NO "temperature" — inherit the model card's sampling (F0/F1).
    }
    try:
        resp = httpx.post(
            f"http://localhost:{port}/api/v1/chat/completions", json=body, timeout=timeout
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        m = re.search(r"\d{1,3}", content or "")
        if not m:
            return 0.5
        return clamp01(int(m.group()) / 100.0)
    except (httpx.HTTPError, KeyError, IndexError, ValueError, TypeError) as e:
        logger.warning("lemonade grader/entailment call failed (neutral 0.5): %s", e)
        return 0.5


def default_igpu_grader(
    *, port: int = _LEMONADE_PORT, model: str = _IGPU_MODEL, timeout: float = 30.0
) -> GraderFn:
    """iGPU spine grader (F1/F2): integer 0–100 rubric, anti-fluency, ÷100. ≤8 output tokens."""

    def grade(task: str, output_text: str) -> float:
        prompt = (
            "You are a STRICT output grader. Rate the OUTPUT's quality for the TASK on an "
            "INTEGER scale 0-100 (0=off-topic/degenerate, 100=on-topic, complete, internally "
            "consistent, well-supported). PENALIZE unsupported or unverifiable claims. Do NOT "
            "reward verbosity, fluency, or length — a longer answer is not a better answer. "
            "Reply with ONLY the integer.\n\n"
            f"TASK:\n{task}\n\nOUTPUT:\n{output_text[:2000]}\n\nScore (0-100):"
        )
        return _lemonade_score(prompt, max_tokens=8, port=port, model=model, timeout=timeout)

    return grade


def default_igpu_entailment(
    *, port: int = _LEMONADE_PORT, model: str = _IGPU_MODEL, timeout: float = 30.0
) -> EntailFn:
    """iGPU faithfulness judge (F5): does INSIGHT entail the ACTUAL metrics? int 0–100 ÷100."""

    def entail(insight: str, metrics: Mapping[str, Any]) -> float:
        facts = {
            k: metrics.get(k)
            for k in ("success", "quality_score", "tier_used", "anomaly_score", "tokens_used")
            if k in metrics
        }
        prompt = (
            "Does the INSIGHT faithfully and non-contradictorily describe the ACTUAL METRICS? "
            "Rate entailment on an INTEGER scale 0-100 (0=contradicts/confabulates, "
            "100=fully faithful). Reply with ONLY the integer.\n\n"
            f"INSIGHT:\n{insight}\n\nACTUAL METRICS:\n{facts}\n\nEntailment (0-100):"
        )
        return _lemonade_score(prompt, max_tokens=16, port=port, model=model, timeout=timeout)

    return entail
