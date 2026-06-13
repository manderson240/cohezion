#!/usr/bin/env python3
"""
Run the Autonomous Recursive Expansion Engine with full integration.

This script:
1. Checks Lemonade on port 13305
2. Verifies SurrealDB connection
3. Runs the recursive expansion loop
4. Propagates learnings to Mycelium
5. Validates via Ouroboros

Usage:
    python scripts/run_recursive_expansion.py --ticks 50 --phi-floor 0.3
    python scripts/run_recursive_expansion.py --daemon --checkpoint-every 10
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Ensure src is on path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cohezion.compound.autonomous_recursive_expansion_engine import (
    RecursiveExpansionEngine,
    create_expansion_engine,
)
from cohezion.compound.autonomous_recursive_expansion_engine import TickContext

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("recursive-expansion")


class RecursiveExpansionRunner:
    """CLI runner with full integration and monitoring."""
    
    def __init__(
        self,
        ticks: int = 50,
        phi_floor: float = 0.3,
        checkpoint_every: int = 10,
        vault_path: str = "cloud-vault-mcp/vault",
        daemon: bool = False,
    ):
        self.ticks = ticks
        self.phi_floor = phi_floor
        self.checkpoint_every = checkpoint_every
        self.vault_path = vault_path
        self.daemon = daemon
        
        self._engine: RecursiveExpansionEngine | None = None
        self._results: list[TickContext] = []
        self._shutdown_requested = False
        
    async def preflight(self) -> bool:
        """Check prerequisites: Lemonade, SurrealDB, Vault."""
        logger.info("=== PREFLIGHT CHECKS ===")
        
        # Check Lemonade on 13305
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "http://localhost:13305/api/v1/models",
                    timeout=5,
                ) as resp:
                    if resp.status == 200:
                        models = await resp.json()
                        logger.info(f"✓ Lemonade ready on :13305 ({len(models.get('data', []))} models)")
                    else:
                        logger.error("✗ Lemonade returned non-200 status")
                        return False
        except Exception as e:
            logger.error(f"✗ Lemonade not available on :13305: {e}")
            logger.info("  Start with: lemonade serve MODEL --port 13305")
            return False
            
        # Check SurrealDB on 8001
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://localhost:8001/sql",
                    json={"query": "INFO FOR DB"},
                    timeout=5,
                ) as resp:
                    if resp.status == 200:
                        logger.info("✓ SurrealDB ready on :8001")
                    else:
                        logger.warning("⚠ SurrealDB returned non-200 (will use vault-only persistence)")
        except Exception as e:
            logger.warning(f"⚠ SurrealDB not available: {e}")
            logger.info("  Continuing with vault-only persistence")
            
        # Check Vault
        vault = Path(self.vault_path) / "cerebellum"
        if vault.exists():
            existing = len(list(vault.glob("*.md")))
            logger.info(f"✓ Vault ready at {self.vault_path} ({existing} notes)")
        else:
            vault.mkdir(parents=True, exist_ok=True)
            logger.info(f"✓ Vault initialized at {self.vault_path}")
            
        return True
        
    async def run(self) -> list[TickContext]:
        """Execute the recursive expansion loop."""
        logger.info("=== RECURSIVE EXPANSION ENGINE START ===")
        logger.info(f"Configuration: ticks={self.ticks}, φ-floor={self.phi_floor}")
        
        self._engine = create_expansion_engine(
            engine_id=f"aree_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            vault_path=self.vault_path,
        )
        
        # Register callback for real-time monitoring
        self._engine.register_tick_callback(self._on_tick_complete)
        
        # Run the loop
        try:
            results = await self._engine.run_recursive_loop(
                max_ticks=self.ticks,
                phi_floor=self.phi_floor,
                checkpoint_every=self.checkpoint_every,
            )
            self._results = results
            return results
        except Exception as e:
            logger.error(f"Loop failed: {e}", exc_info=True)
            raise
            
    def _on_tick_complete(self, ctx: TickContext) -> None:
        """Callback for each tick completion."""
        logger.info(
            f"Tick {ctx.tick_id}: {ctx.phase.name} | "
            f"φ={ctx.phi_score:.3f} | coherence={ctx.coherence:.3f} | "
            f"memory={ctx.memory_pressure_mb:.0f}MB"
        )
        
        # Check for shutdown request
        if self._shutdown_requested:
            raise InterruptedError("Shutdown requested")
            
    async def postflight(self) -> dict:
        """Generate summary and export results."""
        logger.info("=== POSTFLIGHT SUMMARY ===")
        
        if not self._results:
            return {"error": "No results"}
            
        # Calculate metrics
        phi_scores = [r.phi_score for r in self._results]
        coherences = [r.coherence for r in self._results]
        
        summary = {
            "engine_id": self._engine.engine_id if self._engine else "unknown",
            "ticks_executed": len(self._results),
            "phi": {
                "mean": sum(phi_scores) / len(phi_scores),
                "min": min(phi_scores),
                "max": max(phi_scores),
                "final": phi_scores[-1],
            },
            "coherence": {
                "mean": sum(coherences) / len(coherences),
                "final": coherences[-1],
            },
            "scope": {
                "capabilities": list(self._engine.state.cumulative_scope.keys()) if self._engine else [],
                "mycelium_patterns": len(self._engine.state.mycelium_patterns) if self._engine else 0,
            },
            "vault_nodes": list(set(
                node for r in self._results for node in r.vault_nodes_accessed
            )),
        }
        
        # Write summary to vault
        if self._engine:
            summary_path = self._engine.vault.write_learning(
                tick_id="summary",
                content=json.dumps(summary, indent=2),
                tags=["aree", "summary", "metrics"],
            )
            logger.info(f"Summary written to: {summary_path}")
            
        # Print summary
        print("\n" + "=" * 60)
        print("RECURSIVE EXPANSION COMPLETE")
        print("=" * 60)
        print(f"Engine ID:     {summary['engine_id']}")
        print(f"Ticks:         {summary['ticks_executed']}")
        print(f"Mean φ:        {summary['phi']['mean']:.3f}")
        print(f"Final φ:       {summary['phi']['final']:.3f}")
        print(f"Capabilities:  {len(summary['scope']['capabilities'])}")
        print(f"Mycelium:      {summary['scope']['mycelium_patterns']} patterns")
        print("=" * 60)
        
        return summary
        
    def signal_shutdown(self) -> None:
        """Graceful shutdown handler."""
        logger.info("Shutdown signal received, completing current tick...")
        self._shutdown_requested = True


def main():
    parser = argparse.ArgumentParser(
        description="Run the Autonomous Recursive Expansion Engine",
    )
    parser.add_argument(
        "--ticks",
        type=int,
        default=50,
        help="Maximum ticks to execute (default: 50)",
    )
    parser.add_argument(
        "--phi-floor",
        type=float,
        default=0.3,
        help="Early exit threshold for φ (default: 0.3)",
    )
    parser.add_argument(
        "--checkpoint-every",
        type=int,
        default=10,
        help="Checkpoint interval (default: 10)",
    )
    parser.add_argument(
        "--vault-path",
        type=str,
        default="cloud-vault-mcp/vault",
        help="Path to Obsidian vault",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run continuously until interrupted",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    runner = RecursiveExpansionRunner(
        ticks=args.ticks,
        phi_floor=args.phi_floor,
        checkpoint_every=args.checkpoint_every,
        vault_path=args.vault_path,
        daemon=args.daemon,
    )
    
    # Signal handlers
    def signal_handler(sig, frame):
        runner.signal_shutdown()
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    async def run():
        # Preflight
        if not await runner.preflight():
            sys.exit(1)
            
        # Run expansion
        try:
            await runner.run()
        except InterruptedError:
            logger.info("Shutdown complete")
        except Exception as e:
            logger.error(f"Expansion failed: {e}")
            raise
            
        # Postflight
        summary = await runner.postflight()
        
        # Exit code based on success
        if summary["phi"]["final"] < args.phi_floor:
            sys.exit(2)  # Degeneration
        sys.exit(0)
        
    asyncio.run(run())


if __name__ == "__main__":
    main()
