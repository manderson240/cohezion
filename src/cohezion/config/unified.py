"""
ASCENDED COHEZION - Unified Configuration System
Compound Engineering Layer 1: Configuration Foundation

Centralizes all configuration to make future changes easier.
Each component uses this config, making the system more maintainable.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path


logger = logging.getLogger(__name__)


@dataclass
class UniverseTrackConfig:
    """Configuration for a universe simulation track"""

    name: str
    duration_hours: int
    universes: int
    particles_per_universe: int
    epochs: int
    mode: str = "conservative"
    schedule: str = "daily"


@dataclass
class EmailConfig:
    """Email notification configuration"""

    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    username: str = ""
    password: str = ""
    sender: str = ""
    recipient: str = "manderson240@gmail.com"
    enabled: bool = False
    digest_hour: int = 16
    digest_minute: int = 0


@dataclass
class CloudGraderConfig:
    """Cloud grading configuration"""

    primary_model: str = "kimi-k2.5"
    fallback_models: list[str] = field(default_factory=lambda: ["qwen3-coder:30b", "deepseek-r1:7b", "phi4"])
    consensus_threshold: float = 0.7
    request_timeout: int = 120
    max_retries: int = 3


@dataclass
class SystemConfig:
    """Root configuration for ASCENDED COHEZION"""

    # Paths
    root_dir: Path = Path("/home/mike-anderson/dev/cohezion")
    data_dir: Path = field(default_factory=lambda: Path("/home/mike-anderson/dev/cohezion/data"))
    logs_dir: Path = field(default_factory=lambda: Path("/home/mike-anderson/dev/cohezion/logs"))

    # Universe tracks
    tracks: dict[str, UniverseTrackConfig] = field(
        default_factory=lambda: {
            "rapid": UniverseTrackConfig(
                name="Rapid",
                duration_hours=4,
                universes=6,
                particles_per_universe=10000,
                epochs=20,
                mode="conservative",
                schedule="6h",
            ),
            "balanced": UniverseTrackConfig(
                name="Balanced",
                duration_hours=12,
                universes=3,
                particles_per_universe=100000,
                epochs=20,
                mode="performance",
                schedule="12h",
            ),
            "deep": UniverseTrackConfig(
                name="Deep",
                duration_hours=24,
                universes=1,
                particles_per_universe=1000000,
                epochs=24,
                mode="performance",
                schedule="24h",
            ),
        }
    )

    # Email
    email: EmailConfig = field(default_factory=EmailConfig)

    # Cloud grading
    grading: CloudGraderConfig = field(default_factory=CloudGraderConfig)

    # HIHO target
    hiho_target: float = 0.5
    hiho_range: tuple = (0.45, 0.55)

    # Resource limits
    max_memory_gb: int = 112  # Strix Halo allocatable
    target_buffer_gb: int = 20

    @classmethod
    def from_env(cls) -> "SystemConfig":
        """Load configuration from environment variables"""
        config = cls()

        # Override from .env if available
        if os.getenv("GOOGLE_EMAIL"):
            config.email.sender = os.getenv("GOOGLE_EMAIL")
            config.email.recipient = os.getenv("NOTIFICATION_EMAIL", config.email.recipient)

        if os.getenv("NOTIFICATION_PASSWORD"):
            config.email.password = os.getenv("NOTIFICATION_PASSWORD")
            config.email.enabled = True

        # Load from JSON config if exists
        config_path = Path.home() / ".config" / "cohezion" / "system_config.json"
        if config_path.exists():
            try:
                with open(config_path) as f:
                    data = json.load(f)
                    # Apply overrides
                    if "email" in data:
                        for key, value in data["email"].items():
                            setattr(config.email, key, value)
                    if "tracks" in data:
                        for track_name, track_data in data["tracks"].items():
                            if track_name in config.tracks:
                                for key, value in track_data.items():
                                    setattr(config.tracks[track_name], key, value)
            except Exception as e:
                logger.warning("Could not load config from %s: %s", config_path, e)

        return config

    def save(self):
        """Save configuration to disk"""
        config_path = Path.home() / ".config" / "cohezion" / "system_config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "email": {
                "smtp_server": self.email.smtp_server,
                "smtp_port": self.email.smtp_port,
                "sender": self.email.sender,
                "recipient": self.email.recipient,
                "enabled": self.email.enabled,
                "digest_hour": self.email.digest_hour,
                "digest_minute": self.email.digest_minute,
            },
            "tracks": {
                name: {
                    "duration_hours": track.duration_hours,
                    "universes": track.universes,
                    "particles_per_universe": track.particles_per_universe,
                    "epochs": track.epochs,
                    "mode": track.mode,
                }
                for name, track in self.tracks.items()
            },
            "hiho_target": self.hiho_target,
            "hiho_range": self.hiho_range,
        }

        with open(config_path, "w") as f:
            json.dump(data, f, indent=2)


# Singleton instance
_config_instance = None


def get_config() -> SystemConfig:
    """Get or create the global configuration singleton"""
    global _config_instance
    if _config_instance is None:
        _config_instance = SystemConfig.from_env()
    return _config_instance


def reload_config() -> SystemConfig:
    """Force reload configuration from environment"""
    global _config_instance
    _config_instance = SystemConfig.from_env()
    return _config_instance
