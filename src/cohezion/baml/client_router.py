"""BAML bridge for Cohezion LLM calls.

BAML (boundaryml/baml) is the prompt/typed-output DSL adopted 2026-09-08.
This module is the ONLY module allowed to import baml_client — call sites
use :func:`recommend_next_step` / :func:`recommend_next_step_async`, never
the generated client directly, so client wiring stays in one audited place.

Routing follows the AGENTS.md three-tier policy:
  - "local"  -> Lemonade OmniRouter (127.0.0.1:13305, OpenAI-compatible)
  - "cloud"  -> Ollama cloud (127.0.0.1:11434, OpenAI-compatible)
No API keys: local endpoints. api_key is a placeholder the endpoints ignore.

Hermetic testing: unit tests mock the generated client (no live network);
see tests/unit/test_baml_client.py. The static clients in baml_src are for
the BAML playground / local manual runs only.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from baml_client import b as _b
from baml_client.types import NextStep as _NextStep

__all__ = ["recommend_next_step", "recommend_next_step_async", "build_registry"]

_TIER_ENV = "COHEZION_BAML_TIER"


def build_registry(tier: str = "local") -> Any:
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
                "model": "deepseek-r1-0528-8b-FLM",
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
                "model": "deepseek-v4-pro:cloud",
            },
        )
        cr.set_primary("CohezionCloud")
    else:
        raise ValueError(f"unknown BAML tier: {tier!r} (expected 'local' or 'cloud')")
    return cr


def _tier() -> str:
    return os.environ.get(_TIER_ENV, "local")


def recommend_next_step(context: str, candidates: str) -> _NextStep:
    """Synchronous typed next-step recommendation via BAML.

    Returns the generated ``NextStep`` Pydantic model (action/rationale/risk_level).
    """
    return _b.RecommendNextStep(context, candidates, baml_options={"client_registry": build_registry(_tier())})  # type: ignore[attr-defined]


async def recommend_next_step_async(context: str, candidates: str) -> _NextStep:
    """Async typed next-step recommendation via BAML (for async call sites)."""
    return await _b.RecommendNextStep(context, candidates, baml_options={"client_registry": build_registry(_tier())})  # type: ignore[attr-defined]