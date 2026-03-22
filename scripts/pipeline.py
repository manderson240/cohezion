"""End-to-end training pipeline: Mass Sim -> VAE -> RL -> Weight Bridge -> Validate.

Connects all pipeline stages into a single orchestrated run:
1. Run mass sim (demo tier, export_npy=True)
2. Retrain VAE on the exported .npy files
3. Train RL policy on FlumeNav-v0 with CompositeReward
4. Extract trained RL weights via WeightBridge into FlumePhysics
5. Validate coherence of the transferred weights

Usage:
    uv run python scripts/pipeline.py
    uv run python scripts/pipeline.py --agents 50 --epochs 500 --universes 3
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pipeline")


@dataclass
class PipelineConfig:
    """Configuration for the end-to-end pipeline."""

    # Mass sim
    n_agents: int = 100
    n_epochs: int = 1000
    n_universes: int = 5
    # VAE
    vae_epochs: int = 10
    vae_batch_size: int = 32
    # RL
    rl_episodes: int = 50
    rl_max_steps: int = 100
    # Output
    output_dir: Path = Path("data/pipeline")


@dataclass
class PipelineResult:
    """Aggregated results from a full pipeline run."""

    npy_files: list[Path]
    vae_final_loss: float
    rl_final_coherence: float
    weight_bridge_valid: bool
    mean_coherence: float
    elapsed_seconds: float


def step_1_mass_sim(config: PipelineConfig) -> list[Path]:
    """Run mass simulation and export .npy files."""
    from cohezion.mass_sim.batch_runner import BatchSimulationRunner
    from cohezion.mass_sim.config import ScaleTier, SimulationConfig, UniverseSpec

    logger.info("=== Step 1: Mass Simulation ===")

    artifact_dir = config.output_dir / "npy"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    tier = ScaleTier(
        name="pipeline",
        n_agents=config.n_agents,
        n_epochs=config.n_epochs,
        n_universes=config.n_universes,
        checkpoint_interval=config.n_epochs,  # Single checkpoint at end
        batch_size=config.n_agents,
    )
    sim_config = SimulationConfig(
        scale=tier,
        export_npy=True,
        artifact_dir=artifact_dir,
        persist_to_db=False,
    )

    runner = BatchSimulationRunner(sim_config)

    rng = np.random.default_rng(42)
    agents = rng.normal(0.5, 0.25, (config.n_agents, 256)).astype(np.float32)

    for i in range(config.n_universes):
        spec = UniverseSpec(f"pipeline_u{i}", seed=i)
        runner.simulate_universe(spec, agents.copy())

    npy_files = sorted(artifact_dir.glob("*.npy"))
    logger.info("Mass sim exported %d .npy files to %s", len(npy_files), artifact_dir)
    return npy_files


def step_2_train_vae(config: PipelineConfig, data_dir: Path) -> tuple[float, Path]:
    """Train FLUME VAE on exported .npy data."""
    from cohezion.flume.training import FlumeVAETrainer, TrainConfig

    logger.info("=== Step 2: VAE Training ===")

    checkpoint_dir = config.output_dir / "vae_checkpoints"
    train_config = TrainConfig(
        epochs=config.vae_epochs,
        batch_size=config.vae_batch_size,
        data_dir=str(data_dir),
        checkpoint_dir=str(checkpoint_dir),
        log_interval=max(1, config.vae_epochs // 5),
    )

    trainer = FlumeVAETrainer(train_config)
    metrics = trainer.train()

    final_loss = metrics[-1]["total"] if metrics else float("inf")
    checkpoint_path = checkpoint_dir / f"flume_vae_ep{config.vae_epochs}.pt"

    logger.info("VAE training complete. Final loss: %.4f", final_loss)
    return final_loss, checkpoint_path


def step_3_train_rl(config: PipelineConfig) -> tuple[float, Path]:
    """Train RL policy with CompositeReward."""
    from cohezion.rl.trainer import TrainingConfig, train

    logger.info("=== Step 3: RL Training ===")

    output_dir = config.output_dir / "rl_checkpoints"
    rl_config = TrainingConfig(
        n_episodes=config.rl_episodes,
        max_steps=config.rl_max_steps,
        output_dir=str(output_dir),
        log_interval=max(1, config.rl_episodes // 5),
        save_interval=config.rl_episodes,  # Save only at end
    )

    results = train(rl_config)

    final_coherence = results[-1].mean_coherence if results else 0.0
    policy_path = output_dir / "policy_final.pt"

    logger.info("RL training complete. Final coherence: %.4f", final_coherence)
    return final_coherence, policy_path


def step_4_weight_bridge(policy_path: Path) -> tuple[bool, float]:
    """Transfer RL weights to FlumePhysics and validate coherence."""
    from cohezion.pipeline.weight_bridge import WeightBridge

    logger.info("=== Step 4: Weight Bridge ===")

    weights = WeightBridge.policy_to_flume_weights(policy_path)
    logger.info("Extracted weights: w1=%s, w2=%s", weights["w1"].shape, weights["w2"].shape)

    # Create FlumePhysics with trained weights
    physics = WeightBridge.policy_to_flume_physics(policy_path)

    # Validate coherence
    validation = WeightBridge.validate_coherence(physics, n_agents=100, n_epochs=100)

    logger.info(
        "Validation: mean_coherence=%.4f, pct_within=%.1f%%, valid=%s",
        validation["mean_coherence"],
        validation["pct_within_bounds"] * 100,
        validation["valid"],
    )
    return validation["valid"], validation["mean_coherence"]


def step_5_validate_with_factory(policy_path: Path) -> float:
    """Validate that UniverseFactory can use pre-trained weights."""
    from cohezion.mass_sim.config import UniverseSpec
    from cohezion.mass_sim.universe_factory import UniverseFactory
    from cohezion.pipeline.weight_bridge import WeightBridge

    logger.info("=== Step 5: Factory Validation ===")

    weights = WeightBridge.policy_to_flume_weights(policy_path)
    spec = UniverseSpec("validation", seed=99)
    physics = UniverseFactory.create(spec, weights=weights)

    rng = np.random.default_rng(42)
    agents = rng.normal(0.5, 0.25, (50, 256)).astype(np.float32)
    evolved = physics.simulate_epochs_navigated(agents, 100)
    stats = physics.compute_batch_stats(evolved)

    mean_coh = float(stats.get("mean_coherence", 0.0))
    logger.info("Factory validation: mean_coherence=%.4f", mean_coh)
    return mean_coh


def run_pipeline(config: PipelineConfig | None = None) -> PipelineResult:
    """Execute the full pipeline end-to-end."""
    if config is None:
        config = PipelineConfig()

    config.output_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    # Step 1: Mass sim
    npy_files = step_1_mass_sim(config)

    # Step 2: VAE training
    data_dir = config.output_dir / "npy"
    vae_loss, _vae_ckpt = step_2_train_vae(config, data_dir)

    # Step 3: RL training
    rl_coherence, policy_path = step_3_train_rl(config)

    # Step 4: Weight bridge
    valid, mean_coh = step_4_weight_bridge(policy_path)

    # Step 5: Factory validation
    factory_coh = step_5_validate_with_factory(policy_path)

    elapsed = time.time() - t0

    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETE in %.1fs", elapsed)
    logger.info("  .npy files:        %d", len(npy_files))
    logger.info("  VAE final loss:    %.4f", vae_loss)
    logger.info("  RL coherence:      %.4f", rl_coherence)
    logger.info("  Weight bridge:     %s (coherence=%.4f)", valid, mean_coh)
    logger.info("  Factory coherence: %.4f", factory_coh)
    logger.info("=" * 60)

    return PipelineResult(
        npy_files=npy_files,
        vae_final_loss=vae_loss,
        rl_final_coherence=rl_coherence,
        weight_bridge_valid=valid,
        mean_coherence=mean_coh,
        elapsed_seconds=elapsed,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="End-to-end FLUME training pipeline")
    parser.add_argument("--agents", type=int, default=100, help="Agents per universe")
    parser.add_argument("--epochs", type=int, default=1000, help="Simulation epochs per universe")
    parser.add_argument("--universes", type=int, default=5, help="Number of universes")
    parser.add_argument("--vae-epochs", type=int, default=10, help="VAE training epochs")
    parser.add_argument("--rl-episodes", type=int, default=50, help="RL training episodes")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/pipeline",
        help="Output directory",
    )
    args = parser.parse_args()

    config = PipelineConfig(
        n_agents=args.agents,
        n_epochs=args.epochs,
        n_universes=args.universes,
        vae_epochs=args.vae_epochs,
        rl_episodes=args.rl_episodes,
        output_dir=Path(args.output_dir),
    )

    result = run_pipeline(config)
    sys.exit(0 if result.weight_bridge_valid else 1)


if __name__ == "__main__":
    main()
