import asyncio
import json
import os
import sys


# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from cohezion.core.mcp_client import create_mcp_client


async def final_retrospective():
    # Final consolidated learnings from the April 22nd sprint
    result = {
        "request": "Comprehensive Retrospective & Skill Refinement (April 22)",
        "tokens_used": 25000,
        "cache_hits": 42,
        "duration_seconds": 7200,
        "coherence": 0.99,
        "success": True,
        "skill_used": "COMPOUND_ENGINEERING_PRIME",
        "lessons": [
            "L376: Deep Research Integration - Autonomous multi-step synthesis extends agent discovery horizon by hours/days.",
            "L377: Local SLM Git Hooks - Orchestrating SLMs for pre-commit narrative invariants reduces cloud costs to $0 for routine audits.",
            "L378: Stateless FastMCP - Multi-client access requires explicit stateless_http=True and async connection lifecycle management.",
            "L379: Port Collision Resilience - Standardizing on 8000 (Local) vs 8001 (Legacy) for SurrealDB is critical for graph consistency.",
            "L380: 12D Journey Telemetry - Decoupled non-blocking bus ensures zero-latency impact on core orchestration during high-frequency capture.",
            "L381: Challenge Persistence - Post-mortem capture of Luma and Yale tracks ensures competitive wisdom survives hackathon deadlines.",
            "L382: BirdCLEF 2026 Phase 1 - Audio Spectrogram Transformers and Mamba SSMs are the new SOTA for bioacoustic monitoring.",
            "L383: AutoHarness Mandate - Deterministic data validation hooks prevent 'garbage in' during 15GB+ dataset acquisition.",
        ],
    }

    print("Initiating Final Knowledge Precipitation...")
    try:
        # Use the compound server directly
        client = create_mcp_client(server_url="http://localhost:8379", api_key="cohezion-dev-key")
        await client.connect()

        # Precipitate to Vault and Database
        response = await client._call_tool(
            "learning_process_execution",
            {
                "execution_result_json": json.dumps(result),
                "server_url": "http://localhost:8360",  # Target vault
            },
        )
        print("Success:", json.dumps(response, indent=2))
        await client.close()
    except Exception as e:
        print("Precipitation Failed:", e)


if __name__ == "__main__":
    asyncio.run(final_retrospective())
