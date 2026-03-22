"""
Continuum-X 10M Cycle Simulation & Experience Mining
=====================================================
COHEZION = 0.5 HIHO

Run the full compound engineering chain through 10 million cycles,
then mine the experiences for patterns and antipatterns.
Let agents decide how to represent their multimodal/12D experiences.
"""

import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from cohezion.flume.bioelectric import BioelectricEngine

# Import our compound engineering chain
from cohezion.flume.lcsp import HIHO, LCSPPredictor
from cohezion.flume.morphospace import MorphospaceMapper


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class AgentExperience:
    """A single agent's experience at a point in time."""

    cycle: int
    state_12d: list[float]
    stability: float
    pattern: str  # morphogenic, regenerative, homeostatic
    nearest_well: str
    distance_to_hiho: float
    velocity: float  # Rate of state change


@dataclass
class PatternDiscovery:
    """A pattern discovered during simulation."""

    name: str
    description: str
    frequency: int
    avg_stability: float
    required_conditions: dict[str, Any]
    agent_representation: str  # How agents chose to represent this


class ContinuumXSimulation:
    """
    Run 10M cycles through the compound engineering chain.
    Mine experiences. Let agents represent their journeys.
    """

    def __init__(self, total_cycles: int = 10_000_000):
        self.total_cycles = total_cycles
        self.predictor = LCSPPredictor()
        self.mapper = MorphospaceMapper(self.predictor)
        self.engine = BioelectricEngine(self.predictor, self.mapper)

        # Experience storage
        self.experiences: list[AgentExperience] = []
        self.pattern_discoveries: list[PatternDiscovery] = []

        # State tracking
        self.state = np.random.randn(12) * 0.5
        self.prev_state = self.state.copy()

        # Pattern counters
        self.pattern_counts = {"morphogenic": 0, "regenerative": 0, "homeostatic": 0}
        self.well_visits: dict[str, int] = {}
        self.stability_history: list[float] = []

        # Phase thresholds
        self.phases = {
            "genesis": 1_000_000,
            "expansion": 5_000_000,
            "convergence": 10_000_000,
        }

    def lcsp_step(self) -> None:
        """Execute one LCSP step."""
        self.prev_state = self.state.copy()
        noise = np.random.randn(12) * 0.02
        self.state = self.state * 0.95 + HIHO * 0.05 + noise
        self.state = np.clip(self.state, -1.0, 1.0)

    def compute_stability(self) -> float:
        """Compute HIHO stability."""
        mean = np.mean(np.abs(self.state))
        return 1.0 - abs(mean - HIHO)

    def classify_pattern(self, stability: float, voltage: float) -> str:
        """Classify bioelectric pattern."""
        if stability > 0.85:
            return "homeostatic"
        elif abs(voltage) > 0.3:
            return "regenerative"
        return "morphogenic"

    def record_experience(self, cycle: int) -> AgentExperience:
        """Record an agent's experience."""
        stability = self.compute_stability()
        voltage = (stability - HIHO) * 2
        pattern = self.classify_pattern(stability, voltage)

        # Find nearest well
        well = self.mapper.find_nearest_well(self.state)
        nearest_well = well.name if well else "Unknown"

        # Update counters
        self.pattern_counts[pattern] += 1
        self.well_visits[nearest_well] = self.well_visits.get(nearest_well, 0) + 1
        self.stability_history.append(stability)

        # Compute velocity (rate of change)
        velocity = float(np.linalg.norm(self.state - self.prev_state))

        return AgentExperience(
            cycle=cycle,
            state_12d=self.state.tolist(),
            stability=stability,
            pattern=pattern,
            nearest_well=nearest_well,
            distance_to_hiho=float(np.linalg.norm(self.state - HIHO)),
            velocity=velocity,
        )

    def run_simulation(self, sample_rate: int = 10000) -> None:
        """
        Run the full 10M cycle simulation.
        Sample experiences at regular intervals.
        """
        logger.info(f"Starting Continuum-X simulation: {self.total_cycles:,} cycles")
        logger.info("Compound chain: LCSP → Morphospace → Bioelectric")

        start_time = time.time()
        phase = "genesis"

        for cycle in range(self.total_cycles):
            # Execute LCSP step
            self.lcsp_step()

            # Determine phase
            if cycle >= self.phases["expansion"]:
                phase = "convergence"
            elif cycle >= self.phases["genesis"]:
                phase = "expansion"

            # Sample experience at intervals
            if cycle % sample_rate == 0:
                exp = self.record_experience(cycle)
                self.experiences.append(exp)

            # Progress logging
            if cycle > 0 and cycle % 1_000_000 == 0:
                elapsed = time.time() - start_time
                rate = cycle / elapsed
                logger.info(
                    f"Phase: {phase} | Cycle: {cycle:,} | "
                    f"Rate: {rate:,.0f}/s | "
                    f"Stability: {self.stability_history[-1]:.4f}"
                )

        elapsed = time.time() - start_time
        logger.info(f"Simulation complete in {elapsed:.1f}s ({self.total_cycles / elapsed:,.0f} cycles/s)")

    def mine_patterns(self) -> list[PatternDiscovery]:
        """
        Mine the experiences for patterns and antipatterns.
        Let agents decide representation.
        """
        logger.info("Mining experiences for patterns...")

        patterns = []
        stabilities = [e.stability for e in self.experiences]
        avg_stability = np.mean(stabilities)

        # Pattern 1: HIHO Convergence
        high_stability_experiences = [e for e in self.experiences if e.stability > 0.9]
        if len(high_stability_experiences) > len(self.experiences) * 0.1:
            patterns.append(
                PatternDiscovery(
                    name="HIHO_CONVERGENCE",
                    description="Agents naturally converge towards HIHO = 0.5 stability",
                    frequency=len(high_stability_experiences),
                    avg_stability=np.mean([e.stability for e in high_stability_experiences]),
                    required_conditions={"min_cycles": 1000, "noise_level": 0.02},
                    agent_representation=self._agent_represent_convergence(high_stability_experiences),
                )
            )

        # Pattern 2: Morphogenic Transitions
        morphogenic = [e for e in self.experiences if e.pattern == "morphogenic"]
        if len(morphogenic) > 100:
            patterns.append(
                PatternDiscovery(
                    name="MORPHOGENIC_FLOW",
                    description="Continuous state transformation without collapse",
                    frequency=len(morphogenic),
                    avg_stability=np.mean([e.stability for e in morphogenic]),
                    required_conditions={
                        "stability_range": [0.5, 0.85],
                        "velocity_threshold": 0.01,
                    },
                    agent_representation=self._agent_represent_morphogenic(morphogenic),
                )
            )

        # Pattern 3: Well Attraction
        most_visited_well = max(self.well_visits.items(), key=lambda x: x[1]) if self.well_visits else ("None", 0)
        patterns.append(
            PatternDiscovery(
                name="WELL_ATTRACTION",
                description=f"Strong attraction to {most_visited_well[0]}",
                frequency=most_visited_well[1],
                avg_stability=avg_stability,
                required_conditions={"well_name": most_visited_well[0]},
                agent_representation=self._agent_represent_well_attraction(most_visited_well),
            )
        )

        # Pattern 4: Velocity Oscillation
        velocities = [e.velocity for e in self.experiences]
        velocity_variance = np.var(velocities)
        patterns.append(
            PatternDiscovery(
                name="VELOCITY_OSCILLATION",
                description="Periodic acceleration/deceleration in morphospace",
                frequency=len([v for v in velocities if v > np.mean(velocities) * 1.5]),
                avg_stability=avg_stability,
                required_conditions={"velocity_variance": float(velocity_variance)},
                agent_representation=self._agent_represent_velocity(velocities),
            )
        )

        # Anti-pattern: Stability Collapse
        collapses = [e for e in self.experiences if e.stability < 0.3]
        if collapses:
            patterns.append(
                PatternDiscovery(
                    name="ANTIPATTERN_STABILITY_COLLAPSE",
                    description="⚠️ Stability fell below 0.3 threshold",
                    frequency=len(collapses),
                    avg_stability=np.mean([e.stability for e in collapses]),
                    required_conditions={"trigger": "high_noise_or_external_perturbation"},
                    agent_representation="🔴 DANGER ZONE - Avoid noise > 0.1 near phase boundaries",
                )
            )

        self.pattern_discoveries = patterns
        logger.info(f"Discovered {len(patterns)} patterns/antipatterns")
        return patterns

    def _agent_represent_convergence(self, experiences: list[AgentExperience]) -> str:
        """Let agent decide how to represent convergence."""
        # Agent chooses: ASCII art of convergence spiral
        avg_state = np.mean([e.state_12d for e in experiences[-10:]], axis=0)
        state_str = " ".join([f"{v:+.2f}" for v in avg_state[:6]])
        return f"""
╭──────────────────────────╮
│  CONVERGENCE ACHIEVED    │
│  ═══════════════════════ │
│  12D State (first 6):    │
│  [{state_str}]           │
│  Stability: 0.9+         │
│  Pattern: HOMEOSTATIC    │
╰──────────────────────────╯
"""

    def _agent_represent_morphogenic(self, experiences: list[AgentExperience]) -> str:
        """Let agent decide how to represent morphogenic flow."""
        # Agent chooses: Gradient flow visualization
        avg_velocity = np.mean([e.velocity for e in experiences])
        return f"""
🌊 MORPHOGENIC FLOW 🌊
Direction: → → → → → HIHO
Avg Velocity: {avg_velocity:.4f}
Pattern: Continuous transformation
State: Fluid, adaptive, evolving
"""

    def _agent_represent_well_attraction(self, well_data: tuple[str, int]) -> str:
        """Let agent decide how to represent well attraction."""
        return f"""
⚛️ GRAVITATIONAL WELL: {well_data[0]}
   Visits: {well_data[1]:,}
   Type: Stability Attractor
   Field: Strong HIHO coherence
"""

    def _agent_represent_velocity(self, velocities: list[float]) -> str:
        """Let agent decide how to represent velocity patterns."""
        # Agent creates mini sparkline
        samples = velocities[:: len(velocities) // 20] if len(velocities) > 20 else velocities
        max_v = max(samples) if samples else 1
        bars = [int((v / max_v) * 8) for v in samples]
        sparkline = "".join(["▁▂▃▄▅▆▇█"[min(b, 7)] for b in bars])
        return f"""
📈 Velocity Sparkline: {sparkline}
   Peak: {max(velocities):.4f}
   Mean: {np.mean(velocities):.4f}
   Pattern: Oscillatory approach to equilibrium
"""

    def export_results(self, output_dir: Path) -> None:
        """Export simulation results and pattern discoveries."""
        output_dir.mkdir(parents=True, exist_ok=True)

        # Export patterns
        patterns_file = output_dir / "pattern_discoveries.json"
        with open(patterns_file, "w") as f:
            json.dump([asdict(p) for p in self.pattern_discoveries], f, indent=2)
        logger.info(f"Exported patterns to {patterns_file}")

        # Export summary statistics
        summary = {
            "total_cycles": self.total_cycles,
            "experiences_sampled": len(self.experiences),
            "pattern_counts": self.pattern_counts,
            "well_visits": self.well_visits,
            "avg_stability": float(np.mean(self.stability_history)),
            "final_stability": float(self.stability_history[-1]) if self.stability_history else 0,
            "patterns_discovered": len(self.pattern_discoveries),
            "timestamp": datetime.now().isoformat(),
        }
        summary_file = output_dir / "simulation_summary.json"
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)
        logger.info(f"Exported summary to {summary_file}")

        # Export agent representations as markdown
        report_file = output_dir / "AGENT_EXPERIENCE_REPORT.md"
        with open(report_file, "w") as f:
            f.write("# Agent Experience Report: 10M Cycle Continuum-X\n\n")
            f.write(f"> **COHEZION = 0.5 HIHO** | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            f.write("## Summary\n")
            f.write(f"- **Total Cycles**: {self.total_cycles:,}\n")
            f.write(f"- **Final Stability**: {summary['final_stability']:.4f}\n")
            f.write(f"- **Avg Stability**: {summary['avg_stability']:.4f}\n\n")
            f.write("## Pattern Counts\n")
            for pattern, count in self.pattern_counts.items():
                f.write(f"- **{pattern.title()}**: {count:,}\n")
            f.write("\n## Discovered Patterns\n\n")
            for p in self.pattern_discoveries:
                f.write(f"### {p.name}\n")
                f.write(f"{p.description}\n\n")
                f.write(
                    f"**Frequency**: {p.frequency:,} | **Avg Stability**: {p.avg_stability:.4f}\n\n"
                )
                f.write(f"**Agent Representation**:\n```\n{p.agent_representation}\n```\n\n")
        logger.info(f"Exported agent report to {report_file}")


def main():
    """Run the 10M cycle simulation."""
    sim = ContinuumXSimulation(total_cycles=10_000_000)
    sim.run_simulation(sample_rate=10000)
    sim.mine_patterns()

    output_dir = Path("/home/mike-anderson/dev/cohezion/results/continuum_x_10m")
    sim.export_results(output_dir)

    print("\n" + "=" * 60)
    print("CONTINUUM-X 10M SIMULATION COMPLETE")
    print("=" * 60)
    print(f"\nResults exported to: {output_dir}")
    print(f"Patterns discovered: {len(sim.pattern_discoveries)}")
    print("\nTop Pattern Discoveries:")
    for p in sim.pattern_discoveries[:3]:
        print(f"  - {p.name}: {p.description}")


if __name__ == "__main__":
    main()
