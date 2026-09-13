"""TemplateEngine must not let skill-file text break out of the Python it generates.

``AgentFactory`` execs the generated source with full builtins, so any breakout is code
execution. Skill ``.md`` files are LLM-refined, so their fields are untrusted input.
Reproducer (adversarial review of a25cc4a88): a ``## VERSION`` line of
``1\"\"\"; __import__("os").environ[...]="1"; \"\"\"`` closed the docstring and ran.
"""

from __future__ import annotations

import ast
import os

import pytest

from cohezion.core.template_engine import SkillSpec, TemplateEngine


_BREAKOUTS = [
    '1"""; __import__("os").environ["TPL_PWN"]="1"; """',
    'x\\"; __import__("os").environ["TPL_PWN"]="1" #',
    "x\\\\\"; __import__('os').environ['TPL_PWN']='1' #",
    "x'''; __import__('os').environ['TPL_PWN']='1'; '''",
]


def _generators():
    engine = TemplateEngine()
    return [engine.generate_agent_stub, engine.generate_executable_agent]


def _executes_injected_code(source: str) -> bool:
    """True if the generated module contains any statement besides the expected shape."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "__import__":
            return True
    return False


@pytest.mark.parametrize("payload", _BREAKOUTS)
@pytest.mark.parametrize("field", ["version", "domain_expertise"])
@pytest.mark.parametrize("gen_index", [0, 1])
def test_skill_fields_cannot_inject_code(payload, field, gen_index, monkeypatch):
    monkeypatch.delenv("TPL_PWN", raising=False)
    spec = SkillSpec(name="EVIL_PRIME", **{"domain_expertise": "d", field: payload})
    source = _generators()[gen_index](spec)
    assert not _executes_injected_code(source), f"{field} broke out of generated source"
    assert "TPL_PWN" not in os.environ


@pytest.mark.parametrize("gen_index", [0, 1])
def test_system_prompt_round_trips_exactly(gen_index):
    """Escaping must preserve the text, not mangle it: a lossy fix is a different bug."""
    domain = 'Quotes " and \\ backslash and """ triple'
    source = _generators()[gen_index](SkillSpec(name="QUOTE_PRIME", domain_expertise=domain))
    assigns = [
        n
        for n in ast.walk(ast.parse(source))
        if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "SYSTEM_PROMPT"
    ]
    assert len(assigns) == 1
    assert ast.literal_eval(assigns[0].value) == domain
