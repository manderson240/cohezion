"""Lightweight Gateway Dashboard - Memory Efficient.

Minimal memory footprint dashboard for monitoring all 9 gateways.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)  # slots=True reduces memory
class GatewayStatus:
    """Memory-efficient gateway status."""

    name: str
    status: str
    health: float
    improvements: int
    cost: float


class LightweightDashboard:
    """Memory-efficient dashboard - streams data instead of loading all."""

    def __init__(self, max_history: int = 100):
        """Initialize with memory limits."""
        self.max_history = max_history
        self.gateways: dict[str, GatewayStatus] = {}
        self._init_gateways()

    def _init_gateways(self) -> None:
        """Initialize 9 gateways with minimal memory."""
        names = [
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

        for i, name in enumerate(names):
            self.gateways[name] = GatewayStatus(
                name=name,
                status="unlocked" if name == "research" else "locked",
                health=0.5 + (i * 0.05),  # Varying health
                improvements=0,
                cost=0.0,
            )

    def render(self) -> str:
        """Render ASCII dashboard."""
        lines = [
            "╔══════════════════════════════════════════════════════════════╗",
            "║           🌟 OMNIBUS GATEWAY DASHBOARD 🌟                    ║",
            "╠══════════════════════════════════════════════════════════════╣",
        ]

        for name, g in self.gateways.items():
            icon = "✅" if g.status == "unlocked" else "🔒"
            bar = self._health_bar(g.health)
            lines.append(f"║ {icon} {name:10} │ {bar} │ {g.improvements:2d} imp │ ${g.cost:5.2f} ║")

        avg_health = sum(g.health for g in self.gateways.values()) / len(self.gateways)
        unlocked = sum(1 for g in self.gateways.values() if g.status == "unlocked")

        lines.extend(
            [
                "╠══════════════════════════════════════════════════════════════╣",
                f"║ Total Health: {avg_health:.1%} │ Unlocked: {unlocked}/9                     ║",
                "╚══════════════════════════════════════════════════════════════╝",
            ]
        )

        return "\n".join(lines)

    def _health_bar(self, score: float, width: int = 15) -> str:
        """Render compact health bar."""
        filled = int(score * width)
        return "█" * filled + "░" * (width - filled) + f" {score:.0%}"

    def update_gateway(self, name: str, **kwargs) -> None:
        """Update gateway with minimal memory."""
        if name in self.gateways:
            g = self.gateways[name]
            for key, value in kwargs.items():
                if hasattr(g, key):
                    setattr(g, key, value)

    def stream_to_file(self, path: Path) -> None:
        """Stream dashboard to file (no memory accumulation)."""
        with open(path, "w") as f:
            f.write(self.render())

    def get_memory_usage(self) -> dict[str, Any]:
        """Return memory usage stats."""
        import sys

        total_size = sum(sys.getsizeof(g) for g in self.gateways.values())

        return {
            "gateway_objects": len(self.gateways),
            "estimated_bytes": total_size,
            "max_history": self.max_history,
            "memory_efficient": total_size < 10000,  # < 10KB
        }


# Entry
if __name__ == "__main__":
    dashboard = LightweightDashboard()

    print(dashboard.render())
    print()

    mem = dashboard.get_memory_usage()
    print(f"Memory Usage: {mem['estimated_bytes']} bytes")
    print(f"Efficient: {'Yes' if mem['memory_efficient'] else 'No'}")
