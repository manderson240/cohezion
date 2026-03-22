"""
Linguistic Driver: Language Mutation & Memetic Evolution.
v1.0 - "The Babel Edition"

Runs in parallel with Physics and Societal drivers.
- Domain: Linguistics, Memetics, Information Theory.
- Logic: R-Zero Challenger (Mutation vs Intelligibility).
- Memory-Optimized: Aggressive GC.
"""

import asyncio
import gc
import logging
import random
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Internal imports
from cohezion.swarm.mass_simulator import MassSimulator


logger = logging.getLogger("linguistic")

# Constants - Lower for memory safety
TARGET_SIMULATIONS = 500_000
END_TIME_HOUR = 8
BATCH_SIZE = 250


@dataclass
class LanguageState:
    epoch: int = 1
    mutation_rate: float = 0.1
    vocab_size: int = 1000

    def evolve(self, avg_intelligibility: float):
        # If perfectly intelligible, increase mutation (drift)
        if avg_intelligibility > 0.95:
            self.mutation_rate = min(0.9, self.mutation_rate + 0.05)
            self.epoch += 1
            return True
        # If unintelligible, simplify
        if avg_intelligibility < 0.3:
            self.mutation_rate = max(0.01, self.mutation_rate - 0.1)
            return False


class LinguisticDriver:
    def __init__(self):
        self.simulator = MassSimulator(
            total_simulations=TARGET_SIMULATIONS,
            chunk_size=BATCH_SIZE,
            output_dir=Path("src/cohezion/knowledge_graph/universe_nodes/linguistic_evolution"),
        )
        self.state = LanguageState()
        self.total_completed = 0

    async def run_until_morning(self):
        logger.info("Starting Linguistic Simulation (Babel)...")

        while True:
            now = datetime.now()
            if now.hour == END_TIME_HOUR and now.minute > 0:
                break

            await self._run_batch()

            # Aggressive cleanup
            gc.collect()
            await asyncio.sleep(3)

    async def _run_batch(self):
        log_dir = self.simulator.output_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        rate = self.state.mutation_rate

        def process_sim(input_data: str, idx: int) -> dict:
            seed = random.randint(0, 99999)
            random.seed(seed)

            # --- LANGUAGE SIM ---
            base_word = "COHEZION"
            mutation = ""
            chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

            # Mutate
            for char in base_word:
                if random.random() < rate:
                    mutation += random.choice(chars)
                else:
                    mutation += char

            # Calculate Intelligibility (Simulated Levenshtein mostly)
            match_count = sum(1 for a, b in zip(base_word, mutation, strict=False) if a == b)
            intelligibility = match_count / len(base_word)

            # Memetic Spread
            spread = random.uniform(0, 1) * intelligibility

            result_text = (
                f"Lang Seed {seed}: Rate {rate:.2f}. "
                f"Word: {base_word} -> {mutation}. "
                f"Intel: {intelligibility:.2f}. Spread: {spread:.2f}."
            )

            # Log
            with open(log_dir / f"lang_{int(time.time())}_{idx}.txt", "w") as f:
                f.write(result_text)

            return {
                "final_coherence": intelligibility,
                "mutation": mutation,
                "spread": spread,
                "type": "linguistic",
            }

        inputs = [f"Simulate Lang {i}" for i in range(BATCH_SIZE)]

        chunk_result = await asyncio.to_thread(self.simulator.run_custom_chunk, int(time.time()), inputs, process_sim)

        # Update State
        scores = [r["final_coherence"] for r in chunk_result.raw_results if isinstance(r, dict)]
        if scores:
            avg = sum(scores) / len(scores)
            if self.state.evolve(avg):
                logger.info(
                    f"[LINGUISTIC] Evolved to Epoch {self.state.epoch}. Rate: {self.state.mutation_rate:.2f}"
                )

        self.total_completed += len(inputs)
        # Less noisy logging, only every 1000
        if self.total_completed % 1000 == 0:
            logger.info(f"[LINGUISTIC] Batch completed. Total: {self.total_completed}.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    driver = LinguisticDriver()
    asyncio.run(driver.run_until_morning())
