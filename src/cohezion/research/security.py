"""Security guardrails for ResearchAgent.

Validates code changes before execution.
Integrates with Cohezion's security pipeline.
"""

from __future__ import annotations

import ast
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cohezion.security.pipeline import SecurityPipeline

logger = logging.getLogger(__name__)


@dataclass
class CodeChange:
    """Represents a code change."""

    file_path: Path
    old_code: str
    new_code: str
    change_type: str  # 'modify', 'add', 'delete'


@dataclass
class ValidationResult:
    """Result of code validation."""

    is_valid: bool
    issues: list[str]
    risk_level: str  # 'low', 'medium', 'high', 'critical'


class ResearchSecurityGuardrails:
    """Security guardrails for research code changes.

    Validates modifications to train.py before execution.
    Follows elegant simplification - ~150 lines.
    """

    # Forbidden patterns
    FORBIDDEN_IMPORTS = [
        "os.system",
        "subprocess.call",
        "subprocess.run",
        "eval(",
        "exec(",
        "__import__",
        "open(",  # File operations
        "write(",
    ]

    # Allowed training-related imports
    ALLOWED_IMPORTS = [
        "torch",
        "torch.nn",
        "torch.optim",
        "numpy",
        "math",
        "typing",
        "dataclasses",
        "logging",
    ]

    def __init__(self, security_pipeline: SecurityPipeline | None = None):
        """Initialize guardrails.

        Args:
            security_pipeline: Optional Cohezion security pipeline
        """
        self.security_pipeline = security_pipeline

    def validate_change(self, change: CodeChange) -> ValidationResult:
        """Validate a single code change.

        Args:
            change: CodeChange to validate

        Returns:
            ValidationResult with validity and any issues
        """
        issues = []

        # Check for forbidden patterns
        for pattern in self.FORBIDDEN_IMPORTS:
            if pattern in change.new_code:
                issues.append(f"Forbidden pattern: {pattern}")

        # Check AST validity
        if not self._is_valid_ast(change.new_code):
            issues.append("Invalid Python syntax")

        # Check for dangerous operations
        dangerous = self._check_dangerous_operations(change.new_code)
        issues.extend(dangerous)

        # Run through security pipeline if available
        if self.security_pipeline:
            pipeline_result = self.security_pipeline.check_output(change.new_code)
            if pipeline_result.action.value != "allow":
                issues.append(f"Security pipeline blocked: {pipeline_result.reason}")

        # Determine risk level
        risk = self._assess_risk(change, issues)

        return ValidationResult(
            is_valid=len(issues) == 0,
            issues=issues,
            risk_level=risk,
        )

    def _is_valid_ast(self, code: str) -> bool:
        """Check if code is valid Python AST."""
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False

    def _check_dangerous_operations(self, code: str) -> list[str]:
        """Check for potentially dangerous operations."""
        issues = []

        # File operations outside allowed directories
        if re.search(r'open\s*\([^)]*["\']/(?:etc|usr|bin|lib)', code):
            issues.append("Attempted access to system directories")

        # Network operations
        if re.search(r"(socket\.|urllib|requests\.|http\.)", code):
            issues.append("Network operations not allowed in training")

        # GPU memory bombs
        if re.search(r"cuda\s*\(\s*\)\s*\.\s*empty_cache", code):
            issues.append("GPU cache manipulation detected")

        # Infinite loops
        if re.search(r"while\s+True\s*:", code):
            issues.append("Infinite loop detected")

        return issues

    def _assess_risk(self, change: CodeChange, issues: list[str]) -> str:
        """Assess risk level of change."""
        if len(issues) == 0:
            return "low"
        elif len(issues) <= 2:
            return "medium"
        elif len(issues) <= 5:
            return "high"
        else:
            return "critical"

    def validate_batch(
        self,
        changes: list[CodeChange],
    ) -> dict[str, ValidationResult]:
        """Validate multiple code changes.

        Returns dict mapping file paths to validation results.
        """
        results = {}
        for change in changes:
            results[str(change.file_path)] = self.validate_change(change)
        return results

    def get_safe_template(self) -> str:
        """Get safe training template for agents."""
        return '''
"""Safe training template for research agents.

This template provides a constrained environment for experimentation.
"""

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

class SafeTrainingConfig:
    """Safe training configuration."""
    model_depth: int = 8
    vocab_size: int = 8192
    max_seq_len: int = 1024
    batch_size: int = 16
    learning_rate: float = 0.001

def train(
    model: nn.Module,
    train_loader: DataLoader,
    config: SafeTrainingConfig,
) -> dict:
    """Safe training loop.
    
    Agents can modify this function but must:
    - Not add file/network operations
    - Not use eval/exec
    - Keep changes under 50 lines
    """
    # Your experimental code here
    pass

if __name__ == "__main__":
    # Training execution
    pass
'''


class SimpleSecurity:
    """Minimal security for basic use cases."""

    def __init__(self):
        self.forbidden = ["exec(", "eval(", "os.system", "subprocess"]

    def check(self, code: str) -> bool:
        """Quick security check."""
        for pattern in self.forbidden:
            if pattern in code:
                return False
        return True
