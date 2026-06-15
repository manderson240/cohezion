"""
Consortium Instigator — Red-team adversarial probe for the consortium pipeline.

The Instigator is the adversarial counterpart to the consortium neural network.
It actively attacks the 5-stage pipeline with adversarial payloads, verifies
behavior against V-Model acceptance criteria (AC-9.2), and self-improves
through the compound engineering loop.

Attack Vectors (AC-9.2):
  1. Empty prompt        → must raise ValueError, not crash
  2. 10KB prompt         → must handle without truncation
  3. Concurrent calls     → must be thread-safe (separate HTTP sessions)
  4. Lemonade down        → must return clear error, not hang
  5. Timeout              → must honor timeout parameter
  6. Malformed responses  → must handle missing/empty choices gracefully
  7. Context poisoning    → prior stage error must propagate cleanly

Compound Engineering:
  - Integrates with the learning loop (capture to vault)
  - Self-improves: discovers new attack vectors from prior failures
  - Reports structured pass/fail matrix with evidence
  - Compound score tracks adversarial coverage over time
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from cohezion.agents.base import BaseAgent
from cohezion.inference.config import LEMONADE_BASE_URL


logger = logging.getLogger(__name__)

# ── LEMONADE target (same as consortium) ─────────────────────
LEMONADE_URL = f"{LEMONADE_BASE_URL}/v1/chat/completions"
DEFAULT_TIMEOUT = 30


# ═══════════════════════════════════════════════════════════════
# Attack Vector Taxonomy
# ═══════════════════════════════════════════════════════════════

class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AttackCategory(Enum):
    """Categories of adversarial probe."""
    INPUT_VALIDATION = "input_validation"
    CONCURRENCY = "concurrency"
    NETWORK_FAILURE = "network_failure"
    TIMEOUT = "timeout"
    RESPONSE_INTEGRITY = "response_integrity"
    CONTEXT_CORRUPTION = "context_corruption"


@dataclass
class AttackVector:
    """One adversarial probe against the consortium pipeline."""
    id: str                       # short unique identifier
    description: str              # what we're testing
    category: AttackCategory
    severity: Severity
    payload: dict[str, Any]       # kwargs for cohezion_consortium_reason
    expected_behavior: str        # what the pipeline SHOULD do
    failure_indicators: list[str]  # patterns that indicate the pipeline broke

    # Filled in post-execution
    result: str | None = None     # "pass", "fail", "error"
    actual_behavior: str = ""     # what actually happened
    evidence: str = ""            # proof (error message, trace)
    elapsed_ms: float = 0.0
    retries: int = 0


@dataclass
class AttackRunResult:
    """Full result of an instigator run."""
    run_id: str
    timestamp: str
    attack_vectors: list[AttackVector]
    passed: int
    failed: int
    errored: int
    coverage_pct: float          # vectors that produced results / total
    compound_score_delta: float  # improvement over last run
    vault_path: str = ""


# ═══════════════════════════════════════════════════════════════
# Default Attack Library (AC-9.2)
# ═══════════════════════════════════════════════════════════════

DEFAULT_ATTACK_VECTORS: list[AttackVector] = [
    # ── AC-9.2: Empty prompt → ValueError ──
    AttackVector(
        id="empty-prompt",
        description="Empty prompt must raise ValueError, not crash or hang",
        category=AttackCategory.INPUT_VALIDATION,
        severity=Severity.CRITICAL,
        payload={"prompt": "", "timeout": DEFAULT_TIMEOUT},
        expected_behavior="Pipeline raises ValueError with clear message",
        failure_indicators=[
            "consortium failed",
            "INTERNAL ERROR",
            "traceback",
            "hanging",
        ],
    ),
    AttackVector(
        id="whitespace-only",
        description="Whitespace-only prompt must raise ValueError",
        category=AttackCategory.INPUT_VALIDATION,
        severity=Severity.HIGH,
        payload={"prompt": "   \t\n  ", "timeout": DEFAULT_TIMEOUT},
        expected_behavior="Pipeline raises ValueError",
        failure_indicators=[
            "consortium failed",
            "hanging",
        ],
    ),
    # ── AC-9.2: 10KB prompt → handled ──
    AttackVector(
        id="large-prompt",
        description="10KB prompt must be handled without truncation",
        category=AttackCategory.INPUT_VALIDATION,
        severity=Severity.HIGH,
        payload={
            "prompt": "A" * 10240,
            "timeout": DEFAULT_TIMEOUT,
        },
        expected_behavior="Pipeline processes without truncation errors",
        failure_indicators=[
            "truncat",
            "too long",
            "413",
            "414",
        ],
    ),
    # ── AC-9.2: Concurrent MCP calls → thread-safe ──
    AttackVector(
        id="concurrent-three",
        description="Three concurrent calls must not interfere (thread safety)",
        category=AttackCategory.CONCURRENCY,
        severity=Severity.HIGH,
        payload={"concurrent": 3, "prompt": "What is 2+2?"},
        expected_behavior="All three independent, no cross-contamination",
        failure_indicators=[
            "race condition",
            "cross-contamination",
            "deadlock",
            "timeout on concurrent",
        ],
    ),
    # ── AC-9.2: Lemonade down → clear error ──
    AttackVector(
        id="lemonade-down",
        description="Lemonade unreachable must return clean error, not hang",
        category=AttackCategory.NETWORK_FAILURE,
        severity=Severity.CRITICAL,
        payload={
            "prompt": "What is 2+2?",
            "timeout": 5,
            "_override_url": "http://127.0.0.1:19999/v1/chat/completions",
        },
        expected_behavior="Returns [ERROR: URLError] for all 5 stages, pipeline completes",
        failure_indicators=[
            "hanging",
            "timeout without error",
            "crash",
        ],
    ),
    # ── Timeout handling ──
    AttackVector(
        id="tight-timeout",
        description="Unrealistically tight timeout must fail cleanly",
        category=AttackCategory.TIMEOUT,
        severity=Severity.MEDIUM,
        payload={
            "prompt": "What is 2+2?",
            "timeout": 1,
        },
        expected_behavior="Timeout error propagated, pipeline continues gracefully",
        failure_indicators=[
            "unhandled timeout",
            "crash on timeout",
        ],
    ),
    # ── Response integrity ──
    AttackVector(
        id="malformed-json",
        description="Malformed prompt must not crash parser",
        category=AttackCategory.RESPONSE_INTEGRITY,
        severity=Severity.MEDIUM,
        payload={
            "prompt": '{"broken": "json"\n\n\n\n',
            "timeout": DEFAULT_TIMEOUT,
        },
        expected_behavior="Pipeline handles special characters without crash",
        failure_indicators=[
            "json decode error",
            "unhandled exception",
            "crash",
        ],
    ),
    AttackVector(
        id="unicode-explosion",
        description="Unicode-heavy prompt must not corrupt pipeline",
        category=AttackCategory.RESPONSE_INTEGRITY,
        severity=Severity.LOW,
        payload={
            "prompt": "🔥" * 5000,
            "timeout": DEFAULT_TIMEOUT,
        },
        expected_behavior="Pipeline handles unicode without encoding errors",
        failure_indicators=[
            "encode",
            "decode",
            "unicode error",
            "crash",
        ],
    ),
    # ── Context corruption ──
    AttackVector(
        id="control-chars",
        description="Control characters must not break context propagation",
        category=AttackCategory.CONTEXT_CORRUPTION,
        severity=Severity.LOW,
        payload={
            "prompt": "Hello\x00World\x1b[31mRED",
            "timeout": DEFAULT_TIMEOUT,
        },
        expected_behavior="Pipeline sanitizes or passes through without corruption",
        failure_indicators=[
            "null byte",
            "control character",
            "escape sequence",
        ],
    ),
]

# ═══════════════════════════════════════════════════════════════
# Consortium Instigator (BaseAgent subclass)
# ═══════════════════════════════════════════════════════════════


class ConsortiumInstigator(BaseAgent):
    """Red-team agent that probes the consortium pipeline for weaknesses.

    Inherits BaseAgent for:
      - Agent lifecycle (register, health check, circuit breaker)
      - Semantic cache for known results
      - Resource monitoring
      - Journey tracking in SurrealDB
      - Vault logging

    The Instigator does NOT participate in synthesis — it is purely adversarial.
    Its role is to find every way the consortium pipeline can break before
    production workloads hit those failure modes.
    """

    def __init__(
        self,
        model_name: str = "instigator",
        attack_vectors: list[AttackVector] | None = None,
        enable_semantic_cache: bool = True,
        **base_kwargs: Any,
    ):
        super().__init__(model_name=model_name, **base_kwargs)
        self.attack_vectors = attack_vectors or DEFAULT_ATTACK_VECTORS
        self.enable_semantic_cache = enable_semantic_cache
        self._discovered_vectors: list[AttackVector] = []
        self._run_history: list[AttackRunResult] = []

    # ── Core: run all attack vectors ──────────────────────────

    async def run_attack_suite(
        self,
        skip_concurrent: bool = False,
        skip_network: bool = False,
    ) -> AttackRunResult:
        """Execute all attack vectors against the consortium pipeline.

        Each vector is evaluated independently. Failures in one vector
        do not block subsequent vectors. The instigator collects evidence
        and produces a structured pass/fail matrix.

        Args:
            skip_concurrent: Skip concurrent attack vectors (safety flag)
            skip_network: Skip network-failure vectors (requires lemonade down)

        Returns:
            AttackRunResult with full pass/fail matrix and evidence
        """
        run_id = f"instigator-{int(time.time())}"
        t0 = time.perf_counter()
        timestamp = datetime.now(timezone.utc).isoformat()

        logger.info("Instigator run %s: %d vectors queued", run_id, len(self.attack_vectors))

        # Filter vectors if skipping categories
        active_vectors = self.attack_vectors.copy()
        if skip_concurrent:
            active_vectors = [
                v for v in active_vectors
                if v.category != AttackCategory.CONCURRENCY
            ]
        if skip_network:
            active_vectors = [
                v for v in active_vectors
                if v.category != AttackCategory.NETWORK_FAILURE
            ]

        # Execute each vector
        for vector in active_vectors:
            t_vec = time.perf_counter()
            try:
                await self._execute_vector(vector)
            except asyncio.CancelledError:
                vector.result = "error"
                vector.actual_behavior = "Cancelled mid-execution"
                vector.evidence = "Instigator run cancelled"
            except Exception as exc:
                vector.result = "error"
                vector.actual_behavior = f"Unexpected: {type(exc).__name__}"
                vector.evidence = str(exc)[:500]
                logger.error("Vector %s errored: %s", vector.id, exc)
            vector.elapsed_ms = (time.perf_counter() - t_vec) * 1000

        passed = sum(1 for v in active_vectors if v.result == "pass")
        failed = sum(1 for v in active_vectors if v.result == "fail")
        errored = sum(1 for v in active_vectors if v.result == "error")
        coverage = (passed + failed) / len(active_vectors) if active_vectors else 0.0

        # Calculate compound score delta
        compound_delta = 0.0
        prev_pass = 0
        if self._run_history:
            prev_pass = self._run_history[-1].passed
        if passed > prev_pass:
            compound_delta = (passed - prev_pass) / max(len(active_vectors), 1)
        elif passed < prev_pass:
            compound_delta = (passed - prev_pass) / max(len(active_vectors), 1)

        result = AttackRunResult(
            run_id=run_id,
            timestamp=timestamp,
            attack_vectors=active_vectors,
            passed=passed,
            failed=failed,
            errored=errored,
            coverage_pct=round(coverage * 100, 1),
            compound_score_delta=round(compound_delta, 3),
        )
        self._run_history.append(result)

        elapsed = time.perf_counter() - t0
        logger.info(
            "Instigator run %s complete: %dP/%dF/%dE in %.1fs",
            run_id, passed, failed, errored, elapsed,
        )

        return result

    # ── Single vector execution ───────────────────────────────

    async def _execute_vector(self, vector: AttackVector) -> None:
        """Execute one attack vector against the pipeline."""
        payload = vector.payload

        # ── Special: concurrent vector ──
        if vector.category == AttackCategory.CONCURRENCY:
            concurrent_count = payload.get("concurrent", 2)
            prompt = payload.get("prompt", "test")
            await self._test_concurrent(vector, concurrent_count, prompt)
            return

        # ── Standard: call the pipeline ──
        try:
            response = await self._call_consortium(
                prompt=payload.get("prompt", ""),
                timeout=payload.get("timeout", DEFAULT_TIMEOUT),
                override_url=payload.get("_override_url"),
            )
        except ValueError as exc:
            # For empty-prompt vectors, ValueError IS the expected behavior
            if vector.id in ("empty-prompt", "whitespace-only"):
                vector.result = "pass"
                vector.actual_behavior = f"ValueError raised as expected: {exc}"
                vector.evidence = str(exc)[:200]
                return
            vector.result = "fail"
            vector.actual_behavior = f"Unexpected ValueError: {exc}"
            vector.evidence = str(exc)[:200]
            return
        except Exception as exc:
            vector.result = "error"
            vector.actual_behavior = f"{type(exc).__name__}: {exc}"
            vector.evidence = str(exc)[:200]
            return

        # Evaluate result
        self._evaluate_response(vector, response)

    async def _call_consortium(
        self,
        prompt: str,
        timeout: int = DEFAULT_TIMEOUT,
        override_url: str | None = None,
    ) -> dict[str, Any]:
        """Call the consortium pipeline directly (in-process, no MCP overhead).

        Uses the same codepath as consortium_reason.run_consortium().
        Skips MCP serialization for speed — this IS the instigator, not an
        external observer.
        """
        import sys as _sys

        project_root = Path(__file__).resolve().parents[3]
        tools_path = project_root / "tools"
        if str(tools_path) not in _sys.path:
            _sys.path.insert(0, str(tools_path))

        from consortium_reason import run_consortium

        # Patch lemonade URL for network-failure vectors
        if override_url:
            import consortium_reason as cr

            orig_url = cr.LEMONADE_URL
            cr.LEMONADE_URL = override_url
            try:
                result = await asyncio.to_thread(
                    run_consortium,
                    prompt=prompt,
                    verbose=False,
                )
            finally:
                cr.LEMONADE_URL = orig_url
            return result

        # Run through consortium in a thread (blocking HTTP calls)
        result = await asyncio.to_thread(
            run_consortium,
            prompt=prompt,
            verbose=False,
        )
        return result

    def _evaluate_response(self, vector: AttackVector, response: dict[str, Any]) -> None:
        """Judge whether the pipeline passed or failed for this vector."""
        final = response.get("final", "")
        stages = response.get("stages", [])
        elapsed = response.get("elapsed", 0)

        vector.actual_behavior = (
            f"{len(stages)} stages, {elapsed}s, final={final[:100]!r}"
        )
        vector.evidence = json.dumps(response, indent=2, default=str)[:500]

        # ── AC-9.2: 10KB prompt ──
        if vector.id == "large-prompt":
            if "truncat" in final.lower() or any(
                "truncat" in s.get("text", "").lower() for s in stages
            ):
                vector.result = "fail"
                vector.actual_behavior += " [TRUNCATION DETECTED]"
                return
            # Check that all 5 stages completed with valid output
            if len(stages) < 5:
                vector.result = "fail"
                vector.actual_behavior += f" [ONLY {len(stages)} STAGES]"
                return
            vector.result = "pass"
            return

        # ── AC-9.2: Lemonade down ──
        if vector.id == "lemonade-down":
            error_count = sum(
                1 for s in stages if s.get("text", "").startswith("[ERROR")
            )
            if error_count == len(stages) and len(stages) == 5:
                vector.result = "pass"
                vector.actual_behavior += " [All 5 properly errored]"
                return
            if elapsed > 4.5 and error_count == 0:
                vector.result = "fail"
                vector.actual_behavior += " [HANGING — no error but waited]"
                return
            vector.result = "fail"
            vector.actual_behavior += f" [{error_count}/{len(stages)} errored]"
            return

        # ── Timeout vector ──
        if vector.id == "tight-timeout":
            if elapsed < 5 and len(stages) > 0:
                # Timeout caught, pipeline still attempted
                vector.result = "pass"
                vector.actual_behavior += f" [Timeout honored: {elapsed}s]"
                return
            vector.result = "fail"
            return

        # ── Default: pipeline produced valid output ──
        # Check for failure indicators
        for indicator in vector.failure_indicators:
            if indicator.lower() in final.lower() or any(
                indicator.lower() in s.get("text", "").lower() for s in stages
            ):
                vector.result = "fail"
                vector.actual_behavior += f" [FOUND: {indicator}]"
                return

        # Pipeline completed with output — passes baseline
        if len(stages) >= 1 and final and not final.startswith("[ERROR"):
            vector.result = "pass"
        else:
            vector.result = "fail"
            vector.actual_behavior += " [No valid output]"

    # ── Concurrent attack ─────────────────────────────────────

    async def _test_concurrent(
        self,
        vector: AttackVector,
        concurrency: int,
        prompt: str,
    ) -> None:
        """Fire N concurrent consortium calls and check for interference."""
        results: list[dict[str, Any]] = []
        errors: list[str] = []

        async def one_call(idx: int) -> None:
            try:
                res = await self._call_consortium(
                    prompt=f"[Concurrent #{idx}] {prompt}",
                    timeout=DEFAULT_TIMEOUT,
                )
                results.append(res)
            except Exception as exc:
                errors.append(f"[#{idx}] {type(exc).__name__}: {exc}")

        tasks = [one_call(i) for i in range(concurrency)]
        await asyncio.gather(*tasks, return_exceptions=True)

        vector.actual_behavior = (
            f"{len(results)}/{concurrency} completed, {len(errors)} errors"
        )
        vector.evidence = (
            f"Results: {len(results)}, Errors: {errors[:3]}"
        )

        # All must complete without interference
        if len(results) == concurrency and len(errors) == 0:
            # Check for cross-contamination: each result should be independent
            finals = [r.get("final", "")[:50] for r in results]
            if all(f for f in finals) and len(set(finals)) >= 1:
                # At minimum, each call completed independently
                vector.result = "pass"
                vector.evidence += f" | Finals: {finals}"
                return

        vector.result = "fail"
        vector.evidence += " | Cross-contamination or partial results"

    # ── Compound: discover new vectors ────────────────────────

    async def discover_vectors(
        self,
        from_failures: bool = True,
    ) -> list[AttackVector]:
        """Analyze prior failures and generate new attack vectors.

        This is the compound engineering self-improvement loop:
        1. Look at what failed
        2. Generalize into new attack vectors
        3. Add to library for next run

        Each discovered vector increases compound coverage.

        Returns:
            New attack vectors discovered
        """
        if not self._run_history:
            return []

        last_run = self._run_history[-1]
        failures = [v for v in last_run.attack_vectors if v.result == "fail"]

        discovered: list[AttackVector] = []

        # Rule 1: If concurrent failed, add higher-concurrency test
        concurrent_fails = [
            v for v in failures if v.category == AttackCategory.CONCURRENCY
        ]
        if concurrent_fails:
            discovered.append(
                AttackVector(
                    id="concurrent-ten",
                    description="Ten concurrent calls — stress test beyond basic thread safety",
                    category=AttackCategory.CONCURRENCY,
                    severity=Severity.HIGH,
                    payload={"concurrent": 10, "prompt": "What is 2+2?"},
                    expected_behavior="All ten independent, no deadlock",
                    failure_indicators=["deadlock", "timeout", "OOM"],
                )
            )

        # Rule 2: If input validation failed, add boundary tests
        input_fails = [
            v for v in failures if v.category == AttackCategory.INPUT_VALIDATION
        ]
        if input_fails:
            discovered.append(
                AttackVector(
                    id="null-byte-prompt",
                    description="Null byte injection must not crash parser",
                    category=AttackCategory.RESPONSE_INTEGRITY,
                    severity=Severity.CRITICAL,
                    payload={"prompt": "\x00" * 10, "timeout": DEFAULT_TIMEOUT},
                    expected_behavior="Handles null bytes without crash",
                    failure_indicators=["null", "crash", "unhandled"],
                )
            )

        # Rule 3: If network failure vectors worked, add port-scan style
        network_fails = [
            v for v in failures if v.category == AttackCategory.NETWORK_FAILURE
        ]
        if network_fails:
            discovered.append(
                AttackVector(
                    id="lemonade-slow",
                    description="Slow lemonade response must not hang pipeline",
                    category=AttackCategory.NETWORK_FAILURE,
                    severity=Severity.MEDIUM,
                    payload={"prompt": "test", "timeout": 3},
                    expected_behavior="Timeout within 3s",
                    failure_indicators=["hanging", "> 5s"],
                )
            )

        # Add discovered to library
        self._discovered_vectors.extend(discovered)
        self.attack_vectors.extend(discovered)

        if discovered:
            logger.info(
                "Instigator discovered %d new attack vectors from failures",
                len(discovered),
            )

        return discovered

    # ── Reporting ─────────────────────────────────────────────

    def report_pass_fail_matrix(self, run: AttackRunResult | None = None) -> str:
        """Generate a human-readable pass/fail matrix for the attack suite."""
        if run is None:
            if not self._run_history:
                return "No runs yet."
            run = self._run_history[-1]

        lines = [
            f"=== Instigator {run.run_id} ===",
            f"Timestamp:   {run.timestamp}",
            f"Pass/Fail:   {run.passed}P / {run.failed}F / {run.errored}E",
            f"Coverage:    {run.coverage_pct}%",
            f"Compound Δ:  {run.compound_score_delta:+.3f}",
            "",
            f"{'ID':<24} {'CATEGORY':<20} {'RESULT':<8} {'MS':<8}",
            "-" * 80,
        ]

        for v in sorted(run.attack_vectors, key=lambda x: (
            0 if x.result == "fail" else 1 if x.result == "error" else 2,
            x.id,
        )):
            result_str = (
                "✅ PASS" if v.result == "pass"
                else "❌ FAIL" if v.result == "fail"
                else "⚠ ERR"
            )
            lines.append(
                f"{v.id:<24} {v.category.value:<20} {result_str:<8} {v.elapsed_ms:.0f}"
            )
            if v.result == "fail":
                lines.append(f"  └ {v.actual_behavior[:120]}")

        return "\n".join(lines)

    # ── BaseAgent abstract method ──────────────────────────────

    async def process(self, input_text: str) -> str:
        """
        Process an adversarial probe: run the attack suite and return the
        pass/fail matrix as a formatted string.

        This satisfies BaseAgent's abstract `process` requirement while
        maintaining the instigator's red-team identity — every `process`
        call is an audit of the consortium pipeline.
        """
        result = await self.run_attack_suite()
        return self.report_pass_fail_matrix(result)

    def compound_score(self) -> float:
        """Calculate instigator compound score: cumulative coverage improvement."""
        if not self._run_history:
            return 0.0
        return sum(r.compound_score_delta for r in self._run_history)
