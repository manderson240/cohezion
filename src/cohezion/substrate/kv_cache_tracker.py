"""KV Cache tracking and management for memory-efficient inference.

Tracks KV cache allocations across all active requests to prevent
memory exhaustion from context windows.

Designed for AMD Ryzen AI MAX+ 395 with 128GB unified memory.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from cohezion.swarm.context_model_router import ModelContextProfile


logger = logging.getLogger(__name__)


@dataclass
class KVCacheEntry:
    """Tracks KV cache for a single request."""

    request_id: str
    model: str
    context_length: int
    kv_cache_mb: float
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)

    @property
    def age_seconds(self) -> float:
        """Get age in seconds."""
        return (datetime.now() - self.created_at).total_seconds()

    @property
    def idle_seconds(self) -> float:
        """Get idle time in seconds."""
        return (datetime.now() - self.last_accessed).total_seconds()

    def touch(self) -> None:
        """Update last accessed time."""
        self.last_accessed = datetime.now()


@dataclass
class AllocationResult:
    """Result of a KV cache allocation request."""

    success: bool
    allocated_context: int
    kv_cache_mb: float
    queue_position: int = 0
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "allocated_context": self.allocated_context,
            "kv_cache_mb": self.kv_cache_mb,
            "queue_position": self.queue_position,
            "message": self.message,
        }


class KVCacheTracker:
    """Tracks and manages KV cache memory across all active requests.

    For 128GB system:
    - Model weights: ~70GB max
    - KV cache: ~40GB max (this tracker)
    - Activations: ~10GB buffer
    - System: ~8GB reserve
    """

    def __init__(
        self,
        max_total_cache_gb: float = 40.0,
        eviction_threshold_seconds: float = 60.0,
    ):
        self.max_total_cache_gb = max_total_cache_gb
        self.eviction_threshold_seconds = eviction_threshold_seconds
        self.active_caches: dict[str, KVCacheEntry] = {}
        self._pending_allocations: asyncio.Queue[tuple[str, asyncio.Future]] = asyncio.Queue()
        self._lock = asyncio.Lock()
        self._allocation_counter = 0

    def calculate_kv_size(
        self,
        model_params_billions: float,
        context_length: int,
        quantization_bits: int = 4,
        is_moe: bool = False,
        active_params_billions: float | None = None,
    ) -> float:
        """Calculate KV cache size in MB.

        Formula for dense models:
            KV cache ≈ 2 × num_layers × num_heads × head_dim × context_length × bytes_per_param

        For MoE models, only active parameters contribute to KV cache:
            KV cache ≈ 2 × num_layers × num_heads × head_dim × context_length
                      × bytes_per_param × (active/total)

        Simplified estimation:
            Dense: MB = (context_length / 1000) × params_billions × factor
            MoE:   MB = (context_length / 1000) × active_params_billions × factor

        Where factor depends on quantization:
            Q4: 0.5 MB per 1K tokens per 1B params
            Q8: 1.0 MB per 1K tokens per 1B params
            FP16: 2.0 MB per 1K tokens per 1B params

        Args:
            model_params_billions: Total model size in billions of parameters
            context_length: Context window size
            quantization_bits: Quantization bits (4, 8, or 16)
            is_moe: Whether model is Mixture of Experts
            active_params_billions: Active parameters for MoE models

        Returns:
            Estimated KV cache size in MB
        """
        # Base factor per 1K tokens per 1B params
        base_factor = {4: 0.5, 8: 1.0, 16: 2.0}.get(quantization_bits, 0.5)

        # For MoE models, use active parameters
        effective_params = (
            active_params_billions if (is_moe and active_params_billions) else model_params_billions
        )

        # Calculate
        kv_mb = (context_length / 1000) * effective_params * base_factor

        # Add 10% overhead for safety
        return kv_mb * 1.1

    async def allocate(
        self,
        request_id: str,
        model: ModelContextProfile,
        context_length: int,
        timeout: float = 5.0,
    ) -> AllocationResult:
        """Allocate KV cache for a request.

        Algorithm:
        1. Calculate required KV cache
        2. Check if under max_total_cache_gb
        3. If over: evict oldest idle caches
        4. If still over: reduce context length
        5. If still over: queue request

        Args:
            request_id: Unique request identifier
            model: Model context profile
            context_length: Requested context length
            timeout: Maximum time to wait for allocation

        Returns:
            AllocationResult with allocation details
        """
        async with self._lock:
            # Calculate required KV cache
            kv_required = self.calculate_kv_size(
                model.total_params_b,
                context_length,
                self._get_quantization_bits(model.name),
            )

            # Check current usage
            current_usage = self.get_total_kv_cache_gb()

            # Fast path: plenty of space
            if current_usage + (kv_required / 1024) <= self.max_total_cache_gb:
                entry = KVCacheEntry(
                    request_id=request_id,
                    model=model.name,
                    context_length=context_length,
                    kv_cache_mb=kv_required,
                )
                self.active_caches[request_id] = entry
                self._allocation_counter += 1

                logger.debug(
                    f"KV cache allocated: {request_id} = {kv_required:.1f}MB "
                    f"(total: {self.get_total_kv_cache_gb():.1f}GB)"
                )

                return AllocationResult(
                    success=True,
                    allocated_context=context_length,
                    kv_cache_mb=kv_required,
                    message="Allocated successfully",
                )

        # Slow path: need to free space
        return await self._allocate_with_eviction(
            request_id, model, context_length, kv_required, timeout
        )

    async def _allocate_with_eviction(
        self,
        request_id: str,
        model: ModelContextProfile,
        context_length: int,
        kv_required: float,
        timeout: float,
    ) -> AllocationResult:
        """Allocate with eviction and context reduction."""
        async with self._lock:
            # Step 1: Try to evict idle caches
            evicted = self.evict_idle_caches(self.eviction_threshold_seconds)
            if evicted > 0:
                logger.info(f"Evicted {evicted} idle caches to free memory")

            # Check if we have space now
            current_usage = self.get_total_kv_cache_gb()
            if current_usage + (kv_required / 1024) <= self.max_total_cache_gb:
                entry = KVCacheEntry(
                    request_id=request_id,
                    model=model.name,
                    context_length=context_length,
                    kv_cache_mb=kv_required,
                )
                self.active_caches[request_id] = entry

                return AllocationResult(
                    success=True,
                    allocated_context=context_length,
                    kv_cache_mb=kv_required,
                    message=f"Allocated after evicting {evicted} caches",
                )

            # Step 2: Reduce context length
            reduction_factor = 0.75
            while reduction_factor >= 0.5:
                reduced_context = int(context_length * reduction_factor)
                reduced_kv = self.calculate_kv_size(
                    model.total_params_b,
                    reduced_context,
                    self._get_quantization_bits(model.name),
                )

                if current_usage + (reduced_kv / 1024) <= self.max_total_cache_gb:
                    entry = KVCacheEntry(
                        request_id=request_id,
                        model=model.name,
                        context_length=reduced_context,
                        kv_cache_mb=reduced_kv,
                    )
                    self.active_caches[request_id] = entry

                    logger.warning(
                        f"Context reduced: {context_length} -> {reduced_context} "
                        f"({(1 - reduction_factor) * 100:.0f}% reduction)"
                    )

                    return AllocationResult(
                        success=True,
                        allocated_context=reduced_context,
                        kv_cache_mb=reduced_kv,
                        message=f"Context reduced by {(1 - reduction_factor) * 100:.0f}%",
                    )

                reduction_factor -= 0.25

            # Step 3: Queue request
            future = asyncio.Future()
            await self._pending_allocations.put((request_id, future))

            logger.warning(f"KV cache allocation queued: {request_id}")

            return AllocationResult(
                success=False,
                allocated_context=0,
                kv_cache_mb=0.0,
                queue_position=self._pending_allocations.qsize(),
                message="Queued for allocation",
            )

    async def release(self, request_id: str) -> float:
        """Release KV cache for completed request.

        Args:
            request_id: Request ID to release

        Returns:
            Amount of memory freed (MB)
        """
        async with self._lock:
            entry = self.active_caches.pop(request_id, None)
            if entry:
                freed_mb = entry.kv_cache_mb
                logger.debug(
                    f"KV cache released: {request_id} = {freed_mb:.1f}MB (total: "
                    f"{self.get_total_kv_cache_gb():.1f}GB)"
                )

                # Check if we can fulfill pending allocations
                await self._process_pending_allocations()

                return freed_mb
            return 0.0

    async def _process_pending_allocations(self) -> None:
        """Process pending allocations after a release."""
        # This would be implemented with the actual allocation logic
        # For now, just log
        if not self._pending_allocations.empty():
            logger.info(f"Processing {self._pending_allocations.qsize()} pending allocations")

    def get_total_kv_cache_gb(self) -> float:
        """Get total KV cache currently allocated in GB."""
        total_mb = sum(entry.kv_cache_mb for entry in self.active_caches.values())
        return total_mb / 1024

    def get_usage_by_model(self) -> dict[str, float]:
        """Get KV cache usage grouped by model."""
        usage: dict[str, float] = {}
        for entry in self.active_caches.values():
            usage[entry.model] = usage.get(entry.model, 0) + entry.kv_cache_mb
        return {k: v / 1024 for k, v in usage.items()}  # Convert to GB

    def evict_idle_caches(self, max_age_seconds: float) -> int:
        """Evict caches that have been idle too long.

        Called periodically and when under memory pressure.

        Args:
            max_age_seconds: Maximum idle time before eviction

        Returns:
            Number of caches evicted
        """
        now = datetime.now()
        to_evict = [
            req_id
            for req_id, entry in self.active_caches.items()
            if (now - entry.last_accessed).total_seconds() > max_age_seconds
        ]

        for req_id in to_evict:
            del self.active_caches[req_id]

        if to_evict:
            logger.info(f"Evicted {len(to_evict)} idle KV caches (idle > {max_age_seconds}s)")

        return len(to_evict)

    def touch(self, request_id: str) -> bool:
        """Mark a cache as recently used.

        Args:
            request_id: Request ID to touch

        Returns:
            True if cache was found and touched
        """
        entry = self.active_caches.get(request_id)
        if entry:
            entry.touch()
            return True
        return False

    def get_entry(self, request_id: str) -> KVCacheEntry | None:
        """Get cache entry for a request."""
        return self.active_caches.get(request_id)

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about KV cache usage."""
        if not self.active_caches:
            return {
                "total_gb": 0.0,
                "max_gb": self.max_total_cache_gb,
                "utilization": 0.0,
                "active_requests": 0,
                "by_model": {},
                "oldest_cache_seconds": 0,
            }

        now = datetime.now()
        oldest = min(
            (now - entry.created_at).total_seconds() for entry in self.active_caches.values()
        )

        total_gb = self.get_total_kv_cache_gb()

        return {
            "total_gb": total_gb,
            "max_gb": self.max_total_cache_gb,
            "utilization": total_gb / self.max_total_cache_gb,
            "active_requests": len(self.active_caches),
            "by_model": self.get_usage_by_model(),
            "oldest_cache_seconds": oldest,
            "pending_allocations": self._pending_allocations.qsize(),
        }

    def _get_quantization_bits(self, model_name: str) -> int:
        """Determine quantization bits from model name."""
        if "q8" in model_name.lower() or "q8_0" in model_name.lower():
            return 8
        elif "q4" in model_name.lower() or "q4_K" in model_name.lower():
            return 4
        elif "fp16" in model_name.lower():
            return 16
        return 4  # Default to Q4

    async def shutdown(self) -> None:
        """Release all caches on shutdown."""
        async with self._lock:
            count = len(self.active_caches)
            self.active_caches.clear()
            logger.info(f"KVCacheTracker shutdown: released {count} caches")
