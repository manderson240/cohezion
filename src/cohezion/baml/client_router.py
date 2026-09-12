"""BAML bridge for Cohezion LLM calls.

BAML (boundaryml/baml) is the prompt/typed-output DSL adopted 2026-09-08.
This module is the ONLY module allowed to import baml_client — call sites
use the typed functions defined here, never the generated client directly,
so client wiring stays in one audited place.

Routing follows the AGENTS.md three-tier policy:
  - "local"   -> Lemonade OmniRouter (127.0.0.1:13305, OpenAI-compatible)
  - "cloud"   -> Ollama cloud (127.0.0.1:11434, OpenAI-compatible)
  - "hybrid"  -> Fallback cascade: Lemonade Local primary -> Ollama Cloud fallback
No API keys: local endpoints. api_key is a placeholder the endpoints ignore.

Hermetic testing: unit tests mock the generated client (no live network);
see tests/unit/test_baml_client.py. The static clients in baml_src are for
the BAML playground / local manual runs only.
"""

from __future__ import annotations

import os
from typing import Any

from baml_client import b as _b
from baml_client.async_client import b as _async_b
from baml_client.types import (
    CodeHarness,
    NextStep,
    SubmissionStrategy,
    TaskInvariants,
)


__all__ = [
    "CodeHarness",
    "NextStep",
    "SubmissionStrategy",
    "TaskInvariants",
    "audit_leaderboard_next_action",
    "audit_leaderboard_next_action_async",
    "build_registry",
    "derive_task_invariants",
    "derive_task_invariants_async",
    "recommend_next_step",
    "recommend_next_step_async",
    "synthesize_code_harness",
    "synthesize_code_harness_async",
]

_TIER_ENV = "COHEZION_BAML_TIER"


def build_registry(tier: str = "hybrid") -> Any:
    """Build a ClientRegistry routing to the requested Cohezion tier.

    Returns a baml_py.ClientRegistry; raises ValueError on unknown tier.
    """
    from baml_py import ClientRegistry

    cr = ClientRegistry()
    if tier == "local":
        cr.add_llm_client(
            name="CohezionLocal",
            provider="openai-generic",
            options={
                "base_url": "http://127.0.0.1:13305/api/v1",
                "api_key": "local",
                "model": "qwen3-4b-FLM",
                "request_timeout_ms": 60000,
            },
        )
        cr.set_primary("CohezionLocal")
    elif tier == "cloud":
        cr.add_llm_client(
            name="CohezionCloud",
            provider="openai-generic",
            options={
                "base_url": "http://127.0.0.1:11434/v1",
                "api_key": "local",
                "model": "deepseek-v4-flash:cloud",
                "request_timeout_ms": 60000,
            },
        )
        cr.set_primary("CohezionCloud")
    elif tier == "hybrid":
        cr.add_llm_client(
            name="CohezionLocal",
            provider="openai-generic",
            options={
                "base_url": "http://127.0.0.1:13305/api/v1",
                "api_key": "local",
                "model": "qwen3-4b-FLM",
                "request_timeout_ms": 60000,
            },
        )
        cr.add_llm_client(
            name="CohezionCloud",
            provider="openai-generic",
            options={
                "base_url": "http://127.0.0.1:11434/v1",
                "api_key": "local",
                "model": "deepseek-v4-flash:cloud",
                "request_timeout_ms": 60000,
            },
        )
        cr.add_llm_client(
            name="CohezionHybrid",
            provider="fallback",
            options={
                "strategy": ["CohezionLocal", "CohezionCloud"],
            },
        )
        cr.set_primary("CohezionHybrid")
    else:
        raise ValueError(f"unknown BAML tier: {tier!r} (expected 'local', 'cloud', or 'hybrid')")
    return cr


def _tier() -> str:
    return os.environ.get(_TIER_ENV, "hybrid")


# -----------------------------------------------------------------------------
# 1. Next Step Recommendation (Mandate #7)
# -----------------------------------------------------------------------------
def recommend_next_step(context: str, candidates: str) -> NextStep:
    """Synchronous typed next-step recommendation via BAML.

    Returns the generated ``NextStep`` Pydantic model (action/rationale/risk_level).
    """
    return _b.RecommendNextStep(
        context, candidates, baml_options={"client_registry": build_registry(_tier())}
    )  # type: ignore[attr-defined]


async def recommend_next_step_async(context: str, candidates: str) -> NextStep:
    """Async typed next-step recommendation via BAML (for async call sites)."""
    return await _async_b.RecommendNextStep(
        context, candidates, baml_options={"client_registry": build_registry(_tier())}
    )  # type: ignore[attr-defined]


# -----------------------------------------------------------------------------
# 2. ARC & AIMO Task Invariants Derivation (AutoHarness arXiv:2603.03329v1)
# -----------------------------------------------------------------------------
def derive_task_invariants(task_context: str, train_examples: str) -> TaskInvariants:
    """Derive structural invariants (grid shape, color conservation, symmetry) synchronously."""
    return _b.DeriveTaskInvariants(
        task_context, train_examples, baml_options={"client_registry": build_registry(_tier())}
    )  # type: ignore[attr-defined]


async def derive_task_invariants_async(task_context: str, train_examples: str) -> TaskInvariants:
    """Derive structural invariants asynchronously."""
    return await _async_b.DeriveTaskInvariants(
        task_context, train_examples, baml_options={"client_registry": build_registry(_tier())}
    )  # type: ignore[attr-defined]


# -----------------------------------------------------------------------------
# 3. Deterministic Code Harness Synthesis (AutoHarness Code-as-Action Verifiers)
# -----------------------------------------------------------------------------
def synthesize_code_harness(env_spec: str, failure_trace: str) -> CodeHarness:
    """Synthesize deterministic Python code harness verifier synchronously."""
    return _b.SynthesizeCodeHarness(
        env_spec, failure_trace, baml_options={"client_registry": build_registry(_tier())}
    )  # type: ignore[attr-defined]


async def synthesize_code_harness_async(env_spec: str, failure_trace: str) -> CodeHarness:
    """Synthesize deterministic Python code harness verifier asynchronously."""
    return await _async_b.SynthesizeCodeHarness(
        env_spec, failure_trace, baml_options={"client_registry": build_registry(_tier())}
    )  # type: ignore[attr-defined]


# -----------------------------------------------------------------------------
# 4. Kaggle Leaderboard Audit & Next Action
# -----------------------------------------------------------------------------
def audit_leaderboard_next_action(
    competition: str, leaderboard_snapshot: str
) -> SubmissionStrategy:
    """Audit leaderboard snapshot and recommend optimal next submission action synchronously."""
    return _b.AuditLeaderboardNextAction(
        competition, leaderboard_snapshot, baml_options={"client_registry": build_registry(_tier())}
    )  # type: ignore[attr-defined]


async def audit_leaderboard_next_action_async(
    competition: str, leaderboard_snapshot: str
) -> SubmissionStrategy:
    """Audit leaderboard snapshot and recommend optimal next submission action asynchronously."""
    return await _async_b.AuditLeaderboardNextAction(
        competition, leaderboard_snapshot, baml_options={"client_registry": build_registry(_tier())}
    )  # type: ignore[attr-defined]
