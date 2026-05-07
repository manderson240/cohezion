#!/usr/bin/env python3
"""End-to-end driver for the coherent matter precipitation loop.

Chains everything together in one command:

    1. Start PrecipitationBus, register default sinks (vault + surreal + git)
    2. Build a PrecipitationOrchestrator that watches the bus
    3. For generation in range(N):
         a. UniverseFactory.create_universe(spec) — emits COSMOGONY_PHASE,
            GENERATION_SPAWN events
         b. UniverseFactory.run(universe) — rolls out EVO agents in ManifoldEnv,
            emits WITNESS_MARK events
         c. factory.save_trajectories(...) — persists journeys to data/trajectories
         d. Orchestrator's threshold fires, exports DPO + runs training
            (mock by default; pass --real-training to invoke trl.SFTTrainer)
         e. TRAINING_CHECKPOINT event captured; next gen uses the new weights
    4. Print a summary + event counts per generation

Usage:
    uv run python scripts/drivers/run_coherent_precipitation.py \\
        --generations 2 --agents-per-universe 2 --steps-per-rollout 20
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Drive the full precipitation loop")
    parser.add_argument("--generations", type=int, default=2)
    parser.add_argument("--agents-per-universe", type=int, default=2)
    parser.add_argument("--steps-per-rollout", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--base-model", default="Qwen/Qwen2.5-0.5B-Instruct")
    parser.add_argument("--output-dir", type=Path, default=Path("runs/precipitation"))
    parser.add_argument(
        "--real-training", action="store_true", help="Invoke trl.SFTTrainer (requires trl+peft)"
    )
    parser.add_argument("--no-surreal", action="store_true", help="Skip SurrealDB sink")
    parser.add_argument("--witness-interval", type=int, default=5)
    return parser.parse_args(argv)


async def run(args: argparse.Namespace) -> int:
    # Imports after parse so --help is cheap.
    from cohezion.precipitation import (
        PrecipitationBus,
        PrecipitationEvent,
        register_default_sinks,
        set_bus,
    )
    from cohezion.precipitation.orchestrator import (
        OrchestratorConfig,
        PrecipitationOrchestrator,
    )
    from cohezion.universe.factory import UniverseFactory, UniverseSpec

    args.output_dir.mkdir(parents=True, exist_ok=True)
    trajectory_dir = args.output_dir / "trajectories"
    trajectory_dir.mkdir(parents=True, exist_ok=True)

    bus = PrecipitationBus()
    await bus.start()
    set_bus(bus)

    sinks = register_default_sinks(bus, enable_surreal=not args.no_surreal)

    # Track events per generation for the summary.
    per_gen_events: dict[str, dict[str, int]] = {}

    def on_event(event: PrecipitationEvent) -> None:
        per_gen_events.setdefault(event.universe_id, {})
        counts = per_gen_events[event.universe_id]
        counts[event.kind.value] = counts.get(event.kind.value, 0) + 1

    bus.subscribe(on_event, kind=None)

    orch_config = OrchestratorConfig(
        min_coherent_witness_marks=max(2, args.steps_per_rollout // args.witness_interval),
        min_cosmogony_phases=5,
        base_model=args.base_model,
        output_dir=args.output_dir / "models",
        trajectory_dir=trajectory_dir,
        training_data_dir=args.output_dir / "training",
        enable_real_training=args.real_training,
    )
    orch = PrecipitationOrchestrator(config=orch_config, bus=bus)
    orch.subscribe()

    factory = UniverseFactory(bus=bus)

    current_checkpoint: str | None = None
    for generation in range(args.generations):
        universe_id = f"gen-{generation}"
        spec = UniverseSpec(
            universe_id=universe_id,
            agent_count=args.agents_per_universe,
            max_steps=args.steps_per_rollout,
            witness_interval=args.witness_interval,
            seed=args.seed + generation,
            model_checkpoint=current_checkpoint,
        )
        logging.info("driver: creating %s (checkpoint=%s)", universe_id, current_checkpoint)
        universe = await factory.create_universe(spec)
        trajectories = await factory.run(universe)
        await factory.save_trajectories(trajectories, trajectory_dir)

        # Let bus flush + orchestrator process.
        await bus.flush()
        await asyncio.sleep(0.1)

        if orch.generations:
            current_checkpoint = str(orch.generations[-1].checkpoint_path)

    # Drain and close.
    await bus.flush()
    await bus.stop()
    if sinks.get("surreal"):
        await sinks["surreal"].close()

    # Summary.
    print("\n" + "=" * 60)
    print("COHERENT MATTER PRECIPITATION — SUMMARY")
    print("=" * 60)
    print(f"Generations: {args.generations}")
    print(f"Orchestrator fired: {len(orch.generations)} times")
    for record in orch.generations:
        print(
            f"  gen{record.generation}: witness_marks={record.witness_mark_count} "
            f"phases={record.cosmogony_phase_count} succeeded={record.succeeded}"
        )
    print("\nPrecipitation events per universe:")
    for universe_id, counts in sorted(per_gen_events.items()):
        total = sum(counts.values())
        kinds = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
        print(f"  {universe_id}: total={total}  [{kinds}]")
    print(f"\nArtifacts: {args.output_dir.resolve()}")
    print("=" * 60)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    return asyncio.run(run(args))


if __name__ == "__main__":
    sys.exit(main())
