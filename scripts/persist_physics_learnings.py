#!/usr/bin/env python3
"""
Persist Physics Laws Notebook learnings to SurrealDB.
Run with: python3 scripts/persist_physics_learnings.py
"""

import sys


sys.path.insert(0, "/home/mike-anderson/dev/cohezion/src")

import asyncio

from cohezion.core.persistence.surreal_client import (
    SurrealClient,
    UniverseNode,
)


async def persist_learnings():
    """Save physics notebook learnings to SurrealDB."""

    print("🔄 Persisting physics laws notebook learnings...", flush=True)

    db = SurrealClient()
    await db.connect()

    # Ensure schema is setup
    await db.setup_schema()

    # Learning 60: Marimo Process Management
    node60 = UniverseNode(
        id="learning_60",
        content="""
## Problem
Marimo processes get suspended (SIGTTOU) when backgrounded with &

## Solution
Use nohup with output redirect:
```bash
nohup uv run marimo run notebook.py --host 0.0.0.0 --port 8765 > /tmp/marimo.log 2>&1 &
```

## Root Cause
Marimo's interactive output triggers terminal stop signal when process tries to write to background terminal.""",
        node_type="learning",
        metadata={
            "learning_id": 60,
            "title": "Marimo Process Management",
            "tags": ["marimo", "process_management", "nohup", "terminal"],
        },
    )
    await db.store_node(node60)
    print("  ✓ Saved Learning 60: Marimo Process Management", flush=True)

    # Learning 61: Layperson Physics Communication
    node61 = UniverseNode(
        id="learning_61",
        content="""
## Pattern: Universe Storybook Style

For each physics concept:
1. **🏠 Think of it like...** - Relatable everyday analogy
2. **🌍 Why it matters** - Practical implications (bullet list)
3. **👉 One thing to remember** - Single memorable takeaway

## Examples
- Anthropic Selection: "You wake up on a planet with breathable air..."
- HIHO Coherence: "A radio dial finding the clearest station..."
- Multiverse: "A library with every possible book ever written..."

## Key Insight
Visual elements (emojis, cards, spacing) enhance retention.""",
        node_type="learning",
        metadata={
            "learning_id": 61,
            "title": "Layperson Physics Communication Pattern",
            "tags": [
                "communication",
                "layperson",
                "physics",
                "analogies",
                "universe_storybook",
            ],
        },
    )
    await db.store_node(node61)
    print("  ✓ Saved Learning 61: Layperson Physics Communication", flush=True)

    # Physics notebook journey record
    journey_node = UniverseNode(
        id="physics_laws_journey",
        content="Journey record for physics_laws_explorer",
        node_type="notebook_journey",
        metadata={
            "notebook_id": "physics_laws_explorer",
            "topic": "Why Are Physics Laws The Way They Are?",
            "approaches": [
                "mathematical_necessity",
                "anthropic_selection",
                "multiverse_selection",
                "hiho_flume_synthesis",
            ],
            "key_equations": [
                "Noether: Symmetry → Conservation",
                "Least Action: S = ∫L dt",
                "HIHO: max[C(Ψ,Φ)·(1-C(Ψ,Φ))] at C=0.5",
                "FLUME: dz/dt = f(z) + ∇C(z)",
            ],
            "visualization_dimensions": ["Energy", "Coherence", "Stability", "Novelty"],
            "coherence_final": 0.498,
        },
    )
    await db.store_node(journey_node)
    print("  ✓ Saved notebook journey record", flush=True)

    await db.close()
    print("\n✅ All learnings persisted to SurrealDB!", flush=True)


if __name__ == "__main__":
    asyncio.run(persist_learnings())
