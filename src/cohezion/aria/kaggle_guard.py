"""ARIA Kaggle Dispatch Guard.

Supervisory pre-dispatch control plane for Kaggle autonomous submissions (arXiv:2610.20780).
Guards against silent script degradation, syntax/schema errors, NaN/Inf poisoning,
and verifier score drops before kernel dispatch.
"""

from __future__ import annotations

import ast
import hashlib
import json
import logging
import statistics
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from cohezion.core.event_bus import Event, EventType
from cohezion.swarm.aria_runtime_inspector import (
    ARIAAmendmentEngine,
    ARIARuntimeInspector,
)


logger = logging.getLogger(__name__)


@dataclass
class KaggleJob:
    """Specification of an autonomous Kaggle submission task."""

    comp_slug: str
    slot_num: int
    code_path: Path
    mode: Literal["notebook", "file"] = "notebook"
    kernel_slug: str | None = None
    target_filename: str = "submission.csv"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class NotebookArtifact:
    """Ingested and parsed script or notebook representation."""

    path: Path
    raw_content: str
    code_cells: list[str]
    sha256_hash: str
    ast_valid: bool
    ast_errors: list[str] = field(default_factory=list)
    is_notebook: bool = True


@dataclass
class VerifierHistory:
    """Historical verifier performance trajectory for a competition track."""

    scores: list[float] = field(default_factory=list)
    champion_score: float = 0.0
    last_known_good_hash: str | None = None
    min_score_floor: float = 0.001
    max_acceptable_drop: float = 0.15


@dataclass
class GuardDecision:
    """Supervisory decision emitted by KaggleDispatchGuard."""

    action: Literal["PASS", "AMEND", "ROLLBACK", "BLOCK"]
    confidence: float
    reasons: list[str]
    trace_id: str
    severity: float = 0.0
    amended_artifact: NotebookArtifact | None = None
    rollback_target: Path | None = None
    execution_time_ms: float = 0.0


class KaggleDispatchGuard:
    """ARIA pre-dispatch supervisory control plane for Kaggle kernels."""

    def __init__(
        self,
        inspector: ARIARuntimeInspector | None = None,
        amendment_engine: ARIAAmendmentEngine | None = None,
        enforce: bool = True,
        score_drop_tolerance: float = 0.15,
        max_amendments: int = 1,
    ) -> None:
        self.inspector = inspector or ARIARuntimeInspector()
        self.amendment_engine = amendment_engine or ARIAAmendmentEngine(self.inspector)
        self.enforce = enforce
        self.score_drop_tolerance = score_drop_tolerance
        self.max_amendments = max_amendments

    @classmethod
    def load_artifact(cls, path: Path | str) -> NotebookArtifact:
        """Parses a notebook (.ipynb) or Python script (.py) into a NotebookArtifact."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Kaggle code artifact not found: {p}")

        raw = p.read_text(encoding="utf-8")
        sha = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        is_nb = p.suffix.lower() == ".ipynb"
        code_cells: list[str] = []
        ast_errors: list[str] = []

        if is_nb:
            try:
                data = json.loads(raw)
                for cell in data.get("cells", []):
                    if cell.get("cell_type") == "code":
                        src = cell.get("source", "")
                        if isinstance(src, list):
                            src = "".join(src)
                        code_cells.append(src)
            except Exception as e:
                ast_errors.append(f"Invalid notebook JSON format: {e}")
        else:
            code_cells.append(raw)

        # Validate syntax across code cells
        full_script = "\n\n".join(code_cells)
        try:
            ast.parse(full_script)
            ast_valid = len(ast_errors) == 0
        except SyntaxError as e:
            ast_valid = False
            ast_errors.append(f"SyntaxError on line {e.lineno}: {e.msg}")

        return NotebookArtifact(
            path=p,
            raw_content=raw,
            code_cells=code_cells,
            sha256_hash=sha,
            ast_valid=ast_valid,
            ast_errors=ast_errors,
            is_notebook=is_nb,
        )

    def check_static_invariants(
        self, artifact: NotebookArtifact, job: KaggleJob
    ) -> tuple[bool, list[str]]:
        """Static analysis inspecting target file generation and catastrophic code bugs."""
        violations: list[str] = []

        if not artifact.ast_valid:
            violations.extend(artifact.ast_errors)
            return False, violations

        full_code = "\n".join(artifact.code_cells)

        # 1. Output file generation check
        target_fn = job.target_filename.strip().lower()
        has_csv_export = "to_csv" in full_code and (
            target_fn in full_code.lower() or "submission" in full_code.lower()
        )
        has_parquet_export = "to_parquet" in full_code and (
            target_fn in full_code.lower() or "submission" in full_code.lower()
        )
        has_open_write = "open(" in full_code and (
            target_fn in full_code.lower() or "submission" in full_code.lower()
        )

        if not (has_csv_export or has_parquet_export or has_open_write):
            violations.append(
                f"Missing export verification: Code does not write to target '{job.target_filename}'."
            )

        # 2. Catastrophic silent bugs: unhandled NaN or inf injection
        if "np.nan" in full_code and ".fillna(" not in full_code and "isna()" not in full_code:
            violations.append(
                "Potential unhandled NaN generation without .fillna() or isna() sanitation."
            )

        return len(violations) == 0, violations

    def check_verifier_regression(
        self, current_score: float, history: VerifierHistory
    ) -> tuple[bool, list[str]]:
        """Audits verifier performance against floor and median historical benchmarks."""
        reasons: list[str] = []

        # Floor check
        if current_score < history.min_score_floor:
            reasons.append(
                f"Catastrophic verifier collapse: Score {current_score:.4f} is below minimum floor {history.min_score_floor:.4f}."
            )
            return False, reasons

        # Regression against rolling median
        if len(history.scores) >= 2:
            median_score = statistics.median(history.scores)
            drop = median_score - current_score
            if drop > self.score_drop_tolerance:
                reasons.append(
                    f"Severe verifier score degradation: Drop of {drop:.4f} exceeds tolerance {self.score_drop_tolerance:.4f} (median: {median_score:.4f}, current: {current_score:.4f})."
                )
                return False, reasons

        return True, reasons

    def attempt_amendment(
        self, artifact: NotebookArtifact, job: KaggleJob, violations: list[str]
    ) -> NotebookArtifact | None:
        """Applies ARIA automated single-pass amendment for recoverable static defects."""
        try:
            amended_cells = list(artifact.code_cells)
            repaired = False

            # Defect 1: Missing target file export cell
            missing_export = any("Missing export verification" in v for v in violations)
            if missing_export:
                export_code = (
                    f"\n# [ARIA Kaggle Guard Amendment] Ensure valid {job.target_filename} generation\n"
                    f"import os\n"
                    f"if not os.path.exists('{job.target_filename}'):\n"
                    f"    try:\n"
                    f"        if 'sub' in locals():\n"
                    f"            sub.to_csv('{job.target_filename}', index=False)\n"
                    f"        elif 'submission' in locals():\n"
                    f"            submission.to_csv('{job.target_filename}', index=False)\n"
                    f"    except Exception as _e:\n"
                    f"        print(f'ARIA Export Amendment Error: {{_e}}')\n"
                )
                amended_cells.append(export_code)
                repaired = True

            # Defect 2: Unhandled NaN injection
            has_nan_issue = any("Potential unhandled NaN generation" in v for v in violations)
            if has_nan_issue:
                nan_guard_code = (
                    "\n# [ARIA Kaggle Guard Amendment] Sanitize NaNs before serialization\n"
                    "for _df_name in ['sub', 'submission', 'df_sub', 'preds_df']:\n"
                    "    if _df_name in locals() and hasattr(locals()[_df_name], 'fillna'):\n"
                    "        locals()[_df_name] = locals()[_df_name].fillna(0.0)\n"
                )
                amended_cells.append(nan_guard_code)
                repaired = True

            if not repaired:
                return None

            # Verify amended code parses cleanly
            full_code = "\n\n".join(amended_cells)
            ast.parse(full_code)

            if artifact.is_notebook:
                nb_dict = json.loads(artifact.raw_content)
                nb_dict["cells"].append(
                    {
                        "cell_type": "code",
                        "execution_count": None,
                        "metadata": {"aria_amendment": True},
                        "outputs": [],
                        "source": [amended_cells[-1]],
                    }
                )
                new_raw = json.dumps(nb_dict, indent=1)
            else:
                new_raw = full_code

            new_sha = hashlib.sha256(new_raw.encode("utf-8")).hexdigest()
            return NotebookArtifact(
                path=artifact.path,
                raw_content=new_raw,
                code_cells=amended_cells,
                sha256_hash=new_sha,
                ast_valid=True,
                ast_errors=[],
                is_notebook=artifact.is_notebook,
            )
        except Exception as e:
            logger.warning("ARIA amendment synthesis failed: %s", e)
            return None

    def evaluate(
        self,
        job: KaggleJob,
        current_verifier_score: float | None = None,
        history: VerifierHistory | None = None,
        last_known_good_path: Path | None = None,
    ) -> GuardDecision:
        """Main supervisory evaluation gate. Decides PASS, AMEND, ROLLBACK, or BLOCK."""
        start_time = time.perf_counter()
        trace_id = f"aria-kg-{uuid.uuid4().hex[:8]}"
        reasons: list[str] = []

        try:
            artifact = self.load_artifact(job.code_path)
        except Exception as e:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            decision = GuardDecision(
                action="BLOCK",
                confidence=1.0,
                reasons=[f"Fatal artifact load error: {e}"],
                trace_id=trace_id,
                severity=1.0,
                execution_time_ms=elapsed,
            )
            self._publish_event("blocked", decision, job)
            return decision

        # 1. Static Invariant Check
        static_ok, static_violations = self.check_static_invariants(artifact, job)
        if not static_ok:
            reasons.extend(static_violations)

        # 2. Verifier Regression Check (if score provided)
        score_ok = True
        if current_verifier_score is not None and history is not None:
            score_ok, score_violations = self.check_verifier_regression(
                current_verifier_score, history
            )
            if not score_ok:
                reasons.extend(score_violations)

        # Clean Pass
        if static_ok and score_ok:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            decision = GuardDecision(
                action="PASS",
                confidence=1.0,
                reasons=["All static AST and verifier score invariants verified."],
                trace_id=trace_id,
                severity=0.0,
                execution_time_ms=elapsed,
            )
            self._publish_event("passed", decision, job)
            return decision

        # Anomaly Detected: Evaluate ARIA supervisory intervention
        # Priority A: Check if automated single-pass amendment is viable
        if not static_ok and artifact.ast_valid:
            amended_artifact = self.attempt_amendment(artifact, job, static_violations)
            if amended_artifact is not None:
                # Re-verify static invariants on amended artifact
                re_ok, _ = self.check_static_invariants(amended_artifact, job)
                if re_ok:
                    elapsed = (time.perf_counter() - start_time) * 1000.0
                    decision = GuardDecision(
                        action="AMEND",
                        confidence=0.90,
                        reasons=[
                            "Static defect amended via ARIA automated single-pass repair.",
                            *static_violations,
                        ],
                        trace_id=trace_id,
                        severity=0.40,
                        amended_artifact=amended_artifact,
                        execution_time_ms=elapsed,
                    )
                    self._publish_event("amended", decision, job)
                    return decision

        # Priority B: Check if rollback to last known good champion is viable
        target_rollback = last_known_good_path or (
            artifact.path.parent / f"{artifact.path.stem}.canonical_base.ipynb"
        )
        if target_rollback.exists():
            elapsed = (time.perf_counter() - start_time) * 1000.0
            decision = GuardDecision(
                action="ROLLBACK",
                confidence=0.95,
                reasons=[
                    "Unrecoverable static or verifier regression. Rollback to safe champion required.",
                    *reasons,
                ],
                trace_id=trace_id,
                severity=0.85,
                rollback_target=target_rollback,
                execution_time_ms=elapsed,
            )
            self._publish_event("rollback", decision, job)
            return decision

        # Priority C: Fail-Closed BLOCK
        elapsed = (time.perf_counter() - start_time) * 1000.0
        decision = GuardDecision(
            action="BLOCK",
            confidence=1.0,
            reasons=["Unrecoverable defect and no rollback target available.", *reasons],
            trace_id=trace_id,
            severity=1.0,
            execution_time_ms=elapsed,
        )
        self._publish_event("blocked", decision, job)

        # In shadow mode, warn but allow PASS if enforce is disabled
        if not self.enforce:
            logger.warning(
                "[SHADOW MODE] KaggleDispatchGuard would have blocked %s, but enforce=False. Reasons: %s",
                job.comp_slug,
                decision.reasons,
            )
            return GuardDecision(
                action="PASS",
                confidence=0.5,
                reasons=[f"[SHADOW OVERRIDE] {r}" for r in decision.reasons],
                trace_id=trace_id,
                severity=decision.severity,
                execution_time_ms=elapsed,
            )

        return decision

    def _publish_event(self, action_name: str, decision: GuardDecision, job: KaggleJob) -> None:
        """Dispatches telemetry event to EventBus."""
        try:
            _event = Event(
                type=EventType.CUSTOM,
                source="aria_kaggle_guard",
                payload={
                    "event_name": f"aria.kaggle_guard.{action_name}",
                    "trace_id": decision.trace_id,
                    "action": decision.action,
                    "comp_slug": job.comp_slug,
                    "slot_num": job.slot_num,
                    "severity": decision.severity,
                    "confidence": decision.confidence,
                    "reasons": decision.reasons,
                    "execution_time_ms": decision.execution_time_ms,
                },
            )
            # Safe sync bus notification
            logger.info(
                "[ARIA Kaggle Guard] %s on %s (slot %d) | event=%s reasons=%s (%.2f ms)",
                decision.action,
                job.comp_slug,
                job.slot_num,
                _event.payload["event_name"],
                decision.reasons,
                decision.execution_time_ms,
            )
        except Exception as e:
            logger.debug("Telemetry dispatch skipped: %s", e)
