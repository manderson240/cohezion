import asyncio
import json
import logging
from pathlib import Path

from cohezion.simulation.enhanced_simulator import EnhancedSimulator


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("recursive_lab.log"), logging.StreamHandler()],
)
logger = logging.getLogger("RecursiveDriver")


async def run_recursive_evolution(rounds: int = 10, batch_size: int = 100):
    simulator = EnhancedSimulator(output_dir=Path("recursive_simulations"))

    print(f"Starting Recursive Evolution: {rounds} rounds of {batch_size} simulations...")

    for r in range(1, rounds + 1):
        logger.info(f"--- Round {r}/{rounds} Starting ---")
        await simulator.run_batch(batch_size)

        stats = simulator.get_stats()
        logger.info(f"Round {r} Complete. Stats: {stats}")

        # Log round-specific summary
        summary = {"round": r, "stats": stats, "timestamp": stats.get("timestamp")}
        with open("recursive_sim_history.jsonl", "a") as f:
            f.write(json.dumps(summary) + "\n")

        # Add a small cooling period between rounds for resource stability
        await asyncio.sleep(2)

    print(f"\nEvolution Complete. Final Stats: {simulator.get_stats()}")


if __name__ == "__main__":
    asyncio.run(run_recursive_evolution(rounds=10, batch_size=100))
