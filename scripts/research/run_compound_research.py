#!/usr/bin/env python3
"""Proactive research driver for Cohezion compound engineering.

Runs continuous research cycles to discover:
1. SOTA techniques for agentic AI gaps (Mythos benchmarks)
2. Token-efficient architectures for subagent orchestration
3. Novel compound patterns from latest research
4. GitHub tooling for distributed training and RL

Usage:
    # Single research cycle
    uv run python scripts/research/run_compound_research.py
    
    # Continuous mode (background research)
    uv run python scripts/research/run_compound_research.py --continuous --interval 3600
    
    # Focus on specific gaps
    uv run python scripts/research/run_compound_research.py --topics "SWE-bench" "GRPO training" "multi-agent"
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from cohezion.swarm.research_orchestrator import ResearchOrchestrator, run_research

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


# Cohezion-specific research topics mapped to current gaps
COHEZION_RESEARCH_TOPICS = {
    "mythos_coding": [
        "SWE-bench optimization",
        "automated debugging",
        "patch generation LLM",
        "code reasoning agents",
        "test-driven agent training",
    ],
    "mythos_cyber": [
        "CTF automation",
        "cybersecurity agents",
        "penetration testing AI",
        "vulnerability discovery",
        "exploit generation",
    ],
    "mythos_agentic": [
        "long-horizon task agents",
        "browser automation AI",
        "computer use agents",
        "autonomous benchmarking",
        "multi-step reasoning",
    ],
    "compound_engineering": [
        "multi-agent orchestration",
        "token-efficient subagents",
        "agent hierarchy patterns",
        "compound system design",
        "HIHO stable architectures",
    ],
    "training_infrastructure": [
        "distributed training optimization",
        "GRPO reinforcement learning",
        "model distillation",
        "LoRA fine-tuning",
        "RLHF training",
    ],
    "efficiency": [
        "LLM inference optimization",
        "KV cache compression",
        "speculative decoding",
        "model quantization",
        "token budget management",
    ],
}


async def research_cycle(
    focus_areas: list[str] | None = None,
    token_budget: int = 75000,
    save_to_skills: bool = True,
) -> dict[str, Any]:
    """Execute single research cycle.
    
    Args:
        focus_areas: Keys from COHEZION_RESEARCH_TOPICS (e.g., "mythos_coding")
        token_budget: Token budget for this cycle
        save_to_skills: Generate PRIME skill drafts
        
    Returns:
        Research results with actionable insights
    """
    # Select topics based on focus
    if focus_areas:
        topics = []
        for area in focus_areas:
            if area in COHEZION_RESEARCH_TOPICS:
                topics.extend(COHEZION_RESEARCH_TOPICS[area])
            else:
                topics.append(area)  # Treat as custom topic
    else:
        # Default: cover all mythos gaps + compound engineering
        topics = (
            COHEZION_RESEARCH_TOPICS["mythos_coding"][:3] +
            COHEZION_RESEARCH_TOPICS["mythos_cyber"][:2] +
            COHEZION_RESEARCH_TOPICS["compound_engineering"][:3]
        )
    
    logger.info(f"Starting Cohezion research cycle")
    logger.info(f"Focus: {focus_areas or 'default (mythos + compound)'}")
    logger.info(f"Topics: {topics}")
    
    # Run research
    orchestrator = ResearchOrchestrator(token_budget)
    results = await orchestrator.research_compound(
        topics=topics,
        output_format="prime_skills" if save_to_skills else "synthesis_only",
        max_findings_per_source=12,  # Token-efficient
    )
    
    # Log key insights
    logger.info(f"Cycle complete: {results['metadata']['total_findings']} findings")
    logger.info(f"Token efficiency: {results['metadata']['token_budget_used']:.1%}")
    logger.info(f"Top syntheses: {len(results['syntheses'])}")
    
    for synth in results['syntheses'][:3]:
        logger.info(f"  - {synth['id']}: {synth['type']} (confidence: {synth['confidence']:.0%})")
        
    return results


async def continuous_mode(
    interval_seconds: int = 3600,
    token_budget_per_cycle: int = 50000,
) -> None:
    """Run continuous research cycles.
    
    Rotates through focus areas to maintain broad coverage
    while staying within token budget.
    """
    cycle_count = 0
    focus_rotation = list(COHEZION_RESEARCH_TOPICS.keys())
    
    while True:
        cycle_count += 1
        focus = [focus_rotation[cycle_count % len(focus_rotation)]]
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Research Cycle #{cycle_count} - Focus: {focus[0]}")
        logger.info(f"{'='*60}")
        
        try:
            results = await research_cycle(
                focus_areas=focus,
                token_budget=token_budget_per_cycle,
            )
            
            # Brief analysis
            if results['syntheses']:
                logger.info(f"\n🔍 Top actionable insight:")
                top = results['syntheses'][0]
                logger.info(f"   {top['id']}: {top['description'][:150]}...")
                
        except Exception as e:
            logger.exception(f"Cycle {cycle_count} failed: {e}")
            
        logger.info(f"\nSleeping {interval_seconds}s until next cycle...")
        await asyncio.sleep(interval_seconds)


def analyze_research_output(results_file: Path) -> None:
    """Analyze past research results for patterns."""
    with open(results_file) as f:
        data = json.load(f)
        
    print(f"\n📊 Research Analysis: {results_file.name}")
    print(f"Date: {data['metadata']['timestamp']}")
    print(f"Topics: {', '.join(data['metadata']['topics'])}")
    print(f"Total findings: {data['metadata']['total_findings']}")
    
    # Source breakdown
    print(f"\nSources:")
    for source, findings in data['by_source'].items():
        print(f"  {source}: {len(findings)} items")
        
    # Top synthesis
    if data['syntheses']:
        print(f"\n💡 Top insights:")
        for s in data['syntheses'][:5]:
            print(f"  [{s['type'].upper()}] {s['id']}")
            print(f"      Confidence: {s['confidence']:.0%}")
            print(f"      Effort: {s['effort']}")
            print()


async def main():
    parser = argparse.ArgumentParser(
        description="Proactive research for Cohezion compound engineering"
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Run continuous research cycles",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=3600,
        help="Seconds between cycles (continuous mode)",
    )
    parser.add_argument(
        "--topics",
        nargs="+",
        help="Research topics or focus areas (e.g., mythos_coding, training_infrastructure)",
    )
    parser.add_argument(
        "--token-budget",
        type=int,
        default=75000,
        help="Token budget per research cycle",
    )
    parser.add_argument(
        "--analyze",
        type=Path,
        help="Analyze existing research results file",
    )
    parser.add_argument(
        "--no-skills",
        action="store_true",
        help="Skip PRIME skill generation",
    )
    
    args = parser.parse_args()
    
    if args.analyze:
        analyze_research_output(args.analyze)
        return 0
    
    if args.continuous:
        await continuous_mode(
            interval_seconds=args.interval,
            token_budget_per_cycle=args.token_budget,
        )
    else:
        # Single research cycle
        results = await research_cycle(
            focus_areas=args.topics,
            token_budget=args.token_budget,
            save_to_skills=not args.no_skills,
        )
        
        # Show actionable summary
        print(f"\n{'='*60}")
        print("RESEARCH CYCLE COMPLETE")
        print(f"{'='*60}")
        print(f"Token efficiency: {results['metadata']['token_budget_used']:.1%}")
        print(f"Findings: {results['metadata']['total_findings']}")
        print(f"Compound insights: {len(results['syntheses'])}")
        
        if results['syntheses']:
            print(f"\n🎯 Top actions for Cohezion:")
            for i, s in enumerate(results['syntheses'][:3], 1):
                print(f"\n{i}. [{s['type'].upper()}] {s['id']}")
                print(f"   Confidence: {s['confidence']:.0%} | Effort: {s['effort']}")
                print(f"   {s['description'][:120]}...")
                
        print(f"\n💾 Results saved to: data/research_orchestrator/")
        
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
