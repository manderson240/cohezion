"""Auto-test generator for Cohezion.

Generates comprehensive pytest test suites from Python source files.
Uses established patterns from compound test generation.

Usage:
    uv run python -m cohezion.tools.test_generator \
        --target src/cohezion/api/streaming.py \
        --output tests/api/test_streaming.py
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FunctionInfo:
    """Information about a function/method."""

    name: str
    args: list[str]
    is_async: bool
    is_method: bool
    docstring: str = ""
    decorators: list[str] = field(default_factory=list)
    complexity: int = 1  # Estimated complexity score


@dataclass
class ClassInfo:
    """Information about a class."""

    name: str
    methods: list[FunctionInfo]
    docstring: str = ""
    bases: list[str] = field(default_factory=list)


@dataclass
class ModuleInfo:
    """Information about a module."""

    path: Path
    classes: list[ClassInfo]
    functions: list[FunctionInfo]
    imports: list[str] = field(default_factory=list)


class TestGenerator:
    """Generate pytest test files from Python source."""

    def __init__(self, template_style: str = "comprehensive"):
        self.template_style = template_style
        self.indent = "    "

    def analyze_module(self, source_path: Path) -> ModuleInfo:
        """Parse Python source and extract structure."""
        source = source_path.read_text()
        tree = ast.parse(source)

        classes = []
        functions = []
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")

        # Extract classes
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                class_info = self._extract_class(node)
                classes.append(class_info)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_info = self._extract_function(node)
                functions.append(func_info)

        return ModuleInfo(
            path=source_path,
            classes=classes,
            functions=functions,
            imports=imports,
        )

    def _extract_class(self, node: ast.ClassDef) -> ClassInfo:
        """Extract class information."""
        methods = []
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(self._extract_function(child, is_method=True))

        bases = [self._get_name(base) for base in node.bases]

        docstring = ast.get_docstring(node) or ""

        return ClassInfo(
            name=node.name,
            methods=methods,
            docstring=docstring,
            bases=bases,
        )

    def _extract_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_method: bool = False
    ) -> FunctionInfo:
        """Extract function information."""
        args = []
        for arg in node.args.args:
            if arg.arg != "self":
                args.append(arg.arg)
        for arg in node.args.kwonlyargs:
            args.append(arg.arg)

        decorators = [self._get_name(d) for d in node.decorator_list]
        docstring = ast.get_docstring(node) or ""

        # Estimate complexity
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.Try)):
                complexity += 1

        return FunctionInfo(
            name=node.name,
            args=args,
            is_async=isinstance(node, ast.AsyncFunctionDef),
            is_method=is_method,
            docstring=docstring,
            decorators=decorators,
            complexity=complexity,
        )

    def _get_name(self, node: ast.AST) -> str:
        """Get name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return ""

    def generate_tests(self, module_info: ModuleInfo) -> str:
        """Generate test file content."""
        lines = []

        # Header
        lines.extend(self._generate_header(module_info))

        # Imports
        lines.extend(self._generate_imports(module_info))

        # Module-level functions
        for func in module_info.functions:
            if not func.name.startswith("_"):
                lines.extend(self._generate_function_tests(func, module_info))

        # Classes
        for cls in module_info.classes:
            lines.extend(self._generate_class_tests(cls, module_info))

        return "\n".join(lines)

    def _generate_header(self, module_info: ModuleInfo) -> list[str]:
        """Generate file header."""
        _module_name = module_info.path.stem
        return [
            f'"""Tests for {module_info.path}.',
            "",
            "Generated by cohezion.tools.test_generator.",
            f"Covers {len(module_info.classes)} classes, {len(module_info.functions)} functions.",
            '"""',
            "",
            "from __future__ import annotations",
            "",
            "from unittest.mock import AsyncMock, MagicMock, patch",
            "",
            "import pytest",
            "",
        ]

    def _generate_imports(self, module_info: ModuleInfo) -> list[str]:
        """Generate import statements."""
        imports = []
        _module_name = module_info.path.stem

        # Import the module under test
        relative_path = (
            str(module_info.path).replace("src/", "").replace("/", ".").replace(".py", "")
        )
        imports.append(f"from cohezion.{relative_path} import *")
        imports.append("")

        return imports

    def _generate_function_tests(self, func: FunctionInfo, module_info: ModuleInfo) -> list[str]:
        """Generate tests for a function."""
        lines = []
        class_name = f"Test{func.name.replace('_', ' ').title().replace(' ', '')}"

        lines.append(f"class {class_name}:")
        lines.append(f'{self.indent}"""[P0] Unit tests for {func.name} function."""')
        lines.append("")

        # Basic test
        if func.is_async:
            lines.append(f"{self.indent}@pytest.mark.asyncio")
            lines.append(f"{self.indent}async def test_{func.name}_basic(self):")
        else:
            lines.append(f"{self.indent}def test_{func.name}_basic(self):")
        lines.append(
            f'{self.indent}{self.indent}"""[P0] Should execute {func.name} successfully."""'
        )
        lines.append(f"{self.indent}{self.indent}# Arrange")
        for arg in func.args[:3]:  # First 3 args
            lines.append(f"{self.indent}{self.indent}{arg} = None  # TODO: Set appropriate value")
        lines.append("")
        lines.append(f"{self.indent}{self.indent}# Act")
        if func.is_async:
            lines.append(f"{self.indent}{self.indent}result = await {func.name}()")
        else:
            lines.append(f"{self.indent}{self.indent}result = {func.name}()")
        lines.append("")
        lines.append(f"{self.indent}{self.indent}# Assert")
        lines.append(f"{self.indent}{self.indent}assert result is not None")
        lines.append("")

        # Error case for complex functions
        if func.complexity > 2:
            lines.append(f"{self.indent}def test_{func.name}_handles_errors(self):")
            lines.append(f'{self.indent}{self.indent}"""[P0] Should handle errors gracefully."""')
            lines.append(f"{self.indent}{self.indent}# Test error handling")
            lines.append("")

        return lines

    def _generate_class_tests(self, cls: ClassInfo, module_info: ModuleInfo) -> list[str]:
        """Generate tests for a class."""
        lines = []

        # Test class
        lines.append(f"class Test{cls.name}:")
        lines.append(f'{self.indent}"""[P0] Unit tests for {cls.name} class."""')
        lines.append("")

        # Setup fixture
        lines.append(f"{self.indent}@pytest.fixture()")
        lines.append(f"{self.indent}def {cls.name.lower()}(self):")
        lines.append(f'{self.indent}{self.indent}"""Create {cls.name} instance."""')
        lines.append(f"{self.indent}{self.indent}return {cls.name}()")
        lines.append("")

        # Test initialization
        lines.append(f"{self.indent}def test_initialization(self, {cls.name.lower()}):")
        lines.append(f'{self.indent}{self.indent}"""[P0] Should initialize {cls.name}."""')
        lines.append(f"{self.indent}{self.indent}assert {cls.name.lower()} is not None")
        lines.append("")

        # Test each public method
        for method in cls.methods:
            if not method.name.startswith("_"):
                lines.extend(self._generate_method_test(method, cls))

        return lines

    def _generate_method_test(self, method: FunctionInfo, cls: ClassInfo) -> list[str]:
        """Generate test for a method."""
        lines = []

        test_name = f"test_{method.name}_basic"

        if method.is_async:
            lines.append(f"{self.indent}@pytest.mark.asyncio")

        lines.append(f"{self.indent}def {test_name}(self, {cls.name.lower()}):")
        lines.append(f'{self.indent}{self.indent}"""[P0] Should execute {method.name}."""')
        lines.append("")

        # Setup
        if method.args:
            lines.append(f"{self.indent}{self.indent}# Setup arguments")
            for arg in method.args[:3]:
                lines.append(f"{self.indent}{self.indent}{arg} = None  # TODO")
            lines.append("")

        # Execute
        if method.is_async:
            lines.append(
                f"{self.indent}{self.indent}result = await {cls.name.lower()}.{method.name}()"
            )
        else:
            lines.append(f"{self.indent}{self.indent}result = {cls.name.lower()}.{method.name}()")
        lines.append("")

        # Assert
        lines.append(f"{self.indent}{self.indent}assert result is not None")
        lines.append("")

        return lines


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate pytest tests from Python source")
    parser.add_argument("--target", required=True, help="Source file to analyze")
    parser.add_argument("--output", required=True, help="Output test file path")
    parser.add_argument(
        "--template", default="comprehensive", choices=["basic", "comprehensive", "minimal"]
    )

    args = parser.parse_args()

    source_path = Path(args.target)
    output_path = Path(args.output)

    if not source_path.exists():
        print(f"Error: Source file not found: {source_path}")
        return 1

    print(f"Analyzing {source_path}...")
    generator = TestGenerator(template_style=args.template)
    module_info = generator.analyze_module(source_path)

    print(f"Found {len(module_info.classes)} classes, {len(module_info.functions)} functions")
    print("Generating tests...")

    test_content = generator.generate_tests(module_info)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(test_content)

    print(f"Generated {output_path}")
    print(f"Tests generated: {len(module_info.classes) + len(module_info.functions)}")

    return 0


if __name__ == "__main__":
    exit(main())
