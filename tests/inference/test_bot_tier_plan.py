"""Item 118: bot_tier_plan — TDD red→green (2026-06-08).

``bot_tier_plan(message)`` proposes which engine a bot turn should use:
- short/classify   → NPU   (fast categorical; cost-$0, 42 TPS)
- interactive chat → iGPU  (real-time quality; ~200ms)
- long/deep        → CPU   (parallel long-context; ~800ms)

Composes item-114 ``place_task`` affinity rules + the Hermes
``smart_model_routing`` length signal.  Pure (no live gateway).

Discriminating tests — each kills a plausible wrong implementation:

  1. Short message → NPU                     (kills "always return iGPU")
  2. Normal chat → iGPU                      (kills "always return NPU or CPU")
  3. Long/deep-reasoning message → CPU       (kills "ignore message length")
  4. Short and normal plans use diff engines  (kills "always same engine")
  5. Empty message → NPU (trivially classify) (kills "empty → error or iGPU")
  6. BotTierPlan has task_kind field         (kills "return bare string")
  7. Short message task_kind == 'classify'   (kills "wrong task_kind for NPU tier")
"""

from __future__ import annotations

from cohezion.inference.bot_tier import bot_tier_plan


def test_short_message_npu() -> None:
    """Short message (classify-tier) → NPU engine.

    PRIMARY DISCRIMINATOR: kills an impl that always returns iGPU.
    """
    plan = bot_tier_plan("Hi there")
    assert plan.engine == "npu", f"short message must → npu; got {plan.engine!r}"


def test_normal_chat_igpu() -> None:
    """Normal interactive chat → iGPU engine.

    Kills an impl that maps ALL messages to NPU or CPU.
    """
    plan = bot_tier_plan("What is the weather like in Seattle today? I'm planning a short trip.")
    assert plan.engine == "igpu", f"normal chat must → igpu; got {plan.engine!r}"


def test_long_deep_cpu() -> None:
    """Long deep-reasoning message → CPU (escalation tier).

    Kills an impl that ignores message length / complexity.
    """
    long_msg = (
        "Please provide a comprehensive analysis of the relationship between "
        "quantum mechanics and classical thermodynamics, covering the historical "
        "development of both fields, the key theoretical bridges such as "
        "statistical mechanics, decoherence, and entanglement entropy, and the "
        "current open questions in quantum thermodynamics. Include implications "
        "for information theory and the arrow of time. This is a deep analytical "
        "task requiring careful multi-step reasoning."
    )
    plan = bot_tier_plan(long_msg)
    assert plan.engine == "cpu", f"long/deep message must → cpu; got {plan.engine!r}"


def test_no_two_competing_tiers_same_engine() -> None:
    """Short (NPU) and normal (iGPU) plans → DIFFERENT engines.

    Kills an impl that routes all traffic to one engine.
    """
    short_plan = bot_tier_plan("ok")
    normal_plan = bot_tier_plan("What are the key differences between Python and Rust?")
    assert short_plan.engine != normal_plan.engine, (
        f"short and normal must route to different engines; both got {short_plan.engine!r}"
    )


def test_empty_message_npu() -> None:
    """Empty string → NPU (trivially the classify/short tier, no reasoning needed)."""
    plan = bot_tier_plan("")
    assert plan.engine == "npu", f"empty message must → npu; got {plan.engine!r}"


def test_plan_has_task_kind() -> None:
    """BotTierPlan exposes task_kind for observability."""
    plan = bot_tier_plan("Hello")
    assert hasattr(plan, "task_kind"), "BotTierPlan must expose task_kind"
    assert plan.task_kind in ("classify", "interactive", "deep-reasoning"), (
        f"task_kind must be a known tier; got {plan.task_kind!r}"
    )


def test_short_task_kind_is_classify() -> None:
    """Short message → task_kind == 'classify' (the NPU-affinity task from item 114).

    Kills an impl that uses NPU but names the task_kind incorrectly
    (breaking the item-114 compose contract).
    """
    plan = bot_tier_plan("Hello")
    assert plan.task_kind == "classify", (
        f"short message task_kind must be 'classify'; got {plan.task_kind!r}"
    )
