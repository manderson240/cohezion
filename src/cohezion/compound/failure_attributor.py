"""FAPO-style step-level failure attribution for compound execution results.

Classifies failed executions into one of four semantic categories to guide
the appropriate escalation level for skill refinement:

    format     → L1 (prompt edit): structured-output validation failed
    cascading  → L3 (structural): near-empty output; upstream component failed
    retrieval  → L2 (parameter): vault returned no guidance to inform execution
    reasoning  → L1 (prompt edit): format-valid, non-empty, had guidance, wrong answer

Decision tree order matters — format is detected first (most specific),
reasoning is the fallthrough (least specific). No LLM required; all rules are
deterministic and execute in < 1ms.

FAPO reference: Cisco AI — Pipeline-Aware Prompt Optimization (2026-06)
V-Model obligation: R1 satisfied. R3 (overfitting guard) deferred — recorded
as an unsatisfied proof_obligation when skill_refiner writes L2/L3 obligations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cohezion.compound.output_validator import validate_structured_output


# Near-empty output (< this many chars) → cascading failure
_CASCADING_THRESHOLD = 20

# quality_score = 1 - anomaly_score; below this threshold on a failed execution
# → reasoning failure
_REASONING_QUALITY_THRESHOLD = 0.7

# FAPO three-level escalation map (category → level)
_ESCALATION: dict[str, str] = {
    "format": "L1",  # prompt edit: inject exact validation error into skill guidance
    "reasoning": "L1",  # prompt edit: add reasoning scaffolding to PRIME skill
    "retrieval": "L2",  # parameter change: vault indexing / guidance structure needs review
    "cascading": "L3",  # structural: upstream component produced near-empty output
}


@dataclass(frozen=True)
class FailureAttribution:
    """FAPO failure attribution result."""

    category: str  # "format" | "cascading" | "retrieval" | "reasoning"
    escalation_level: str  # "L1" | "L2" | "L3"
    evidence: str  # human-readable rationale, injected into proof_obligation


class FailureAttributor:
    """Deterministic FAPO-style failure attributor.

    Classifies compound execution failures into one of four semantic categories
    using a fixed, priority-ordered decision tree. No LLM calls — all rules are
    deterministic. Call-sites invoke classify() on every execution and ignore the
    None return for successful runs.

    The decision tree:
        1. format     — output_validator detects invalid structured output
        2. cascading  — output near-empty (< _CASCADING_THRESHOLD chars)
        3. retrieval  — no vault guidance was retrieved (empty decision_paths)
        4. reasoning  — fallthrough: format-valid, non-empty, had guidance, low quality
    """

    def classify(
        self,
        output: str,
        metrics: dict[str, Any],
        decision_paths: list[str] | None = None,
    ) -> FailureAttribution | None:
        """Attribute a failed execution to a FAPO failure category.

        Returns None when the quality signal indicates success (quality_score above
        threshold AND no explicit validation failure flag). Call-sites may invoke on
        every execution and handle the None result as "no failure to attribute."

        Args:
            output: Raw execution output string.
            metrics: CompoundExecutor metrics dict. Relevant keys:
                ``anomaly_score`` (float 0–1, lower = better),
                ``output_validation_failed`` (bool),
                ``output_validation_error`` (str).
            decision_paths: Vault guidance paths retrieved during execution.
                An empty list or None means no vault context was available.

        Returns:
            FailureAttribution if a failure category was detected, None otherwise.
        """
        validation_failed = bool(metrics.get("output_validation_failed", False))
        quality_score = 1.0 - float(metrics.get("anomaly_score", 0.5))

        # Short-circuit: healthy execution (high quality, no explicit validation error)
        if quality_score > _REASONING_QUALITY_THRESHOLD and not validation_failed:
            return None

        text = output.strip()

        # ── 1. FORMAT ────────────────────────────────────────────────────────
        # Explicit flag from execute_with_output_validation retry loop
        if validation_failed:
            val_err = (
                metrics.get("output_validation_error") or "structured output validation failed"
            )
            return FailureAttribution(
                category="format",
                escalation_level=_ESCALATION["format"],
                evidence=f"output_validator: {val_err}",
            )
        # Run validator when output looks like it was attempting structured output
        if text.startswith(("{", "[")):
            valid, err = validate_structured_output(text)
            if not valid:
                return FailureAttribution(
                    category="format",
                    escalation_level=_ESCALATION["format"],
                    evidence=f"output_validator: {err}",
                )

        # ── 2. CASCADING ─────────────────────────────────────────────────────
        # Near-empty output indicates an upstream component produced nothing
        if len(text) < _CASCADING_THRESHOLD:
            return FailureAttribution(
                category="cascading",
                escalation_level=_ESCALATION["cascading"],
                evidence=f"output length {len(text)} < threshold {_CASCADING_THRESHOLD}; upstream produced nothing",
            )

        # ── 3. RETRIEVAL ─────────────────────────────────────────────────────
        # No vault guidance was available to inform this execution
        if not decision_paths:
            return FailureAttribution(
                category="retrieval",
                escalation_level=_ESCALATION["retrieval"],
                evidence="no vault guidance retrieved (empty decision_paths); vault indexing may need review",
            )

        # ── 4. REASONING ─────────────────────────────────────────────────────
        # Fallthrough: format-valid, non-empty, had guidance — the model reasoned poorly
        return FailureAttribution(
            category="reasoning",
            escalation_level=_ESCALATION["reasoning"],
            evidence=(
                f"quality_score={quality_score:.3f} below threshold {_REASONING_QUALITY_THRESHOLD}; "
                "format valid, non-empty, vault guidance present — reasoning failure"
            ),
        )
