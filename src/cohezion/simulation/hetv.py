"""
HETV Physics Engine (High-Efficiency Toroidal Vorticities)
==========================================================
Applies Toroidal Geometry to optimize agent clustering under stress.
When "Global Coherence" drops (due to market/climate chaos),
agents form HETV structures to preserve energy.

Math:
Based on the conceptual "Twistor" dynamics.
"""

import logging
import math

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HETV")


class HETVEngine:
    def __init__(self, core_radius: float = 1.0):
        self.a = core_radius  # Core radius
        self.gamma = 1.0  # Circulation strength

    def calculate_vortex_velocity(self, r: float) -> float:
        """
        Calculates tangential velocity at radius r from the vortex center.
        Formula: V = (Gamma / 2pi*r) * (1 - e^(-r^2 / a^2))
        """
        if r <= 0.001:
            return 0.0

        term1 = self.gamma / (2 * math.pi * r)
        term2 = 1.0 - math.exp(-(r**2) / (self.a**2))

        return term1 * term2

    def stabilize_swarm(
        self, positions: list[tuple[float, float]], global_entropy: float
    ) -> list[tuple[float, float]]:
        """
        Adjusts agent positions to form a stable Toroid if entropy is high.
        """
        if global_entropy < 0.3:
            return positions  # Low entropy: Free movement allowed

        logger.info(
            f"⚠️ High Entropy ({global_entropy:.2f}). Engaging HETV Protocols..."
        )

        new_positions = []
        center_x, center_y = 0.5, 0.5  # Normalized center

        for _i, (x, y) in enumerate(positions):
            # Calculate distance from center
            dx, dy = x - center_x, y - center_y
            r = math.sqrt(dx**2 + dy**2)

            # Apply suction towards the "Stable Radius" (0.5 for our normalized space)
            stable_r = 0.3
            suction_strength = global_entropy * 0.1  # Stronger suction for higher chaos

            if r > stable_r:
                r -= suction_strength
            else:
                r += suction_strength

            # Add rotation (Vortex Spin)
            theta = math.atan2(dy, dx)
            theta += 0.1  # Spin

            # Recalculate cartesian
            new_x = center_x + r * math.cos(theta)
            new_y = center_y + r * math.sin(theta)

            new_positions.append((new_x, new_y))

        return new_positions
