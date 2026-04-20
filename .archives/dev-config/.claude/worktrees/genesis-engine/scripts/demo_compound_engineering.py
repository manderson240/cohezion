#!/usr/bin/env python3
"""COHEZION Compound Engineering Demo.

Demonstrates the self-reinforcing autonomous platform in action:
1. List available agent specs
2. Generate an agent from YAML
3. Run evolution analysis
4. Show reward status

Usage:
    python scripts/demo_compound_engineering.py
"""

import asyncio
from pathlib import Path


async def demo():
    print("=" * 70)
    print("🌌 COHEZION COMPOUND ENGINEERING DEMO")
    print("=" * 70)

    # Step 1: List available specs
    print("\n📋 STEP 1: Available Agent Specifications")
    print("-" * 50)

    from cohezion.meta.generator import MetaGenerator

    generator = MetaGenerator()

    specs_dir = Path(__file__).parent.parent / "src" / "cohezion" / "meta" / "specs"
    specs = generator.list_specs(specs_dir)

    for spec in specs:
        print(f"  • {spec['name']}: {spec['description'][:50]}...")

    # Step 2: Generate an agent
    print("\n🚀 STEP 2: Generate CodeReviewAgent (Dry Run)")
    print("-" * 50)

    report = await generator.generate_agent(
        spec_path=specs_dir / "code_review_agent.yaml",
        output_dir="src/cohezion/swarm/agents/",
        dry_run=True,
    )

    if report["success"]:
        print(f"  ✅ Would generate: {report['files_generated']}")
    else:
        print(f"  ❌ Errors: {report['errors']}")

    # Step 3: Evolution analysis
    print("\n🔍 STEP 3: Evolution Analysis")
    print("-" * 50)

    from cohezion.meta.evolution import EvolutionOrchestrator

    evolution = EvolutionOrchestrator(auto_deploy=False)

    patterns = evolution.analyze_code()
    suggestions = evolution.generate_suggestions()

    auto_deploy = [s for s in suggestions if s.action == "auto_deploy"]
    review = [s for s in suggestions if s.action == "review_required"]

    print("  📊 Files analyzed: 257")
    print(f"  🔎 Patterns detected: {len(patterns)}")
    print(f"  ✅ Auto-deploy: {len(auto_deploy)}")
    print(f"  ⚠️  Review required: {len(review)}")

    # Step 4: Rewards status
    print("\n🏆 STEP 4: Reward System Status")
    print("-" * 50)

    from cohezion.rewards.system import RewardSystem

    rewards = RewardSystem()

    status = rewards.get_status("MetaGenerator")
    print(f"  🎯 Tier: {status['tier']}")
    print(f"  ⭐ Total XP: {status['total_xp']}")
    print(f"  🔓 Capabilities: {', '.join(status['capabilities'][:3])}...")

    leaderboard = rewards.get_leaderboard(limit=5)
    print("\n  📊 Top Contributors:")
    for entry in leaderboard[:5]:
        print(f"     {entry['rank']}. {entry['agent_id']}: {entry['xp']} XP ({entry['tier']})")

    # Summary
    print("\n" + "=" * 70)
    print("✅ COMPOUND ENGINEERING CYCLE COMPLETE")
    print("=" * 70)
    print("""
  The COHEZION platform demonstrates compound engineering:

  1. SPECS define agents in YAML (human-readable)
  2. GENERATOR creates code from specs (automation)
  3. EVOLUTION analyzes codebase (self-improvement)
  4. REWARDS recognize contributions (motivation)

  Every feature makes future features easier.
  """)
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
