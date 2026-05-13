# ruff: noqa: E501  # long lines: SQL/URLs/docstrings — wrapping reduces readability
"""Ralph Lopps Red Team adversarial review system.

Ralph Lopps is the adversarial reviewer who injects failure modes,
identifies edge cases, and challenges assumptions before execution.
"""

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class AdversarialFinding:
    """A finding from adversarial review."""

    severity: str  # "critical", "high", "medium", "low"
    category: str  # "coherence", "token_efficiency", "failure_mode", "assumption"
    description: str
    recommendation: str
    line_number: int | None = None


class RalphLoppsReviewer:
    """Red Team adversarial reviewer for compound engineering.

    Ralph's job is to break things before they go live.
    He identifies:
    - Missing coherence checks
    - Token waste patterns
    - Unhandled failure modes
    - Hidden assumptions
    """

    def __init__(self):
        self.failure_patterns = {
            "missing_coherence": r"(?!.*coherence).*execute.*\(",
            "sequential_processing": r"for\s+\w+\s+in\s+\w+.*:\s*\n\s+\w+\(",
            "no_timeout": r"(async\s+def|def)\s+\w+.*\(.*\)(?!.*timeout)",
            "missing_checkpoint": r"(delete|remove|drop)(?!.*checkpoint)",
            "hardcoded_config": r"=\s*[\"']\w+[\"'](?!.*config)",
        }

    def review(self, code: str, context: dict[str, Any] | None = None) -> list[AdversarialFinding]:
        """Review code for adversarial concerns.

        Args:
            code: Code to review
            context: Optional execution context

        Returns:
            List of adversarial findings
        """
        findings = []

        # Check for missing coherence checks
        if self._has_missing_coherence_check(code):
            findings.append(
                AdversarialFinding(
                    severity="critical",
                    category="coherence",
                    description="Execution proceeds without coherence validation",
                    recommendation="Add RequestAlignmentAnalyzer.check_alignment() before execution",
                    line_number=self._find_line(code, r"execute"),
                )
            )

        # Check for token waste patterns
        if self._has_sequential_processing(code):
            findings.append(
                AdversarialFinding(
                    severity="high",
                    category="token_efficiency",
                    description="Sequential processing detected - potential for batching",
                    recommendation="Use BatchExecutor for parallel processing",
                    line_number=self._find_line(code, r"for\s+\w+\s+in"),
                )
            )

        # Check for missing timeouts
        if self._has_missing_timeout(code):
            findings.append(
                AdversarialFinding(
                    severity="high",
                    category="failure_mode",
                    description="Async function lacks timeout protection",
                    recommendation="Add timeout parameter: asyncio.wait_for(..., timeout=30)",
                    line_number=self._find_line(code, r"async\s+def"),
                )
            )

        # Check for destructive operations without checkpoint
        if self._has_destructive_without_checkpoint(code):
            findings.append(
                AdversarialFinding(
                    severity="critical",
                    category="failure_mode",
                    description="Destructive operation without checkpoint",
                    recommendation="Call create_checkpoint() before destructive operations",
                    line_number=self._find_line(code, r"(delete|remove|drop)"),
                )
            )

        # Check for hardcoded values
        if self._has_hardcoded_config(code):
            findings.append(
                AdversarialFinding(
                    severity="medium",
                    category="assumption",
                    description="Hardcoded configuration value detected",
                    recommendation="Move to ServerConfig dataclass",
                    line_number=self._find_line(code, r"=\s*[\"']\w+[\"']"),
                )
            )

        return findings

    def _has_missing_coherence_check(self, code: str) -> bool:
        """Check if code lacks coherence validation."""
        # Remove comments before checking
        code_no_comments = re.sub(r"#.*", "", code)
        has_execute = bool(re.search(r"execute.*\(", code_no_comments))
        has_coherence = bool(
            re.search(r"coherence|alignment|check.*threshold", code_no_comments, re.I)
        )
        return has_execute and not has_coherence

    def _has_sequential_processing(self, code: str) -> bool:
        """Check for sequential loops that could be batched."""
        # Look for for loops followed by any function call in the body
        return bool(re.search(r"for\s+\w+\s+in\s+\w+.*:\s*\n", code))

    def _has_missing_timeout(self, code: str) -> bool:
        """Check if async functions lack timeout."""
        async_funcs = re.findall(r"async\s+def\s+(\w+)", code)
        for func in async_funcs:
            func_pattern = rf"async\s+def\s+{func}.*:\s*(.*?)(?=async\s+def|class\s+|def\s+|\Z)"
            match = re.search(func_pattern, code, re.DOTALL)
            if match and "timeout" not in match.group(1).lower():
                return True
        return False

    def _has_destructive_without_checkpoint(self, code: str) -> bool:
        """Check for destructive operations without checkpoint."""
        has_destructive = bool(re.search(r"(delete|remove|drop|clear)", code, re.I))
        has_checkpoint = bool(re.search(r"checkpoint|backup|snapshot", code, re.I))
        return has_destructive and not has_checkpoint

    def _has_hardcoded_config(self, code: str) -> bool:
        """Check for hardcoded configuration values."""
        hardcoded = re.findall(r"=\s*[\"']\w+[\"']", code)
        config_refs = re.findall(r"config\.\w+|Config\.\w+|settings\.\w+", code)
        return len(hardcoded) > len(config_refs)

    def _find_line(self, code: str, pattern: str) -> int | None:
        """Find line number for pattern."""
        lines = code.split("\n")
        for i, line in enumerate(lines, 1):
            if re.search(pattern, line):
                return i
        return None


class MultiperspectiveReviewBoard:
    """Blue/Green/Yellow Hat multiperspective review system."""

    def __init__(self):
        self.blue: BlueHatReviewer = BlueHatReviewer()
        self.green: GreenHatReviewer = GreenHatReviewer()
        self.yellow: YellowHatReviewer = YellowHatReviewer()
        self.reviewers: dict[str, Any] = {
            "blue": self.blue,
            "green": self.green,
            "yellow": self.yellow,
        }

    def full_review(self, proposal: dict[str, Any]) -> dict[str, Any]:
        """Run all perspectives on a proposal.

        Args:
            proposal: Design proposal to review

        Returns:
            Combined review results
        """
        return {
            "blue": self.blue.review_process(proposal),
            "green": self.green.generate_alternatives(proposal),
            "yellow": self.yellow.assess_risks(proposal),
            "ralph": RalphLoppsReviewer().review(str(proposal)),
        }


class BlueHatReviewer:
    """Blue Hat: Process optimization and control."""

    def review_process(self, workflow: dict) -> list[dict]:
        """Review workflow for optimization opportunities."""
        optimizations = []
        steps = workflow.get("steps", [])

        # Check for parallelizable steps
        if len(steps) > 2:
            optimizations.append(
                {
                    "type": "parallelization",
                    "finding": "Steps could execute in parallel",
                    "recommendation": "Use asyncio.gather() for independent steps",
                }
            )

        # Check for caching opportunities
        if any("load" in step.lower() for step in steps):
            optimizations.append(
                {
                    "type": "caching",
                    "finding": "Repeated loading detected",
                    "recommendation": "Implement MultiLayerCache for warm starts",
                }
            )

        return optimizations


class GreenHatReviewer:
    """Green Hat: Creative alternatives and lateral thinking."""

    def generate_alternatives(self, current_design: dict) -> list[dict]:
        """Generate creative alternatives to current design."""
        alternatives = []

        # Alternative 1: Event-driven architecture
        alternatives.append(
            {
                "name": "Event-Driven MCP",
                "description": "Use Redis pub/sub for async MCP communication",
                "benefits": ["Decoupled services", "Better scalability"],
                "risks": ["Added complexity", "Eventual consistency"],
            }
        )

        # Alternative 2: Shared memory cache
        alternatives.append(
            {
                "name": "Shared Memory Cache",
                "description": "Use POSIX shared memory for zero-copy cache",
                "benefits": ["Zero serialization overhead", "Microsecond latency"],
                "risks": ["Platform-specific", "Complex cleanup"],
            }
        )

        # Alternative 3: WASM plugins
        alternatives.append(
            {
                "name": "WASM MCP Plugins",
                "description": "Sandbox MCP tools as WebAssembly modules",
                "benefits": ["Isolation", "Language agnostic"],
                "risks": ["Overhead", "Limited stdlib"],
            }
        )

        return alternatives


class YellowHatReviewer:
    """Yellow Hat: Risk assessment and critical analysis."""

    def assess_risks(self, architecture: dict) -> list[dict]:
        """Assess risks in architecture."""
        risks = []
        components = architecture.get("components", [])

        # MCP-specific risks
        if "vault_mcp" in components:
            risks.append(
                {
                    "component": "vault_mcp",
                    "risk": "Session state loss on server restart",
                    "mitigation": "Enable stateless_http mode",
                    "severity": "high",
                }
            )

        if "redis_cache" in components:
            risks.append(
                {
                    "component": "redis_cache",
                    "risk": "Cache stampede on cold start",
                    "mitigation": "Implement circuit breaker and gradual warmup",
                    "severity": "medium",
                }
            )

        if "compound_executor" in components:
            risks.append(
                {
                    "component": "compound_executor",
                    "risk": "Infinite loop in skill refinement",
                    "mitigation": "Set max_refinement_iterations=5",
                    "severity": "critical",
                }
            )

        return risks
