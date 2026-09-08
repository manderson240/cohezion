"""FLUME VAE module for semantic embeddings and latent space operations."""

import contextlib

from cohezion.flume.vae_encoder import FlumeVAEEncoder


# Wiring-sweep 2026-06-22: diversity.py was a genuine import-graph orphan (Gvendi diversity
# filter + LatentDirectionProbe for mechanistic interpretability).
with contextlib.suppress(Exception):
    from cohezion.flume.diversity import (
        ConceptDirection as ConceptDirection,
    )
    from cohezion.flume.diversity import (
        LatentDirectionProbe as LatentDirectionProbe,
    )
    from cohezion.flume.diversity import (
        gvendi_diversity_filter as gvendi_diversity_filter,
    )

# Wiring-sweep 2026-06-22: skill_state_encoder.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.flume.skill_state_encoder import (
        SkillStateEncoder as SkillStateEncoder,
    )


__all__ = [
    "DomainEncoder",
    "EncodedTrajectoryPoint",
    "ExperienceDataset",
    "ExperienceEncoder",
    "ExperienceTrainingPipeline",
    "FlumeVAEEncoder",
    "capture_trajectory",
    "get_encoder",
]


def __getattr__(name: str):
    """Lazy imports for experience pipeline classes."""
    if name == "ExperienceEncoder":
        from cohezion.flume.experience_encoder import ExperienceEncoder

        return ExperienceEncoder
    if name == "ExperienceDataset":
        from cohezion.flume.experience_dataset import ExperienceDataset

        return ExperienceDataset
    if name == "ExperienceTrainingPipeline":
        from cohezion.flume.experience_pipeline import ExperienceTrainingPipeline

        return ExperienceTrainingPipeline
    if name == "DomainEncoder":
        from cohezion.flume.domain_encoder import DomainEncoder

        return DomainEncoder
    if name == "EncodedTrajectoryPoint":
        from cohezion.flume.domain_encoder import EncodedTrajectoryPoint

        return EncodedTrajectoryPoint
    if name == "get_encoder":
        from cohezion.flume.domain_encoder import get_encoder

        return get_encoder
    if name == "capture_trajectory":
        from cohezion.flume.trajectory_capture import capture_trajectory

        return capture_trajectory
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# Wiring-sweep 2026-06-22: vae.py was a genuine import-graph orphan (FlumeVAE is the
# canonical VAE used by the compound loop; build_optimal_vae is harness invariant A4).
with contextlib.suppress(Exception):
    from cohezion.flume.vae import FlumeVAE as FlumeVAE
    from cohezion.flume.vae import FlumeVAEConfig as FlumeVAEConfig
    from cohezion.flume.vae import flume_vae_loss as flume_vae_loss

# latent_health.py — SVD-based latent basis health monitor (A3 complement, #119).
with contextlib.suppress(Exception):
    from cohezion.flume.latent_health import LatentBasisMonitor as LatentBasisMonitor

# Wiring-sweep 2026-06-22: alignment.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.flume.alignment import DomainAlignmentMLP as DomainAlignmentMLP
    from cohezion.flume.alignment import LatentAligner as LatentAligner

# Wiring-sweep 2026-06-22: autoencoder.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.flume.autoencoder import FlumeConfig as FlumeConfig
    from cohezion.flume.autoencoder import FlumeEncoder as FlumeEncoder
    from cohezion.flume.autoencoder import ThoughtDecoder as ThoughtDecoder
    from cohezion.flume.autoencoder import ThoughtEncoder as ThoughtEncoder

# Wiring-sweep 2026-06-22: bioelectric.py (flume) was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.flume.bioelectric import ActionVector as ActionVector
    from cohezion.flume.bioelectric import BioelectricEngine as BioelectricEngine
    from cohezion.flume.bioelectric import BioelectricSignal as BioelectricSignal

# Wiring-sweep 2026-06-22: bridge.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.flume.bridge import HFEmbeddingBridge as HFEmbeddingBridge

# Wiring-sweep 2026-06-22: coherence_guard.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.flume.coherence_guard import TurboQuantHarness as TurboQuantHarness

# Wiring-sweep 2026-06-22: compression.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.flume.compression import FlumeCompressionPipeline as FlumeCompressionPipeline
    from cohezion.flume.compression import PolarQuantEncoder as PolarQuantEncoder
    from cohezion.flume.compression import QJLProjector as QJLProjector

# Wiring-sweep 2026-06-22: data_pipeline.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.flume.data_pipeline import ContrastivePairMiner as ContrastivePairMiner
    from cohezion.flume.data_pipeline import SyntheticTaskGenerator as SyntheticTaskGenerator
    from cohezion.flume.data_pipeline import TrainingDataPipeline as TrainingDataPipeline

# Wiring-sweep 2026-06-22: dataset.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.flume.dataset import FlumeTrajectoryDataset as FlumeTrajectoryDataset
    from cohezion.flume.dataset import SyntheticFlumeDataset as SyntheticFlumeDataset

# Wiring-sweep 2026-06-22: embedding_provider.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.flume.embedding_provider import CachedEmbeddingProvider as CachedEmbeddingProvider
    from cohezion.flume.embedding_provider import HashFallbackProvider as HashFallbackProvider
    from cohezion.flume.embedding_provider import OllamaEmbeddingProvider as OllamaEmbeddingProvider

# Wiring-sweep 2026-06-22: experience_collector.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.flume.experience_collector import ExperienceCollector as ExperienceCollector

# Wiring-sweep 2026-06-22: geometric_bridge.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.flume.geometric_bridge import GeometricLatentBridge as GeometricLatentBridge

# Wiring-sweep 2026-06-22: git_encoder.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.flume.git_encoder import GitEncoder as GitEncoder

# Wiring-sweep 2026-06-22: grid_encoder.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.flume.grid_encoder import ARCGridEncoder as ARCGridEncoder
    from cohezion.flume.grid_encoder import FlumeGridHarness as FlumeGridHarness

# Wiring-sweep 2026-06-22: journey_encoder.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.flume.journey_encoder import JourneyEncoderConfig as JourneyEncoderConfig
    from cohezion.flume.journey_encoder import JourneyToFlumeEncoder as JourneyToFlumeEncoder

# Wiring-sweep 2026-06-22: journey_finetune_pipeline.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.flume.journey_finetune_pipeline import (
        JourneyToFinetuneConverter as JourneyToFinetuneConverter,
    )

# Wiring-sweep 2026-06-22: latent_channel.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.flume.latent_channel import LatentMessage as LatentMessage
    from cohezion.flume.latent_channel import SharedLatentMemory as SharedLatentMemory
    from cohezion.flume.latent_channel import get_shared_latent_memory as get_shared_latent_memory

# Wiring-sweep 2026-06-22: lcsp.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.flume.lcsp import LCSPPrediction as LCSPPrediction
    from cohezion.flume.lcsp import LCSPPredictor as LCSPPredictor

# Wiring-sweep 2026-06-22: local_finetune_pipeline.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.flume.local_finetune_pipeline import LocalFinetuner as LocalFinetuner

# Wiring-sweep 2026-06-22: mnm.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.flume.mnm import ManifoldManager as ManifoldManager
    from cohezion.flume.mnm import ManifoldWarp as ManifoldWarp

# Wiring-sweep 2026-06-22: morphospace.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.flume.morphospace import MorphoPath as MorphoPath
    from cohezion.flume.morphospace import MorphospaceMapper as MorphospaceMapper
    from cohezion.flume.morphospace import StabilityWell as StabilityWell

# Wiring-sweep 2026-06-22: mps_compressor.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.flume.mps_compressor import MPSCompressor as MPSCompressor

# Wiring-sweep 2026-06-22: navigation.py was a genuine import-graph orphan (lerp/slerp).
with contextlib.suppress(Exception):
    from cohezion.flume.navigation import lerp as lerp
    from cohezion.flume.navigation import similarity_score as similarity_score
    from cohezion.flume.navigation import slerp as slerp

# Wiring-sweep 2026-06-22: navigator.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.flume.navigator import FlumeNavigator as FlumeNavigator

# Wiring-sweep 2026-06-22: predictor.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.flume.predictor import TrajectoryPredictor as TrajectoryPredictor

# Wiring-sweep 2026-06-22: spectral_encoder.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.flume.spectral_encoder import SpectralEncoder as SpectralEncoder

# Wiring-sweep 2026-06-22: tda_detector.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.flume.tda_detector import TDADetector as TDADetector

# Wiring-sweep 2026-06-22: temporal_encoder.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.flume.temporal_encoder import TemporalDecoder as TemporalDecoder
    from cohezion.flume.temporal_encoder import TemporalEncoder as TemporalEncoder
    from cohezion.flume.temporal_encoder import TemporalVAELoader as TemporalVAELoader

# Wiring-sweep 2026-06-22: tokenizer.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.flume.tokenizer import FlumeTokenizer as FlumeTokenizer

# Wiring-sweep 2026-06-22: train.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.flume.train import FlumeTrainConfig as FlumeTrainConfig

# Wiring-sweep 2026-06-22: training.py was a genuine import-graph orphan (VAE trainer).
with contextlib.suppress(Exception):
    from cohezion.flume.training import FlumeVAETrainer as FlumeVAETrainer
    from cohezion.flume.training import TrainConfig as TrainConfig

# Wiring-sweep 2026-06-22: trajectory_dataset.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.flume.trajectory_dataset import (
        TrajectorySequenceDataset as TrajectorySequenceDataset,
    )

# Wiring-sweep 2026-06-22: turbo_quant.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.flume.turbo_quant import TurboQuantCPU as TurboQuantCPU

# Wiring-sweep 2026-06-22: evaluate_vae.py was a genuine import-graph orphan (VAE evaluator).
with contextlib.suppress(Exception):
    from cohezion.flume.evaluate_vae import VAEEvaluator as VAEEvaluator

# Wiring-sweep 2026-06-22: vliw_kernel_sim.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.flume.vliw_kernel_sim import VLIWSimulator as VLIWSimulator

# Wiring-sweep 2026-06-22: sparse_analysis.py — overcomplete dictionary learning.
with contextlib.suppress(Exception):
    from cohezion.flume.sparse_analysis import (
        SparseLatentAnalysis as SparseLatentAnalysis,
    )
