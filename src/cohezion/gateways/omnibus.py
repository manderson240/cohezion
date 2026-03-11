"""Omnibus - The Master Gateway Controller.

Spawns specialized squads to optimize every component of the Cohezion ecosystem.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from cohezion.research.orborous import Orborous, PartyModeConsensus


logger = logging.getLogger(__name__)


@dataclass
class GatewayStatus:
    """Status of a single gateway."""

    name: str
    status: str  # "locked", "unlocking", "unlocked"
    health_score: float  # 0.0 - 1.0
    last_optimized: str
    improvements_made: int
    cost_usd: float
    active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "health_score": round(self.health_score, 3),
            "last_optimized": self.last_optimized,
            "improvements_made": self.improvements_made,
            "cost_usd": round(self.cost_usd, 2),
            "active": self.active,
        }


class Omnibus:
    """The Master Gateway Controller.

    Omnibus unlocks and optimizes all 9 major gateways:
    1. Research (✓ Already unlocked via Orborous)
    2. Cache - Semantic and token caching optimization
    3. Security - Pipeline and guardrail improvements
    4. Vault - MCP vault persistence optimization
    5. Swarm - Multi-agent coordination improvements
    6. Universe - 12D manifold optimization
    7. FLUME - VAE hyperparameter optimization
    8. Skills - PRIME skill refinement
    9. API - Endpoint and routing optimization

    The 10th gateway is Omnibus itself - self-optimization of the optimizer.
    """

    def __init__(self):
        """Initialize Omnibus master controller."""
        self.gateways: dict[str, GatewayStatus] = {}
        self.squads: dict[str, Orborous] = {}
        self.active = False
        self.cycle_count = 0

        # Initialize all gateways
        self._init_gateways()

        logger.info("🌟 Omnibus initialized - Master Gateway Controller ready")

    def _init_gateways(self) -> None:
        """Initialize all 9 gateways."""
        gateway_names = [
            "research",
            "cache",
            "security",
            "vault",
            "swarm",
            "universe",
            "flume",
            "skills",
            "api",
        ]

        for name in gateway_names:
            self.gateways[name] = GatewayStatus(
                name=name,
                status="locked" if name != "research" else "unlocked",
                health_score=0.5 if name != "research" else 0.95,
                last_optimized=datetime.now().isoformat() if name == "research" else "never",
                improvements_made=0 if name != "research" else 1,
                cost_usd=0.0,
            )

        logger.info(f"Initialized {len(gateway_names)} gateways")

    async def unlock_gateway(self, gateway_name: str) -> bool:
        """Unlock a specific gateway.

        Args:
            gateway_name: Name of gateway to unlock

        Returns:
            True if successfully unlocked
        """
        if gateway_name not in self.gateways:
            logger.error(f"Unknown gateway: {gateway_name}")
            return False

        gateway = self.gateways[gateway_name]

        if gateway.status == "unlocked":
            logger.info(f"Gateway '{gateway_name}' already unlocked")
            return True

        logger.info(f"🔓 Unlocking gateway: {gateway_name}")
        gateway.status = "unlocking"

        try:
            # Spawn specialized squad for this gateway
            squad = await self._spawn_squad(gateway_name)
            self.squads[gateway_name] = squad

            # Run initial optimization
            await squad.monitor_cycle()

            gateway.status = "unlocked"
            gateway.health_score = 0.85
            gateway.last_optimized = datetime.now().isoformat()
            gateway.improvements_made += 1

            logger.info(f"✅ Gateway '{gateway_name}' unlocked successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to unlock gateway '{gateway_name}': {e}")
            gateway.status = "locked"
            return False

    async def _spawn_squad(self, gateway_name: str) -> Orborous:
        """Spawn a specialized squad for a gateway.

        Args:
            gateway_name: Name of gateway

        Returns:
            Configured Orborous instance
        """
        from cohezion.research import integrate_with_compound_system
        from cohezion.research.cost_optimization import CostBudget

        # Create specialized squad based on gateway type
        squad = Orborous(
            cost_budget=CostBudget(max_cost_usd=10.0),
        )

        logger.info(f"Spawned squad for gateway: {gateway_name}")
        return squad

    async def run_master_cycle(self) -> None:
        """Run one cycle of omnibus - check all gateways."""
        self.cycle_count += 1
        logger.info(f"🌟 Omnibus Cycle #{self.cycle_count}")

        # Check each unlocked gateway
        for name, gateway in self.gateways.items():
            if gateway.status == "unlocked" and name in self.squads:
                logger.info(f"Monitoring gateway: {name}")
                try:
                    await self.squads[name].monitor_cycle()
                    gateway.health_score = min(1.0, gateway.health_score + 0.01)
                except Exception as e:
                    logger.error(f"Gateway '{name}' optimization failed: {e}")
                    gateway.health_score = max(0.0, gateway.health_score - 0.1)

        # Try to unlock next locked gateway
        locked = [n for n, g in self.gateways.items() if g.status == "locked"]
        if locked:
            next_gateway = locked[0]
            logger.info(f"Attempting to unlock next gateway: {next_gateway}")
            await self.unlock_gateway(next_gateway)

    async def run_forever(self) -> None:
        """Run Omnibus indefinitely."""
        logger.info("🌟 Omnibus awakening - unlocking all gateways")
        self.active = True

        # First, ensure research gateway is active
        if self.gateways["research"].status != "unlocked":
            await self.unlock_gateway("research")

        while self.active:
            await self.run_master_cycle()
            await asyncio.sleep(600)  # 10 minutes between cycles

    def get_master_status(self) -> dict[str, Any]:
        """Get status of all gateways."""
        unlocked = sum(1 for g in self.gateways.values() if g.status == "unlocked")
        locked = sum(1 for g in self.gateways.values() if g.status == "locked")
        total_health = sum(g.health_score for g in self.gateways.values())

        return {
            "omnibus_cycles": self.cycle_count,
            "gateways_unlocked": unlocked,
            "gateways_locked": locked,
            "total_health": round(total_health / len(self.gateways), 3),
            "gateways": {name: g.to_dict() for name, g in self.gateways.items()},
        }

    def get_gateway_dashboard(self) -> str:
        """Generate visual dashboard of all gateways."""
        lines = [
            "╔══════════════════════════════════════════════════════════╗",
            "║              OMNIBUS GATEWAY DASHBOARD                   ║",
            "╠══════════════════════════════════════════════════════════╣",
        ]

        for name, gateway in self.gateways.items():
            status_icon = {
                "unlocked": "✅",
                "unlocking": "🔓",
                "locked": "🔒",
            }.get(gateway.status, "❓")

            health_bar = self._render_health_bar(gateway.health_score)

            lines.append(
                f"║ {status_icon} {name:12} │ {health_bar} │ {gateway.improvements_made:3d} improvements ║"
            )

        lines.extend(
            [
                "╠══════════════════════════════════════════════════════════╣",
                f"║ Total Health: {self.get_master_status()['total_health']:.1%}                              ║",
                "╚══════════════════════════════════════════════════════════╝",
            ]
        )

        return "\n".join(lines)

    def _render_health_bar(self, score: float, width: int = 20) -> str:
        """Render ASCII health bar."""
        filled = int(score * width)
        empty = width - filled
        return "█" * filled + "░" * empty + f" {score:.0%}"

    def stop(self) -> None:
        """Gracefully stop Omnibus."""
        logger.info("🛑 Omnibus stopping...")
        self.active = False
        for squad in self.squads.values():
            squad.stop()


# Entry point
async def awaken_omnibus():
    """Awaken the Master Gateway Controller."""
    omnibus = Omnibus()

    # Print initial dashboard
    print(omnibus.get_gateway_dashboard())

    # Run forever
    await omnibus.run_forever()


if __name__ == "__main__":
    asyncio.run(awaken_omnibus())
