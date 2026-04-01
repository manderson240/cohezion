"""
Failure Logger - Experiential Learning

Logs failure modes to vault for skill refinement.
Captures root causes and triggers recursive improvement.
"""

import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class FailureType(Enum):
    """Types of failure modes."""

    TIMEOUT_HANG = "timeout_hang"
    EXTRACTION_FAILURE = "extraction_failure"
    ROUTING_ERROR = "routing_error"
    DRIFT_DETECTED = "drift_detected"
    TIE_BREAKER_LOOP = "tie_breaker_loop"
    MODEL_ERROR = "model_error"
    VALIDATION_FAILURE = "validation_failure"
    MEMORY_OOM = "memory_oom"


@dataclass
class FailureRecord:
    """Record of a failure mode."""

    failure_id: str
    failure_type: str
    problem_id: str
    problem_text: str
    timestamp: str
    context: Dict[str, Any]
    root_cause: str
    remediation_pattern: str
    stack_trace: Optional[str] = None
    response_text: Optional[str] = None
    expected_answer: Optional[int] = None
    actual_answer: Optional[int] = None


class FailureLogger:
    """Logs failures to vault for skill refinement."""

    def __init__(self, vault_path: str = None, local_path: str = None):
        """
        Initialize failure logger.

        Args:
            vault_path: Path to vault (MCP storage)
            local_path: Local fallback path
        """
        self.vault_path = vault_path or os.path.expanduser(
            "~/vaults/cohezion-vault/regions/cerebrum/failures/aimo"
        )
        self.local_path = local_path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "failures"
        )

        # Ensure directories exist
        Path(self.vault_path).mkdir(parents=True, exist_ok=True)
        Path(self.local_path).mkdir(parents=True, exist_ok=True)

        self.failure_log: List[FailureRecord] = []

    def log_failure(
        self,
        failure_type: FailureType,
        problem_id: str,
        problem_text: str,
        context: Dict[str, Any],
        root_cause: str,
        remediation_pattern: str,
        response_text: str = None,
        expected_answer: int = None,
        actual_answer: int = None,
        stack_trace: str = None,
    ) -> FailureRecord:
        """
        Log a failure mode.

        Args:
            failure_type: Type of failure
            problem_id: Problem identifier
            problem_text: Full problem string
            context: Additional context (timing, model, specialist, etc.)
            root_cause: Root cause analysis
            remediation_pattern: Suggested fix
            response_text: Model response (if applicable)
            expected_answer: Expected answer (if known)
            actual_answer: Actual answer produced
            stack_trace: Stack trace (if exception)

        Returns:
            FailureRecord object
        """
        record = FailureRecord(
            failure_id=f"{failure_type.value}_{int(time.time() * 1000)}",
            failure_type=failure_type.value,
            problem_id=problem_id,
            problem_text=problem_text,
            timestamp=datetime.now().isoformat(),
            context=context,
            root_cause=root_cause,
            remediation_pattern=remediation_pattern,
            response_text=response_text,
            expected_answer=expected_answer,
            actual_answer=actual_answer,
            stack_trace=stack_trace,
        )

        self.failure_log.append(record)

        # Save to both vault and local
        self._save_to_vault(record)
        self._save_to_local(record)

        return record

    def _save_to_vault(self, record: FailureRecord):
        """Save failure to vault (MCP storage)."""
        try:
            # Group by failure type
            type_dir = os.path.join(self.vault_path, record.failure_type)
            Path(type_dir).mkdir(parents=True, exist_ok=True)

            # Save as markdown
            md_path = os.path.join(type_dir, f"{record.failure_id}.md")
            md_content = self._format_as_markdown(record)

            with open(md_path, "w") as f:
                f.write(md_content)

            # Also save JSON for programmatic access
            json_path = os.path.join(type_dir, f"{record.failure_id}.json")
            with open(json_path, "w") as f:
                json.dump(asdict(record), f, indent=2)

        except Exception as e:
            # Fallback to local only
            print(f"Vault save failed: {e}")

    def _save_to_local(self, record: FailureRecord):
        """Save failure to local path."""
        # Save JSON
        json_path = os.path.join(self.local_path, f"{record.failure_id}.json")
        with open(json_path, "w") as f:
            json.dump(asdict(record), f, indent=2)

        # Append to master log
        master_log = os.path.join(self.local_path, "failure_log.jsonl")
        with open(master_log, "a") as f:
            f.write(json.dumps(asdict(record)) + "\n")

    def _format_as_markdown(self, record: FailureRecord) -> str:
        """Format failure record as markdown."""
        md = f"""# Failure Mode: {record.failure_type}

## Metadata
- **ID:** {record.failure_id}
- **Problem:** {record.problem_id}
- **Timestamp:** {record.timestamp}
- **Type:** {record.failure_type}

## Problem
```
{record.problem_text[:500]}{"..." if len(record.problem_text) > 500 else ""}
```

## Context
```json
{json.dumps(record.context, indent=2)}
```

## Root Cause Analysis
{record.root_cause}

## Remediation Pattern
{record.remediation_pattern}

## Evidence
"""

        if record.response_text:
            md += f"""
### Model Response
```
{record.response_text[:1000]}{"..." if len(record.response_text) > 1000 else ""}
```
"""

        if record.expected_answer is not None and record.actual_answer is not None:
            md += f"""
### Answer Mismatch
- Expected: {record.expected_answer}
- Actual: {record.actual_answer}
"""

        if record.stack_trace:
            md += f"""
### Stack Trace
```
{record.stack_trace}
```
"""

        return md

    def get_all_failures(self, failure_type: FailureType = None) -> List[FailureRecord]:
        """Get all logged failures, optionally filtered by type."""
        if failure_type:
            return [f for f in self.failure_log if f.failure_type == failure_type.value]
        return self.failure_log

    def get_failure_summary(self) -> Dict[str, Any]:
        """Get summary of failures."""
        by_type = {}
        for failure in self.failure_log:
            by_type[failure.failure_type] = by_type.get(failure.failure_type, 0) + 1

        return {
            "total_failures": len(self.failure_log),
            "by_type": by_type,
            "most_common": max(by_type, key=by_type.get) if by_type else None,
            "recent_failures": self.failure_log[-5:] if self.failure_log else [],
        }

    def export_for_skill_refinement(self) -> str:
        """Export failures in format for skill refiner."""
        export_path = os.path.join(self.local_path, "skill_refinement_input.json")

        data = {
            "failures": [asdict(f) for f in self.failure_log],
            "summary": self.get_failure_summary(),
            "exported_at": datetime.now().isoformat(),
        }

        # Convert summary to serializable format
        data["summary"] = {
            "total_failures": data["summary"]["total_failures"],
            "by_type": data["summary"]["by_type"],
            "most_common": data["summary"]["most_common"],
            "recent_failures": [asdict(f) for f in data["summary"]["recent_failures"]],
        }

        with open(export_path, "w") as f:
            json.dump(data, f, indent=2)

        return export_path


class FailureDetector:
    """Detects failures during swarm execution."""

    def __init__(self, logger: FailureLogger):
        self.logger = logger

    def detect_timeout(self, response: str, timeout: int) -> bool:
        """Detect timeout failure."""
        return "timeout" in response.lower() or "timed out" in response.lower()

    def detect_extraction_failure(self, response: str, answer: int) -> bool:
        """Detect extraction failure."""
        return answer == 0 and "\\boxed" not in response

    def detect_routing_error(self, specialists: List[str], problem_text: str) -> bool:
        """Detect routing error (wrong specialist)."""
        # Heuristic: if problem clearly matches a domain but specialist doesn't
        keywords = {
            "Algebraist": ["solve", "equation", "polynomial", "quadratic"],
            "NumberTheorist": ["prime", "divisor", "modular", "gcd"],
            "Geometer": ["triangle", "circle", "area", "angle"],
            "Combinatorist": ["how many", "ways", "permutation", "probability"],
        }

        problem_lower = problem_text.lower()
        for domain, domain_keywords in keywords.items():
            if any(kw in problem_lower for kw in domain_keywords):
                if domain not in specialists:
                    return True
        return False

    def detect_drift(self, ans1: int, ans2: int) -> bool:
        """Detect drift between dual runs."""
        return ans1 != ans2

    def detect_tie_breaker_loop(self, ans1: int, ans2: int, ans3: int) -> bool:
        """Detect tie-breaker still divergent."""
        return not (ans1 == ans2 == ans3 or ans1 == ans3 or ans2 == ans3)

    def detect_model_error(self, response: str) -> bool:
        """Detect model error."""
        return response.startswith("Error")

    def detect_validation_failure(self, answer: int) -> bool:
        """Detect validation failure (out of range)."""
        return not (0 <= answer <= 99999)

    def log_if_failure(
        self,
        problem_id: str,
        problem_text: str,
        response: str,
        answer: int,
        specialists: List[str],
        ans1: int = None,
        ans2: int = None,
        ans3: int = None,
        timeout: int = 300,
        expected_answer: int = None,
    ):
        """Log any detected failures."""
        context = {
            "specialists": specialists,
            "timeout": timeout,
            "answer": answer,
            "response_length": len(response),
        }

        if self.detect_timeout(response, timeout):
            self.logger.log_failure(
                failure_type=FailureType.TIMEOUT_HANG,
                problem_id=problem_id,
                problem_text=problem_text,
                context=context,
                root_cause="Model did not respond within timeout window",
                remediation_pattern="Increase timeout or use faster model",
                response_text=response,
                expected_answer=expected_answer,
                actual_answer=answer,
            )

        if self.detect_extraction_failure(response, answer):
            self.logger.log_failure(
                failure_type=FailureType.EXTRACTION_FAILURE,
                problem_id=problem_id,
                problem_text=problem_text,
                context=context,
                root_cause="Regex extraction failed to find \\boxed{} or fallback number",
                remediation_pattern="Improve extraction patterns or validate response format",
                response_text=response,
                expected_answer=expected_answer,
                actual_answer=answer,
            )

        if self.detect_routing_error(specialists, problem_text):
            self.logger.log_failure(
                failure_type=FailureType.ROUTING_ERROR,
                problem_id=problem_id,
                problem_text=problem_text,
                context=context,
                root_cause="Wrong specialist assigned for problem domain",
                remediation_pattern="Improve domain detection keywords in SwarmCoordinator",
                response_text=response,
                expected_answer=expected_answer,
                actual_answer=answer,
            )

        if ans1 is not None and ans2 is not None and self.detect_drift(ans1, ans2):
            self.logger.log_failure(
                failure_type=FailureType.DRIFT_DETECTED,
                problem_id=problem_id,
                problem_text=problem_text,
                context={**context, "ans1": ans1, "ans2": ans2},
                root_cause="Dual-run answers diverged - instability in reasoning",
                remediation_pattern="Add adversarial review or use tie-breaker",
                response_text=response,
                expected_answer=expected_answer,
                actual_answer=answer,
            )

        if ans1 is not None and ans2 is not None and ans3 is not None:
            if self.detect_tie_breaker_loop(ans1, ans2, ans3):
                self.logger.log_failure(
                    failure_type=FailureType.TIE_BREAKER_LOOP,
                    problem_id=problem_id,
                    problem_text=problem_text,
                    context={**context, "ans1": ans1, "ans2": ans2, "ans3": ans3},
                    root_cause="Tie-breaker also diverged - fundamental ambiguity",
                    remediation_pattern="Add majority voting or escalate to human",
                    response_text=response,
                    expected_answer=expected_answer,
                    actual_answer=answer,
                )

        if self.detect_model_error(response):
            self.logger.log_failure(
                failure_type=FailureType.MODEL_ERROR,
                problem_id=problem_id,
                problem_text=problem_text,
                context=context,
                root_cause="Model returned error instead of reasoning",
                remediation_pattern="Check model availability, increase timeout, or handle error gracefully",
                response_text=response,
                expected_answer=expected_answer,
                actual_answer=answer,
            )

        if self.detect_validation_failure(answer):
            self.logger.log_failure(
                failure_type=FailureType.VALIDATION_FAILURE,
                problem_id=problem_id,
                problem_text=problem_text,
                context=context,
                root_cause="Answer out of valid range (0-99999)",
                remediation_pattern="Add range validation before returning",
                response_text=response,
                expected_answer=expected_answer,
                actual_answer=answer,
            )


def create_failure_logger() -> FailureLogger:
    """Create failure logger with default paths."""
    return FailureLogger()
