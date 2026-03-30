"""Tests for cohezion.tools.test_generator — auto-test scaffold generation.

Phase 3c coverage push.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cohezion.tools.test_generator import (
    ClassInfo,
    FunctionInfo,
    ModuleInfo,
    TestGenerator,
)


@pytest.fixture()
def generator():
    """Create a default TestGenerator."""
    return TestGenerator()


@pytest.fixture()
def sample_source(tmp_path):
    """Create a sample Python source file for analysis."""
    source = tmp_path / "sample.py"
    source.write_text(
        '''"""Sample module."""


def greet(name: str) -> str:
    """Greet someone."""
    return f"Hello, {name}"


async def fetch_data(url: str, timeout: int = 30) -> dict:
    """Fetch data from URL."""
    if not url:
        raise ValueError("URL required")
    return {"url": url}


class Calculator:
    """A simple calculator."""

    def add(self, a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    def divide(self, a: float, b: float) -> float:
        """Divide a by b."""
        if b == 0:
            raise ZeroDivisionError
        return a / b

    async def async_compute(self, expr: str) -> float:
        """Compute expression asynchronously."""
        return 42.0


class _PrivateHelper:
    """Private helper class."""

    def _internal(self):
        pass
'''
    )
    return source


class TestFunctionInfo:
    """Tests for FunctionInfo dataclass."""

    def test_defaults(self):
        """Should have sensible defaults."""
        info = FunctionInfo(name="test", args=[], is_async=False, is_method=False)
        assert info.complexity == 1
        assert info.decorators == []
        assert info.docstring == ""


class TestTestGenerator:
    """Tests for TestGenerator analysis and generation."""

    def test_init_default(self):
        """Should initialize with comprehensive template."""
        gen = TestGenerator()
        assert gen.template_style == "comprehensive"
        assert gen.indent == "    "

    def test_init_custom_style(self):
        """Should accept custom template style."""
        gen = TestGenerator(template_style="minimal")
        assert gen.template_style == "minimal"

    def test_analyze_module(self, generator, sample_source):
        """Should extract classes and functions from source."""
        info = generator.analyze_module(sample_source)
        assert isinstance(info, ModuleInfo)
        assert info.path == sample_source
        # Should find 2 top-level functions
        assert len(info.functions) == 2
        func_names = [f.name for f in info.functions]
        assert "greet" in func_names
        assert "fetch_data" in func_names
        # Should find 2 classes (Calculator and _PrivateHelper)
        assert len(info.classes) == 2
        class_names = [c.name for c in info.classes]
        assert "Calculator" in class_names

    def test_async_detection(self, generator, sample_source):
        """Should correctly detect async functions."""
        info = generator.analyze_module(sample_source)
        fetch = next(f for f in info.functions if f.name == "fetch_data")
        assert fetch.is_async is True
        greet = next(f for f in info.functions if f.name == "greet")
        assert greet.is_async is False

    def test_method_extraction(self, generator, sample_source):
        """Should extract methods from classes."""
        info = generator.analyze_module(sample_source)
        calc = next(c for c in info.classes if c.name == "Calculator")
        method_names = [m.name for m in calc.methods]
        assert "add" in method_names
        assert "divide" in method_names
        assert "async_compute" in method_names

    def test_complexity_estimation(self, generator, sample_source):
        """Should estimate higher complexity for branching code."""
        info = generator.analyze_module(sample_source)
        fetch = next(f for f in info.functions if f.name == "fetch_data")
        # fetch_data has an if statement, so complexity > 1
        assert fetch.complexity >= 2

    def test_args_extraction(self, generator, sample_source):
        """Should extract function arguments (excluding self)."""
        info = generator.analyze_module(sample_source)
        fetch = next(f for f in info.functions if f.name == "fetch_data")
        assert "url" in fetch.args
        assert "timeout" in fetch.args

    def test_generate_tests(self, generator, sample_source):
        """Should generate valid Python test file content."""
        info = generator.analyze_module(sample_source)
        output = generator.generate_tests(info)
        assert "import pytest" in output
        assert "class TestGreet" in output or "class TestCalculator" in output
        assert "def test_" in output

    def test_generate_includes_async_marker(self, generator, sample_source):
        """Should include @pytest.mark.asyncio for async functions."""
        info = generator.analyze_module(sample_source)
        output = generator.generate_tests(info)
        assert "pytest.mark.asyncio" in output

    def test_generate_skips_private_functions(self, generator, sample_source):
        """Should not generate tests for private functions."""
        info = generator.analyze_module(sample_source)
        output = generator.generate_tests(info)
        assert "test__internal" not in output

    def test_imports_extraction(self, generator, sample_source):
        """Should extract import statements."""
        info = generator.analyze_module(sample_source)
        # sample.py has no imports, but this should not fail
        assert isinstance(info.imports, list)


class TestGenerateClassTests:
    """Tests for class-specific test generation."""

    def test_fixture_generated(self, generator, sample_source):
        """Should generate fixture for each class."""
        info = generator.analyze_module(sample_source)
        output = generator.generate_tests(info)
        assert "@pytest.fixture" in output
        assert "def calculator(self)" in output

    def test_init_test_generated(self, generator, sample_source):
        """Should generate initialization test."""
        info = generator.analyze_module(sample_source)
        output = generator.generate_tests(info)
        assert "test_initialization" in output
