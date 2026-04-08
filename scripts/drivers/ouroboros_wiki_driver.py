#!/usr/bin/env python3
"""Ouroboros + Wiki Integration Driver.

Runs the self-improvement loop with persistent wiki-based knowledge:
1. Monitor Cohezion executions for failures
2. Log failures to wiki (episodic memory)
3. Analyze patterns across failures
4. Generate rewrites and store in wiki (knowledge vault)
5. Use wiki queries to inform future rewrites (compounding)

Usage:
    python -m scripts.drivers.ouroboros_wiki_driver --vault ./.ouroboros-wiki
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

from cohezion.learning.ouroboros import ExecutionExhaust
from cohezion.ouroboros.wiki_integration import OuroborosWikiBridge, OuroborosWikiEngine


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("ouroboros-wiki")


class OuroborosWikiLoop:
    """Main loop integrating Ouroboros self-improvement with wiki persistence."""
    
    def __init__(self, vault_path: Path, target_coherence: float = 0.5):
        self.engine = OuroborosWikiEngine(
            target_coherence=target_coherence,
            vault_path=vault_path,
        )
        
        # Simulated monitoring state
        self.running = False
        self.cycles = 0
    
    async def run_cycle(self) -> dict:
        """Execute one Ouroboros cycle with wiki integration."""
        self.cycles += 1
        logger.info(f"=== Ouroboros Wiki Cycle #{self.cycles} ===")
        
        # In real implementation, this would monitor actual system
        # For demo, we simulate exhaust from various sources
        exhaust = self._simulate_exhaust()
        
        # Consume and potentially rewrite
        rewritten = await self.engine.consume_exhaust(exhaust)
        
        # Query accumulated knowledge
        lessons = await self.engine.wiki_bridge.query_lessons_learned(limit=5)
        
        return {
            "cycle": self.cycles,
            "exhaust_logged": exhaust.task_id,
            "rewritten": rewritten,
            "accumulated_lessons": len(lessons),
            "latest_rules": self.engine.get_latest_system_rules()[-3:],  # Last 3
        }
    
    async def run_continuous(
        self,
        interval_sec: float = 60.0,
        max_cycles: int | None = None,
    ) -> None:
        """Run continuous monitoring loop."""
        self.running = True
        logger.info(f"Starting Ouroboros Wiki Loop at {self.engine.wiki_bridge.vault_path}")
        
        try:
            while self.running:
                result = await self.run_cycle()
                logger.info(f"Cycle {result['cycle']}: {result}")
                
                if max_cycles and result["cycle"] >= max_cycles:
                    logger.info(f"Reached max_cycles ({max_cycles}), stopping.")
                    break
                    
                await asyncio.sleep(interval_sec)
                
        except KeyboardInterrupt:
            logger.info("Interrupted by user.")
            self.running = False
    
    def _simulate_exhaust(self) -> ExecutionExhaust:
        """Simulate execution exhaust for demo."""
        import random
        
        components = ["vault_mcp", "surreal_db", "swarm_orchestrator", "wiki_bridge"]
        errors = [
            "Connection timeout",
            "Coherence below threshold",
            "Token limit exceeded",
            "Parser error",
        ]
        
        component = random.choice(components)
        error = random.choice(errors)
        
        return ExecutionExhaust(
            task_id=f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.cycles}",
            error_message=error if random.random() < 0.3 else None,  # 30% chance of error
            coherence_drop=random.uniform(0.1, 0.5),
            token_usage=random.randint(1000, 10000),
            diagnostics={
                "component": component,
                "cycle": self.cycles,
                "severity": random.choice(["low", "medium", "high"]),
            },
        )
    
    async def generate_report(self) -> str:
        """Generate wiki-based report of improvements."""
        vault_path = self.engine.wiki_bridge.vault_path
        
        # Query all Ouroboros knowledge
        lessons = await self.engine.wiki_bridge.query_lessons_learned(limit=50)
        
        report = f"""# Ouroboros Wiki Report

Generated: {datetime.now().isoformat()}
Cycles Run: {self.cycles}
Total Rules: {len(self.engine.rewrite_history)}

## Recent Improvements
"""
        for rule in self.engine.get_latest_system_rules()[-5:]:
            report += f"- {rule}\n"
        
        report += "\n## Component Patterns\n"
        components = set()
        for lesson in lessons:
            for tag in lesson.get("tags", []):
                if tag not in ["ouroboros", "rewrite", "pattern", "exhaust"]:
                    components.add(tag)
        
        for comp in sorted(components):
            comp_lessons = [l for l in lessons if comp in l.get("tags", [])]
            report += f"- **{comp}**: {len(comp_lessons)} lessons learned\n"
        
        report += f"\n## Wiki Location\n{vault_path}\n"
        
        return report


async def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Ouroboros Wiki Integration")
    parser.add_argument(
        "--vault",
        type=Path,
        default=Path("data/ouroboros-wiki"),
        help="Path to wiki vault",
    )
    parser.add_argument(
        "--coherence",
        type=float,
        default=0.5,
        help="Target coherence threshold",
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=10,
        help="Number of cycles to run",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Seconds between cycles",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate report after running",
    )
    
    args = parser.parse_args()
    
    # Create vault directory
    args.vault.mkdir(parents=True, exist_ok=True)
    
    loop = OuroborosWikiLoop(
        vault_path=args.vault,
        target_coherence=args.coherence,
    )
    
    await loop.run_continuous(
        interval_sec=args.interval,
        max_cycles=args.cycles,
    )
    
    if args.report:
        report = await loop.generate_report()
        report_path = args.vault / "Ouroboros_Report.md"
        report_path.write_text(report)
        print(f"\nReport saved to: {report_path}")
        print(report)
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
