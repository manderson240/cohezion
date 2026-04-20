#!/usr/bin/env python3
"""Test Genesis Engine Compound Executor."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cohezion.compound.executor import CompoundExecutor, ExecutorFactory
from cohezion.core.mcp_client import MCPClient, MCPConfig
from cohezion.registry.skill_registry import search_skills

def test_skill_lookup():
    """Test skill registry queries."""
    print("\n--- Testing Skill Registry ---")

    # Search for AMD-related skills
    results = search_skills("AMD optimization")
    print(f"Found {len(results)} skills for 'AMD optimization':")
    for r in results[:3]:
        print(f"  - {r['name']}: {r['description'][:60]}...")

    # Search for compound engineering
    results = search_skills("compound engineering")
    print(f"\nFound {len(results)} skills for 'compound engineering':")
    for r in results[:3]:
        print(f"  - {r['name']}: {r['description'][:60]}...")

def test_compound_executor():
    """Test compound executor initialization."""
    print("\n--- Testing Compound Executor ---")

    # Create config
    config = MCPConfig(
        server_url="http://localhost:8360",
        api_key="cohezion-dev-key",
    )

    # Create MCP client
    mcp_client = MCPClient(config)

    # Create executor with full features
    executor = CompoundExecutor(
        mcp_client=mcp_client,
        enable_skill_refinement=True,
        enable_guardrails=True,
        enable_alignment_analysis=True,
    )

    print(f"Executor created successfully")
    print(f"  - Skill refiner: {executor.skill_refiner is not None}")
    print(f"  - Guardrails: {executor.guardrail_pipeline is not None}")
    print(f"  - Alignment analyzer: {executor.alignment_analyzer is not None}")

    # Test skill suggestion
    print("\n--- Testing Skill Suggestion ---")
    suggestions = executor.suggest_skills(
        task_description="Optimize AMD GPU kernels for MoE inference",
        operation_type="generate",
        project="genesis-engine",
        top_k=3
    )
    print(f"Suggested {len(suggestions)} skills:")
    for skill, score in suggestions:
        print(f"  - {skill}: {score:.3f}")

    # Test experience guidance
    print("\n--- Testing Experience Guidance ---")
    guidance = executor.get_experience_guidance(
        task_description="AMD GPU kernel optimization",
        project="genesis-engine"
    )
    print(f"Guidance keys: {list(guidance.keys())}")

    print("\n✅ All tests passed!")

def main():
    print("=" * 60)
    print("GENESIS ENGINE COMPONENT TEST")
    print("=" * 60)

    test_skill_lookup()
    test_compound_executor()

    print("\n" + "=" * 60)
    print("🚀 Genesis Engine components are operational!")
    print("=" * 60)

if __name__ == "__main__":
    main()
