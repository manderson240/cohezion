"""Discriminating tests for the TIDE problem-discovery registry (backlog item 73, 2026-06-07).

Unifies cohezion's scattered deterministic audit instruments under a template+iteration
framework (arXiv 2606.04743): a `ProblemTemplate` registry + `discover_problems(paths, *,
templates, exclude_known)` that runs them all and SUPPRESSES findings already in `exclude_known`
(TIDE iterative discovery — actioned problems don't re-surface). Report-only, deterministic.

Each test fails a plausible wrong impl:
  - an impl that runs only the first template → test_runs_all_templates,
  - an impl that ignores exclude_known → test_exclude_known_suppresses,
  - an impl that defaults to the real registry even when [] is passed → test_empty_registry,
  - an impl whose default registry does NOT wire the real instruments → test_default_templates_real.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from cohezion.compound.problem_discovery import (
    Problem,
    ProblemTemplate,
    default_templates,
    discover_problems,
)


def _const(findings: list[str]) -> Callable[[list[Path]], list[str]]:
    return lambda _paths: list(findings)


def _ident(f: object) -> str:
    return str(f)


_T_A = ProblemTemplate("classA", _const(["a1", "a2"]), _ident)
_T_B = ProblemTemplate("classB", _const(["b1"]), _ident)


def test_runs_all_templates() -> None:
    probs = discover_problems([], templates=[_T_A, _T_B])
    assert {p.problem_class for p in probs} == {"classA", "classB"}  # K templates → K classes
    assert {p.finding_id for p in probs} == {"classA:a1", "classA:a2", "classB:b1"}
    assert all(isinstance(p, Problem) for p in probs)


def test_exclude_known_suppresses() -> None:
    probs = discover_problems([], templates=[_T_A], exclude_known={"classA:a1"})
    # a1 is already known → SUPPRESSED; a2 is novel → surfaced.
    assert {p.finding_id for p in probs} == {"classA:a2"}


def test_empty_registry() -> None:
    assert discover_problems([], templates=[]) == []  # explicit empty registry → no scan


def test_default_templates_real() -> None:
    tmpls = default_templates()
    classes = {t.problem_class for t in tmpls}
    # the unification: the default registry wires the REAL scattered instruments.
    assert {"complexity_outlier", "nesting_outlier", "unsandboxed_exec"} <= classes
    assert len(tmpls) >= 5
