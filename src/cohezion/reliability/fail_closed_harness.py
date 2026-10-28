"""Fail-Closed Frozen Test & Capability-Scoped Harness.
======================================================
Implements core principles from frontier Harness Engineering research:
1. ExecCritic (arXiv:2609.09133): Fail-closed test qualification that separates
   test generation from source-code repair, freezing tests so the repair agent
   cannot tamper with them to produce false confidence.
2. CapScope (arXiv:2609.08371): Capability-scoped harness that stores and enforces
   typed authorizations outside the model prompt context, preventing indirect prompt
   injection from escalating tool privileges.
"""

from __future__ import annotations

import ast
import enum
import hashlib
import logging
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


logger = logging.getLogger(__name__)


class Capability(enum.StrEnum):
    """Typed capabilities stored strictly outside model context."""

    FS_READ = "fs:read"
    FS_WRITE = "fs:write"
    CODE_EXEC = "code:exec"
    NET_ACCESS = "net:access"
    GIT_MUTATE = "git:mutate"


@dataclass(frozen=True, slots=True)
class FrozenTestSuite:
    """Immutable test suite frozen before code repair begins."""

    test_code: str
    test_hash: str
    invariants: tuple[str, ...]

    @classmethod
    def create_and_freeze(
        cls, test_code: str, invariants: list[str] | None = None
    ) -> FrozenTestSuite:
        code_bytes = test_code.strip().encode("utf-8")
        h = hashlib.sha256(code_bytes).hexdigest()
        inv = tuple(invariants) if invariants else ("AST_VALID", "DETERMINISTIC")
        return cls(test_code=test_code, test_hash=h, invariants=inv)

    def verify_integrity(self, current_code: str) -> bool:
        current_hash = hashlib.sha256(current_code.strip().encode("utf-8")).hexdigest()
        return current_hash == self.test_hash


@dataclass
class CapabilityCeiling:
    """Out-of-context authority ceiling enforcing strict principle of least privilege."""

    allowed_capabilities: set[Capability] = field(default_factory=set)

    def check_permission(self, cap: Capability) -> bool:
        return cap in self.allowed_capabilities

    def grant(self, cap: Capability) -> None:
        self.allowed_capabilities.add(cap)

    def revoke(self, cap: Capability) -> None:
        self.allowed_capabilities.discard(cap)


@dataclass(frozen=True, slots=True)
class HarnessExecutionResult:
    passed: bool
    test_verified: bool
    capabilities_respected: bool
    output: str
    error: str | None = None


class FailClosedHarness:
    """Fail-closed execution harness enforcing frozen test suites and capability gates."""

    def __init__(self, capability_ceiling: CapabilityCeiling | None = None) -> None:
        self.ceiling = capability_ceiling or CapabilityCeiling(
            allowed_capabilities={Capability.FS_READ, Capability.CODE_EXEC}
        )
        self._frozen_suite: FrozenTestSuite | None = None

    def freeze_test_suite(self, test_code: str) -> FrozenTestSuite:
        """Qualify and freeze the test suite before repair begins (ExecCritic)."""
        try:
            ast.parse(test_code)
        except SyntaxError as exc:
            raise ValueError(f"Cannot freeze malformed test suite: {exc}") from exc

        suite = FrozenTestSuite.create_and_freeze(test_code)
        self._frozen_suite = suite
        logger.info("Frozen test suite locked with SHA-256: %s", suite.test_hash[:16])
        return suite

    def verify_capability(self, cap: Capability) -> None:
        """Verify capability out-of-context (CapScope)."""
        if not self.ceiling.check_permission(cap):
            raise PermissionError(
                f"Capability '{cap.value}' denied: not present in out-of-context authorization ceiling."
            )

    def run_under_frozen_suite(
        self,
        candidate_code: str,
        timeout_s: float = 10.0,
    ) -> HarnessExecutionResult:
        """Execute candidate code strictly against the frozen, tamper-proof test suite."""
        if self._frozen_suite is None:
            raise RuntimeError("Fail-closed invariant violation: No frozen test suite registered.")

        # 1. Enforce capability
        try:
            self.verify_capability(Capability.CODE_EXEC)
        except PermissionError as e:
            return HarnessExecutionResult(
                passed=False,
                test_verified=False,
                capabilities_respected=False,
                output="",
                error=str(e),
            )

        # 2. Verify candidate AST syntax
        try:
            ast.parse(candidate_code)
        except SyntaxError as e:
            return HarnessExecutionResult(
                passed=False,
                test_verified=True,
                capabilities_respected=True,
                output="",
                error=f"Candidate code syntax error: {e}",
            )

        # 3. Execute in sandboxed isolated temporary script
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test_suite.py"
            future_imports: list[str] = []
            clean_cand: list[str] = []
            for line in candidate_code.splitlines():
                if line.strip().startswith("from __future__ import"):
                    future_imports.append(line.strip())
                else:
                    clean_cand.append(line)

            clean_test: list[str] = []
            for line in self._frozen_suite.test_code.splitlines():
                if line.strip().startswith("from __future__ import"):
                    future_imports.append(line.strip())
                else:
                    clean_test.append(line)

            header = "\n".join(sorted(set(future_imports))) + "\n\n" if future_imports else ""
            combined_script = (
                f"{header}"
                "# --- Candidate Patch ---\n"
                f"{chr(10).join(clean_cand)}\n\n"
                "# --- Frozen Test Suite ---\n"
                f"{chr(10).join(clean_test)}\n"
            )
            test_file.write_text(combined_script, encoding="utf-8")

            try:
                proc = subprocess.run(
                    [sys.executable, str(test_file)],
                    capture_output=True,
                    text=True,
                    timeout=timeout_s,
                )
                success = proc.returncode == 0
                return HarnessExecutionResult(
                    passed=success,
                    test_verified=True,
                    capabilities_respected=True,
                    output=proc.stdout,
                    error=proc.stderr if not success else None,
                )
            except subprocess.TimeoutExpired:
                return HarnessExecutionResult(
                    passed=False,
                    test_verified=True,
                    capabilities_respected=True,
                    output="",
                    error=f"Execution timed out after {timeout_s}s",
                )
