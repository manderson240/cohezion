import logging
import shutil
import subprocess
from pathlib import Path


logger = logging.getLogger(__name__)


class LocalRegistry:
    """
    Dynamic Local Model Registry (Gateway 28).

    Manages the "Active Roster" of Sovereign models.
    Prevents 404s by verifying installed models via `ollama list`.
    Enforces storage safety limits (20GB headroom).
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._minit()
        return cls._instance

    def _minit(self):
        self.roster_path = Path("src/cohezion/core/roster.json")
        self.available_models: set[str] = set()
        self.refresh()

    def refresh(self):
        """Scans local Ollama instance for installed models."""
        try:
            result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                # Parse output (skip header)
                lines = result.stdout.strip().split("\n")[1:]
                self.available_models = {line.split()[0] for line in lines}
                logger.info(f"🛡️ Local Registry Refreshed: {len(self.available_models)} models found.")
                logger.debug(f"Available: {self.available_models}")
            else:
                logger.warning("Failed to list Ollama models.")
        except Exception as e:
            logger.error(f"Registry refresh error: {e}")

    def is_available(self, model_name: str) -> bool:
        """Check if a model is installed."""
        # Handle tags (e.g. mistral:7b vs mistral)
        if model_name in self.available_models:
            return True
        # Try finding partial match if no tag provided
        return any(m.startswith(model_name) for m in self.available_models)

    def get_best_available_local(self, preferred: list[str]) -> str:
        """
        Return the first available model from the preferred list.
        Falls back to 'phi3:mini' or 'mistral:7b' if nothing matches.
        """
        for model in preferred:
            if self.is_available(model):
                return model

        # Emergency fallbacks
        for fallback in ["phi3:mini", "deepseek-r1:7b", "gemma3:4b"]:
            if self.is_available(fallback):
                return fallback

        return "phi3:mini"  # Hope and pray

    def check_capacity(self, min_gb: float = 20.0) -> bool:
        """
        Check if system has enough storage headroom.
        """
        _total, _used, free = shutil.disk_usage("/")
        free_gb = free / (1024**3)
        return free_gb >= min_gb


def get_local_registry() -> LocalRegistry:
    return LocalRegistry()
