"""System Guardrails for COHEZION Simulations.

Prevents OOM errors and manages resource allocation.
"""

import os
import subprocess
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SystemGuardrails:
    """System resource guardrails configuration."""

    min_free_gb: int = 20
    max_memory_percent: int = 85
    max_concurrent_agents: int = 4
    max_concurrent_benchmarks: int = 2
    default_local_model: str = "qwen3-coder:30b"
    reasoning_model: str = "deepseek-r1:7b"
    embedding_model: str = "nomic-embed-text:latest"
    max_humaneval_problems: int = 50
    max_batch_size: int = 10

    def check_memory(self) -> bool:
        """Check if sufficient memory is available."""
        try:
            result = subprocess.run(
                ["free", "-g"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            for line in result.stdout.split("\n"):
                if line.startswith("Mem:"):
                    parts = line.split()
                    available = int(parts[6])
                    if available < self.min_free_gb:
                        logger.warning(
                            f"Low memory: {available}GB available, need {self.min_free_gb}GB minimum"
                        )
                        return False
                    logger.info(f"Memory OK: {available}GB available")
                    return True
        except Exception as e:
            logger.error(f"Failed to check memory: {e}")
        return True  # Assume OK if check fails

    def check_process_count(self) -> bool:
        """Check if process count is within limits."""
        try:
            result = subprocess.run(
                ["pgrep", "-f", "python.*cohezion"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            count = (
                len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0
            )
            if count >= self.max_concurrent_agents:
                logger.warning(
                    f"High process count: {count} (max: {self.max_concurrent_agents})"
                )
                return False
            logger.info(f"Process count OK: {count} running")
            return True
        except Exception as e:
            logger.error(f"Failed to check process count: {e}")
        return True

    def get_local_model(self, preferred: Optional[str] = None) -> str:
        """Get available local Ollama model."""
        model = preferred or self.default_local_model

        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            base_name = model.split(":")[0]
            if base_name in result.stdout:
                return model
        except Exception as e:
            logger.warning(f"Could not check Ollama models: {e}")

        # Fallback chain
        fallbacks = [
            "qwen3:8b",
            "mistral:latest",
            "phi4-mini-reasoning:latest",
        ]
        for fallback in fallbacks:
            try:
                result = subprocess.run(
                    ["ollama", "list"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if fallback.split(":")[0] in result.stdout:
                    logger.info(f"Falling back to model: {fallback}")
                    return fallback
            except Exception:
                continue

        logger.error("No local models available!")
        return "llama3.2-vision:11b-instruct-fp16"

    def can_run_simulation(self) -> bool:
        """Check if system can safely run a new simulation."""
        return self.check_memory() and self.check_process_count()


# Global guardrails instance
guardrails = SystemGuardrails()


def get_guardrails() -> SystemGuardrails:
    """Get the global guardrails instance."""
    return guardrails
