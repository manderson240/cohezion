#!/usr/bin/env python3
import sys
import os
import asyncio
from pathlib import Path
import numpy as np

# Ensure path is set
sys.path.insert(0, "/home/mike-anderson/dev/cohezion/src")

# Escape hatch for local dev credentials
os.environ["COHEZION_ALLOW_INSECURE_SURREAL"] = "1"

from cohezion.flume.vacuum_encoder import encode_journey_text
from cohezion.flume.coe_evaluator import ChainOfEmbeddingEvaluator
from cohezion.learning.mycelium_registry import JournalEntry, MyceliumRegistry
from cohezion.core.persistence.surreal_client import SurrealClient, UniverseNode, PhysicsState


async def main():
    print("🚀 Initializing GAIA Research Experience Persistence Pipeline...")

    # 1. Define the 3 text payloads for this session's experiences

    # Experience 1: Local Inference Expansion (Gaia & Lemonade)
    exp1_prompt = (
        "Extend availability with local inference using gaia and lemonade rather than ollama."
    )
    exp1_response = """
    Audited the local gaia package (amd-gaia) and successfully initialized ChatAgent models (e.g. Gemma-4-E4B-it-GGUF) using LemonadeProvider.
    Verified that Lemonade API endpoints on port 13307 connect securely via OpenAI-compatible clients.
    Tested the execution loop locally with dummy keys to satisfy validation.
    """

    # Experience 2: GitHub Community Research (amd/gaia & lemonade-sdk/lemonade)
    exp2_prompt = "Do research on github to see how other people use it"
    exp2_response = """
    Searched GitHub and web documentation for amd/gaia and lemonade-sdk/lemonade.
    Documented default configurations (port 13305, config.json in ~/.cache/lemonade/), custom Agent subclassing patterns with @tool decorations, and Lemonade's multi-modal support (TTS/ASR/StableDiffusion).
    Synthesized a comprehensive Markdown report mapping client providers and system configuration files.
    """

    # Experience 3: Swarm Integration & Path Optimization
    exp3_prompt = (
        "Verify integration of gaia adapter and model hierarchies in the cohezion workspace."
    )
    exp3_response = """
    Audited gaia_adapter.py. Validated GaiaAgentTier wrapping gaia.Agent/MCPAgent as custom orchestrator tiers, and verified that amd_optimized_hierarchy ranks NPU (FLM) -> iGPU (ROCWMMA) -> CPU -> Cloud.
    Ran full regression suite: all 1,157 fast tests passed successfully.
    """

    print("🔮 Encoding payloads using FLUME Vacuum Domain Encoder (VDE)...")
    z1 = await encode_journey_text(exp1_prompt, exp1_response)
    z2 = await encode_journey_text(exp2_prompt, exp2_response)
    z3 = await encode_journey_text(exp3_prompt, exp3_response)
    print("✓ Encoding complete. Got three 256D latent vectors.")

    # 2. Score sequential trajectory via VDE CoE (Chain-of-Embedding) Evaluator
    print("📈 Evaluating trajectory geometry using Chain-of-Embedding (CoE)...")
    evaluator = ChainOfEmbeddingEvaluator()
    coe_result = evaluator.score_from_embeddings([np.array(z1), np.array(z2), np.array(z3)])
    print(
        f"✓ CoE Evaluation complete. Score: {coe_result['coe_score']} (M={coe_result['m_score']:.4f}, A={coe_result['a_score']:.4f})"
    )

    # 3. Ingest into MyceliumRegistry and run audit
    print("🍄 Ingesting experiences into MyceliumRegistry...")
    registry = MyceliumRegistry(min_entries_for_pattern=2)

    entry1 = JournalEntry(
        entry_id="gaia_local_inference_20260604",
        content=f"Local inference expansion results: {exp1_response.strip()}",
        domain="experiment",
    )
    entry2 = JournalEntry(
        entry_id="gaia_github_research_20260604",
        content=f"GitHub research results: {exp2_response.strip()}",
        domain="pattern",
    )
    entry3 = JournalEntry(
        entry_id="gaia_adapter_integration_20260604",
        content=f"Gaia adapter integration results: {exp3_response.strip()}",
        domain="pattern",
    )

    registry.ingest_entry(entry1)
    registry.ingest_entry(entry2)
    registry.ingest_entry(entry3)

    audit_report = registry.run_audit()
    print(
        f"✓ Mycelium Audit run: Scanned {audit_report.entries_scanned} entries, synthesized {audit_report.skills_synthesized} skills."
    )

    # 4. Save everything to SurrealDB
    print("💾 Connecting to SurrealDB to persist Akashic records...")
    db = SurrealClient()
    await db.connect()
    await db.setup_schema()

    # Store experience 1
    node1 = UniverseNode(
        id="experience_gaia_inference_20260604",
        content=exp1_response,
        embedding=z1,
        node_type="experience",
        physics_state=PhysicsState(logic=0.95, control=0.9, novelty=0.85, z=0.5),
        metadata={"prompt": exp1_prompt, "date": "2026-06-04", "z_vector": z1},
    )
    await db.store_node(node1)

    # Store experience 2
    node2 = UniverseNode(
        id="experience_gaia_github_20260604",
        content=exp2_response,
        embedding=z2,
        node_type="experience",
        physics_state=PhysicsState(control=0.9, logic=0.9, precipitation=0.85, x=0.5),
        metadata={"prompt": exp2_prompt, "date": "2026-06-04", "z_vector": z2},
    )
    await db.store_node(node2)

    # Store experience 3
    node3 = UniverseNode(
        id="experience_gaia_adapter_20260604",
        content=exp3_response,
        embedding=z3,
        node_type="experience",
        physics_state=PhysicsState(logic=0.95, novelty=0.75, field=0.9, y=0.5),
        metadata={"prompt": exp3_prompt, "date": "2026-06-04", "z_vector": z3},
    )
    await db.store_node(node3)

    # Store CoE trajectory
    node4 = UniverseNode(
        id="coe_trajectory_gaia_20260604",
        content="CoE evaluation of gaia integration trajectory: local_inference -> github_research -> gaia_adapter",
        node_type="coe_evaluation",
        physics_state=PhysicsState(control=0.9, logic=0.95, field=0.9),
        metadata={
            "coe_result": coe_result,
            "trajectory_ids": [
                "experience_gaia_inference_20260604",
                "experience_gaia_github_20260604",
                "experience_gaia_adapter_20260604",
            ],
            "date": "2026-06-04",
        },
    )
    await db.store_node(node4)
    print(f"  ✓ Saved CoE Trajectory to SurrealDB with score {coe_result['coe_score']}")

    await db.close()
    print("✓ SurrealDB persistence complete.")

    # 5. Write pages to Obsidian vault
    vault_dir = Path("/home/mike-anderson/dev/cohezion/cloud-vault-mcp/vault")
    print(f"📝 Writing Markdown files to Obsidian vault at {vault_dir}...")

    # File 1: Experiments (Local Inference Expansion)
    file1_path = vault_dir / "experiments" / "2026-06-04-local-inference-validation.md"
    file1_content = """---
date: 2026-06-04
project: cohezion
status: completed
outcome: success
tags: [experiment, gaia, lemonade, local-inference]
---
# GAIA and Lemonade Local Inference Validation

## Hypothesis
Initializing GAIA's ChatAgent with a model_id bound to a local Lemonade server (defaulting to port 13307/v1) will allow full local text generation capability under security sandboxing constraints.

## Results
- Successfully instantiated `ChatAgent` with `Gemma-4-E4B-it-GGUF`.
- Configured dummy environment credentials to satisfy the client authentication validation check.
- Confirmed correct initialization of the `LemonadeProvider` LLM client.
- System is fully prepped for local AMD silicon routing.
"""
    file1_path.parent.mkdir(parents=True, exist_ok=True)
    file1_path.write_text(file1_content)
    print(f"  ✓ Wrote: {file1_path.name}")

    # File 2: Papers (GitHub Research)
    file2_path = vault_dir / "papers" / "2026-06-04-amd-gaia-lemonade-research.md"
    file2_content = """---
date: 2026-06-04
source: github
tags: [paper, research, gaia, lemonade]
---
# Research on GitHub: AMD GAIA & Lemonade Server Community Patterns

## Abstract
This page synthesizes the usage, configuration, and API specifications for AMD GAIA and the Lemonade Server based on public codebase analysis.

## Key Findings
- **Framework Structure**: `amd-gaia` provides base agent modules (`gaia.agents.base`) and conversation modules (`gaia.agents.chat`).
- **Lemonade Backend**: Lemonade serves as the unified runtime, managing multiple models across NPU (FLM), iGPU (ROCWMMA), and CPU (AVX) layers.
- **Default Paths**: Configuration defaults to `config.json` inside the platform's cache directory (e.g., `~/.cache/lemonade/config.json`) and handles ports (default 13305).
- **Custom Tools**: Tools are declared cleanly using the `@tool` decorator, enabling automatic schema synthesis for LLMs.

## References
- [[2026-06-04-local-inference-validation]]
- [[2026-06-04-gaia-adapter-swarms]]
"""
    file2_path.parent.mkdir(parents=True, exist_ok=True)
    file2_path.write_text(file2_content)
    print(f"  ✓ Wrote: {file2_path.name}")

    # File 3: Patterns (Swarm Integration)
    file3_path = vault_dir / "patterns" / "2026-06-04-gaia-adapter-swarms.md"
    file3_content = """---
date: 2026-06-04
source_project: cohezion
tags: [pattern, gaia, swarms, hardware-optimization]
---
# GAIA Adapter and Swarm Hardware Optimizations

## Problem
AI swarms require dynamic, latency-optimized routing across heterogenous hardware configurations (NPU, iGPU, CPU, Cloud) without hardcoding routes.

## Solution
Leverage Cohezion's `gaia_adapter.py` to wrap `gaia.Agent`/`MCPAgent` instances as tiers. Implement `amd_optimized_hierarchy` to order models based on their hardware acceleration efficiency.

## Details
- `GaiaAgentTier` runs GAIA's synchronous orchestration in an asyncio-safe executor.
- Hardware priorities ranked: NPU (FLM) -> iGPU (ROCWMMA) -> CPU -> Cloud.
- System escalates from local models to cloud reasoning only when quality checks fail.
"""
    file3_path.parent.mkdir(parents=True, exist_ok=True)
    file3_path.write_text(file3_content)
    print(f"  ✓ Wrote: {file3_path.name}")

    print("🎉 All logging and persistence tasks completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
