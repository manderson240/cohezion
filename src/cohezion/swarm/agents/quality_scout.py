# ruff: noqa: E501  # long lines: SQL/URLs/docstrings — wrapping reduces readability
"""
Quality Scout - Performs zero-token static analysis to identify code smells and high-complexity files.
Acts as the primary filter for selective LLM analysis.
"""

import ast
import logging
from pathlib import Path

from cohezion.swarm.agents.base_scout import BaseScout, Finding


logger = logging.getLogger(__name__)


class QualityScout(BaseScout):
    """
    Scans files for technical debt and complexity using pure AST analysis.
    """

    def __init__(self, **kwargs) -> None:
        # QualityScout doesn't need an LLM model for its core phase,
        # but we pass a placeholder for compatibility.
        super().__init__(model="static-only", **kwargs)

    async def analyze(self, path: Path) -> list[Finding]:
        """Perform static analysis on the file."""
        findings = []
        rel_path = str(path)

        ast_summary = self._parse_python_ast(path)
        if not ast_summary:
            return []

        # 1. Complexity check
        if ast_summary.complexity_score > 15:
            findings.append(
                Finding(
                    type="anti_pattern",
                    name="High Cyclomatic Complexity",
                    category="complexity",
                    description=f"File has cyclomatic complexity of {ast_summary.complexity_score}, exceeding threshold of 15.",
                    file_path=rel_path,
                    line_range=(1, ast_summary.loc),
                    confidence=1.0,
                    code_snippet="N/A (Structural)",
                    severity="medium",
                )
            )

        # 2. Function length & nesting deep dive
        try:
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Function length
                    fn_lines = node.end_lineno - node.lineno
                    if fn_lines > 50:
                        findings.append(
                            Finding(
                                type="anti_pattern",
                                name="Long Function",
                                category="readability",
                                description=f"Function '{node.name}' is {fn_lines} lines long (threshold: 50).",
                                file_path=rel_path,
                                line_range=(node.lineno, node.end_lineno),
                                confidence=1.0,
                                code_snippet=ast.get_source_segment(path.read_text(), node) or "",
                                severity="low",
                            )
                        )

                    # Nesting depth check
                    max_depth = self._get_nesting_depth(node)
                    if max_depth > 4:
                        findings.append(
                            Finding(
                                type="anti_pattern",
                                name="Deep Nesting",
                                category="complexity",
                                description=f"Function '{node.name}' reached nesting depth of {max_depth} (threshold: 4).",
                                file_path=rel_path,
                                line_range=(node.lineno, node.end_lineno),
                                confidence=1.0,
                                code_snippet=ast.get_source_segment(path.read_text(), node) or "",
                                severity="medium",
                            )
                        )

                    # Bare except check
                    for body_node in ast.walk(node):
                        if isinstance(body_node, ast.ExceptHandler) and body_node.type is None:
                            findings.append(
                                Finding(
                                    type="anti_pattern",
                                    name="Bare Except",
                                    category="reliability",
                                    description=f"Bare except caught in '{node.name}'. Use specific exceptions.",
                                    file_path=rel_path,
                                    line_range=(body_node.lineno, body_node.end_lineno),
                                    confidence=1.0,
                                    code_snippet=ast.get_source_segment(path.read_text(), body_node)
                                    or "",
                                    severity="high",
                                )
                            )

        except Exception as e:
            logger.error(f"Deep AST analysis failed for {path}: {e}")

        return findings

    def _get_nesting_depth(self, node: ast.AST, current_depth: int = 0) -> int:
        """Calculate maximum nesting depth of a node."""
        depths = [current_depth]
        for child in ast.iter_child_nodes(node):
            if isinstance(
                child, (ast.If, ast.While, ast.For, ast.AsyncFor, ast.Try, ast.With, ast.AsyncWith)
            ):
                depths.append(self._get_nesting_depth(child, current_depth + 1))
            else:
                depths.append(self._get_nesting_depth(child, current_depth))
        return max(depths)
