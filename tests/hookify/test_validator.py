"""Discriminating tests for HookifyValidator condition evaluation (V-model audit, 2026-06-05).

`hookify` was a no-test module (658-LOC validator.py, 4 external importers). The
highest-stakes logic is the condition evaluator — it gates rule actions and is a
SECURITY boundary (it refuses to evaluate dangerous expressions). Each test below is
written to fail the most plausible wrong implementation, not merely to prove a method
fires:
  - a no-op safety guard that returns True for everything,
  - a guard that SILENTLY treats unsafe input as False instead of raising,
  - an inverted comparison operator, AND-evaluated-as-OR,
  - a case-sensitive goal match, a crash on a non-numeric context value.
"""
from __future__ import annotations

import pytest

from cohezion.hookify.validator import HookifyValidator, Rule


@pytest.fixture
def v() -> HookifyValidator:
    return HookifyValidator(rules=[])  # DB/vault are lazy — construction is offline


# ---- security boundary (the centerpiece) ----------------------------------------


def test_is_safe_condition_blocks_dangerous_patterns(v: HookifyValidator) -> None:
    # Discriminates a no-op guard (returns True for all): each of these MUST be unsafe.
    for bad in ["os.system('rm')", "subprocess.run(x)", "eval('1')", "exec('x')",
                "__import__('os')", "import os"]:
        assert v._is_safe_condition(bad) is False, bad


def test_is_safe_condition_allows_legitimate_conditions(v: HookifyValidator) -> None:
    for ok in ["always", "coherence < 0.5", 'goal.contains("deploy")',
               "coherence > 0.1 AND coherence < 0.9"]:
        assert v._is_safe_condition(ok) is True, ok


def test_check_condition_RAISES_on_unsafe_not_silently_false(v: HookifyValidator) -> None:
    # The critical contract: an unsafe expression must raise ValueError, NOT be silently
    # swallowed as a benign False. A silent-False impl would hide an injection attempt.
    with pytest.raises(ValueError, match=r"[Uu]nsafe"):
        v._check_condition("os.system('rm -rf /')", {})


# ---- evaluation correctness -----------------------------------------------------


def test_numeric_comparison_operators_not_inverted(v: HookifyValidator) -> None:
    assert v._check_condition("coherence < 0.5", {"coherence": 0.3}) is True
    assert v._check_condition("coherence < 0.5", {"coherence": 0.7}) is False
    assert v._check_condition("coherence > 0.5", {"coherence": 0.7}) is True
    assert v._check_condition("coherence >= 0.5", {"coherence": 0.5}) is True


def test_and_requires_all_or_requires_any(v: HookifyValidator) -> None:
    # AND-as-OR is the classic bug: 0.05 satisfies "<0.9" but not ">0.1", so AND must be False.
    ctx_mid, ctx_low = {"coherence": 0.3}, {"coherence": 0.05}
    assert v._check_condition("coherence > 0.1 AND coherence < 0.9", ctx_mid) is True
    assert v._check_condition("coherence > 0.1 AND coherence < 0.9", ctx_low) is False
    assert v._check_condition("coherence < 0.1 OR coherence > 0.9", {"coherence": 0.95}) is True


def test_goal_contains_is_case_insensitive(v: HookifyValidator) -> None:
    # Discriminates a case-sensitive substring impl.
    assert v._check_condition('goal.contains("deploy")', {"goal": "DEPLOY the app"}) is True
    assert v._check_condition('goal.matches("deploy.*app")', {"goal": "Deploy the App"}) is True


def test_non_numeric_context_value_returns_false_not_crash(v: HookifyValidator) -> None:
    # context value is a string -> isinstance(int|float) fails -> falls through to False,
    # must not raise a TypeError comparing str to float.
    assert v._check_condition("coherence < 0.5", {"coherence": "high"}) is False


def test_always_is_true_and_unknown_is_false(v: HookifyValidator) -> None:
    assert v._check_condition("always", {}) is True
    assert v._check_condition("nonsense_unparseable", {}) is False


# ---- value parsing + public surface ---------------------------------------------


def test_parse_value_type_coercion(v: HookifyValidator) -> None:
    assert v._parse_value("true") is True          # identity, not == 1
    assert v._parse_value("False") is False
    assert v._parse_value("3.14") == 3.14 and isinstance(v._parse_value("3.14"), float)
    assert v._parse_value("5") == 5 and isinstance(v._parse_value("5"), int)
    assert v._parse_value('"quoted"') == "quoted"  # quotes stripped
    assert v._parse_value("bareword") == "bareword"


def test_list_and_get_rule_public_api() -> None:
    rule = Rule(id="r1", trigger="on_deploy", condition="always", action="warn")
    vv = HookifyValidator(rules=[rule])
    assert vv.list_rules() == ["r1"]
    assert vv.get_rule("r1") is rule
    assert vv.get_rule("missing") is None
