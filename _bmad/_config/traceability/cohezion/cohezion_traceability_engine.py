#!/usr/bin/env python3
"""
Cohezion Codebase Traceability Engine

Analyzes the entire Cohezion Python codebase for:
- Module dependency graphs
- Class inheritance trees
- Function call relationships
- Test coverage mapping
- Import/export relationships
- Circular dependency detection
"""

from __future__ import annotations

import ast
import csv
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class Module:
    """Python module representation."""

    path: Path
    name: str
    imports: List[str] = field(default_factory=list)
    from_imports: List[Tuple[str, str]] = field(default_factory=list)  # (module, name)
    classes: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    async_functions: List[str] = field(default_factory=list)
    has_init: bool = False
    line_count: int = 0


@dataclass
class Dependency:
    """Module dependency relationship."""

    source_module: str
    target_module: str
    import_type: str  # import, from_import
    symbols: List[str] = field(default_factory=list)


@dataclass
class Inheritance:
    """Class inheritance relationship."""

    class_name: str
    base_class: str
    module: str
    file_path: str


@dataclass
class TestCoverage:
    """Test file coverage mapping."""

    test_file: Path
    test_module: str
    tested_module: str
    test_count: int
    test_types: List[str] = field(default_factory=list)  # unit, integration, fast


@dataclass
class CodeTraceabilityMatrix:
    """Complete code traceability matrix."""

    modules: List[Module] = field(default_factory=list)
    dependencies: List[Dependency] = field(default_factory=list)
    inheritances: List[Inheritance] = field(default_factory=list)
    test_coverage: List[TestCoverage] = field(default_factory=list)
    circular_deps: List[Tuple[str, str]] = field(default_factory=list)


class CohezionTraceabilityEngine:
    """Main traceability extraction engine for Cohezion codebase."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.src_root = project_root / "src" / "cohezion"
        self.test_root = project_root / "tests"
        self.output_dir = project_root / "_bmad" / "_config" / "traceability" / "cohezion"

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Storage
        self.modules: Dict[str, Module] = {}
        self.dependencies: List[Dependency] = []
        self.inheritances: List[Inheritance] = []
        self.test_coverage: List[TestCoverage] = []

    def discover_python_files(self) -> List[Path]:
        """Discover all Python files in src/cohezion."""
        return list(self.src_root.glob("**/*.py"))

    def discover_test_files(self) -> List[Path]:
        """Discover all test files."""
        return list(self.test_root.glob("**/test_*.py"))

    def parse_module(self, file_path: Path) -> Optional[Module]:
        """Parse a Python module and extract metadata."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)
            module_name = self._path_to_module_name(file_path)

            module = Module(
                path=file_path,
                name=module_name,
                line_count=len(content.split("\n")),
                has_init=file_path.name == "__init__.py",
            )

            # Extract imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module.imports.append(alias.name)

                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        for alias in node.names:
                            module.from_imports.append((node.module, alias.name))

                elif isinstance(node, ast.ClassDef):
                    module.classes.append(node.name)
                    # Extract inheritance
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            inheritance = Inheritance(
                                class_name=node.name,
                                base_class=base.id,
                                module=module_name,
                                file_path=str(file_path.relative_to(self.src_root)),
                            )
                            self.inheritances.append(inheritance)

                elif isinstance(node, ast.FunctionDef):
                    module.functions.append(node.name)

                elif isinstance(node, ast.AsyncFunctionDef):
                    module.async_functions.append(node.name)

            self.modules[module_name] = module
            return module

        except SyntaxError as e:
            print(f"Syntax error in {file_path}: {e}")
            return None
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None

    def _path_to_module_name(self, file_path: Path) -> str:
        """Convert file path to module name."""
        relative = file_path.relative_to(self.src_root)
        parts = list(relative.parts)
        if parts[-1] == "__init__.py":
            parts = parts[:-1]
        else:
            parts[-1] = parts[-1][:-3]  # Remove .py
        return ".".join(parts)

    def build_dependencies(self) -> List[Dependency]:
        """Build module dependency graph."""
        deps = []

        for module_name, module in self.modules.items():
            # Process regular imports
            for imp in module.imports:
                # Check if it's a cohezion import
                if imp.startswith("cohezion"):
                    target = imp.replace(".", "/").replace("cohezion/", "")
                    deps.append(
                        Dependency(
                            source_module=module_name,
                            target_module=imp,
                            import_type="import",
                        )
                    )

            # Process from imports
            for from_module, symbol in module.from_imports:
                if from_module.startswith("cohezion"):
                    deps.append(
                        Dependency(
                            source_module=module_name,
                            target_module=from_module,
                            import_type="from_import",
                            symbols=[symbol],
                        )
                    )

        self.dependencies = deps
        return deps

    def detect_circular_dependencies(self) -> List[Tuple[str, str]]:
        """Detect circular dependencies in module graph."""
        cycles = []

        # Build adjacency list
        graph: Dict[str, Set[str]] = defaultdict(set)
        for dep in self.dependencies:
            if dep.target_module.startswith("cohezion"):
                graph[dep.source_module].add(dep.target_module)

        # DFS cycle detection
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: List[str]) -> Optional[Tuple[str, str]]:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    result = dfs(neighbor, path + [neighbor])
                    if result:
                        return result
                elif neighbor in rec_stack:
                    return (node, neighbor)

            rec_stack.remove(node)
            return None

        for node in graph:
            if node not in visited:
                cycle = dfs(node, [node])
                if cycle:
                    cycles.append(cycle)

        self.circular_deps = cycles
        return cycles

    def map_test_coverage(self) -> List[TestCoverage]:
        """Map test files to modules they test."""
        coverage = []

        test_files = self.discover_test_files()
        for test_file in test_files:
            test_module_name = self._path_to_module_name(test_file, test_root=True)
            tested_module = self._infer_tested_module(test_module_name)

            try:
                with open(test_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # Count test functions
                test_count = len(re.findall(r"def test_\w+", content))
                test_types = []

                if "@pytest.mark.fast" in content:
                    test_types.append("fast")
                if "@pytest.mark.integration" in content:
                    test_types.append("integration")
                if "@pytest.mark.mcp" in content:
                    test_types.append("mcp")

                cov = TestCoverage(
                    test_file=test_file,
                    test_module=test_module_name,
                    tested_module=tested_module,
                    test_count=test_count,
                    test_types=test_types,
                )
                coverage.append(cov)

        self.test_coverage = coverage
        return coverage

    def _path_to_module_name(
        self, file_path: Path, test_root: bool = False
    ) -> str:
        """Convert file path to module name."""
        if test_root:
            root = self.test_root
        else:
            root = self.src_root

        relative = file_path.relative_to(root)
        parts = list(relative.parts)
        if parts[-1].endswith(".py"):
            parts[-1] = parts[-1][:-3]
        if parts[-1] == "__init__":
            parts = parts[:-1]
        return ".".join(parts)

    def _infer_tested_module(self, test_module: str) -> str:
        """Infer which module a test file tests."""
        # Remove 'test_' prefix and 'tests' parent
        parts = test_module.split(".")
        if parts[-1].startswith("test_"):
            parts[-1] = parts[-1][5:]
        if "tests" in parts:
            parts.remove("tests")
        return ".".join(parts) if parts else "unknown"

    def run_full_extraction(self) -> CodeTraceabilityMatrix:
        """Execute full extraction pipeline."""
        print("🔍 Cohezion Codebase Traceability Engine")
        print("=" * 60)

        print("Discovering Python files...")
        py_files = self.discover_python_files()
        print(f"Found {len(py_files)} Python files")

        print("Parsing modules...")
        for i, py_file in enumerate(py_files, 1):
            self.parse_module(py_file)
            if i % 100 == 0:
                print(f"  Parsed {i}/{len(py_files)} modules")

        print(f"✓ Parsed {len(self.modules)} modules")

        print("Building dependency graph...")
        self.build_dependencies()
        print(f"✓ Found {len(self.dependencies)} dependencies")

        print("Detecting circular dependencies...")
        cycles = self.detect_circular_dependencies()
        if cycles:
            print(f"⚠️  Detected {len(cycles)} circular dependencies: {cycles}")
        else:
            print("✓ No circular dependencies detected")

        print("Mapping test coverage...")
        self.map_test_coverage()
        print(f"✓ Mapped {len(self.test_coverage)} test files")

        matrix = CodeTraceabilityMatrix(
            modules=list(self.modules.values()),
            dependencies=self.dependencies,
            inheritances=self.inheritances,
            test_coverage=self.test_coverage,
            circular_deps=self.circular_deps,
        )

        return matrix

    def write_matrices(self, matrix: CodeTraceabilityMatrix) -> Dict[str, Path]:
        """Write all matrices to CSV files."""
        output_files = {}

        # Module inventory
        module_path = self.output_dir / "module-inventory.csv"
        with open(module_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "module_name",
                    "file_path",
                    "line_count",
                    "imports",
                    "from_imports",
                    "classes",
                    "functions",
                    "async_functions",
                    "has_init",
                ]
            )
            for mod in matrix.modules:
                writer.writerow(
                    [
                        mod.name,
                        str(mod.path.relative_to(self.src_root)),
                        mod.line_count,
                        len(mod.imports),
                        len(mod.from_imports),
                        len(mod.classes),
                        len(mod.functions),
                        len(mod.async_functions),
                        mod.has_init,
                    ]
                )
        output_files["module_inventory"] = module_path

        # Dependency graph
        dep_path = self.output_dir / "dependency-graph.csv"
        with open(dep_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["source_module", "target_module", "import_type", "symbols"]
            )
            for dep in matrix.dependencies:
                writer.writerow(
                    [
                        dep.source_module,
                        dep.target_module,
                        dep.import_type,
                        ";".join(dep.symbols),
                    ]
                )
        output_files["dependency_graph"] = dep_path

        # Inheritance tree
        inherit_path = self.output_dir / "inheritance-tree.csv"
        with open(inherit_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["class_name", "base_class", "module", "file_path"])
            for inh in matrix.inheritances:
                writer.writerow(
                    [inh.class_name, inh.base_class, inh.module, inh.file_path]
                )
        output_files["inheritance_tree"] = inherit_path

        # Test coverage
        test_path = self.output_dir / "test-coverage.csv"
        with open(test_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "test_file",
                    "test_module",
                    "tested_module",
                    "test_count",
                    "test_types",
                ]
            )
            for cov in matrix.test_coverage:
                writer.writerow(
                    [
                        str(cov.test_file.relative_to(self.test_root)),
                        cov.test_module,
                        cov.tested_module,
                        cov.test_count,
                        ";".join(cov.test_types),
                    ]
                )
        output_files["test_coverage"] = test_path

        return output_files

    def generate_report(self, matrix: CodeTraceabilityMatrix) -> str:
        """Generate summary report."""
        report = []
        report.append("# Cohezion Codebase Traceability Report")
        report.append("")
        report.append("## Summary Statistics")
        report.append("")
        report.append(f"- **Modules**: {len(matrix.modules)}")
        report.append(f"- **Dependencies**: {len(matrix.dependencies)}")
        report.append(f"- **Inheritances**: {len(matrix.inheritances)}")
        report.append(f"- **Test Files**: {len(matrix.test_coverage)}")
        report.append(f"- **Circular Dependencies**: {len(matrix.circular_deps)}")
        report.append("")

        # Module breakdown
        report.append("## Module Breakdown")
        report.append("")
        module_types = defaultdict(int)
        for mod in matrix.modules:
            parts = mod.name.split(".")
            if len(parts) > 1:
                module_types[parts[0]] += 1
            else:
                module_types["root"] += 1

        for module_type, count in sorted(module_types.items(), key=lambda x: -x[1]):
            report.append(f"- **{module_type}**: {count} modules")
        report.append("")

        # Top dependencies
        report.append("## Top Module Dependencies")
        report.append("")
        dep_counts = defaultdict(int)
        for dep in matrix.dependencies:
            dep_counts[dep.target_module] += 1

        for target, count in sorted(dep_counts.items(), key=lambda x: -x[1])[:10]:
            report.append(f"- `{target}`: {count} imports")
        report.append("")

        # Test coverage
        report.append("## Test Coverage")
        report.append("")
        total_tests = sum(c.test_count for c in matrix.test_coverage)
        tested_modules = len(set(c.tested_module for c in matrix.test_coverage))
        report.append(f"- **Total Tests**: {total_tests}")
        report.append(f"- **Tested Modules**: {tested_modules}")
        report.append("")

        # Circular deps
        if matrix.circular_deps:
            report.append("## ⚠️ Circular Dependencies")
            report.append("")
            for src, tgt in matrix.circular_deps:
                report.append(f"- `{src}` ↔ `{tgt}`")
            report.append("")

        return "\n".join(report)


def main():
    """Main entry point."""
    project_root = Path("/home/mike-anderson/dev/cohezion")
    engine = CohezionTraceabilityEngine(project_root)

    matrix = engine.run_full_extraction()
    output_files = engine.write_matrices(matrix)

    print("\n📊 Generated matrices:")
    for name, path in output_files.items():
        print(f"  {name}: {path}")

    report = engine.generate_report(matrix)
    report_path = engine.output_dir / "traceability-report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n📄 Report written to: {report_path}")
    print("\n✅ Cohezion traceability extraction complete!")


if __name__ == "__main__":
    main()
