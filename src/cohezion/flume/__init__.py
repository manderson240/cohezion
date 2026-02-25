"""FLUME VAE module for semantic embeddings and latent space operations."""

from cohezion.flume.vae_encoder import FlumeVAEEncoder


__all__ = [
    "ExperienceDataset",
    "ExperienceEncoder",
    "ExperienceTrainingPipeline",
    "FlumeVAE",
    "FlumeVAEEncoder",
    "TemporalEncoder",
    "VAEEvaluator",
    "VAETrainer",
]


def __getattr__(name: str):
    """Lazy imports for pipeline classes."""
    if name == "ExperienceEncoder":
        from cohezion.flume.experience_encoder import ExperienceEncoder

        return ExperienceEncoder
    if name == "ExperienceDataset":
        from cohezion.flume.experience_dataset import ExperienceDataset

        return ExperienceDataset
    if name == "ExperienceTrainingPipeline":
        from cohezion.flume.experience_pipeline import ExperienceTrainingPipeline

        return ExperienceTrainingPipeline
    if name == "FlumeVAE":
        from cohezion.flume.vae import FlumeVAE

        return FlumeVAE
    if name == "VAETrainer":
        from cohezion.flume.train_vae import VAETrainer

        return VAETrainer
    if name == "VAEEvaluator":
        from cohezion.flume.evaluate_vae import VAEEvaluator

        return VAEEvaluator
    if name == "TemporalEncoder":
        from cohezion.flume.temporal_encoder import TemporalEncoder

        return TemporalEncoder
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
