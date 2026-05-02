"""
Ollama Model Manager - Benchmark, auto-swap, and storage management.

Handles:
- Model benchmarking per task type
- Automatic swapping of underperformers
- Storage cleanup of unused models
- Landscape research for new models
"""

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx


logger = logging.getLogger(__name__)

OLLAMA_HOST = "http://localhost:11434"
METRICS_PATH = Path(__file__).parent.parent / "knowledge_graph" / "model_metrics.json"


@dataclass
class ModelMetrics:
    """Metrics for a single model."""

    name: str
    task_type: str  # analysis, critique, synthesis, function_call, vision
    avg_latency_ms: float = 0.0
    success_rate: float = 1.0
    quality_score: float = 0.5  # 0-1, from critique feedback
    total_calls: int = 0
    last_used: str = ""
    confidence_score: float = 0.0  # 0-1, dynamic confidence estimate
    confidence_samples: int = 0  # Number of samples for confidence calculation

    def update(self, latency_ms: float, success: bool, quality: float = 0.5):
        n = self.total_calls
        self.avg_latency_ms = (self.avg_latency_ms * n + latency_ms) / (n + 1)
        self.success_rate = (self.success_rate * n + (1.0 if success else 0.0)) / (n + 1)
        self.quality_score = (self.quality_score * n + quality) / (n + 1)
        self.total_calls += 1
        self.last_used = datetime.now().isoformat()

        # Update confidence score using Bayesian updating
        if n > 0:
            # Confidence is based on success rate and quality score
            self.confidence_score = self.success_rate * 0.6 + self.quality_score * 0.4
            # Apply sample size adjustment - more samples = higher confidence
            sample_adjustment = min(1.0, n / 50.0)  # Cap at 50 samples
            self.confidence_score *= sample_adjustment
        else:
            self.confidence_score = 0.0

        self.confidence_samples = n + 1


@dataclass
class ModelConfig:
    """Configuration for model roles."""

    role: str
    primary: str
    fallback: str | None = None
    min_quality: float = 0.6


# Default role assignments (aligned with installed Ollama roster)
DEFAULT_ROLES: list[ModelConfig] = [
    ModelConfig("analysis", "phi4:latest", "gemma3:4b"),
    ModelConfig("critique", "deepseek-r1:7b", "qwen3:8b"),
    ModelConfig("synthesis", "qwen2.5-coder:7b", "qwen2.5-coder:14b"),
    ModelConfig("function_call", "qwen2.5-coder:7b", "qwen3:8b"),
    ModelConfig("vision", "minicpm-v:8b-2.6-fp16", "llama3.2-vision:11b-instruct-fp16"),
]


class OllamaModelManager:
    """
    Manages Ollama models with benchmarking and auto-optimization.

    Features:
    - Track performance metrics per model per task
    - Automatically swap underperforming models
    - Clean up unused models to save storage
    - Research new models from landscape
    """

    def __init__(self, ollama_host: str = OLLAMA_HOST):
        self.ollama_host = ollama_host
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self._metrics: dict[str, ModelMetrics] = {}
        self._roles = {r.role: r for r in DEFAULT_ROLES}
        self._load_metrics()

    def _load_metrics(self) -> None:
        """Load metrics from persistent storage."""
        if METRICS_PATH.exists():
            data = json.loads(METRICS_PATH.read_text())
            for key, m in data.get("metrics", {}).items():
                self._metrics[key] = ModelMetrics(**m)

    def _save_metrics(self) -> None:
        """Save metrics to persistent storage."""
        METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "updated": datetime.now().isoformat(),
            "metrics": {k: vars(v) for k, v in self._metrics.items()},
        }
        METRICS_PATH.write_text(json.dumps(data, indent=2))

    async def list_models(self) -> list[dict[str, Any]]:
        """List installed Ollama models."""
        try:
            resp = await self.http_client.get(f"{self.ollama_host}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            return data.get("models", [])
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

    async def pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama registry."""
        try:
            resp = await self.http_client.post(
                f"{self.ollama_host}/api/pull",
                json={"name": model_name},
                timeout=600.0,  # Long timeout for large models
            )
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Failed to pull {model_name}: {e}")
            return False

    async def delete_model(self, model_name: str) -> bool:
        """Delete a model to free storage."""
        try:
            resp = await self.http_client.delete(
                f"{self.ollama_host}/api/delete",
                json={"name": model_name},
            )
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Failed to delete {model_name}: {e}")
            return False

    async def benchmark_model(
        self,
        model_name: str,
        task_type: str,
        test_prompt: str = "Explain quantum computing in one sentence.",
    ) -> ModelMetrics:
        """Benchmark a model for a specific task type with Context Guard."""
        key = f"{model_name}:{task_type}"

        if key not in self._metrics:
            self._metrics[key] = ModelMetrics(name=model_name, task_type=task_type)

        metrics = self._metrics[key]

        # --- CONTEXT GUARD (Learning 77) ---
        safe_prompt = self._sanitize_prompt(test_prompt)
        # -----------------------------------

        start = time.perf_counter()
        try:
            resp = await self.http_client.post(
                f"{self.ollama_host}/api/generate",
                json={"model": model_name, "prompt": safe_prompt, "stream": False},
                timeout=60.0,
            )
            latency_ms = (time.perf_counter() - start) * 1000

            success = resp.status_code == 200
            quality = 0.7 if success else 0.0  # Basic quality estimate

            metrics.update(latency_ms, success, quality)
            self._save_metrics()

            logger.info(f"Benchmarked {model_name} for {task_type}: {latency_ms:.0f}ms")

        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            metrics.update(latency_ms, False, 0.0)
            logger.error(f"Benchmark failed for {model_name}: {e}")

        return metrics

    def _sanitize_prompt(self, prompt: str, max_chars: int = 20000) -> str:
        """
        Truncate or summarize prompt if it exceeds the safety threshold.
        Prevents crashes like the one on 2026-01-31.
        """
        if len(prompt) <= max_chars:
            return prompt

        logger.warning(f"⚠️ Context Guard: Truncating large prompt ({len(prompt)} chars)")
        header = f"--- CONTEXT TRUNCATED ({len(prompt)} -> {max_chars}) ---\n"
        footer = "\n--- END TRUNCATED CONTEXT ---"

        # Take the first 10k and last 10k chars
        half = max_chars // 2
        return f"{header}{prompt[:half]} ... [SNIP] ... {prompt[-half:]}{footer}"

    async def get_model_confidence(self, model_name: str, task_type: str) -> float:
        """Get confidence score for a model on a specific task."""
        key = f"{model_name}:{task_type}"
        metrics = self._metrics.get(key)
        if metrics:
            return metrics.confidence_score
        return 0.0

    async def get_recommended_model(self, task_type: str, min_confidence: float = 0.3) -> str | None:
        """Get the best model for a task based on confidence scores."""
        candidates = []
        for model_name in await self.list_models():
            model_name = model_name["name"]
            confidence = await self.get_model_confidence(model_name, task_type)
            if confidence >= min_confidence:
                candidates.append((model_name, confidence))

        if candidates:
            # Return model with highest confidence
            return max(candidates, key=lambda x: x[1])[0]
        return None

    async def should_escalate(self, model_name: str, task_type: str, min_confidence: float = 0.3) -> bool:
        """Check if we should escalate to a stronger model."""
        confidence = await self.get_model_confidence(model_name, task_type)
        return confidence < min_confidence

    def get_best_model(self, task_type: str) -> str:
        """Get the best performing model for a task type."""
        role = self._roles.get(task_type)
        if not role:
            return "phi4:latest"  # Default

        # Check if primary meets quality threshold
        key = f"{role.primary}:{task_type}"
        if key in self._metrics:
            if self._metrics[key].quality_score >= role.min_quality:
                return role.primary
            elif role.fallback:
                return role.fallback

        return role.primary

    def record_result(
        self,
        model_name: str,
        task_type: str,
        latency_ms: float,
        success: bool,
        quality: float = 0.5,
    ) -> None:
        """Record a model result for tracking."""
        key = f"{model_name}:{task_type}"
        if key not in self._metrics:
            self._metrics[key] = ModelMetrics(name=model_name, task_type=task_type)

        self._metrics[key].update(latency_ms, success, quality)
        self._save_metrics()

    async def cleanup_unused(self, days_threshold: int = 30) -> list[str]:
        """Remove models not used in the last N days."""
        deleted = []
        cutoff = datetime.now().timestamp() - (days_threshold * 86400)

        models = await self.list_models()
        for model in models:
            name = model.get("name", "")

            # Check last used across all task types
            last_used = None
            for _key, metrics in self._metrics.items():
                if metrics.name == name and metrics.last_used:
                    used_ts = datetime.fromisoformat(metrics.last_used).timestamp()
                    if last_used is None or used_ts > last_used:
                        last_used = used_ts

            if last_used and last_used < cutoff and await self.delete_model(name):
                deleted.append(name)
                logger.info(f"Cleaned up unused model: {name}")

        return deleted

    def get_role_assignments(self) -> dict[str, str]:
        """Get current role → model assignments."""
        return {role: self.get_best_model(role) for role in self._roles}

    def get_metrics_summary(self) -> dict[str, Any]:
        """Get summary of all model metrics."""
        return {
            key: {
                "avg_latency_ms": m.avg_latency_ms,
                "success_rate": m.success_rate,
                "quality_score": m.quality_score,
                "total_calls": m.total_calls,
            }
            for key, m in self._metrics.items()
        }


# Singleton
_manager: OllamaModelManager | None = None


def get_manager() -> OllamaModelManager:
    global _manager
    if _manager is None:
        _manager = OllamaModelManager()
    return _manager
