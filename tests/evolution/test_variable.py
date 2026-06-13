"""Discriminating tests for evolution.Variable (V-model audit, 2026-06-05).

`evolution` was a no-test module. Variable is its pure-logic core (TextGrad-style
trainable prompt component). Each test fails a plausible wrong impl:
  - add_gradient that appends unconditionally (no dedup, no empty-skip),
  - get_gradient_text that doesn't bullet-format,
  - __str__ that returns repr instead of the raw value (would corrupt prompt composition),
  - from_prime_section that drops require_grad.
"""

from __future__ import annotations

from cohezion.evolution.variable import Variable, from_prime_section


def test_add_gradient_dedups_and_skips_empty() -> None:
    # Discriminates an unconditional-append impl: duplicate and empty feedback are no-ops.
    v = Variable(name="intro", value="hello")
    v.add_gradient("be more specific")
    v.add_gradient("be more specific")  # duplicate -> ignored
    v.add_gradient("")  # empty -> ignored
    v.add_gradient("add an example")
    assert v.gradients == ["be more specific", "add an example"]


def test_get_gradient_text_bullet_formats() -> None:
    v = Variable(name="x", value="v")
    v.add_gradient("a")
    v.add_gradient("b")
    assert v.get_gradient_text() == "- a\n- b"


def test_reset_gradients_clears() -> None:
    v = Variable(name="x", value="v")
    v.add_gradient("a")
    v.reset_gradients()
    assert v.gradients == []
    assert v.get_gradient_text() == ""


def test_record_update_appends_history_entry() -> None:
    v = Variable(name="x", value="v")
    v.record_update("old", "new", "because reasons")
    assert v.history == [{"old": "old", "new": "new", "reasoning": "because reasons"}]


def test_str_returns_raw_value_not_repr() -> None:
    # Critical for prompt composition: str(variable) must be the value, not a Variable(...) repr.
    v = Variable(name="intro", value="You are a helpful agent.")
    assert str(v) == "You are a helpful agent."
    assert "Variable(" in repr(v) and "intro" in repr(v)


def test_from_prime_section_marks_trainable_by_default() -> None:
    var = from_prime_section("## Goal", "Optimize the loop")
    assert var.name == "## Goal" and var.value == "Optimize the loop"
    assert var.require_grad is True
    assert "PRIME skill section" in var.description
    # explicit opt-out
    assert from_prime_section("s", "c", require_grad=False).require_grad is False
