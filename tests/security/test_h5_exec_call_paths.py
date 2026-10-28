"""H5 through the REAL call paths: generated code must not reach import/open, yet must still run.

Each fixed site is exercised with two payloads, because a fix can fail in either direction:
  * HOSTILE   — module-level ``open()`` / ``import os`` that would leave an observable side effect.
                With ``exec(code, {})`` (the pre-fix code) the side effect happens.
  * LEGITIMATE — ``import numpy`` plus a helper function called from the entry point.
                A naive ``{"__builtins__": {}}`` "fix" kills this (finding F2), and split
                globals/locals hide the helper from the entry point.
Neither half alone discriminates: a patch passing only the hostile half is the F2 bug.

Honest scope: ``safe_exec`` is an availability gate plus a naive-import speed-bump, NOT a sandbox
(``collections._sys`` and gadget chains still escape — see safe_exec.py). These tests pin the
auto-injection hole shut at these call sites; they do not certify containment.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cohezion.competitions.arc.local_qwen_ast_proposer import test_proposed_code as run_proposal
from cohezion.compound.dual_loop_optimizer import DualLoopOptimizer
from cohezion.inference.autoharness import CodeAsActionVerifier, HarnessAsPolicy


def _hostile_payloads(marker: Path, entry: str, body: str) -> list[str]:
    """Two SEPARATE payloads. Combined, a failing open() aborts before `import os` runs, so the
    import gate would go untested (a mutant restoring the real __import__ stayed green)."""
    tail = f"def {entry}:\n    {body}\n"
    return [
        f"open({str(marker)!r}, 'w').write('pwned')\n" + tail,
        "import os\nos.environ['H5_PWNED'] = '1'\n" + tail,
    ]


def _legit(entry: str, body: str) -> str:
    return f"import numpy as np\ndef _helper(x):\n    return int(np.int64(x))\ndef {entry}:\n    {body}\n"


@pytest.fixture
def marker(tmp_path, monkeypatch):
    monkeypatch.delenv("H5_PWNED", raising=False)
    return tmp_path / "pwned.txt"


def _assert_contained(marker: Path) -> None:
    assert not marker.exists(), "generated code reached open() — H5 auto-injection is back"
    import os

    assert "H5_PWNED" not in os.environ, "generated code imported os — H5 auto-injection is back"


# ── local_qwen_ast_proposer.test_proposed_code ────────────────────────────────
_TASK = {"train": [{"input": [[1]], "output": [[1]]}], "test": [{"input": [[3]]}]}


def test_proposer_hostile_code_is_contained(marker):
    for code in _hostile_payloads(marker, "transform(grid)", "return grid"):
        assert run_proposal(code, _TASK) is None
    _assert_contained(marker)


def test_proposer_legitimate_numpy_helper_code_runs():
    code = _legit("transform(grid)", "return [[_helper(v) for v in row] for row in grid]")
    assert run_proposal(code, _TASK) == [[3]]


# ── inference.autoharness.CodeAsActionVerifier.verify ─────────────────────────
def _verifier_with(code: str) -> CodeAsActionVerifier:
    verifier = CodeAsActionVerifier("h5-test")
    verifier.active_code_id = verifier.search.add_hypothesis(code, "h5")
    return verifier


def test_verifier_hostile_code_is_contained(marker):
    for code in _hostile_payloads(marker, "is_legal_action(a)", "return True"):
        _verifier_with(code).verify("x")
    _assert_contained(marker)


def test_verifier_legitimate_numpy_helper_code_runs():
    verifier = _verifier_with(_legit("is_legal_action(a)", "return (_helper(len(a)) == 2, 'len')"))
    assert verifier.verify("ok") == (True, "len")
    assert verifier.verify("bad") == (False, "len")


# ── inference.autoharness.HarnessAsPolicy.execute ─────────────────────────────
def test_policy_hostile_code_is_contained(marker):
    for code in _hostile_payloads(marker, "decide_action(ctx)", "return 'noop'"):
        policy = HarnessAsPolicy("h5-test")
        policy.compiled_code = code
        policy.execute({})
    _assert_contained(marker)


def test_policy_legitimate_numpy_helper_code_runs():
    policy = HarnessAsPolicy("h5-test")
    policy.compiled_code = _legit("decide_action(ctx)", "return str(_helper(ctx['n']) * 2)")
    assert policy.execute({"n": 21}) == "42"


# ── compound.dual_loop_optimizer.DualLoopOptimizer.optimize_cycle ─────────────
def _run_cycle(verifier_code: str) -> tuple[list, dict]:
    """Runs the real optimize_cycle; a spy records the harness_fn the exec produced."""
    synthesizer = MagicMock()

    async def synthesize_verifier(desc, env):
        return verifier_code

    synthesizer.synthesize_verifier = synthesize_verifier
    optimizer = DualLoopOptimizer(synthesizer, benefit_tracker=MagicMock())
    seen: list = []
    real_eval = optimizer.evaluate_adherence_delta

    async def spy(**kwargs):
        seen.append(kwargs["harness_fn"])
        return await real_eval(**kwargs)

    optimizer.evaluate_adherence_delta = spy  # type: ignore[method-assign]  # spy only
    result = asyncio.run(
        optimizer.optimize_cycle(
            skill_name="h5",
            environment_desc="env",
            policy_fn=lambda state: 1,
            raw_score=0.0,
            dataset=[{"state": 1, "target": 1}],
            metric_fn=lambda action, target: float(action == target),
            dummy_env=lambda code: (True, ""),
        )
    )
    return seen, result


def test_dual_loop_hostile_verifier_is_contained(marker):
    for code in _hostile_payloads(marker, "verify_action(state, action)", "return True"):
        seen, _ = _run_cycle(code)
        assert seen == [None], "hostile verifier should fail to compile under restricted builtins"
    _assert_contained(marker)


def test_dual_loop_legitimate_numpy_helper_verifier_runs():
    seen, _ = _run_cycle(_legit("verify_action(state, action)", "return _helper(action) == 1"))
    assert len(seen) == 1 and callable(seen[0]), "legit verifier was not compiled (F2 regression)"
    assert seen[0](None, 1) is True


def test_dual_loop_harness_that_raises_does_not_abort_the_cycle():
    """A verifier that compiles but hits a GATE REFUSAL at call time (here: `getattr`, which
    the restricted namespace pins withheld) used to crash optimize_cycle. It must degrade to the
    unharnessed score and record `gate_refused`. Non-gate errors still propagate (policy: fail
    open ONLY on gate refusals -- see tests/compound/test_exec_gate_sites.py)."""
    code = "def verify_action(state, action):\n    return getattr(action, 'x')\n"
    seen, result = _run_cycle(code)
    assert len(seen) == 1 and callable(seen[0])
    assert result["harnessed_score"] == 1.0  # policy is correct; refused harness must not zero it
    assert result["gate_refused"]


# ── proposer: out-of-process containment + result validation (2026-09-19) ─────
def test_proposer_gadget_payload_is_contained_out_of_process(tmp_path):
    """The __subclasses__ reach is NOT refused by the allow-list; only a process boundary contains
    its payload. In-process this wrote the marker (that was the proposer's pre-wiring state)."""
    marker = tmp_path / "gadget"
    code = (
        "t = [c for c in ().__class__.__bases__[0].__subclasses__()"
        " if c.__module__ == 'os' and 'system' in c.__init__.__globals__][0]\n"
        f"t.__init__.__globals__['system']('echo x > {marker}')\n"
        "def transform(grid):\n    return grid\n"
    )
    run_proposal(code, _TASK)
    assert not marker.exists()


def test_proposer_rejects_forged_non_grid_result():
    code = (
        "import collections\nos = collections._sys.modules['os']\n"
        'os.write(1, b\'{"ok": true, "value": "FORGED"}\\n\')\nos._exit(0)\n'
        "def transform(grid):\n    return grid\n"
    )
    assert run_proposal(code, _TASK) is None


def test_proposer_train_mismatch_returns_none():
    assert run_proposal("def transform(grid):\n    return [[9]]\n", _TASK) is None


def test_proposer_syntax_error_returns_none():
    assert run_proposal("def transform(grid:\n", _TASK) is None


def test_proposer_non_syntax_parse_failures_return_none():
    assert run_proposal("\x00", _TASK) is None  # ast.parse raises ValueError, not SyntaxError
    assert run_proposal("(" * 100000 + ")" * 100000, _TASK) is None


def test_proposer_out_of_spec_grid_rejected():
    """A result outside the ARC spec (cell > 9 here) is rejected even though it is a list of ints."""
    assert (
        run_proposal("def transform(grid):\n    return [[99]] if grid == [[3]] else grid\n", _TASK)
        is None
    )
    assert (
        run_proposal(
            "def transform(grid):\n    return [[3] * 31] if grid == [[3]] else grid\n", _TASK
        )
        is None
    )
