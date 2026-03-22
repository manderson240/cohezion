"""
Simulation Analysis Module (PRIME)
==================================
Handles post-simulation analysis for Fractal Universe data.
1. Loads parquet shards.
2. Calculates stability metrics.
3. Generates visualizations.
4. Produces a markdown report.
"""

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from cohezion.simulation.simulation_logger import SimulationLogger


logger = logging.getLogger("SimAnalyzer")


class SimulationAnalyzer:
    def __init__(self, storage_dir: str = "data/simulations/fractal_nexus"):
        self.sim_dir = Path(storage_dir)
        self.logger_tool = SimulationLogger(storage_dir=storage_dir)

    async def run_analysis_async(self, output_file: str = "SIMULATION_REPORT.md"):
        logger.info("Starting automated simulation analysis...")

        # 1. Load Data (Hybrid: Parquet + SurrealDB)
        try:
            # Load Fracture Universe Data
            dataset = self.logger_tool.load_universe_data(domain="fractal_nexus")
            df = dataset.to_pandas()

            # Load QFTDHD Optimization Data from SurrealDB
            from cohezion.core.persistence.surreal_client import SurrealClient

            client = SurrealClient()
            if await client.connect():
                # Query for experiment summaries
                q = "SELECT * FROM universe_nodes WHERE node_type = 'experiment_summary'"
                res = await client.query(q)
                # Handle result format (list of lists of dicts usually)
                if res and hasattr(res, "__getitem__") and len(res) > 0:
                    exps = res[0].get("result", [])
                    if exps:
                        logger.info(f"Found {len(exps)} QFTDHD Trace Summaries in SurrealDB")
                        best_energy = min([float(e.get("metadata", {}).get("final_energy", 999)) for e in exps])

                        if best_energy < 50.0:
                            logger.info(f"Optimization Breakthrough detected! Best Energy: {best_energy}")
                            self._crystallize_skill(best_energy)

            await client.close()

            if df.empty:
                logger.warning("No fractal universe data found.")
                return
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            return

        # 2. Compute Metrics
        # Extract cycle number from cycle_id (e.g., "tick_100" -> 100)
        df["tick"] = df["cycle_id"].apply(lambda x: int(x.split("_")[1]) if "_" in x else 0)
        df = df.sort_values("tick")

        total_cycles = len(df["tick"].unique())
        avg_coherence = df["phi_score"].mean()
        final_coherence = df[df["tick"] == df["tick"].max()]["phi_score"].mean()

        stability_trend = "Stable"
        if final_coherence > 0.6:
            stability_trend = "Stagnating (Too Static)"
        if final_coherence < 0.4:
            stability_trend = "Collapsing (Too Chaotic)"
        if 0.45 <= final_coherence <= 0.55:
            stability_trend = "Optimal (HIHO)"

        # 3. Visualization
        self._plot_stability(df)

        # 4. Generate Report
        report = f"""# Simulation Analysis Report
**Timestamp**: {pd.Timestamp.now()}
**Domain**: Fractal Nexus
**Cycles Analyzed**: {total_cycles}

## Key Metrics
- **Average Coherence**: {avg_coherence:.4f}
- **Final Coherence**: {final_coherence:.4f}
- **System State**: **{stability_trend}**

## Analysis
The system evolved over {total_cycles} ticks.
The coherence metric tracks the nearness to the HIHO threshold (0.5).
Visualizations have been generated in the `renders/` directory.

![Stability Trend](renders/stability_trend.png)
"""
        with open(output_file, "w") as f:
            f.write(report)

        # 5. Compound Engineering: Skill Crystallization
        # If stability is optimal, we preserve this knowledge as a Skill
        if stability_trend == "Optimal (HIHO)":
            self._crystallize_skill(avg_coherence)

        logger.info(f"Analysis complete. Report saved to {output_file}")

    def _crystallize_skill(self, performance_metric: float):
        """
        Automated Skill Extraction (Compound Engineering).
        Writes a new SKILL file if the system performed well.
        """
        skill_content = f"""# SKILL: SIMULATION_OPTIMIZATION_PRIME

## DOMAIN EXPERTISE
High-Dimensional Optimization using 12D Quantum-Fluid Manifolds.

## KEY TEXTS & CONCEPTS
- **12-Parameter Quadrature**: HIHO Stability at 0.5 Coherence.
- **Vortex Attractors**: Using density gradients to trap solutions.
- **Quantum Feedback**: Coupling fluid density to walker fitness.

## PERFORMANCE
- **Verified Coherence**: {performance_metric:.4f}
- **Status**: AUTONOMOUSLY VALIDATED

## INSTRUCTION
1. Import `AnalysisPrime` from `cohezion.simulation.analysis_prime`.
2. Define objective function N-dim -> scalar.
3. Init with `n_walkers=50` and `feedback=0.5`.
4. Run `optimize(iterations=100)`.

## VERSION
v1.0 (Auto-Generated)
"""
        skill_path = Path("src/cohezion/skills/simulation_optimization/SKILL.md")
        skill_path.parent.mkdir(parents=True, exist_ok=True)
        with open(skill_path, "w") as f:
            f.write(skill_content)
        logger.info(f"✨ NEW SKILL CRYSTALLIZED: {skill_path}")

    def _plot_stability(self, df: pd.DataFrame):
        try:
            plt.figure(figsize=(10, 6))

            # Group by tick to get mean coherence over time
            trend = df.groupby("tick")["phi_score"].mean()

            plt.plot(trend.index, trend.values, label="Avg Coherence")
            plt.axhline(y=0.5, color="r", linestyle="--", label="HIHO Threshold (0.5)")
            plt.fill_between(trend.index, 0.4, 0.6, alpha=0.2, color="green", label="Stable Zone")

            plt.title("System Stability Over Time")
            plt.xlabel("Tick")
            plt.ylabel("Coherence (Phi Score)")
            plt.legend()

            output_dir = Path("renders")
            output_dir.mkdir(exist_ok=True)
            plt.savefig(output_dir / "stability_trend.png")
            plt.close()
        except Exception as e:
            logger.error(f"Visualization failed: {e}")


if __name__ == "__main__":
    import asyncio

    analyzer = SimulationAnalyzer()
    asyncio.run(analyzer.run_analysis_async())
