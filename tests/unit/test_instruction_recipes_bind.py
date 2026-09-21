"""Code recipes in the root instruction files must call real signatures.

Measured 2026-09-21: AGENTS.md's event-bus recipe called `Event.agent_complete(agent=...)`;
the factory needs `agent_name` and `duration_ms`, so every agent that copied it got a
TypeError. Nothing checked the snippets. This test parses each ```python block (top-level
`await` allowed), resolves calls whose target the block imports (`Name(...)` and
`Name.attr(...)`), and binds the call's arguments to the real signature with placeholders.
`Signature.bind` raises the same TypeError the copying agent would hit, and nothing runs.

Calls whose target cannot be resolved statically are skipped, not failed: this guards the
drift class that actually happened, it does not claim the recipes are correct end to end.
"""

from __future__ import annotations

import ast
import importlib
import inspect
import re
import textwrap
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[2]
DOCS = [REPO / "AGENTS.md", REPO / "CLAUDE.md"]
_BLOCK = re.compile(r"```python\n(.*?)```", re.DOTALL)


def _blocks() -> list[tuple[str, int, str]]:
    """Recipe blocks only: ones that import from cohezion. Illustrative pseudo-code
    (e.g. `Edit(file_path=f, ...)`) is not something an agent copies verbatim."""
    found = []
    for doc in DOCS:
        for i, m in enumerate(_BLOCK.finditer(doc.read_text(encoding="utf-8"))):
            block = textwrap.dedent(m.group(1))  # blocks nested in list items are indented
            if re.search(r"^\s*from cohezion[\w.]* import ", block, re.MULTILINE):
                found.append((doc.name, i, block))
    return found


def _imported(tree: ast.AST) -> dict[str, object]:
    names: dict[str, object] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("cohezion"):
            mod = importlib.import_module(node.module)
            for alias in node.names:
                if hasattr(mod, alias.name):
                    names[alias.asname or alias.name] = getattr(mod, alias.name)
    return names


def _target(func: ast.expr, names: dict[str, object]) -> object | None:
    if isinstance(func, ast.Name):
        return names.get(func.id)
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        base = names.get(func.value.id)
        return getattr(base, func.attr, None) if base is not None else None
    return None


def _problems(block: str) -> list[str]:
    tree = compile(
        block, "<recipe>", "exec", flags=ast.PyCF_ONLY_AST | ast.PyCF_ALLOW_TOP_LEVEL_AWAIT
    )
    names = _imported(tree)
    problems = []
    for call in (n for n in ast.walk(tree) if isinstance(n, ast.Call)):
        target = _target(call.func, names)
        if target is None or not callable(target):
            continue
        if any(isinstance(a, ast.Starred) for a in call.args) or any(
            k.arg is None for k in call.keywords
        ):
            continue  # *args / **kwargs spread: not statically bindable
        try:
            sig = inspect.signature(target)
        except (TypeError, ValueError):
            continue
        try:
            sig.bind(
                *[None] * len(call.args),
                **{k.arg: None for k in call.keywords if k.arg is not None},
            )
        except TypeError as err:
            problems.append(f"line {call.lineno}: {ast.unparse(call.func)}(...) -> {err}")
    return problems


@pytest.mark.parametrize(("doc", "index", "block"), _blocks(), ids=lambda v: str(v)[:24])
def test_recipe_calls_bind_to_real_signatures(doc: str, index: int, block: str) -> None:
    problems = _problems(block)
    assert not problems, f"{doc} python block #{index}:\n" + "\n".join(problems)


def test_the_checker_catches_the_2026_09_21_recipe() -> None:
    """The broken recipe itself must be flagged, or this test proves nothing."""
    broken = (
        "from cohezion.core.event_bus import Event, EventBus\n"
        "bus = EventBus()\n"
        "await bus.publish(Event.agent_complete(agent='x', result={}))\n"
    )
    assert any("agent_complete" in p for p in _problems(broken))
