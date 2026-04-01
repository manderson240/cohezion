import asyncio
import json
import logging
import multiprocessing
import os
import random
import sys
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List

# Add src to path to import cohezion modules
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../src"))

from cohezion.core.persistence.surreal_client import (
    PhysicsState,
    SurrealClient,
    UniverseNode,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(processName)s - %(message)s"
)
logger = logging.getLogger("SwarmSimulator")


@dataclass
class SimulationConfig:
    # Kernel Parameters
    smart_load_depth: int = 2
    unroll_factor: int = 1

    # Reality Parameters (The "Distortion Field")
    load_slots: int = 2
    alu_slots: int = 12
    valu_slots: int = 6
    disable_hash_opt: bool = False
    idx_math_variant: int = 0
    modulo_mode: int = 0

    # Meta
    simulation_id: str = ""


def run_simulation_worker(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Runs a single simulation in a separate process.
    """
    config = SimulationConfig(**config_dict)

    try:
        # 1. Reality Distortion (Monkeypatching Limits)
        import problem

        problem.SLOT_LIMITS["load"] = config.load_slots
        problem.SLOT_LIMITS["alu"] = config.alu_slots
        problem.SLOT_LIMITS["valu"] = config.valu_slots

        # 2. Kernel Config Injection (Using SimpleKernelBuilder)
        import optimizer
        import simple_builder
        from simple_builder import KernelConfig

        # Monkeypatch optimizer to use SimpleBuilder
        optimizer.OptimizedKernelBuilder = simple_builder.SimpleKernelBuilder

        # Monkeypatch init to force config
        original_init = simple_builder.SimpleKernelBuilder.__init__

        def patched_init(self, cfg=None):
            # Force our config
            c = KernelConfig(
                smart_load_depth=config.smart_load_depth,
                load_slots=config.load_slots,
                disable_hash_opt=config.disable_hash_opt,
                idx_math_variant=config.idx_math_variant,
                modulo_mode=config.modulo_mode,
            )
            original_init(self, c)

        simple_builder.SimpleKernelBuilder.__init__ = patched_init

        # 3. Execution
        # 3. Execution
        from custom_harness import do_kernel_test

        start_time = time.time()
        # Run test (using fixed seed for deterministic input, but changed kernel parameters)
        cycles = do_kernel_test(10, 16, 256, prints=False)
        duration = time.time() - start_time

        return {
            "status": "success",
            "cycles": cycles,
            "duration": duration,
            "config": asdict(config),
            "simulation_id": config.simulation_id,
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "config": asdict(config),
            "simulation_id": config.simulation_id,
        }


class SurrealLogger:
    def __init__(self):
        self.client = SurrealClient()

    async def log_journey(self, result: Dict[str, Any]):
        try:
            cfg = result["config"]
            cycles = result.get("cycles", -1)

            # Physics State Mapping:
            # X = Load Slots (Reality)
            # Y = Smart Load Depth (Strategy)
            # Z = ALU Slots
            # Mass = Efficiency (10000 / cycles)

            efficiency = 10000.0 / cycles if cycles > 0 else 0

            state = PhysicsState(
                x=float(cfg["load_slots"]),
                y=float(cfg["smart_load_depth"]),
                z=float(cfg["alu_slots"]),
                mass=efficiency,
                time=time.time(),
                novelty=0.5,  # Placeholder
                stability=1.0 if result["status"] == "success" else 0.0,
            )

            node = UniverseNode(
                id=f"sim_{cfg['simulation_id']}",
                content=json.dumps(result),
                physics_state=state,
                node_type="simulation_run",
                metadata={
                    "cycles": cycles,
                    "target": 1487,
                    "beat_target": cycles < 1487 if cycles > 0 else False,
                },
            )

            await self.client.store_node(node)

        except Exception as e:
            logger.error(f"Surreal logging failed: {e}")


class SwarmController:
    def __init__(self, output_file="swarm_results.jsonl"):
        self.output_file = output_file
        self.max_workers = 30  # Leave 2 cores for system/DB
        self.surreal_logger = SurrealLogger()
        self.loop = asyncio.new_event_loop()

    def generate_configs(self, n=1000) -> List[Dict[str, Any]]:
        configs = []
        for i in range(n):
            # FLUME Search Strategy
            # 50% Baseline Reality (Load=2)
            # 50% Distorted Reality (Load > 2)

            if random.random() < 0.5:
                load = 2
            else:
                load = random.choice([3, 4, 8])

            # Smart load depth search
            smart_load = random.choice([0, 1, 2, 3, 4, 5, 6, 8])

            # Hash Opt Search
            disable_hash = random.choice([True, False])

            # Idx Math Variant
            idx_var = 0  # Fixed to known correct

            # Modulo Mode
            mod_mode = 0  # Fixed to known correct

            cfg = SimulationConfig(
                smart_load_depth=smart_load,
                load_slots=load,
                disable_hash_opt=disable_hash,
                idx_math_variant=idx_var,
                modulo_mode=mod_mode,
                simulation_id=f"{int(time.time())}_{i}_{random.randint(1000, 9999)}",
            )
            configs.append(asdict(cfg))
        return configs

    def run_swarm(self, batches=10):
        logger.info(f"Igniting Swarm on {self.max_workers} cores...")

        for b in range(batches):
            configs = self.generate_configs(self.max_workers * 2)  # Queue up 2x workers

            with multiprocessing.Pool(processes=self.max_workers) as pool:
                results = pool.imap_unordered(run_simulation_worker, configs)

                for res in results:
                    # File Log
                    with open(self.output_file, "a") as f:
                        f.write(json.dumps(res) + "\n")

                    # Surreal Log
                    self.loop.run_until_complete(self.surreal_logger.log_journey(res))

                    if res["status"] == "success":
                        cycles = res["cycles"]
                        load = res["config"]["load_slots"]
                        sld = res["config"]["smart_load_depth"]
                        logger.info(
                            f"Sim {res['simulation_id']}: {cycles} cycles (Load={load}, SmartLoad={sld})"
                        )

                        if cycles < 1487 and load == 2:
                            logger.info(">>> GRAIL FOUND! <<<")


if __name__ == "__main__":
    swarm = SwarmController()
    swarm.run_swarm(batches=5)  # Run 5 batches of ~60 sims
