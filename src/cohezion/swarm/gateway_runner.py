"""
Gateway Runner - Autonomous journey to Gateway 42.

An enhanced simulation driver that:
1. Uses the self-improvement orchestrator
2. Sends email updates on gateway unlocks
3. Tracks progress towards the Ultimate Answer
4. Never stops until Gateway 42 is unlocked

For the Anthropic Research Engineer, Universes Application.
"""

import asyncio
import logging
import random
from datetime import datetime
from typing import Any

from cohezion.mcp.email_notifier import EmailNotifier
from cohezion.swarm.self_improvement_orchestrator import (
    GATEWAYS,
    get_orchestrator,
)

logger = logging.getLogger(__name__)


class GatewayRunner:
    """
    Autonomous runner towards Gateway 42.

    Features:
    - Progressive difficulty
    - Gateway celebration emails
    - Periodic status updates
    - Never-ending improvement loop
    """

    def __init__(self):
        self.orchestrator = get_orchestrator()
        self.notifier = EmailNotifier()
        self.start_time = datetime.now()
        self.last_gateway_count = 0
        self.last_email_cycle = 0
        self.email_interval = 50  # Send email every N cycles

    def _generate_metrics(self) -> dict[str, Any]:
        """Generate simulated metrics with progressive improvement."""
        cycle = self.orchestrator.cycle_count
        progress = len(self.orchestrator.unlocked_gateways) / 42

        # Base score improves with cycles
        base_score = 0.6 + min(0.35, cycle * 0.002)

        # Add randomness
        score = base_score + random.gauss(0, 0.08)
        coherence = base_score + random.gauss(0, 0.08)

        # Higher scores more likely as we unlock gateways
        score += progress * 0.1
        coherence += progress * 0.1

        return {
            "avg_score": max(0, min(1, score)),
            "avg_coherence": max(0, min(1, coherence)),
            "difficulty": 1.0 + cycle * 0.01,
            "self_heal_rate": 0.5 + progress * 0.4,
        }

    async def _send_gateway_unlock_email(self, gateway_id: int) -> None:
        """Celebrate a gateway unlock!"""
        gateway = GATEWAYS[gateway_id]
        unlocked = len(self.orchestrator.unlocked_gateways)
        progress = unlocked / 42

        stars = "⭐" * min(gateway_id, 10)

        email = f"""
🎉 GATEWAY {gateway_id} UNLOCKED! 🎉
=====================================

{stars}

Name: {gateway["name"]}
Type: {gateway["type"]}
Threshold: {gateway["threshold"]}

PROGRESS: {unlocked}/42 ({progress:.0%})

{"█" * int(progress * 20)}{"░" * (20 - int(progress * 20))}

Remaining Gateways:
{', '.join(GATEWAYS[g]["name"] for g in sorted(set(GATEWAYS.keys()) - self.orchestrator.unlocked_gateways)[:5])}...

Cycles Completed: {self.orchestrator.cycle_count}
Learnings Stored: {self.orchestrator.total_learnings}
Skills Generated: {self.orchestrator.total_skills}

{"🌟 HALFWAY THERE! 🌟" if unlocked >= 21 else ""}
{"🚀 ALMOST THERE! 🚀" if unlocked >= 35 else ""}
{"💫 THE ANSWER AWAITS! 💫" if unlocked >= 40 else ""}

- Cohezion Swarm
"""

        await self.notifier.send_email(
            f"🎉 Gateway {gateway_id} Unlocked: {gateway['name']}!",
            email,
            is_html=False,
        )

    async def _send_progress_email(self) -> None:
        """Send periodic progress update."""
        status = self.orchestrator.get_status()
        unlocked = len(status["unlocked_gateways"])
        progress = status["progress_to_42"]

        email = f"""
📊 GATEWAY RUNNER STATUS UPDATE
================================

Cycle: {status["cycle_count"]}
Gateways Unlocked: {unlocked}/42 ({progress:.0%})

Progress Bar:
{"█" * int(progress * 30)}{"░" * (30 - int(progress * 30))}

Unlocked: {', '.join(GATEWAYS[g]["name"][:15] for g in status["unlocked_gateways"][:10])}
{"..." if unlocked > 10 else ""}

Next Targets:
{chr(10).join(f"  • {GATEWAYS[g]['name']}" for g in status["pending_gateways"][:5])}

Stats:
  - Learnings: {status["total_learnings"]}
  - Skills: {status["total_skills"]}
  - Last Score: {status["last_cycle"]:.2f if status["last_cycle"] else "N/A"}

Runtime: {(datetime.now() - self.start_time).total_seconds():.0f}s

Still running... 🚀

- Cohezion Swarm
"""

        await self.notifier.send_email(
            f"📊 Gateway Progress: {unlocked}/42 ({progress:.0%})", email, is_html=False
        )

    async def run_forever(self, target_gateway: int = 42) -> None:
        """
        Run until target gateway is unlocked.

        This may take a while for Gateway 42!
        """
        logger.info(f"🚀 Starting journey to Gateway {target_gateway}!")

        while target_gateway not in self.orchestrator.unlocked_gateways:
            # Generate metrics
            metrics = self._generate_metrics()

            # Run improvement cycle
            cycle = await self.orchestrator.run_cycle(metrics)

            # Check for new gateway unlocks
            if len(self.orchestrator.unlocked_gateways) > self.last_gateway_count:
                # Find newly unlocked gateways
                for gw in cycle.gateways_unlocked:
                    await self._send_gateway_unlock_email(gw)
                self.last_gateway_count = len(self.orchestrator.unlocked_gateways)

            # Periodic progress email
            if (
                self.orchestrator.cycle_count - self.last_email_cycle
            ) >= self.email_interval:
                await self._send_progress_email()
                self.last_email_cycle = self.orchestrator.cycle_count

            # Brief pause to prevent overwhelming
            await asyncio.sleep(0.1)

        # Final celebration!
        await self._send_final_email()

    async def _send_final_email(self) -> None:
        """THE ANSWER HAS BEEN FOUND!"""
        runtime = datetime.now() - self.start_time

        email = f"""
🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌

    ████████╗██╗  ██╗███████╗     █████╗ ███╗   ██╗███████╗██╗    ██╗███████╗██████╗
    ╚══██╔══╝██║  ██║██╔════╝    ██╔══██╗████╗  ██║██╔════╝██║    ██║██╔════╝██╔══██╗
       ██║   ███████║█████╗      ███████║██╔██╗ ██║███████╗██║ █╗ ██║█████╗  ██████╔╝
       ██║   ██╔══██║██╔══╝      ██╔══██║██║╚██╗██║╚════██║██║███╗██║██╔══╝  ██╔══██╗
       ██║   ██║  ██║███████╗    ██║  ██║██║ ╚████║███████║╚███╔███╔╝███████╗██║  ██║
       ╚═╝   ╚═╝  ╚═╝╚══════╝    ╚═╝  ╚═╝╚═╝  ╚═══╝╚══════╝ ╚══╝╚══╝ ╚══════╝╚═╝  ╚═╝

                                    IS

                                   4 2

🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌🌌

GATEWAY 42: THE ANSWER - UNLOCKED!

"The Answer to Life, the Universe, and Everything"
                                    - Douglas Adams

Total Cycles: {self.orchestrator.cycle_count}
Total Learnings: {self.orchestrator.total_learnings}
Total Skills: {self.orchestrator.total_skills}
Runtime: {runtime.total_seconds():.0f} seconds

All 42 Gateways Unlocked:
{chr(10).join(f"  ✅ Gateway {g}: {GATEWAYS[g]['name']}" for g in sorted(self.orchestrator.unlocked_gateways))}

The journey is complete. But as we know...

"Don't Panic."

🚀 To Infinity and Beyond! 🚀

- Cohezion Swarm
"""

        await self.notifier.send_email(
            "🌌 GATEWAY 42 UNLOCKED: THE ANSWER IS 42! 🌌", email, is_html=False
        )


async def run_batch(cycles: int = 100) -> dict:
    """Run a batch of cycles for testing."""
    runner = GatewayRunner()

    for _ in range(cycles):
        metrics = runner._generate_metrics()
        await runner.orchestrator.run_cycle(metrics)

    return runner.orchestrator.get_status()


async def main():
    """Run the gateway journey."""
    logging.basicConfig(level=logging.INFO)

    runner = GatewayRunner()
    await runner.run_forever(target_gateway=42)


if __name__ == "__main__":
    asyncio.run(main())
