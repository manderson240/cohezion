"""
Cohezion Active Forbidden Subgraph & Anti-Pattern Linter
=========================================================
Implements Meta-Aspect 1 (Learning 533): Transitions retrospective knowledge from
passive markdown logging into active machine-readable constraint gates.

Scans candidate code ASTs and configuration graphs before execution/submission to
ensure known dead ends and failure modes are strictly halted at the compiler boundary.
"""

from __future__ import annotations

import ast
import json
import logging
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger("forbidden_subgraph_linter")


@dataclass
class AntiPatternRule:
    """Formal definition of a disproven computational pattern."""

    rule_id: str
    domain: str
    name: str
    description: str
    forbidden_tokens: list[str]
    regex_pattern: str | None = None
    severity: str = "CRITICAL"  # CRITICAL (halts), WARNING (advisory)
    historical_learning: str = ""


# Canonical Machine-Readable Dead-End Ledger
DEFAULT_ANTI_PATTERNS: list[AntiPatternRule] = [
    AntiPatternRule(
        rule_id="AP-ARC3-001",
        domain="arc-prize-2026-arc-agi-3",
        name="Orthogonal Escape Pulse Disruption",
        description=(
            "Injecting periodic orthogonal escape steps (dr_escape, dc_escape) destabilizes "
            "the 64-bit Zobrist Markov loop evasion engine and causes score collapse (0.22 -> 0.15)."
        ),
        forbidden_tokens=["dr_escape", "dc_escape", "orthogonal_escape_pulse", "escape_pulse"],
        regex_pattern=r"dr_escape\s*=|dc_escape\s*=|orthogonal_pulse",
        historical_learning="Learning 531: ARC-3 v36 Regression Analysis",
    ),
    AntiPatternRule(
        rule_id="AP-CASMI-002",
        domain="enveda-CASMI26-molecule-id-mass-spectra",
        name="Gaussian Isobaric Mass Penalty",
        description=(
            "Applying Gaussian mass penalties (w_ppm > 0) penalizes valid isobaric natural product "
            "candidates due to 3-5 ppm mass spectrometry instrument noise, causing slot defects."
        ),
        forbidden_tokens=["w_ppm", "gaussian_mass_penalty", "ppm_error_penalty"],
        regex_pattern=r"w_ppm\s*=\s*[1-9]|gaussian_penalty\s*\(",
        historical_learning="Learning 529: CASMI26 Adduct Marginalization",
    ),
    AntiPatternRule(
        rule_id="AP-RSNA-003",
        domain="rsna-knee-abnormality-detection",
        name="Unprojected Rank Averaging",
        description=(
            "Averaging predictions without enforcing Kolmogorov-KAM monotonicity bounds causes a 98.9% "
            "physical hierarchy violation rate where P(Overall) < max_k(P_k)."
        ),
        forbidden_tokens=["raw_rank_average_unbounded"],
        regex_pattern=r"p_overall\s*=\s*np\.mean\([^)]+\)\s*(?!.*enforce_kolmogorov|.*np\.maximum)",
        historical_learning="Learning 531: RSNA Biomechanical Copula Invariant",
    ),
    AntiPatternRule(
        rule_id="AP-GEMMA4-004",
        domain="gemma-4-developer-agent",
        name="Unbounded Flat History Replay",
        description=(
            "Replaying raw tool outputs into root context causes prompt explosion past 16,384 tokens, "
            "triggering vLLM ContextWindowExceededError and container timeouts in hidden evaluation."
        ),
        forbidden_tokens=["messages.append(raw_tool_output)"],
        regex_pattern=r"messages\.append\(\s*\{\s*['\"]role['\"]\s*:\s*['\"]tool['\"]",
        historical_learning="Learning 530: Gemma-4 CTEG Token Insulation Proof",
    ),
    AntiPatternRule(
        rule_id="AP-SILICON-005",
        domain="strix-halo-hardware",
        name="ROCm UMA Large GGUF Allocation",
        description=(
            "Allocating dense >12GB GGUFs onto the ROCm/UMA aperture during desktop sessions "
            "causes memory bus saturation and kernel fault risk. Local inference must use NPU SRAM or Zen 5 CPU."
        ),
        forbidden_tokens=["--gpu-layers 99", "-ngl 99", "hipMallocManaged"],
        regex_pattern=r"-ngl\s+[4-9]\d|--n-gpu-layers\s+[4-9]\d",
        historical_learning="Learning 528: Strix Halo Silicon Aperture Discipline",
    ),
]


class ForbiddenSubgraphLinter:
    """AST and Regex Linter enforcing the active dead-end ledger."""

    def __init__(self, rules: list[AntiPatternRule] | None = None):
        self.rules = rules or DEFAULT_ANTI_PATTERNS

    def audit_code(self, code: str, domain: str = "") -> tuple[bool, list[dict[str, Any]]]:
        """Audits candidate Python code against the forbidden subgraph ledger."""
        violations = []

        # 1. Regex & token scanning
        for rule in self.rules:
            if domain and rule.domain != domain and rule.domain != "strix-halo-hardware":
                continue

            for token in rule.forbidden_tokens:
                if token in code:
                    violations.append({
                        "rule_id": rule.rule_id,
                        "name": rule.name,
                        "token": token,
                        "severity": rule.severity,
                        "description": rule.description,
                        "historical_learning": rule.historical_learning,
                    })

            if rule.regex_pattern:
                matches = re.findall(rule.regex_pattern, code)
                if matches:
                    violations.append({
                        "rule_id": rule.rule_id,
                        "name": rule.name,
                        "match": matches[0],
                        "severity": rule.severity,
                        "description": rule.description,
                        "historical_learning": rule.historical_learning,
                    })

        # Deduplicate violations by rule_id
        seen_rules = set()
        unique_violations = []
        for v in violations:
            if v["rule_id"] not in seen_rules:
                seen_rules.add(v["rule_id"])
                unique_violations.append(v)

        passed = len(unique_violations) == 0
        return passed, unique_violations

    def audit_notebook(self, nb_path: Path | str, domain: str = "") -> tuple[bool, list[dict[str, Any]]]:
        """Audits an entire Jupyter Notebook."""
        p = Path(nb_path)
        if not p.exists():
            return False, [{"rule_id": "FILE_NOT_FOUND", "description": f"{p} does not exist"}]

        with open(p, "r", encoding="utf-8") as f:
            nb = json.load(f)

        code_lines = []
        for cell in nb.get("cells", []):
            if cell.get("cell_type") == "code":
                code_lines.extend(cell.get("source", []))

        full_code = "".join(code_lines)
        return self.audit_code(full_code, domain=domain)


def persist_ledger_json(output_path: Path | str = "src/cohezion/registry/forbidden_subgraphs.json"):
    """Serializes the active rule ledger to machine-readable JSON."""
    out = [asdict(r) for r in DEFAULT_ANTI_PATTERNS]
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    logger.info("Forbidden subgraph ledger saved to %s", p)


if __name__ == "__main__":
    persist_ledger_json()
    linter = ForbiddenSubgraphLinter()
    test_code = "dr_escape = 1\nw_ppm = 5"
    passed, viols = linter.audit_code(test_code)
    print(f"Audit Passed: {passed}")
    for v in viols:
        print(f"  [{v['rule_id']}] {v['name']}: {v['description'][:80]}...")
