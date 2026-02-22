"""Configuration for Trigger.dev integration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class TriggerConfig:
    """Trigger.dev connection and task configuration.

    Parameters
    ----------
    api_url : str
        Base URL of the Trigger.dev instance (cloud or self-hosted).
    secret_key : str
        Secret API key (``tr_dev_*``, ``tr_prod_*``, etc.).
    project_ref : str
        Trigger.dev project reference identifier.
    default_queue : str
        Default queue name for tasks.
    max_concurrent : int
        Default max concurrent runs per queue.
    """

    api_url: str = field(
        default_factory=lambda: os.environ.get(
            "TRIGGER_API_URL", "https://api.trigger.dev"
        )
    )
    secret_key: str = field(
        default_factory=lambda: os.environ.get("TRIGGER_SECRET_KEY", "")
    )
    project_ref: str = field(
        default_factory=lambda: os.environ.get("TRIGGER_PROJECT_REF", "cohezion")
    )
    default_queue: str = "cohezion-default"
    max_concurrent: int = 4

    @property
    def is_configured(self) -> bool:
        """Return True if a secret key is available."""
        return bool(self.secret_key)

    @property
    def headers(self) -> dict[str, str]:
        """HTTP headers for Trigger.dev API requests."""
        return {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }
