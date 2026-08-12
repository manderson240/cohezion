"""Pins what AutoHarnessVerifier actually does -- including what it does NOT do.

The bypass tests below assert that dangerous code is ACCEPTED. That is deliberate.
They are not endorsing the behaviour; they are making the module's real contract
executable, so a future reader cannot assume this AST lint is a safety boundary.
If someone hardens the blocklist, these tests fail loudly and the docstring must
be updated in the same change -- which is exactly the review conversation we want.

Measured 2026-08-12 on the restored implementation.
"""

from __future__ import annotations

import pytest

from cohezion.actioner.autoharness_verifier import AutoHarnessVerifier, ExecutableAction


@pytest.fixture
def verifier() -> AutoHarnessVerifier:
    return AutoHarnessVerifier()


# --------------------------------------------------------------------------
# What it soundly does
# --------------------------------------------------------------------------


def test_clean_code_passes(verifier: AutoHarnessVerifier) -> None:
    result = verifier.verify_code("x = 1 + 1\n")
    assert result.valid
    assert result.metadata["node_count"] > 0


def test_syntax_error_is_reported_not_raised(verifier: AutoHarnessVerifier) -> None:
    result = verifier.verify_code("def broken(:\n")
    assert not result.valid
    assert any("SyntaxError" in e for e in result.errors)


def test_node_count_limit_is_enforced() -> None:
    tight = AutoHarnessVerifier(max_ast_nodes=5)
    result = tight.verify_code("a = 1\nb = 2\nc = 3\nd = 4\ne = 5\n")
    assert not result.valid
    assert any("AST node count" in e for e in result.errors)


def test_complexity_limit_is_enforced() -> None:
    tight = AutoHarnessVerifier(max_cyclomatic_complexity=2)
    src = "if a:\n    pass\nif b:\n    pass\nif c:\n    pass\n"
    result = tight.verify_code(src)
    assert not result.valid
    assert any("complexity" in e.lower() for e in result.errors)


def test_complexity_is_reported_even_when_valid(verifier: AutoHarnessVerifier) -> None:
    """The metadata is the module's real signal, so it must be populated."""
    flat = verifier.verify_code("x = 1\n")
    branchy = verifier.verify_code("if a:\n    pass\nfor i in y:\n    pass\n")
    assert branchy.metadata["complexity"] > flat.metadata["complexity"]


def test_eval_and_exec_calls_are_blocked(verifier: AutoHarnessVerifier) -> None:
    assert not verifier.verify_code("eval('1+1')").valid
    assert not verifier.verify_code("exec('x=1')").valid


def test_exact_blocklisted_import_spelling_is_blocked(verifier: AutoHarnessVerifier) -> None:
    result = verifier.verify_code("from os import system\nsystem('x')\n")
    assert not result.valid
    assert any("os.system" in e for e in result.errors)


# --------------------------------------------------------------------------
# What it does NOT do -- these ACCEPT dangerous code, on purpose, documented
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("label", "source"),
    [
        ("idiomatic import os", "import os\nos.system('echo pwned')\n"),
        ("dunder import", "__import__('os').system('echo pwned')\n"),
        ("subprocess not blocklisted", "import subprocess\nsubprocess.run(['echo', 'x'])\n"),
        ("getattr indirection", "import os\ngetattr(os, 'sys' + 'tem')('echo pwned')\n"),
    ],
)
def test_known_bypasses_are_accepted(
    verifier: AutoHarnessVerifier, label: str, source: str
) -> None:
    """NOT A SAFETY BOUNDARY. Each of these executes arbitrary commands and passes.

    Failing here means someone hardened the check -- good, but the module
    docstring's measured table is now stale and must be corrected.
    """
    assert verifier.verify_code(source).valid, f"expected {label} to be accepted (see docstring)"


def test_blocklist_matches_literal_names_only(verifier: AutoHarnessVerifier) -> None:
    """The precise reason the bypasses work: `import os` yields alias 'os', not 'os.system'."""
    assert "os.system" in verifier.disallowed_imports
    assert "os" not in verifier.disallowed_imports


# --------------------------------------------------------------------------
# ExecutableAction wrapper
# --------------------------------------------------------------------------


def test_executable_action_delegates_to_its_verifier() -> None:
    action = ExecutableAction("clean", "x = 1\n")
    assert action.name == "clean"
    assert action.verify().valid


def test_executable_action_honours_injected_verifier() -> None:
    """A wrapper that ignored the injected verifier would still pass the test above."""
    tight = AutoHarnessVerifier(max_ast_nodes=1)
    action = ExecutableAction("clean", "x = 1\n", verifier=tight)
    assert not action.verify().valid
