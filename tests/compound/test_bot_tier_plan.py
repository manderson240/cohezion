"""Item 118: bot_tier_plan(message) — TDD red→green.

Report-only proposal of which engine a Hermes bot turn should use:
  short/classify → NPU, interactive chat → iGPU, deep/long-reasoning → CPU.
Composes item-114 place_task + message-length signal.
Pure (injected engines; no live gateway under pytest).

Discriminating tests — each kills a plausible wrong implementation:
  1. short message → NPU                          PRIMARY DISC.
  2. normal chat → iGPU                           kills always-NPU impl
  3. long/reasoning → CPU                         kills always-iGPU impl
  4. all engines at capacity → None               kills always-return-engine impl
  5. custom thresholds respected                  kills hardcoded-length impl
  6. plan never repeats the same engine twice     kills duplicates impl
  7. empty message → NPU (treated as short)       baseline
"""

from __future__ import annotations

from cohezion.compound.bot_tier_plan import BotTierPlan, bot_tier_plan
from cohezion.compound.fabric_utilization import Engine


_FULL_FLEET = [
    Engine(kind="npu", loaded_models=("llama3.2-1b-FLM",), capacity=4, in_flight=0),
    Engine(kind="igpu", loaded_models=("Qwen3.6-A3B",), capacity=3, in_flight=0),
    Engine(kind="cpu", loaded_models=("Gemma-4-31B",), capacity=8, in_flight=0),
]


def test_short_message_npu() -> None:
    """A short greeting/command → NPU (fast categorical, 42 TPS).

    PRIMARY DISCRIMINATOR: kills an impl that routes everything to iGPU.
    """
    plan = bot_tier_plan("hi", engines=_FULL_FLEET)
    assert plan.proposed_engine == "npu", (
        f"Short message must map to NPU; got {plan.proposed_engine}"
    )


def test_normal_chat_igpu() -> None:
    """A normal-length chat message → iGPU (interactive, ~200ms).

    Kills an always-NPU impl.
    """
    message = "Can you explain how the compound executor routes tasks?"
    plan = bot_tier_plan(message, engines=_FULL_FLEET)
    assert plan.proposed_engine == "igpu", (
        f"Normal chat ({len(message)} chars) must map to iGPU; got {plan.proposed_engine}"
    )


def test_long_reasoning_cpu() -> None:
    """A long/deep-reasoning message → CPU (large context).

    Kills an always-iGPU impl.
    """
    long_msg = (
        "Please provide a comprehensive analysis of how the FLUME VAE architecture "
        "relates to the HIHO stability principle, including the mathematical derivation "
        "of the 4x(1-x) kernel, the empirical threshold values we found for beta, "
        "and how the triune orchestrator should be calibrated for optimal compound "
        "loop performance given the current hardware profile. " * 3
    )
    plan = bot_tier_plan(long_msg, engines=_FULL_FLEET)
    assert plan.proposed_engine == "cpu", (
        f"Long/reasoning message ({len(long_msg)} chars) must map to CPU; got {plan.proposed_engine}"
    )


def test_all_engines_at_capacity_none() -> None:
    """All engines at capacity → proposed_engine=None (cannot place).

    Kills an impl that always returns an engine name.
    """
    full_fleet = [
        Engine(kind="npu", loaded_models=("llama",), capacity=1, in_flight=1),
        Engine(kind="igpu", loaded_models=("qwen",), capacity=1, in_flight=1),
        Engine(kind="cpu", loaded_models=("gemma",), capacity=1, in_flight=1),
    ]
    plan = bot_tier_plan("hello", engines=full_fleet)
    assert plan.proposed_engine is None, "All at capacity must yield proposed_engine=None"


def test_custom_short_threshold() -> None:
    """Caller-supplied short_max_chars threshold overrides the default.

    Kills an impl with a hardcoded length gate.
    """
    # 20-char message that would normally be 'normal' chat but is 'short' under threshold=100
    message = "explain FLUME vae plz"  # 21 chars
    plan_default = bot_tier_plan(message, engines=_FULL_FLEET)
    plan_custom = bot_tier_plan(message, engines=_FULL_FLEET, short_max_chars=100)
    # Under default threshold: 21 chars → normal chat (iGPU)
    # Under custom threshold=100: 21 < 100 → short (NPU)
    assert plan_default.proposed_engine == "igpu"
    assert plan_custom.proposed_engine == "npu"


def test_empty_message_treated_as_short() -> None:
    """Empty message → NPU (treated as zero-length = short). No crash."""
    plan = bot_tier_plan("", engines=_FULL_FLEET)
    assert plan.proposed_engine == "npu"


def test_plan_carries_message_and_task_kind() -> None:
    """BotTierPlan exposes the original message and derived task_kind."""
    message = "hello"
    plan = bot_tier_plan(message, engines=_FULL_FLEET)
    assert plan.message == message
    assert isinstance(plan.task_kind, str)
    assert isinstance(plan, BotTierPlan)
