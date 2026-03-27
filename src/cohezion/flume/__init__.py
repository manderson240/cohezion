"""FLUME VAE module for semantic embeddings and latent space operations."""

from cohezion.flume.vae_encoder import FlumeVAEEncoder


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
