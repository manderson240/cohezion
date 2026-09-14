"""H5 exec-gate consolidation: the remaining LLM-code ``exec()`` sites route through
``safe_exec_globals`` and report gate refusals DISTINCTLY from ordinary synthesis failures.

Scope note: ``safe_exec`` is an availability / naive-import gate, NOT a sandbox (see its module
docstring). These tests assert that the gate is APPLIED at each site and that a refusal is
visible, not that hostile code is contained.

Every site test is discriminating: the payload succeeds under the raw ``{}`` globals these
sites used before (CPython auto-injects full builtins), so reverting a site to raw globals makes
its test fail.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from cohezion.compound.dual_loop_optimizer import DualLoopOptimizer
from cohezion.compound.safe_exec import gate_refusal, safe_exec_globals
from cohezion.inference.autoharness import CodeAsActionVerifier, HarnessAsPolicy


def _raise_from(code: str, g: dict) -> BaseException:
    try:
        exec(code, g)  # noqa: S102 — deliberate: testing the exec gate
    except BaseException as exc:
        return exc
    raise AssertionError("expected the exec'd code to raise")


# ── gate_refusal classifier ────────────────────────────────────────────────────


def test_gate_refusal_names_a_refused_import():
    exc = _raise_from("import os", safe_exec_globals())
    assert isinstance(exc, ImportError), "refusal must stay an ImportError for existing callers"
    assert gate_refusal(exc) == "import of 'os'"


def test_gate_refusal_names_a_withheld_builtin():
    exc = _raise_from("open('/etc/hostname')", safe_exec_globals())
    assert gate_refusal(exc) == "builtin 'open'"


def test_gate_refusal_ignores_an_undefined_user_name():
    """A typo in generated code is a synthesis failure, not the gate."""
    exc = _raise_from("undefined_helper_xyz()", safe_exec_globals())
    assert isinstance(exc, NameError)
    assert gate_refusal(exc) is None


def test_gate_refusal_ignores_a_genuinely_missing_allowlisted_module():
    """An ImportError raised by the real import machinery (not by the gate) is not a refusal."""
    exc = _raise_from("import numpy.no_such_submodule_xyz", safe_exec_globals())
    assert isinstance(exc, ImportError)
    assert gate_refusal(exc) is None


def test_gate_refusal_ignores_ordinary_exceptions():
    assert gate_refusal(ValueError("bad grid")) is None


# ── autoharness.CodeAsActionVerifier.verify ────────────────────────────────────

_IMPORTS_OS_VERIFIER = (
    "def is_legal_action(action: str) -> tuple[bool, str]:\n"
    "    import os\n"
    "    return True, os.name\n"
)


def _verifier_with(code: str) -> CodeAsActionVerifier:
    verifier = CodeAsActionVerifier("probe_env")
    verifier.active_code_id = verifier.search.add_hypothesis(code, "probe")
    return verifier


def test_raw_globals_would_run_the_payload():
    """Control: the payload DOES run under the pre-fix raw globals, so the site tests below
    can only pass because the gate is applied."""
    g: dict = {}
    exec(_IMPORTS_OS_VERIFIER, g)  # noqa: S102 — deliberate control for the discriminating tests
    assert g["is_legal_action"]("x")[0] is True


def test_verify_reports_gate_refusal_distinctly():
    ok, err = _verifier_with(_IMPORTS_OS_VERIFIER).verify("move_up")
    assert ok is False
    assert err.startswith("safe_exec gate refused import of 'os'"), err


def test_verify_still_reports_ordinary_errors_as_execution_errors():
    ok, err = _verifier_with("def is_legal_action(a):\n    raise ValueError('boom')\n").verify("x")
    assert ok is False
    assert err.startswith("Harness execution error: ValueError"), err


def test_verify_benign_generated_code_unchanged():
    """Availability: the shape of code the live model produced (re/json, pure logic) still runs."""
    code = (
        "import re\n"
        "def is_legal_action(action: str) -> tuple[bool, str]:\n"
        "    if re.fullmatch(r'move_(up|down|left|right)(:[1-3])?', action):\n"
        "        return True, ''\n"
        "    return False, 'bad move'\n"
    )
    verifier = _verifier_with(code)
    assert verifier.verify("move_up:2") == (True, "")
    assert verifier.verify("fly") == (False, "bad move")


# ── autoharness.HarnessAsPolicy ────────────────────────────────────────────────

_OPEN_POLICY = "def decide_action(context: dict) -> str:\n    return open('/etc/hostname').read()\n"


def test_policy_execute_applies_gate():
    policy = HarnessAsPolicy("probe_task")
    policy.compiled_code = _OPEN_POLICY
    assert policy.execute({"x": 1}) is None


@pytest.mark.asyncio
async def test_compile_policy_applies_gate():
    policy = HarnessAsPolicy("probe_task")
    policy.add_trace({"x": 1}, "right")
    policy._call_local_llm = AsyncMock(  # type: ignore[method-assign]
        return_value="import os\ndef decide_action(context: dict) -> str:\n    return 'right'\n"
    )
    assert await policy.compile_policy() is False
    assert policy.compiled_code is None


# ── dual_loop_optimizer.DualLoopOptimizer.optimize_cycle ──────────────────────


@pytest.mark.asyncio
async def test_dual_loop_reports_gate_refusal():
    synth = MagicMock()
    synth.synthesize_verifier = AsyncMock(
        return_value="import os\ndef verify_action(state, action):\n    return os.name != ''\n"
    )
    tracker = MagicMock()
    result = await DualLoopOptimizer(synth, benefit_tracker=tracker).optimize_cycle(
        skill_name="probe",
        environment_desc="any",
        policy_fn=lambda x: x,
        raw_score=0.5,
        dataset=[],
        metric_fn=lambda a, b: 1.0,
        dummy_env=lambda a: (True, ""),
    )
    assert result["gate_refused"] == "import of 'os'"


@pytest.mark.asyncio
async def test_dual_loop_benign_verifier_has_no_refusal():
    synth = MagicMock()
    synth.synthesize_verifier = AsyncMock(
        return_value="def verify_action(state, action):\n    return 0 < action <= state\n"
    )
    result = await DualLoopOptimizer(synth, benefit_tracker=MagicMock()).optimize_cycle(
        skill_name="probe",
        environment_desc="any",
        policy_fn=lambda x: x,
        raw_score=0.5,
        dataset=[],
        metric_fn=lambda a, b: 1.0,
        dummy_env=lambda a: (True, ""),
    )
    assert result["gate_refused"] is None
