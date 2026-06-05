"""Recursive Trace Engine — v1.0

Closes the loop between LeWM latent space, Ouroboros failure detection, and Mycelium cross-universe knowledge synthesis.

Components:
  - RecursiveTraceLoop  (orchestrator with bounded recursion)
  - LatentStateTracker    (LeWM-encoded state search + retrieval)
  - OuborosBridge         (failure analysis → repair strategies)
  - MyceliumSynthesizer   (trace success → cross-universe cluster push)
  - TraceMemory           (temporal decay, pruning, cosine similarity store)

Invariants:
  - Per-action JSON lines written to ~/.cohezion-research/logs/traces.jsonl
  - Embeddings via Qwen3-Embedding-0.6B at lemonade-local :13305
  - Semantic threshold >= 0.72, max_depth=5, time_budget=180s (configurable)
  - Coherence decay: exp(-age_hours / half_life), default_half_life_hrs=48h

V-Model Phases completed or in-flight via this module init + patch pass pattern.
"""

from cohezion.recursive_trace.core import (
    LatentStateTracker,
    RecursiveTraceLoop,
    TraceMemory,
)


__all__: list[str] = [
    "LatentStateTracker",
    "RecursiveTraceLoop",
    "TraceMemory",
]
