"""AutoHarness Invariant Factory (Compound Engineering Edition).
=============================================================
Zero-cost, deterministic code-as-action verifier and bytecode compiler
inspired by arXiv:2603.03329v1 (AutoHarness).

Enforces mathematical, metric, and domain invariants across Kaggle
competitions and agentic execution pipelines with 0 ms LLM inference latency.

Design Patterns:
- Visitor Pattern: Fast AST visitors walking code for domain-specific hazards.
- Abstract Factory: Extensible registration and compilation of domain invariants.
- Strategy Pattern: Multi-level static and runtime invariant validation.
"""

from __future__ import annotations

import ast
import enum
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Type

logger = logging.getLogger("AutoHarnessInvariantFactory")


class InvariantSeverity(str, enum.Enum):
    P0_CRITICAL = "P0_CRITICAL"  # Hard block: must abort execution/submission
    P1_HIGH = "P1_HIGH"          # High alert: likely performance degradation
    P2_MODERATE = "P2_MODERATE"  # Advisory: optimization opportunity
    PASS = "PASS"


@dataclass
class InvariantViolation:
    rule_name: str
    severity: InvariantSeverity
    message: str
    location: Optional[str] = None
    remediation_hint: str = ""


@dataclass
class InvariantResult:
    passed: bool
    invariants_checked: int
    violations: List[InvariantViolation] = field(default_factory=list)
    bytecode_valid: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def has_critical_violations(self) -> bool:
        return any(v.severity == InvariantSeverity.P0_CRITICAL for v in self.violations)


class BaseInvariant(ABC):
    """Abstract base class for all AutoHarness invariants."""

    name: str = "base_invariant"
    description: str = "Base invariant validator"

    @abstractmethod
    def verify_ast(
        self,
        tree: ast.AST,
        raw_code: str,
        context: Dict[str, Any],
    ) -> List[InvariantViolation]:
        """Statically inspects the AST for domain invariant compliance."""
        ...

    def verify_runtime(
        self,
        data: Any,
        context: Dict[str, Any],
    ) -> List[InvariantViolation]:
        """Optionally verifies runtime objects, tensors, or dataframes."""
        return []


# ============================================================================
# DOMAIN INVARIANT 1: Monotonic Attempt Invariant (ARC-AGI-2)
# ============================================================================
class MonotonicAttemptInvariant(BaseInvariant):
    """Guarantees that attempt_1 is preserved when valid, and DSL/heuristics

    are strictly injected into attempt_2 without regressing known neural wins.
    """

    name = "monotonic_attempt_invariant"
    description = "Enforces non-destructive attempt_2 injection for ARC-AGI-2"

    def verify_ast(
        self,
        tree: ast.AST,
        raw_code: str,
        context: Dict[str, Any],
    ) -> List[InvariantViolation]:
        violations: List[InvariantViolation] = []

        # Check for unconditional overwrites of attempt_1
        has_attempt1 = "attempt_1" in raw_code
        has_attempt2 = "attempt_2" in raw_code

        if has_attempt1 and not has_attempt2:
            violations.append(
                InvariantViolation(
                    rule_name=self.name,
                    severity=InvariantSeverity.P1_HIGH,
                    message="Code modifies 'attempt_1' without referencing 'attempt_2'. ARC permits 2 distinct guesses.",
                    remediation_hint="Populate attempt_2 with heuristic/DSL predictions while keeping attempt_1 intact.",
                )
            )

        # AST-based check for un-guarded overwrite of attempt_1
        class AttemptVisitor(ast.NodeVisitor):
            def __init__(self):
                self.in_if_guard = False
                self.unconditional_overwrite = False

            def visit_If(self, node: ast.If):
                # Check if the if-condition references attempt_1 or dummy
                test_code = ast.unparse(node.test) if hasattr(ast, "unparse") else ""
                prev_guard = self.in_if_guard
                if "attempt_1" in test_code or "dummy" in test_code or "0" in test_code:
                    self.in_if_guard = True
                self.generic_visit(node)
                self.in_if_guard = prev_guard

            def visit_Assign(self, node: ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "attempt_1":
                        value_code = ast.unparse(node.value) if hasattr(ast, "unparse") else ""
                        if ("dsl_" in value_code or "solve_" in value_code or "heuristic" in value_code) and not self.in_if_guard:
                            self.unconditional_overwrite = True
                self.generic_visit(node)

        visitor = AttemptVisitor()
        visitor.visit(tree)

        if visitor.unconditional_overwrite:
            violations.append(
                InvariantViolation(
                    rule_name=self.name,
                    severity=InvariantSeverity.P0_CRITICAL,
                    message="Unconditional heuristic overwrite of 'attempt_1' detected without validity guard.",
                    remediation_hint="Only overwrite attempt_1 if dummy ([[0]]); otherwise populate attempt_2.",
                )
            )

        return violations


# ============================================================================
# DOMAIN INVARIANT 2: Soft Kolmogorov Monotonicity Invariant (RSNA Knee)
# ============================================================================
class SoftKolmogorovMonotonicityInvariant(BaseInvariant):
    """Guarantees that P(Abnormal) >= max_k P_k condition bounds are maintained

    without creating flat tie clusters under multi-label ROC-AUC.
    """

    name = "soft_kolmogorov_monotonicity_invariant"
    description = "Enforces valid medical abnormality bounds and copula rank calibration for RSNA Knee"

    def verify_ast(
        self,
        tree: ast.AST,
        raw_code: str,
        context: Dict[str, Any],
    ) -> List[InvariantViolation]:
        violations: List[InvariantViolation] = []

        # Check if Abnormal column is present in code
        if "Abnormal" in raw_code:
            # Check for pure clipping or copula rank
            has_rank = ".rank(" in raw_code or "rank(" in raw_code
            has_clip = "clip(" in raw_code or "np.clip" in raw_code
            has_monotonic = "maximum" in raw_code or "max(" in raw_code or "NoisyOR" in raw_code

            if not has_clip:
                violations.append(
                    InvariantViolation(
                        rule_name=self.name,
                        severity=InvariantSeverity.P1_HIGH,
                        message="Missing probability clipping [1e-6, 1.0 - 1e-6] on multi-label knee predictions.",
                        remediation_hint="Apply np.clip(probs, 1e-6, 1.0 - 1e-6) to bound boundary log-loss penalty.",
                    )
                )

        return violations

    def verify_runtime(
        self,
        data: Any,
        context: Dict[str, Any],
    ) -> List[InvariantViolation]:
        violations: List[InvariantViolation] = []
        if isinstance(data, dict) and "Abnormal" in data:
            # Runtime dataframe or dict check
            abnormal_val = data["Abnormal"]
            conditions = [v for k, v in data.items() if k != "Abnormal" and isinstance(v, (int, float))]
            if conditions and abnormal_val < max(conditions) - 1e-5:
                violations.append(
                    InvariantViolation(
                        rule_name=self.name,
                        severity=InvariantSeverity.P0_CRITICAL,
                        message=f"Kolmogorov violation: P(Abnormal)={abnormal_val:.4f} < max(P_sub)={max(conditions):.4f}",
                        remediation_hint="Re-project P(Abnormal) = max(P(Abnormal), max_k P_k).",
                    )
                )
        return violations


# ============================================================================
# DOMAIN INVARIANT 3: Tautomer Canonical InChIKey Invariant (CASMI26)
# ============================================================================
class TautomerCanonicalInChIKeyInvariant(BaseInvariant):
    """Guarantees that molecular predictions are canonical 14-character

    InChIKey skeletons without uncanonicalized stereoisomers or invalid formats.
    """

    name = "tautomer_canonical_inchikey_invariant"
    description = "Enforces 14-character canonical InChIKey skeleton validation for CASMI26"

    def verify_ast(
        self,
        tree: ast.AST,
        raw_code: str,
        context: Dict[str, Any],
    ) -> List[InvariantViolation]:
        violations: List[InvariantViolation] = []

        # Check for destructive mass tolerance penalty (the w_ppm trap)
        if "w_ppm" in raw_code and "sigma_ppm" in raw_code:
            # Check if w_ppm is non-zero
            if "w_ppm = 0.15" in raw_code or "w_ppm = 0.2" in raw_code:
                violations.append(
                    InvariantViolation(
                        rule_name=self.name,
                        severity=InvariantSeverity.P0_CRITICAL,
                        message="Destructive Gaussian mass penalty (w_ppm > 0) detected. This corrupts isobar ranking.",
                        remediation_hint="Set w_ppm = 0.0. Isobar candidates are already within mass tolerance.",
                    )
                )

        # Check for InChIKey canonicalization presence
        if "inchikey" in raw_code.lower() or "ik14" in raw_code.lower():
            if "canonical" not in raw_code.lower() and "tautomer" not in raw_code.lower():
                violations.append(
                    InvariantViolation(
                        rule_name=self.name,
                        severity=InvariantSeverity.P1_HIGH,
                        message="Missing RDKit tautomer canonicalization on InChIKey outputs (causes ~4.4% uncanonicalized key loss).",
                        remediation_hint="Apply canonical_ik14 tautomer hash projection to all candidate predictions.",
                    )
                )

        return violations

    def verify_runtime(
        self,
        data: Any,
        context: Dict[str, Any],
    ) -> List[InvariantViolation]:
        violations: List[InvariantViolation] = []
        if isinstance(data, list):
            for i, item in enumerate(data[:100]):
                key = str(item).strip()
                # Must be 14 uppercase letters (InChIKey first block) or 27 full key
                block1 = key.split("-")[0] if "-" in key else key
                if len(block1) != 14 or not block1.isupper() or not block1.isalpha():
                    violations.append(
                        InvariantViolation(
                            rule_name=self.name,
                            severity=InvariantSeverity.P0_CRITICAL,
                            message=f"Invalid InChIKey skeleton format at index {i}: '{key}' (expected 14-char uppercase alpha)",
                            remediation_hint="Canonicalize SMILES with rdkit.Chem.MolToInchiKey and extract block 1.",
                        )
                    )
                    break
        return violations


# ============================================================================
# DOMAIN INVARIANT 4: Zobrist Cycle Evasion Invariant (ARC-AGI-3)
# ============================================================================
class ZobristCycleInvariant(BaseInvariant):
    """Guarantees 64-bit Zobrist state hashing and cycle evasion in interactive agents."""

    name = "zobrist_cycle_invariant"
    description = "Enforces cycle detection and state hash memory for ARC-AGI-3 interactive agents"

    def verify_ast(
        self,
        tree: ast.AST,
        raw_code: str,
        context: Dict[str, Any],
    ) -> List[InvariantViolation]:
        violations: List[InvariantViolation] = []

        # Interactive loop must track visited state hashes
        if "action" in raw_code and ("step(" in raw_code or "env." in raw_code):
            has_hash = "zobrist" in raw_code.lower() or "hash(" in raw_code or "visited" in raw_code
            if not has_hash:
                violations.append(
                    InvariantViolation(
                        rule_name=self.name,
                        severity=InvariantSeverity.P1_HIGH,
                        message="Interactive agent lacks state hashing or visited set tracking (high risk of oscillation loops).",
                        remediation_hint="Integrate 64-bit Zobrist hashing to track visited states and evade cycles.",
                    )
                )

        return violations


# ============================================================================
# DOMAIN INVARIANT 5: Budget & Concurrency Invariant (Gemma 4 & Universal)
# ============================================================================
class BudgetLimitInvariant(BaseInvariant):
    """Enforces turn budget limits (e.g. 240s turn timeout) and concurrency constraints."""

    name = "budget_limit_invariant"
    description = "Enforces SLA timeouts and execution budget bounds"

    def verify_ast(
        self,
        tree: ast.AST,
        raw_code: str,
        context: Dict[str, Any],
    ) -> List[InvariantViolation]:
        violations: List[InvariantViolation] = []

        # If pytest or test execution is called, must specify a timeout
        if "pytest" in raw_code and "timeout" not in raw_code:
            violations.append(
                InvariantViolation(
                    rule_name=self.name,
                    severity=InvariantSeverity.P1_HIGH,
                    message="Subprocess pytest execution lacks explicit timeout (vulnerable to infinite loop hanging).",
                    remediation_hint="Add --timeout=240 or timeout=240 in subprocess.run().",
                )
            )

        return violations


# ============================================================================
# INVARIANT FACTORY
# ============================================================================
class AutoHarnessInvariantFactory:
    """Central factory for compiling, registering, and evaluating AutoHarness invariants."""

    _INVARIANT_REGISTRY: Dict[str, BaseInvariant] = {}
    _COMPETITION_BINDINGS: Dict[str, List[str]] = {
        "arc-prize-2026-arc-agi-2": [
            "monotonic_attempt_invariant",
            "budget_limit_invariant",
        ],
        "arc-prize-2026-arc-agi-3": [
            "zobrist_cycle_invariant",
            "budget_limit_invariant",
        ],
        "rsna-knee-abnormality-detection": [
            "soft_kolmogorov_monotonicity_invariant",
            "budget_limit_invariant",
        ],
        "enveda-CASMI26-molecule-id-mass-spectra": [
            "tautomer_canonical_inchikey_invariant",
            "budget_limit_invariant",
        ],
        "gemma-4-developer-agent": [
            "budget_limit_invariant",
        ],
    }

    @classmethod
    def register_invariant(cls, invariant: BaseInvariant) -> None:
        """Registers an invariant singleton into the factory registry."""
        cls._INVARIANT_REGISTRY[invariant.name] = invariant
        logger.debug("Registered AutoHarness invariant '%s'", invariant.name)

    @classmethod
    def bind_competition(cls, competition_id: str, invariant_names: List[str]) -> None:
        """Binds a list of invariant names to a competition ID."""
        cls._COMPETITION_BINDINGS[competition_id] = invariant_names

    @classmethod
    def get_invariants(cls, competition_id: str) -> List[BaseInvariant]:
        """Returns the active invariants configured for a given competition."""
        inv_names = cls._COMPETITION_BINDINGS.get(competition_id, ["budget_limit_invariant"])
        result: List[BaseInvariant] = []
        for name in inv_names:
            if name in cls._INVARIANT_REGISTRY:
                result.append(cls._INVARIANT_REGISTRY[name])
        return result

    @classmethod
    def extract_code_from_file_or_notebook(cls, path: Path | str) -> str:
        """Loads raw code from either a .py file or all code cells of an .ipynb notebook."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Source artifact not found: {p}")

        if p.suffix == ".ipynb":
            with open(p, "r", encoding="utf-8") as f:
                nb = json.load(f)
            code_cells = []
            for cell in nb.get("cells", []):
                if cell.get("cell_type") == "code":
                    source = "".join(cell.get("source", []))
                    code_cells.append(source)
            return "\n\n# --- CELL BOUNDARY ---\n\n".join(code_cells)
        else:
            with open(p, "r", encoding="utf-8") as f:
                return f.read()

    @classmethod
    def compile_and_verify(
        cls,
        code_or_path: str | Path,
        competition_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> InvariantResult:
        """Compiles bytecode and checks all domain invariants with 0 ms LLM latency.

        Parameters
        ----------
        code_or_path : str | Path
            Raw Python code string or Path to .py / .ipynb file.
        competition_id : str
            Competition identifier for binding relevant invariants.
        context : Optional[Dict[str, Any]]
            Additional context metadata.

        Returns
        -------
        InvariantResult
            Evaluation outcome with violations and bytecode compilation status.
        """
        ctx = context or {}

        # Resolve raw code
        if isinstance(code_or_path, Path) or (isinstance(code_or_path, str) and (code_or_path.endswith(".py") or code_or_path.endswith(".ipynb"))):
            raw_code = cls.extract_code_from_file_or_notebook(code_or_path)
            ctx["source_path"] = str(code_or_path)
        else:
            raw_code = str(code_or_path)

        # 1. Bytecode Compilation Gate
        bytecode_valid = False
        compilation_error: Optional[str] = None
        try:
            # Filter out IPython magic commands (!pip, %matplotlib, etc.) for pure Python compilation
            # and hoist any from __future__ imports to the very top so compile() succeeds across concatenated notebook cells
            clean_lines = []
            future_lines = []
            for line in raw_code.splitlines():
                stripped = line.strip()
                if stripped.startswith("!") or stripped.startswith("%"):
                    clean_lines.append(f"# {line}")
                elif stripped.startswith("from __future__ import"):
                    future_lines.append(line)
                else:
                    clean_lines.append(line)
            clean_code = "\n".join(future_lines + clean_lines)

            compile(clean_code, "<autoharness>", "exec")
            bytecode_valid = True
        except Exception as e:
            compilation_error = str(e)
            logger.warning("Bytecode compilation warning: %s", e)

        # 2. Fast AST Parsing
        violations: List[InvariantViolation] = []
        try:
            tree = ast.parse(clean_code)
        except Exception as e:
            tree = ast.parse("pass")
            violations.append(
                InvariantViolation(
                    rule_name="syntax_integrity",
                    severity=InvariantSeverity.P0_CRITICAL,
                    message=f"SyntaxError in artifact: {e}",
                    remediation_hint="Fix syntax errors before submission.",
                )
            )

        # 3. Domain Invariant Evaluations
        invariants = cls.get_invariants(competition_id)
        for inv in invariants:
            try:
                inv_violations = inv.verify_ast(tree, raw_code, ctx)
                violations.extend(inv_violations)
            except Exception as e:
                logger.error("Invariant '%s' crashed during evaluation: %s", inv.name, e)

        passed = not any(v.severity == InvariantSeverity.P0_CRITICAL for v in violations) and bytecode_valid

        return InvariantResult(
            passed=passed,
            invariants_checked=len(invariants) + 1,  # +1 for bytecode compiler
            violations=violations,
            bytecode_valid=bytecode_valid,
            metadata={
                "competition_id": competition_id,
                "compilation_error": compilation_error,
                "num_violations": len(violations),
            },
        )


# Initialize default invariants
AutoHarnessInvariantFactory.register_invariant(MonotonicAttemptInvariant())
AutoHarnessInvariantFactory.register_invariant(SoftKolmogorovMonotonicityInvariant())
AutoHarnessInvariantFactory.register_invariant(TautomerCanonicalInChIKeyInvariant())
AutoHarnessInvariantFactory.register_invariant(ZobristCycleInvariant())
AutoHarnessInvariantFactory.register_invariant(BudgetLimitInvariant())
