"""Greenfield tests for cohezion.tools.test_generator (Z7).

The TestGenerator parses a Python source file via AST and emits a pytest
template. We exercise both the analysis pass and the code-gen pass against
a small synthetic source file written into a tmp_path.
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


SAMPLE_SOURCE = '''"""Sample module."""
from typing import Any

import os


def add(a, b):
    """Add two numbers."""
    return a + b


async def fetch(url):
    """Fetch a URL."""
    if url:
        return url
    return None


class Greeter:
    """A greeter."""

    def __init__(self, name="world"):
        self.name = name

    def greet(self):
        """Return a greeting."""
        if self.name:
            return f"hello {self.name}"
        return "hello"

    async def greet_async(self):
        return await self._inner()

    def _hidden(self):
        return None
'''


@pytest.fixture()
def sample_module(tmp_path: Path) -> Path:
    src = tmp_path / "sample.py"
    src.write_text(SAMPLE_SOURCE)
    return src


def test_test_generator_default_construction():
    gen = TestGenerator()
    assert gen.template_style == "comprehensive"
    assert gen.indent == "    "


def test_analyze_module_extracts_classes_and_functions(sample_module: Path):
    gen = TestGenerator()
    info = gen.analyze_module(sample_module)
    assert isinstance(info, ModuleInfo)
    func_names = {f.name for f in info.functions}
    assert {"add", "fetch"} <= func_names
    class_names = {c.name for c in info.classes}
    assert "Greeter" in class_names
    # Imports captured (both `import` and `from` forms)
    assert any(imp.endswith("os") or imp == "os" for imp in info.imports)


def test_analyze_module_marks_async_function(sample_module: Path):
    gen = TestGenerator()
    info = gen.analyze_module(sample_module)
    fetch = next(f for f in info.functions if f.name == "fetch")
    assert fetch.is_async is True
    add = next(f for f in info.functions if f.name == "add")
    assert add.is_async is False
    # `add` has no branching -> complexity 1; `fetch` has an `if` -> complexity 2
    assert add.complexity == 1
    assert fetch.complexity >= 2


def test_analyze_module_extracts_class_methods_and_skips_self(sample_module: Path):
    gen = TestGenerator()
    info = gen.analyze_module(sample_module)
    greeter = next(c for c in info.classes if c.name == "Greeter")
    method_names = {m.name for m in greeter.methods}
    # Both public and private methods are captured by the analyzer; the
    # _filter_ to public happens in the code-gen pass.
    assert "greet" in method_names
    assert "greet_async" in method_names
    # `self` is stripped from the args list
    init = next(m for m in greeter.methods if m.name == "__init__")
    assert "self" not in init.args


def test_generate_tests_includes_class_and_function_blocks(sample_module: Path):
    gen = TestGenerator()
    info = gen.analyze_module(sample_module)
    output = gen.generate_tests(info)
    # Public function `add` -> TestAdd class
    assert "class TestAdd" in output
    # Public function `fetch` -> async test path
    assert "async def test_fetch_basic" in output
    # Class `Greeter` -> TestGreeter class with init test and a fixture
    assert "class TestGreeter" in output
    assert "def test_initialization" in output
    # Private method `_hidden` is filtered out of the generated tests
    assert "test__hidden" not in output


def test_generate_tests_emits_module_docstring_header(sample_module: Path):
    gen = TestGenerator()
    info = gen.analyze_module(sample_module)
    output = gen.generate_tests(info)
    # Docstring header + import + pytest scaffold
    assert output.startswith('"""Tests for')
    assert "import pytest" in output
    assert "from unittest.mock import" in output


def test_function_info_dataclass_defaults():
    fn = FunctionInfo(name="f", args=["x"], is_async=False, is_method=False)
    assert fn.docstring == ""
    assert fn.decorators == []
    assert fn.complexity == 1


def test_class_info_dataclass_defaults():
    cls = ClassInfo(name="C", methods=[])
    assert cls.docstring == ""
    assert cls.bases == []
