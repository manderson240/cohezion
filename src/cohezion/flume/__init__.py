"""FLUME VAE module for semantic embeddings and latent space operations."""

from cohezion.flume.vae_encoder import FlumeVAEEncoder


__all__ = [
    "ExperienceDataset",
    "ExperienceEncoder",
    "ExperienceTrainingPipeline",
    "FlumeEncoder",
    "FlumeVAEEncoder",
]


def __getattr__(name: str):
    """Lazy imports for experience pipeline classes."""
    if name == "FlumeEncoder":
        from cohezion.flume.autoencoder import FlumeEncoder

        return FlumeEncoder
    if name == "ExperienceEncoder":
        from cohezion.flume.experience_encoder import ExperienceEncoder

        return ExperienceEncoder
    if name == "ExperienceDataset":
        from cohezion.flume.experience_dataset import ExperienceDataset

        return ExperienceDataset
    if name == "ExperienceTrainingPipeline":
        from cohezion.flume.experience_pipeline import ExperienceTrainingPipeline

        return ExperienceTrainingPipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
