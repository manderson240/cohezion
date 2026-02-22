"""Configuration management for cohezion-engine."""
from pathlib import Path


def get_config_dir() -> Path:
    """Return the cohezion-engine config directory, creating it if needed."""
    config_dir = Path.home() / ".cohezion-engine"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir
