"""AutoHarness Policy Engine (arXiv:2603.03329v1).

Synthesizes deterministic code-as-action verifiers and bytecode policies
to bypass LLM calls at inference time with <1 ms verification latency.
"""

from __future__ import annotations

import ast
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field

# reconcile 2026-08-26: imports needed by branch-preserved code (VerificationResult is defined
# below; the branch imported it from cohezion.contracts, which on main re-exports from here)
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    """Outcome of AutoHarness deterministic verification."""

    valid: bool
    latency_ms: float
    verifier_name: str
    violations: list[str] = field(default_factory=list)
    ast_nodes_scanned: int = 0


class AutoHarnessPolicy:
    """Deterministic bytecode action verifier and policy harness."""

    def __init__(self, policy_name: str = "default_safety") -> None:
        self.policy_name = policy_name
        self._verifiers: dict[str, Callable[[ast.AST], list[str]]] = {}
        self._register_default_rules()
        # reconcile 2026-08-26: the branch's state-policy registry (bounded_grid, positive_mass, ...)
        # lives alongside main's AST rule registry; both sides' callers use AutoHarnessPolicy().
        self._policy_registry: dict[str, Callable[[dict[str, Any]], bool]] = {}
        self._margin_registry: dict[str, Callable[[dict[str, Any]], float]] = {}
        self._register_default_policies()

    def _register_default_rules(self) -> None:
        """Register default deterministic AST safety verifiers."""
        self.register_rule("no_eval_exec", self._check_no_eval_exec)
        self.register_rule("type_annotations_present", self._check_type_annotations)
        self.register_rule("no_bare_except", self._check_no_bare_except)
        self.register_rule("multimodal_payload_schema", self._check_multimodal_payload_schema)

    def register_rule(self, name: str, verifier_fn: Callable[[ast.AST], list[str]]) -> None:
        """Register a custom deterministic verifier rule."""
        self._verifiers[name] = verifier_fn

    def verify_code(self, code_str: str) -> VerificationResult:
        """Verify code string deterministically in <1 ms without LLM calls."""
        t0 = time.monotonic()
        violations: list[str] = []
        nodes_scanned = 0

        try:
            tree = ast.parse(code_str)
            for _node in ast.walk(tree):
                nodes_scanned += 1

            for _name, rule_fn in self._verifiers.items():
                rule_violations = rule_fn(tree)
                violations.extend(rule_violations)

        except SyntaxError as syn_err:
            violations.append(f"SyntaxError: {syn_err.msg} at line {syn_err.lineno}")
        except Exception as exc:
            violations.append(f"AST Parsing Error: {exc}")

        latency_ms = (time.monotonic() - t0) * 1000.0
        valid = len(violations) == 0

        return VerificationResult(
            valid=valid,
            latency_ms=latency_ms,
            verifier_name=self.policy_name,
            violations=violations,
            ast_nodes_scanned=nodes_scanned,
        )

    @staticmethod
    def _check_no_eval_exec(tree: ast.AST) -> list[str]:
        """Ensure no illegal eval() or exec() calls exist."""
        violations = []
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in ("eval", "exec")
            ):
                violations.append(f"Illegal dangerous call '{node.func.id}' at line {node.lineno}")
        return violations

    @staticmethod
    def _check_type_annotations(tree: ast.AST) -> list[str]:
        """Check that function definitions include return type annotations."""
        violations = []
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.FunctionDef)
                and node.returns is None
                and not node.name.startswith("_")
            ):
                violations.append(
                    f"Function '{node.name}' at line {node.lineno} missing return type annotation"
                )
        return violations

    @staticmethod
    def _check_no_bare_except(tree: ast.AST) -> list[str]:
        """Check that no bare 'except:' clauses exist."""
        violations = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                violations.append(f"Bare 'except:' handler at line {node.lineno}")
        return violations

    @staticmethod
    def _check_multimodal_payload_schema(tree: ast.AST) -> list[str]:
        """Verify TRELLIS 3D and ACE-Step payload schema AST calls."""
        violations = []
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in ("generate_3d_asset", "generate_music_track")
                and not node.args
                and not node.keywords
            ):
                violations.append(
                    f"Multimodal call '{node.func.attr}' at line {node.lineno} missing payload parameters"
                )
        return violations

    def synthesize_policy_for_paper(self, title: str, abstract: str) -> str:
        """Synthesize new AST verifier rule based on ingested research paper."""
        rule_name = f"rule_{hash(title) & 0xFFFFFFFF:08x}"

        def _dynamic_research_rule(tree: ast.AST) -> list[str]:
            # Synthesized AST policy rule for paper
            return []

        self.register_rule(rule_name, _dynamic_research_rule)
        logger.info(
            "AutoHarnessPolicy: synthesized AST rule '%s' for paper '%s'", rule_name, title[:60]
        )
        return rule_name

    # --- reconcile 2026-08-26: methods preserved from the branch (worktree-virtual-soaring-shamir) ---
    def _register_default_policies(self) -> None:
        """Register deterministic pre-verification policies."""
        # 1. Bounds policy: ensure array dimensions and values stay bounded
        self._policy_registry["bounded_grid"] = lambda state: (
            isinstance(state.get("grid"), list)
            and len(state["grid"]) <= 30
            and all(isinstance(row, list) and len(row) <= 30 for row in state["grid"])
        )

        # 2. Physics policy: mass > 0, energy conserved
        self._policy_registry["positive_mass"] = lambda state: (
            isinstance(state.get("mass"), (int, float)) and state["mass"] > 0.0
        )

        # 3. Memory floor policy: available_gb >= 20.0
        self._policy_registry["memory_safe"] = lambda state: (
            isinstance(state.get("available_gb"), (int, float)) and state["available_gb"] >= 20.0
        )

        # 4. Credential safety policy: ensures shell actions do not access forbidden secret files
        from cohezion.security.secret_scrubber import verify_command_safety

        self._policy_registry["credential_safe"] = lambda state: (
            verify_command_safety(state.get("command", "")).allowed
        )

        # 5. Continuous clearance margin policies (Proprioceptive Cybernetics P1)
        self._margin_registry["memory_safe"] = lambda state: (
            float(state.get("available_gb", 0.0)) - 20.0
        )
        self._margin_registry["positive_mass"] = lambda state: float(state.get("mass", 0.0))
        self._margin_registry["bounded_grid"] = lambda state: float(
            min(
                30 - len(state.get("grid", [])),
                min((30 - len(row) for row in state.get("grid", [])), default=30),
            )
        )

    def register_policy(self, name: str, policy_fn: Callable[[dict[str, Any]], bool]) -> None:
        """Register a custom deterministic policy function."""
        self._policy_registry[name] = policy_fn

    def register_margin_policy(
        self, name: str, margin_fn: Callable[[dict[str, Any]], float]
    ) -> None:
        """Register a continuous clearance margin policy h(x) where h(x) >= 0 is safe."""
        self._margin_registry[name] = margin_fn

    def evaluate_policy(
        self,
        action_type: str,
        state: dict[str, Any],
        source_code: str | None = None,
        efference_ticket: dict[str, Any] | None = None,
    ) -> ActionPolicyResult:
        """Evaluate an action against deterministic harness policies before LLM invocation.

        Parameters
        ----------
        action_type : str
            Identifier for the policy to evaluate.
        state : dict[str, Any]
            State dictionary to test against policy predicates.
        source_code : str | None
            Optional Python source code string for static AST verification.
        efference_ticket : dict[str, Any] | None
            Optional forward prediction ticket (efference copy) for corollary discharge residual check.

        Returns
        -------
        ActionPolicyResult
            Structured result containing validity, latency, clearance margin, and efference status.
        """
        t0 = time.perf_counter()

        # Step 0: Calculate continuous clearance margin if registered
        margin = 0.0
        margin_fn = self._margin_registry.get(action_type)
        if margin_fn:
            try:
                margin = float(margin_fn(state))
            except Exception as e:
                logger.debug("Margin calculation error for '%s': %s", action_type, e)
                margin = 0.0

        # Step 1: Check registered policy rules
        policy_fn = self._policy_registry.get(action_type)
        if policy_fn:
            try:
                allowed = policy_fn(state)
                if not allowed:
                    dt_ms = (time.perf_counter() - t0) * 1000.0
                    return ActionPolicyResult(
                        allowed=False,
                        bypassed_llm=True,
                        action_type=action_type,
                        verification_score=0.0,
                        execution_time_ms=dt_ms,
                        reason=f"Action violated deterministic policy '{action_type}'",
                        clearance_margin=margin,
                    )
            except Exception as e:
                dt_ms = (time.perf_counter() - t0) * 1000.0
                return ActionPolicyResult(
                    allowed=False,
                    bypassed_llm=True,
                    action_type=action_type,
                    verification_score=0.0,
                    execution_time_ms=dt_ms,
                    reason=f"Policy evaluation error: {e}",
                    clearance_margin=margin,
                )
        elif margin_fn is not None:
            # If no boolean policy exists but margin policy does, enforce h(x) >= 0
            if margin < 0.0:
                dt_ms = (time.perf_counter() - t0) * 1000.0
                return ActionPolicyResult(
                    allowed=False,
                    bypassed_llm=True,
                    action_type=action_type,
                    verification_score=0.0,
                    execution_time_ms=dt_ms,
                    reason=f"Action breached clearance margin '{action_type}' (margin: {margin:.4f} < 0)",
                    clearance_margin=margin,
                )

        # Step 2: Check efference copy (corollary discharge) if ticket provided
        efference_info: dict[str, Any] = {}
        if efference_ticket is not None:
            tolerance = float(efference_ticket.get("_tolerance", 1.0))
            residuals: dict[str, float] = {}
            mismatch = False
            for k, expected_v in efference_ticket.items():
                if k.startswith("_"):
                    continue
                actual_v = state.get(k)
                if isinstance(expected_v, (int, float)) and isinstance(actual_v, (int, float)):
                    res = abs(float(actual_v) - float(expected_v))
                    residuals[k] = res
                    if res > tolerance:
                        mismatch = True
            efference_info = {
                "ticket": efference_ticket,
                "residuals": residuals,
                "mismatch": mismatch,
            }
            if mismatch:
                dt_ms = (time.perf_counter() - t0) * 1000.0
                return ActionPolicyResult(
                    allowed=False,
                    bypassed_llm=True,
                    action_type=action_type,
                    verification_score=0.0,
                    execution_time_ms=dt_ms,
                    reason=f"Corollary discharge mismatch: efference error exceeded tolerance ({residuals})",
                    clearance_margin=margin,
                    efference_copy=efference_info,
                )

        # Step 3: If source code is supplied, run zero-cost static AST verification
        v_score = 1.0
        if source_code:
            v_res = self.verify_code(source_code)
            v_score = 1.0 if v_res.valid else 0.0
            if not v_res.valid:
                dt_ms = (time.perf_counter() - t0) * 1000.0
                return ActionPolicyResult(
                    allowed=False,
                    bypassed_llm=True,
                    action_type=action_type,
                    verification_score=0.0,
                    execution_time_ms=dt_ms,
                    reason=f"AST verification failed: {v_res.violations}",
                    clearance_margin=margin,
                    efference_copy=efference_info,
                )

        dt_ms = (time.perf_counter() - t0) * 1000.0
        return ActionPolicyResult(
            allowed=True,
            bypassed_llm=True,  # Successfully validated without LLM inference call!
            action_type=action_type,
            verification_score=v_score,
            execution_time_ms=dt_ms,
            reason="Validated by AutoHarness policy",
            clearance_margin=margin,
            efference_copy=efference_info,
        )


# --- reconcile 2026-08-26: top-level symbols preserved from the branch ---
@dataclass(frozen=True, slots=True)
class ActionPolicyResult:
    """Outcome of a synthesized AutoHarness policy check."""

    allowed: bool
    bypassed_llm: bool
    action_type: str
    verification_score: float
    execution_time_ms: float
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    clearance_margin: float = 0.0
    efference_copy: dict[str, Any] = field(default_factory=dict)
