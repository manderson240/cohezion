"""Core Cohezion configuration management.

Central configuration for the compound engineering system, including:
- Model routing (per-operation defaults)
- Token budgets and limits
- Cache configuration
- Batch processing settings
- Timeout and retry policies
"""

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class ModelConfig:
    """Per-operation model selection."""

    generate: str = "qwen3-coder:30b"
    analyze: str = "phi3:mini"
    search: str = "phi3:mini"
    transform: str = "phi3:mini"
    persist: str = "phi3:mini"

    def for_operation(self, operation: str) -> str:
        """Get model for operation."""
        return getattr(self, operation, "phi3:mini")


@dataclass
class TokenBudget:
    """Token budgets for different operations."""

    generate_max: int = 1024
    analyze_max: int = 512
    search_max: int = 256
    transform_max: int = 256
    persist_max: int = 128
    per_execution_max: int = 5000  # Total per compound execution
    per_session_max: int = 100000  # Total per session

    def for_operation(self, operation: str) -> int:
        """Get max tokens for operation."""
        key = f"{operation}_max"
        return getattr(self, key, 256)


@dataclass
class CacheConfig:
    """Token cache configuration."""

    enabled: bool = True
    max_size: int = 512  # Number of entries
    ttl_seconds: int | None = None  # None = no expiration
    hash_method: str = "sha256"  # Cache key method

    @property
    def cache_hit_value(self) -> int:
        """Estimated tokens saved per hit (average)."""
        return 150


@dataclass
class BatchConfig:
    """Batch processing configuration."""

    enabled: bool = True
    max_batch_size: int = 10
    parallel_tasks: int = 4  # Max concurrent executions
    timeout_seconds: int = 300  # 5 minute timeout for batch
    phase1_cache_check: bool = True  # Phase 1: check all cache hits first
    phase2_parallel_execute: bool = True  # Phase 2: execute misses in parallel


@dataclass
class InferenceConfig:
    """Long-running inference optimization."""

    context_max_tokens: int = 4096  # Max context size for single prompt
    context_prune_ratio: float = 0.8  # Keep 80% of context when pruning
    num_predict_default: int = 256  # Default prediction length
    timeout_default: int = 300  # 5 minutes default
    timeout_per_token: float = 0.1  # 100ms per 1000 tokens
    retry_on_timeout: int = 2  # Retry failed requests up to 2 times
    stream_responses: bool = True  # Use streaming for long responses


@dataclass
class CohezionConfig:
    """Master configuration for Cohezion compound engineering system."""

    # Model selection
    models: ModelConfig = field(default_factory=ModelConfig)

    # Token management
    token_budget: TokenBudget = field(default_factory=TokenBudget)

    # Caching
    cache: CacheConfig = field(default_factory=CacheConfig)

    # Batch processing
    batch: BatchConfig = field(default_factory=BatchConfig)

    # Inference optimization
    inference: InferenceConfig = field(default_factory=InferenceConfig)

    # Debugging
    debug: bool = False
    verbose: bool = False

    @property
    def model_for_operation(self) -> Callable[[str], str]:
        """Get model selection function."""
        return self.models.for_operation

    @property
    def token_limit_for_operation(self) -> Callable[[str], int]:
        """Get token limit function."""
        return self.token_budget.for_operation

    def to_dict(self) -> dict:
        """Export config as dictionary."""
        return {
            "models": {
                "generate": self.models.generate,
                "analyze": self.models.analyze,
                "search": self.models.search,
                "transform": self.models.transform,
                "persist": self.models.persist,
            },
            "token_budget": {
                "per_execution_max": self.token_budget.per_execution_max,
                "per_session_max": self.token_budget.per_session_max,
            },
            "cache": {
                "enabled": self.cache.enabled,
                "max_size": self.cache.max_size,
            },
            "batch": {
                "enabled": self.batch.enabled,
                "max_batch_size": self.batch.max_batch_size,
                "parallel_tasks": self.batch.parallel_tasks,
            },
            "inference": {
                "context_max_tokens": self.inference.context_max_tokens,
                "timeout_default": self.inference.timeout_default,
            },
        }
