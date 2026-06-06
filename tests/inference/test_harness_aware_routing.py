"""Discriminating tests for harness-aware routing (2026-06-06, item 7, arXiv 2605.30621).

Lin et al. 2026: harness-BENEFIT is non-monotonic — the mid-tier gains most, and weak models
(NPU-1B) don't faithfully follow scaffolds, so keep NPU harness-free. select_harness encodes
that. Each test fails a plausible wrong impl:
  - one that hands the NPU a ReAct scaffold (the §rule-3 violation the paper warns against),
  - one that gives the mid-tier the SAME harness regardless of whether it's a tool task,
  - one that over-scaffolds the strong/cloud tier instead of going minimal.
"""
from __future__ import annotations

from cohezion.inference.task_classifier import Harness, classify_with_harness, select_harness


def test_npu_never_gets_react_scaffold() -> None:
    # THE central guarantee: a weak 1B model must never be handed a ReAct tool-loop.
    assert select_harness("npu", tool_task=True) is not Harness.REACT
    assert select_harness("npu", tool_task=False) is Harness.COT


def test_mid_tier_tool_task_gets_the_tool_loop() -> None:
    # The tier that benefits most (iGPU) gets ReAct — but only for tool/agentic tasks.
    assert select_harness("igpu_rocwmma", tool_task=True) is Harness.REACT
    assert select_harness("gpu", tool_task=True) is Harness.REACT  # classifier's binary "gpu"


def test_mid_tier_non_tool_task_stays_plain() -> None:
    # A non-tool task on the mid-tier does NOT get a tool-loop scaffold (over-scaffolding guard).
    assert select_harness("igpu", tool_task=False) is Harness.COT


def test_strong_tier_is_minimal() -> None:
    # Strong/deep tiers need less scaffold, not more.
    assert select_harness("cpu", tool_task=True) is Harness.MINIMAL
    assert select_harness("cloud", tool_task=True) is Harness.MINIMAL


def test_classify_with_harness_pairs_decision_and_harness() -> None:
    # Advisory pairing: returns the existing RouteDecision UNCHANGED + a harness recommendation.
    decision, harness = classify_with_harness("Reply with one word only.")
    assert decision.node == "npu"            # routing unchanged (CL invariants intact)
    assert harness is Harness.COT            # NPU → plain CoT, never ReAct
    d2, h2 = classify_with_harness("Write a python function to sort a list", tool_task=True)
    assert d2.node == "gpu" and h2 is Harness.REACT
