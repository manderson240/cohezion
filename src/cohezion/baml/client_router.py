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
from baml_client.type_builder import TypeBuilder
from baml_client.types import (
    CodeHarness,
    ExtractedEntity,
    ExtractedRelation,
    GoalSpecification,
    HardwareVitalsSnapshot,
    KanbanItem,
    ModelCardProfile,
    NextStep,
    RoutingDecision,
    SheafDirichletState,
    SubmissionStrategy,
    TaskClassificationResult,
    TaskInvariants,
    VaultGraphExtraction,
    VModelTrace,
)


__all__ = [
    "CodeHarness",
    "ExtractedEntity",
    "ExtractedRelation",
    "GoalSpecification",
    "HardwareVitalsSnapshot",
    "KanbanItem",
    "ModelCardProfile",
    "NextStep",
    "RoutingDecision",
    "SheafDirichletState",
    "SubmissionStrategy",
    "TaskClassificationResult",
    "TaskInvariants",
    "TypeBuilder",
    "VModelTrace",
    "VaultGraphExtraction",
    "audit_leaderboard_next_action",
    "audit_leaderboard_next_action_async",
    "build_registry",
    "classify_task_intent",
    "classify_task_intent_async",
    "decide_hardware_routing",
    "decide_hardware_routing_async",
    "derive_task_invariants",
    "derive_task_invariants_async",
    "evaluate_harmonic_sheaf",
    "evaluate_harmonic_sheaf_async",
    "extract_vault_graph",
    "extract_vault_graph_async",
    "extract_vault_graph_stream",
    "get_type_builder",
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
    cloud_timeout_ms = int(os.environ.get("COHEZION_BAML_TIMEOUT_MS", "120000"))
    local_timeout_ms = int(os.environ.get("COHEZION_BAML_LOCAL_TIMEOUT_MS", "60000"))

    if tier == "local":
        cr.add_llm_client(
            name="CohezionLocal",
            provider="openai-generic",
            options={
                "base_url": "http://127.0.0.1:13305/api/v1",
                "api_key": "local",
                "model": "qwen3-4b-FLM",
                "request_timeout_ms": local_timeout_ms,
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
                "request_timeout_ms": cloud_timeout_ms,
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
                "request_timeout_ms": local_timeout_ms,
            },
        )
        cr.add_llm_client(
            name="CohezionCloud",
            provider="openai-generic",
            options={
                "base_url": "http://127.0.0.1:11434/v1",
                "api_key": "local",
                "model": "deepseek-v4-flash:cloud",
                "request_timeout_ms": cloud_timeout_ms,
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


# -----------------------------------------------------------------------------
# 5. Neurosymbolic Knowledge Graph Extraction (Vault Graph Pipeline)
# -----------------------------------------------------------------------------
def extract_vault_graph(source_document: str, content: str) -> VaultGraphExtraction:
    """Extract structured knowledge graph from document synchronously via BAML."""
    return _b.ExtractVaultGraph(
        source_document,
        content,
        baml_options={"client_registry": build_registry(_tier())},
    )  # type: ignore[attr-defined]


async def extract_vault_graph_async(source_document: str, content: str) -> VaultGraphExtraction:
    """Extract structured knowledge graph from document asynchronously via BAML."""
    return await _async_b.ExtractVaultGraph(
        source_document,
        content,
        baml_options={"client_registry": build_registry(_tier())},
    )  # type: ignore[attr-defined]


def extract_vault_graph_stream(source_document: str, content: str) -> Any:
    """Stream structured knowledge graph extraction token-by-token."""
    return _async_b.stream.ExtractVaultGraph(
        source_document,
        content,
        baml_options={"client_registry": build_registry(_tier())},
    )  # type: ignore[attr-defined]


# -----------------------------------------------------------------------------
# 6. Task Intent Classification (APU Hardware Routing)
# -----------------------------------------------------------------------------
def classify_task_intent(task_description: str) -> TaskClassificationResult:
    """Classify task compute tier and output intent synchronously via BAML."""
    return _b.ClassifyTaskIntent(
        task_description,
        baml_options={"client_registry": build_registry(_tier())},
    )  # type: ignore[attr-defined]


async def classify_task_intent_async(
    task_description: str,
) -> TaskClassificationResult:
    """Classify task compute tier and output intent asynchronously via BAML."""
    return await _async_b.ClassifyTaskIntent(
        task_description,
        baml_options={"client_registry": build_registry(_tier())},
    )  # type: ignore[attr-defined]


# -----------------------------------------------------------------------------
# 7. Model Card Hardware Dispatch Routing
# -----------------------------------------------------------------------------
def decide_hardware_routing(
    task_type: str, input_tokens: int, required_modes: list[str]
) -> RoutingDecision:
    """Determine card-aligned hardware routing decision synchronously via BAML."""
    return _b.DecideHardwareRouting(
        task_type,
        input_tokens,
        required_modes,
        baml_options={"client_registry": build_registry(_tier())},
    )  # type: ignore[attr-defined]


async def decide_hardware_routing_async(
    task_type: str, input_tokens: int, required_modes: list[str]
) -> RoutingDecision:
    """Determine card-aligned hardware routing decision asynchronously via BAML."""
    return await _async_b.DecideHardwareRouting(
        task_type,
        input_tokens,
        required_modes,
        baml_options={"client_registry": build_registry(_tier())},
    )  # type: ignore[attr-defined]


# -----------------------------------------------------------------------------
# 8. Topological Cellular Sheaf Evaluation
# -----------------------------------------------------------------------------
def evaluate_harmonic_sheaf(stalk_values: str, restriction_maps: str) -> SheafDirichletState:
    """Evaluate cellular sheaf Dirichlet energy synchronously via BAML."""
    return _b.EvaluateHarmonicSheaf(
        stalk_values,
        restriction_maps,
        baml_options={"client_registry": build_registry(_tier())},
    )  # type: ignore[attr-defined]


async def evaluate_harmonic_sheaf_async(
    stalk_values: str, restriction_maps: str
) -> SheafDirichletState:
    """Evaluate cellular sheaf Dirichlet energy asynchronously via BAML."""
    return await _async_b.EvaluateHarmonicSheaf(
        stalk_values,
        restriction_maps,
        baml_options={"client_registry": build_registry(_tier())},
    )  # type: ignore[attr-defined]


# -----------------------------------------------------------------------------
# 9. Dynamic TypeBuilder Factory
# -----------------------------------------------------------------------------
def get_type_builder() -> TypeBuilder:
    """Create a fresh TypeBuilder instance for dynamic runtime schema adaptation."""
    return TypeBuilder()
