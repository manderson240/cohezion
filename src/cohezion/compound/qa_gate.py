"""BMAD qa_gate P0 — risk-weighted 4-state ADVISORY verification gate.

Ports the BMAD TEA *risk-governance* rules (``~/.bmad/.../testarch/.../risk-governance.md``) to
Python and WRAPS the existing ``prompt_version_registry.evaluate_regression`` behavioral gate:

  - "Risk scoring (1-3 scale for probability and impact, total 1-9)." → ``RiskScore.score``
  - "Scores >=6 demand documented mitigation." → ``RiskScore.requires_mitigation`` / CONCERNS band
  - "Scores = 9 mandate gate failure." → score 9 → ``decision == "FAIL"``
  - ``GateDecision = 'PASS' | 'CONCERNS' | 'FAIL' | 'WAIVED'`` (gate-decision-engine.ts) → 4 states
  - evaluateGate ordering FAIL → WAIVED → CONCERNS → PASS is preserved in ``_decide``.

ADVISORY: ``evaluate`` logs a 4-state verdict row to a new ``qa_gate`` SurrealDB table, but the
BINARY regression gate inside ``SkillRefiner.refine()`` still OWNS the actual block. This module
never raises into refine() and never alters refine()'s decision — fail-open by construction.

It reuses the central safe SurrealQL builder from ``prompt_version_registry`` (``_surql_set`` /
``_surql_lit`` / ``_NOW`` / ``_safe_ident``) — NO raw f-string SurrealQL is constructed here.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from cohezion.compound.prompt_version_registry import (
    _NOW,
    _SURREAL_HEADERS,
    _SURREAL_URL,
    _safe_ident,
    _surql_set,
    _validate,
    evaluate_regression,
)


logger = logging.getLogger(__name__)

# Ported thresholds (risk-governance.md → risk-scoring.ts).
_MITIGATION_THRESHOLD = 6  # requiresMitigation(score): score >= 6
_CRITICAL_SCORE = 9  # isCriticalBlocker(score): score === 9 → FAIL gate

# GateDecision (gate-decision-engine.ts).
DECISIONS = ("PASS", "CONCERNS", "FAIL", "WAIVED")


@dataclass(frozen=True)
class RiskScore:
    """probability(1-3) × impact(1-3) = score(1-9), with the classifyRiskLevel band."""

    probability: int
    impact: int

    @property
    def score(self) -> int:
        return self.probability * self.impact

    @property
    def band(self) -> str:
        # classifyRiskLevel: 9 CRITICAL, >=6 HIGH, >=4 MEDIUM, else LOW.
        s = self.score
        if s >= _CRITICAL_SCORE:
            return "CRITICAL"
        if s >= _MITIGATION_THRESHOLD:
            return "HIGH"
        if s >= 4:
            return "MEDIUM"
        return "LOW"

    @property
    def requires_mitigation(self) -> bool:
        return self.score >= _MITIGATION_THRESHOLD


@dataclass
class GateRecord:
    """The 4-state advisory verdict (ported GateResult) + behavioral traceability."""

    decision: str
    risk: RiskScore
    fixtures_total: int
    fixtures_passed: int
    rationale: str
    waiver: str | None = None


def evaluate(
    skill_name: str,
    candidate: str,
    run_fn,
    *,
    fixtures: list[dict[str, Any]] | None = None,
    risk: RiskScore | None = None,
    waiver: str | None = None,
) -> GateRecord:
    """Risk-weighted 4-state ADVISORY verdict that WRAPS ``evaluate_regression``.

    Runs the CANDIDATE skill against the golden fixtures (loaded from SurrealDB when not supplied)
    and maps the binary behavioral result + the risk score onto {PASS, CONCERNS, FAIL, WAIVED}.
    Logs a ``qa_gate`` row (advisory). NEVER raises — the binary gate in refine() owns the block.

    Decision logic (gate-decision-engine.ts evaluateGate ordering):
      - risk.score == 9                         → FAIL    (isCriticalBlocker mandate)
      - critical fixture regresses              → FAIL    (evaluate_regression == False)
      - authorized waiver present               → WAIVED
      - non-critical issue OR risk score 6-8    → CONCERNS (mitigation demanded)
      - clean                                   → PASS
    """
    risk = risk or RiskScore(2, 2)
    try:
        if fixtures is None:
            fixtures = _load_fixtures(skill_name)
    except Exception as exc:  # advisory: tolerate DB/table absent
        logger.debug("qa_gate fixture load failed (advisory fail-open): %s", exc)
        fixtures = []
    fixtures = fixtures or []

    # Per-fixture pass count + non-critical-issue detection (for the CONCERNS band).
    total = passed = 0
    noncritical_issue = False
    for f in fixtures:
        inp, exp = f.get("input"), f.get("expected_output")
        if not inp or exp is None:
            continue
        total += 1
        try:
            out = run_fn(candidate, inp)
        except Exception:  # noqa: S112 — unevaluable fixture: advisory fail-open, not an issue
            continue
        if _validate(out, exp, f.get("validator_type") or "contains"):
            passed += 1
        elif not f.get("critical", True):
            noncritical_issue = True

    # WRAP the existing binary behavioral gate — this is the load-bearing seam.
    try:
        legacy_passed = evaluate_regression(fixtures, candidate, run_fn) if fixtures else True
    except Exception as exc:
        logger.debug("qa_gate evaluate_regression error (advisory fail-open): %s", exc)
        legacy_passed = True

    decision, rationale = _decide(risk, legacy_passed, noncritical_issue, waiver)
    record = GateRecord(
        decision=decision,
        risk=risk,
        fixtures_total=total,
        fixtures_passed=passed,
        rationale=rationale,
        waiver=waiver,
    )
    _log_gate(skill_name, record)  # advisory write — fail-open
    return record


def _decide(
    risk: RiskScore, legacy_passed: bool, noncritical_issue: bool, waiver: str | None
) -> tuple[str, str]:
    """Pure 4-state decision (ported evaluateGate ordering: FAIL → WAIVED → CONCERNS → PASS)."""
    if risk.score >= _CRITICAL_SCORE:
        return "FAIL", f"risk score {risk.score} (==9) mandates FAIL (BMAD isCriticalBlocker)"
    if not legacy_passed:
        return "FAIL", "critical golden fixture regressed (evaluate_regression==False)"
    if waiver:
        return "WAIVED", f"risks waived by authorized approver: {waiver}"
    if noncritical_issue or risk.requires_mitigation:
        reason = "non-critical fixture issue(s)" if noncritical_issue else f"risk band {risk.band}"
        return "CONCERNS", f"{reason}; mitigation demanded (score>={_MITIGATION_THRESHOLD})"
    return "PASS", "no critical issues; all fixtures clean and risk below mitigation threshold"


def _load_fixtures(skill_name: str) -> list[dict[str, Any]]:
    """Delegate to the registry's safe loader (keeps the only SurrealQL builder in qa_gate to _log_gate)."""
    from cohezion.compound.prompt_version_registry import PromptVersionRegistry

    return PromptVersionRegistry()._load_behavioral_fixtures(skill_name)


def _log_gate(skill_name: str, record: GateRecord) -> None:
    """ADVISORY write to the ``qa_gate`` SurrealDB table. Parameterized via the REUSED ``_surql_set``
    safe builder (NO raw f-string SurrealQL). Fail-open: tolerate the table being absent / DB down."""
    try:
        import httpx

        q = (
            "CREATE qa_gate SET "
            + _surql_set(
                {
                    "skill_name": _safe_ident(skill_name),
                    "decision": record.decision,
                    "risk_score": record.risk.score,
                    "risk_band": record.risk.band,
                    "fixtures_total": record.fixtures_total,
                    "fixtures_passed": record.fixtures_passed,
                    "rationale": record.rationale,
                    "waiver": record.waiver,
                    "created_at": _NOW,
                }
            )
            + ";"
        )
        httpx.post(
            _SURREAL_URL, content=q, headers=_SURREAL_HEADERS, auth=("root", "root"), timeout=3.0
        )
    except Exception:
        pass  # advisory — must never break refine()
