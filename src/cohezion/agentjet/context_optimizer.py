# ruff: noqa: RUF003  # math/physics symbols intentional
"""Per-model context profiles and OOM-safe Ollama lifecycle management."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

import aiohttp


logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"
TOTAL_SYSTEM_MEMORY_GB = 128.0
SAFETY_BUFFER_GB = 10.0
OS_OVERHEAD_GB = 8.0

_DEFAULT_HOT_MODELS = ["phi4-mini-reasoning:latest", "nomic-embed-text:latest"]


@dataclass
class ModelContextProfile:
    """Per-model Ollama context settings to prevent KV-cache OOM."""

    model_name: str
    num_ctx: int  # Context window (KV cache driver)
    num_gpu: int = -1  # GPU layers (-1 = all)
    flash_attention: bool = True  # Reduces KV cache ~50%
    rope_scaling: str = "linear"  # "linear"|"ntk"|"yarn"
    num_parallel: int = 1  # Concurrent requests
    keep_alive: str = "5m"  # How long to keep loaded ("0" = unload immediately)
    size_gb: float = 0.0  # Approximate model size in GB (for OOM checks)


def _mk(
    model_name: str, num_ctx: int, size_gb: float, flash_attention: bool = True, **kw: object
) -> ModelContextProfile:
    return ModelContextProfile(
        model_name=model_name,
        num_ctx=num_ctx,
        size_gb=size_gb,
        flash_attention=flash_attention,
        **kw,
    )  # type: ignore[arg-type]


def _training(base: ModelContextProfile) -> ModelContextProfile:
    """Return a copy of a profile with training overrides (num_ctx=2048, keep_alive=0)."""
    return ModelContextProfile(
        model_name=base.model_name,
        num_ctx=2048,
        num_gpu=base.num_gpu,
        flash_attention=base.flash_attention,
        rope_scaling=base.rope_scaling,
        num_parallel=base.num_parallel,
        keep_alive="0",
        size_gb=base.size_gb,
    )


# ---------------------------------------------------------------------------
# Per-model context profiles
# ---------------------------------------------------------------------------
_BASE_PROFILES: list[ModelContextProfile] = [
    # Routing models (0.8B–2B): 32768 ctx
    _mk("qwen3.5:0.8b", num_ctx=32768, size_gb=1.0, flash_attention=True),
    _mk("phi4-mini-reasoning:latest", num_ctx=32768, size_gb=4.0, flash_attention=True),
    _mk("nomic-embed-text:latest", num_ctx=8192, size_gb=0.5, flash_attention=False),
    # Execution models (9B–30B): 16384 ctx
    _mk("qwen3.5:9b", num_ctx=16384, size_gb=10.0, flash_attention=True),
    _mk("nemotron-3-nano:30b", num_ctx=8192, size_gb=20.0, flash_attention=True),
    _mk("glm-4.7-flash:latest", num_ctx=16384, size_gb=8.0, flash_attention=True),
    _mk("qwen3-coder:30b", num_ctx=16384, size_gb=20.0, flash_attention=True),
    _mk("deepcoder:14b", num_ctx=16384, size_gb=14.0, flash_attention=True),
    _mk("qwen3-coder-next", num_ctx=16384, size_gb=50.0, flash_attention=True),
    _mk("minimax-m2.7", num_ctx=16384, size_gb=25.0, flash_attention=True),
    # Deep reasoning (70B+): 8192 ctx
    _mk(
        "nemotron-3-super:120b", num_ctx=8192, size_gb=30.0, flash_attention=True
    ),  # MoE, 12B active
    _mk("glm-5", num_ctx=8192, size_gb=20.0, flash_attention=True),  # 40B active params
    _mk("openai/gpt-oss-20b", num_ctx=8192, size_gb=22.0, flash_attention=True),
    # Utility / fine-tuned domain
    _mk("phi3:mini", num_ctx=8192, size_gb=4.0, flash_attention=True),
    # Fallback
    _mk("default", num_ctx=16384, size_gb=10.0, flash_attention=True),
]

# Training variants that override the base profile with reduced context and no keep_alive
_TRAINING_VARIANTS = ["qwen3.5:9b", "nemotron-3-nano:30b", "phi3:mini"]

CONTEXT_PROFILES: dict[str, ModelContextProfile] = {p.model_name: p for p in _BASE_PROFILES}

for _model_name in _TRAINING_VARIANTS:
    _key = f"{_model_name}:training"
    CONTEXT_PROFILES[_key] = _training(CONTEXT_PROFILES[_model_name])

# Maps Ollama model identifiers to LocalFinetuner base_model keys.
# Used by AgentJetTrainer and UnslothBridge to translate pull names → training keys.
MODEL_OLLAMA_KEY_MAP: dict[str, str] = {
    "qwen3.5:9b": "qwen3.5",
    "qwen3.5": "qwen3.5",
    "phi4": "phi4",
    "phi4-mini-reasoning:latest": "phi4",
    "phi3:mini": "qwen3-4b",
    "qwen3-4b": "qwen3-4b",
    "gemma3": "gemma3",
}


# ---------------------------------------------------------------------------
# OllamaContextManager
# ---------------------------------------------------------------------------


class OllamaContextManager:
    """Apply context profiles to Ollama models; enforce OOM-safe training lifecycle."""

    def __init__(self, base_url: str = OLLAMA_BASE_URL) -> None:
        self._base_url = base_url.rstrip("/")
        self._cached_available_gb: float = (
            TOTAL_SYSTEM_MEMORY_GB - OS_OVERHEAD_GB - SAFETY_BUFFER_GB
        )

    # ------------------------------------------------------------------
    # Profile lookup
    # ------------------------------------------------------------------

    def get_profile(self, model_name: str) -> ModelContextProfile:
        """Return profile for model; falls back to 'default' if not found."""
        return CONTEXT_PROFILES.get(model_name, CONTEXT_PROFILES["default"])

    # ------------------------------------------------------------------
    # Ollama API helpers
    # ------------------------------------------------------------------

    async def apply_profile(self, model: str, profile: ModelContextProfile) -> None:
        """Log the intended context options for a model (advisory; Ollama applies these at generate time)."""
        logger.info(
            "Context profile for %s: num_ctx=%d flash_attention=%s keep_alive=%s",
            model,
            profile.num_ctx,
            profile.flash_attention,
            profile.keep_alive,
        )

    async def get_loaded_models(self) -> list[str]:
        """Query /api/ps for currently loaded models. Returns empty list on error."""
        url = f"{self._base_url}/api/ps"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10.0)) as resp:
                    if resp.status != 200:
                        logger.warning("GET /api/ps returned HTTP %d", resp.status)
                        return []
                    data = await resp.json()
                    models: list[str] = [m["name"] for m in data.get("models", [])]
                    return models
        except TimeoutError:
            logger.warning("Timeout querying Ollama /api/ps")
            return []
        except aiohttp.ClientError as exc:
            logger.warning("ClientError querying Ollama /api/ps: %s", exc)
            return []

    async def unload_model(self, model: str) -> None:
        """Unload a specific model via POST /api/generate with keep_alive=0."""
        url = f"{self._base_url}/api/generate"
        payload = {"model": model, "keep_alive": 0}
        try:
            async with (
                aiohttp.ClientSession() as session,
                session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=30.0)) as resp,
            ):
                if resp.status not in (200, 404):
                    logger.warning("Unload of %s returned HTTP %d", model, resp.status)
                else:
                    logger.info("Unloaded model: %s", model)
        except TimeoutError:
            logger.warning("Timeout unloading model %s", model)
        except aiohttp.ClientError as exc:
            logger.warning("ClientError unloading model %s: %s", model, exc)

    async def unload_all_for_training(self) -> None:
        """CRITICAL OOM prevention: unload ALL models before training begins.

        Steps:
        1. GET /api/ps to find all loaded models.
        2. POST /api/generate keep_alive=0 for each.
        3. Poll /api/ps until empty (max 60 s timeout).
        """
        loaded = await self.get_loaded_models()
        if not loaded:
            logger.info("No models loaded; nothing to unload before training.")
            return

        logger.info("Unloading %d model(s) before training: %s", len(loaded), loaded)
        await asyncio.gather(*(self.unload_model(m) for m in loaded))

        # Poll until /api/ps is empty or timeout
        deadline = time.monotonic() + 60.0
        while time.monotonic() < deadline:
            remaining = await self.get_loaded_models()
            if not remaining:
                logger.info("All models unloaded; safe to begin training.")
                return
            await asyncio.sleep(2.0)

        remaining = await self.get_loaded_models()
        if remaining:
            raise RuntimeError(
                f"Training unload timeout: {len(remaining)} model(s) still loaded after 60s: "
                f"{remaining}. Cannot proceed — risk of OOM during training."
            )

    async def reload_inference_models(self, hot_models: list[str] | None = None) -> None:
        """Restore hot-tier models after training completes.

        Sends a lightweight /api/generate prompt to each model so Ollama pre-loads it.
        """
        targets = hot_models if hot_models is not None else _DEFAULT_HOT_MODELS
        url = f"{self._base_url}/api/generate"

        async def _warm(model: str) -> None:
            payload = {"model": model, "prompt": "", "keep_alive": "5m", "stream": False}
            try:
                async with (
                    aiohttp.ClientSession() as session,
                    session.post(
                        url, json=payload, timeout=aiohttp.ClientTimeout(total=60.0)
                    ) as resp,
                ):
                    if resp.status == 200:
                        logger.info("Reloaded inference model: %s", model)
                    else:
                        logger.warning("Reload of %s returned HTTP %d", model, resp.status)
            except TimeoutError:
                logger.warning("Timeout reloading model %s", model)
            except aiohttp.ClientError as exc:
                logger.warning("ClientError reloading model %s: %s", model, exc)

        await asyncio.gather(*(_warm(m) for m in targets))

    async def get_available_memory_gb(self) -> float:
        """Estimate available unified memory in GB.

        Formula: 128 - sum(loaded model sizes from /api/ps) - OS_OVERHEAD_GB.
        Clamps to >= 0.0. Updates internal cache used by check_oom_risk().
        """
        url = f"{self._base_url}/api/ps"
        loaded_gb = 0.0
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10.0)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for m in data.get("models", []):
                            size_bytes: int = m.get("size", 0)
                            loaded_gb += size_bytes / (1024**3)
        except TimeoutError:
            logger.warning("Timeout querying Ollama /api/ps for memory estimate")
        except aiohttp.ClientError as exc:
            logger.warning("ClientError querying /api/ps for memory: %s", exc)

        available = max(0.0, TOTAL_SYSTEM_MEMORY_GB - loaded_gb - OS_OVERHEAD_GB - SAFETY_BUFFER_GB)
        self._cached_available_gb = available
        return available

    def check_oom_risk(
        self,
        model_size_gb: float,
        training_overhead_factor: float = 3.0,
    ) -> bool:
        """Return True if loading model for training risks OOM.

        Uses cached available GB (call get_available_memory_gb() first for accuracy).
        OOM risk when: available_gb < model_size_gb * training_overhead_factor * 1.2
        """
        required = model_size_gb * training_overhead_factor * 1.2
        return self._cached_available_gb < required

    @property
    def cached_available_gb(self) -> float:
        """Last known available GB. Updated by get_available_memory_gb()."""
        return self._cached_available_gb


# ---------------------------------------------------------------------------
# ContextOptimizer (simple helper)
# ---------------------------------------------------------------------------


class ContextOptimizer:
    """Helper to select optimal context settings for a given task type."""

    def __init__(self) -> None:
        self._manager = OllamaContextManager()

    def get_training_profile(self, model_name: str) -> ModelContextProfile:
        """Return reduced-context profile for training (num_ctx=2048, keep_alive=0)."""
        training_key = f"{model_name}:training"
        if training_key in CONTEXT_PROFILES:
            return CONTEXT_PROFILES[training_key]
        # Build an ad-hoc training profile from whatever base we find
        base = self._manager.get_profile(model_name)
        return _training(base)

    def get_inference_profile(self, model_name: str) -> ModelContextProfile:
        """Return standard inference profile for a model."""
        return self._manager.get_profile(model_name)

    def estimate_kv_cache_gb(self, num_ctx: int, model_size_gb: float) -> float:
        """Estimate KV cache memory in GB.

        Approximation: num_ctx * model_size_gb / 128_000.
        KV cache grows roughly linearly with context length for a given model size.
        """
        return (num_ctx * model_size_gb) / 128_000
