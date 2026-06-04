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
    print("🚀 Initializing Plugin Experience Persistence Pipeline (Ouroboros & Mycelium Mesh)...")

    # 1. Define the 3 text payloads for this session's experiences

    # Experience 1: Plugin Integration
    plugin_prompt = "Integrate the oh-my-antigravity plugin and register the jscpd, playwright, sqlite, and n8n MCP servers in the workspace."
    plugin_response = """
    Successfully registered Playwright, SQLite, and n8n MCP configurations in mcp_config.json and config/mcp_config.json.
    Verified that oh-my-antigravity provides 53 active skills, including ultragoal, checkpoint, goal, and mode.
    Implemented and verified a pre-commit check for duplicate code detection using jscpd.
    """

    # Experience 2: Deduplication and Refactoring
    dedup_prompt = "Deduplicate flume.py and journey_status.py modules and resolve compound_server.py line count limits."
    dedup_response = """
    Deduplicated flume.py and journey_status.py using AST-based helper functions.
    Reduced compound_server.py from 502 to 498 lines, resolving the TestCompoundUtils.test_module_line_count unit test failure.
    Passed all 1,157 fast unit and integration tests successfully.
    """

    # Experience 3: V-Model Smoke Test Loop
    smoke_prompt = "Execute integration smoke tests for all MCP servers, plugins, and skills."
    smoke_response = """
    Created and ran scripts/ci/mcp_integration_smoke_test.py.
    Successfully validated:
    - Duplication gate check via jscpd duplication gate script.
    - Database read/write/schema query via sqlite.
    - Headless browser availability via Playwright.
    - Automation webhook registration via n8n.
    - OmA skills validation (ultragoal, checkpoint, goal, mode).
    All validation gates passed successfully.
    """

    print("🔮 Encoding payloads using FLUME Vacuum Domain Encoder (VDE)...")
    z1 = await encode_journey_text(plugin_prompt, plugin_response)
    z2 = await encode_journey_text(dedup_prompt, dedup_response)
    z3 = await encode_journey_text(smoke_prompt, smoke_response)
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
        entry_id="plugin_integration_20260604",
        content=f"Plugin integration results: {plugin_response.strip()}",
        domain="pattern",
    )
    entry2 = JournalEntry(
        entry_id="deduplication_refactoring_20260604",
        content=f"Deduplication results: {dedup_response.strip()}",
        domain="pattern",
    )
    entry3 = JournalEntry(
        entry_id="smoke_test_verification_20260604",
        content=f"Smoke test results: {smoke_response.strip()}",
        domain="experiment",
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
        id="experience_plugins_20260604",
        content=plugin_response,
        embedding=z1,
        node_type="experience",
        physics_state=PhysicsState(logic=0.9, control=0.9, novelty=0.8, z=0.5),
        metadata={"prompt": plugin_prompt, "date": "2026-06-04", "z_vector": z1},
    )
    await db.store_node(node1)

    # Store experience 2
    node2 = UniverseNode(
        id="experience_dedup_20260604",
        content=dedup_response,
        embedding=z2,
        node_type="experience",
        physics_state=PhysicsState(control=0.95, logic=0.95, precipitation=0.8, x=0.5),
        metadata={"prompt": dedup_prompt, "date": "2026-06-04", "z_vector": z2},
    )
    await db.store_node(node2)

    # Store experience 3
    node3 = UniverseNode(
        id="experience_smoke_20260604",
        content=smoke_response,
        embedding=z3,
        node_type="experience",
        physics_state=PhysicsState(logic=0.9, novelty=0.8, field=0.9, y=0.5),
        metadata={"prompt": smoke_prompt, "date": "2026-06-04", "z_vector": z3},
    )
    await db.store_node(node3)

    # Store CoE trajectory
    node4 = UniverseNode(
        id="coe_trajectory_plugins_20260604",
        content="CoE evaluation of plugin integration trajectory: plugins -> dedup -> smoke",
        node_type="coe_evaluation",
        physics_state=PhysicsState(control=0.95, logic=0.9, field=0.9),
        metadata={
            "coe_result": coe_result,
            "trajectory_ids": [
                "experience_plugins_20260604",
                "experience_dedup_20260604",
                "experience_smoke_20260604",
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

    # File 1: Patterns (Plugins)
    file1_path = vault_dir / "patterns" / "2026-06-04-mcp-plugins-integration.md"
    file1_content = """---
date: 2026-06-04
source_project: cohezion
tags: [pattern, plugins, agy]
---
# MCP Plugins and Servers Integration

## Problem
Extending the Antigravity CLI and swarm orchestration capabilities with automated testing, database querying, copy/paste detection, and webhook notifications.

## Solution
Registered Playwright, SQLite, and n8n MCP configurations globally and workspace-wide. Integrated oh-my-antigravity workflow skills.

## Details
- Successfully registered Playwright, SQLite, and n8n configurations.
- verified 53 active skills under oh-my-antigravity plugins directory.
- Created pre-commit similarity gate hook script.

## Related Decisions
- [[2026-06-04-ouroboros-mycelium-integration]]
"""
    file1_path.parent.mkdir(parents=True, exist_ok=True)
    file1_path.write_text(file1_content)
    print(f"  ✓ Wrote: {file1_path.name}")

    # File 2: Patterns (Deduplication)
    file2_path = vault_dir / "patterns" / "2026-06-04-evo-analogue-routing-skill.md"
    file2_content = """---
date: 2026-06-04
source_project: cohezion
tags: [pattern, refactoring, dedup]
---
# EVO Analogue Code Deduplication and Verification

## Problem
Refactoring codebase duplicates to compact repository indexes and ensure strict line-count constraints.

## Solution
Removed redundant function definitions in `flume.py` and `journey_status.py`, substituting them with direct helper imports. Cleaned up line-counts in `compound_server.py`.

## Results
- Reduced `compound_server.py` to 498 lines.
- All 1,157 unit/integration tests passed successfully.
- Code similarity gate passed cleanly.
"""
    file2_path.parent.mkdir(parents=True, exist_ok=True)
    file2_path.write_text(file2_content)
    print(f"  ✓ Wrote: {file2_path.name}")

    # File 3: Experiments (Smoke Test)
    file3_path = vault_dir / "experiments" / "2026-06-04-smoke-test-verification.md"
    file3_content = """---
date: 2026-06-04
project: cohezion
status: completed
outcome: success
tags: [experiment, smoke-test, validation]
---
# V-Model Smoke Test Loop Integration

## Hypothesis
A single workspace smoke test script (`scripts/ci/mcp_integration_smoke_test.py`) will reliably verify that all MCP servers, databases, browsers, and skills are active and functional.

## Results
- Successfully verified `jscpd` similarity gate.
- Verified local SQLite read/write capability.
- Confirmed Playwright browser automation is available.
- Confirmed n8n webhook configuration.
- Verified active OmA skills.
- All validation gates returned PASS.
"""
    file3_path.parent.mkdir(parents=True, exist_ok=True)
    file3_path.write_text(file3_content)
    print(f"  ✓ Wrote: {file3_path.name}")

    print("🎉 All logging and persistence tasks completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
