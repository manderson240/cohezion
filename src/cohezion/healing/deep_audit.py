"""
Deep Codebase Auditor.

Performs static analysis to identify:
1. Code Quality (Complexity, Length)
2. Performance Risks (Blocking I/O in async)
3. Architectural Coupling (Import depth)
4. Classification: Good / Needs Improvement / Bottleneck
"""

import ast
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CodeIssue:
    file_path: str
    line: int
    severity: str  # Critical, Warning, Info
    category: str  # Performance, Quality, Architecture
    message: str


@dataclass
class FileStats:
    path: str
    loc: int
    complexity: int
    functions: int
    imports: int
    score: float = 100.0


class DeepAuditor(ast.NodeVisitor):
    def __init__(self):
        self.issues: list[CodeIssue] = []
        self.stats: dict[str, FileStats] = {}
        self.current_file = ""
        self.current_complexity = 0

    def audit_file(self, file_path: Path):
        self.current_file = str(file_path)
        try:
            content = file_path.read_text()
            tree = ast.parse(content)

            # Basic stats
            loc = len(content.splitlines())

            self.visit(tree)

            # Create FileStats entry (complexity populated by visit)
            self.stats[self.current_file] = FileStats(
                path=str(file_path),
                loc=loc,
                complexity=self.current_complexity,
                functions=sum(
                    1
                    for node in ast.walk(tree)
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                ),
                imports=sum(
                    1 for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))
                ),
            )

            # Reset for next file
            self.current_complexity = 0

        except Exception as e:
            self.issues.append(
                CodeIssue(str(file_path), 0, "Critical", "Parser", f"Failed to parse: {e}")
            )

    def visit_AsyncFunctionDef(self, node):
        self._check_blocking_io(node)
        self._check_complexity(node)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self._check_complexity(node)
        self.generic_visit(node)

    def _check_complexity(self, node):
        """Cyclomatic complexity approximation."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(
                child,
                (
                    ast.If,
                    ast.For,
                    ast.While,
                    ast.ExceptHandler,
                    ast.With,
                    ast.AsyncWith,
                ),
            ):
                complexity += 1

        self.current_complexity += complexity

        if complexity > 15:
            self.issues.append(
                CodeIssue(
                    self.current_file,
                    node.lineno,
                    "Warning",
                    "Quality",
                    f"High complexity function '{node.name}' (score: {complexity})",
                )
            )

    def _check_blocking_io(self, node):
        """Check for blocking calls in async functions."""
        for child in ast.walk(node):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                # Check for time.sleep
                if getattr(child.func.value, "id", "") == "time" and child.func.attr == "sleep":
                    self.issues.append(
                        CodeIssue(
                            self.current_file,
                            child.lineno,
                            "Critical",
                            "Performance",
                            f"Blocking 'time.sleep' in async function '{node.name}'",
                        )
                    )
                # Check for subprocess.run without loop.run_in_executor (heuristic)
                if getattr(child.func.value, "id", "") == "subprocess" and child.func.attr == "run":
                    self.issues.append(
                        CodeIssue(
                            self.current_file,
                            child.lineno,
                            "Warning",
                            "Performance",
                            f"Blocking 'subprocess.run' in async function '{node.name}'. Use "
                            f"'asyncio.create_subprocess_exec' or run_in_executor.",
                        )
                    )

    def generate_report(self):
        report = "# Deep Codebase Audit Report\n\n"

        # 1. Executive Summary
        critical_issues = [i for i in self.issues if i.severity == "Critical"]
        report += "## 🎯 Executive Summary\n"
        report += f"- **Files Analyzed:** {len(self.stats)}\n"
        report += f"- **Code Quality Score:** {self._calculate_global_score()}/100\n"
        report += f"- **Critical Bottlenecks:** {len(critical_issues)}\n\n"

        if critical_issues:
            report += "### 🚨 Potential Bottlenecks (Fix Immediately)\n"
            for issue in critical_issues:
                report += f"- `{issue.file_path}:{issue.line}`: {issue.message}\n"
            report += "\n"

        # 2. Classification
        report += "## 📊 Classification\n"
        good = []
        ok = []
        bad = []

        for _path, stat in self.stats.items():
            if stat.complexity > 50 or stat.loc > 300:
                bad.append(stat)
            elif stat.complexity > 20 or stat.loc > 150:
                ok.append(stat)
            else:
                good.append(stat)

        report += "| Category | Count | Files |\n"
        report += "|----------|-------|-------|\n"
        report += f"| 🟢 Good | {len(good)} | Clean, simple components |\n"
        report += (
            f"| 🟡 Could Improve | {len(ok)} | {', '.join([Path(f.path).name for f in ok[:3]])}... "
            f"|\n"
        )
        bad_names = ", ".join([Path(f.path).name for f in bad])
        report += f"| 🔴 Needs Refactor | {len(bad)} | {bad_names} |\n\n"

        # 3. High Complexity Analysis
        if bad:
            report += "### 🔴 Complex Modules (Refactor Candidates)\n"
            for stat in bad:
                report += (
                    f"- **{Path(stat.path).name}** (LOC: {stat.loc}, Complexity: "
                    f"{stat.complexity})\n"
                )
                # Find specific issues for this file
                file_issues = [i for i in self.issues if i.file_path == stat.path]
                for issue in file_issues:
                    report += f"  - ⚠️ {issue.message}\n"

        return report

    def _calculate_global_score(self):
        # Heuristic score
        len(self.stats) or 1
        criticals = len([i for i in self.issues if i.severity == "Critical"])
        warnings = len([i for i in self.issues if i.severity == "Warning"])

        score = 100 - (criticals * 5) - (warnings * 1)
        return max(0, score)


def run_deep_audit():
    auditor = DeepAuditor()
    base_path = Path("src/cohezion")

    for root, _, files in os.walk(base_path):
        for file in files:
            if file.endswith(".py"):
                auditor.audit_file(Path(root) / file)

    report = auditor.generate_report()

    output_path = base_path / "knowledge_graph/audits/deep_audit_report.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report)
    print(report)


if __name__ == "__main__":
    run_deep_audit()
