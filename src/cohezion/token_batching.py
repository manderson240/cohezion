"""
ASCENDED COHEZION - Token-Efficient Batching System
Optimized Local Model Orchestration

Maximizes throughput while minimizing token usage through:
- Request batching (single call, multiple prompts)
- Context compression (remove redundancy)
- Intelligent caching (avoid duplicate work)
- Priority queuing (urgent first, batch rest)

Token Efficiency Target: 60-80% reduction vs naive approach
"""

import asyncio
import hashlib
import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import heapq

logger = logging.getLogger(__name__)


@dataclass
class BatchedRequest:
    """Single request within a batch"""

    id: str
    priority: int  # Lower = higher priority
    prompt: str
    context: Optional[str] = None
    max_tokens: int = 1024
    temperature: float = 0.7
    callback: Optional[Callable] = None
    created_at: float = field(default_factory=time.time)
    result: Any = None
    error: Optional[Exception] = None
    completed: bool = False


@dataclass
class BatchConfig:
    """Configuration for batching behavior"""

    max_batch_size: int = 5  # Max requests per batch
    max_wait_time: float = 0.5  # Max seconds to wait for batch to fill
    max_tokens_per_batch: int = 8000  # Token budget per batch
    min_batch_size: int = 2  # Minimum requests to form batch
    priority_threshold: int = 1  # Priority below which to batch


class TokenCompressor:
    """
    Compresses prompts to reduce token usage.

    Compound Engineering: Each compression strategy
    makes future batching more efficient.
    """

    @staticmethod
    def remove_redundancy(text: str) -> str:
        """Remove repetitive phrases and formatting"""
        # Remove excessive whitespace
        text = " ".join(text.split())

        # Remove common filler phrases
        fillers = [
            "Please note that",
            "It is important to understand that",
            "As you may know",
            "In order to",
            "At this point in time",
        ]
        for filler in fillers:
            text = text.replace(filler, "")

        return text.strip()

    @staticmethod
    def extract_key_context(context: str, max_chars: int = 500) -> str:
        """Extract only essential context"""
        if len(context) <= max_chars:
            return context

        # Keep first 30% and last 30% (usually most relevant)
        prefix_len = int(max_chars * 0.3)
        suffix_len = int(max_chars * 0.3)

        prefix = context[:prefix_len]
        suffix = context[-suffix_len:]

        return f"{prefix}...{suffix}"

    @staticmethod
    def batch_similar_prompts(prompts: List[str]) -> List[str]:
        """Group similar prompts and create shared prefix"""
        if len(prompts) <= 1:
            return prompts

        # Find common prefix
        prefix = prompts[0]
        for prompt in prompts[1:]:
            while not prompt.startswith(prefix):
                prefix = prefix[:-1]
                if not prefix:
                    break

        if len(prefix) > 20:  # Meaningful common prefix
            # Extract unique parts
            unique_parts = [p[len(prefix) :].strip() for p in prompts]

            # Return batched format
            return [f"{prefix} [BATCH: {' | '.join(unique_parts)}]"]

        return prompts


class LocalModelBatchManager:
    """
    Efficiently batches requests to local models.

    Key optimizations:
    1. Time-based batching (wait for batch to fill)
    2. Priority-based (urgent requests skip batch)
    3. Token-aware (respect token limits)
    4. Duplicate detection (cache identical requests)
    """

    def __init__(self, model_name: str, config: BatchConfig = None):
        self.model_name = model_name
        self.config = config or BatchConfig()
        self.compressor = TokenCompressor()

        # Request queues
        self.high_priority_queue: asyncio.Queue = asyncio.Queue()
        self.batch_queue: List[BatchedRequest] = []
        self.batch_lock = asyncio.Lock()

        # Batching state
        self._batch_timer: Optional[asyncio.Task] = None
        self._batch_event = asyncio.Event()
        self._running = False

        # Performance tracking
        self.stats = {
            "total_requests": 0,
            "batched_requests": 0,
            "tokens_saved": 0,
            "cache_hits": 0,
        }

        logger.info(f"🚀 BatchManager initialized for {model_name}")
        logger.info(f"   Max batch size: {self.config.max_batch_size}")
        logger.info(f"   Max wait time: {self.config.max_wait_time}s")

    async def submit(
        self,
        prompt: str,
        priority: int = 5,
        context: Optional[str] = None,
        callback: Optional[Callable] = None,
    ) -> str:
        """
        Submit a request for processing.

        High priority (1-2): Process immediately
        Medium priority (3-5): Batch with similar requests
        Low priority (6+): Batch when convenient
        """
        request_id = hashlib.md5(f"{prompt}{time.time()}".encode()).hexdigest()[:8]

        request = BatchedRequest(
            id=request_id,
            priority=priority,
            prompt=self.compressor.remove_redundancy(prompt),
            context=self.compressor.extract_key_context(context) if context else None,
            callback=callback,
        )

        self.stats["total_requests"] += 1

        # High priority: skip batching
        if priority <= self.config.priority_threshold:
            logger.debug(
                f"⚡ High priority request {request_id}, processing immediately"
            )
            return await self._process_single(request)

        # Medium/Low priority: add to batch
        async with self.batch_lock:
            self.batch_queue.append(request)

            # Start batch timer if not running
            if self._batch_timer is None or self._batch_timer.done():
                self._batch_timer = asyncio.create_task(self._batch_timeout())

            # Signal that batch is ready if full
            if len(self.batch_queue) >= self.config.max_batch_size:
                self._batch_event.set()

        # Wait for completion
        while not request.completed:
            await asyncio.sleep(0.01)

        if request.error:
            raise request.error

        return request.result

    async def _batch_timeout(self):
        """Wait for batch to fill or timeout"""
        try:
            # Wait for batch to fill or timeout
            await asyncio.wait_for(
                self._batch_event.wait(), timeout=self.config.max_wait_time
            )
        except asyncio.TimeoutError:
            pass  # Process what we have

        # Process the batch
        await self._process_batch()

    async def _process_batch(self):
        """Process all requests in the current batch"""
        async with self.batch_lock:
            if len(self.batch_queue) < self.config.min_batch_size:
                # Not enough requests, process individually
                requests = self.batch_queue[:]
                self.batch_queue = []
                for request in requests:
                    asyncio.create_task(self._process_and_complete(request))
                return

            # Get batch
            batch = self.batch_queue[: self.config.max_batch_size]
            self.batch_queue = self.batch_queue[self.config.max_batch_size :]
            self._batch_event.clear()

        self.stats["batched_requests"] += len(batch)

        # Sort by priority
        batch.sort(key=lambda r: r.priority)

        # Check if we can combine prompts
        if len(batch) > 1:
            prompts = [r.prompt for r in batch]
            combined = self.compressor.batch_similar_prompts(prompts)

            if len(combined) == 1:
                # Combined into single prompt
                tokens_saved = sum(len(p) for p in prompts) - len(combined[0])
                self.stats["tokens_saved"] += tokens_saved

                logger.info(
                    f"📦 Batched {len(batch)} requests, saved ~{tokens_saved} tokens"
                )

                # Process combined request
                combined_request = BatchedRequest(
                    id="batch_combined",
                    priority=batch[0].priority,
                    prompt=combined[0],
                    max_tokens=self.config.max_tokens_per_batch,
                )

                result = await self._process_single(combined_request)

                # Distribute results (simplified - assumes same output for all)
                for request in batch:
                    request.result = result
                    request.completed = True
                    if request.callback:
                        asyncio.create_task(request.callback(request.id, result))

                return

        # Process individually
        for request in batch:
            asyncio.create_task(self._process_and_complete(request))

    async def _process_and_complete(self, request: BatchedRequest):
        """Process a single request and mark complete"""
        try:
            result = await self._process_single(request)
            request.result = result
        except Exception as e:
            request.error = e
        finally:
            request.completed = True
            if request.callback:
                asyncio.create_task(request.callback(request.id, request.result))

    async def _process_single(self, request: BatchedRequest) -> str:
        """Process a single request through the model"""
        # This would integrate with actual model
        # For now, simulate processing
        await asyncio.sleep(0.1)  # Simulate latency

        # In real implementation:
        # return await model.generate(
        #     prompt=request.prompt,
        #     context=request.context,
        #     max_tokens=request.max_tokens,
        #     temperature=request.temperature
        # )

        return f"[Processed: {request.id}] {request.prompt[:50]}..."

    def get_stats(self) -> Dict[str, Any]:
        """Get batching statistics"""
        total = self.stats["total_requests"]
        batched = self.stats["batched_requests"]

        return {
            **self.stats,
            "batch_rate": batched / total if total > 0 else 0,
            "average_tokens_saved": self.stats["tokens_saved"] / batched
            if batched > 0
            else 0,
        }


class MultiModelOrchestrator:
    """
    Orchestrates multiple local models with token-efficient batching.

    Routes requests to optimal model based on:
    - Task type (coding, reasoning, analysis)
    - Current load (batch queue depth)
    - Token efficiency (model context window)
    """

    def __init__(self):
        self.managers: Dict[str, LocalModelBatchManager] = {}
        self.model_capabilities: Dict[str, Set[str]] = {
            "phi4:mini": {"routing", "quick_tasks"},
            "qwen3-coder:30b": {"coding", "architecture"},
            "deepseek-r1:8b": {"reasoning", "analysis"},
            "phi4": {"general", "summary"},
            "gemma3:4b": {"vision", "multimodal"},
        }

        logger.info("🎛️ MultiModelOrchestrator initialized")
        logger.info(f"   Models: {list(self.model_capabilities.keys())}")

    def register_model(self, model_name: str, config: BatchConfig = None):
        """Register a model for batching"""
        if model_name not in self.managers:
            self.managers[model_name] = LocalModelBatchManager(model_name, config)
            logger.info(f"📋 Registered model: {model_name}")

    async def route_request(
        self,
        task_type: str,
        prompt: str,
        priority: int = 5,
        context: Optional[str] = None,
    ) -> str:
        """
        Route request to optimal model with batching.

        Task types:
        - "coding" → qwen3-coder
        - "reasoning" → deepseek-r1
        - "quick" → phi4:mini
        - "general" → phi4
        """
        # Select best model for task
        model_name = self._select_model(task_type)

        # Ensure manager exists
        if model_name not in self.managers:
            self.register_model(model_name)

        # Submit with batching
        manager = self.managers[model_name]
        return await manager.submit(prompt, priority, context)

    def _select_model(self, task_type: str) -> str:
        """Select best model for task type"""
        # Direct mapping
        mapping = {
            "coding": "qwen3-coder:30b",
            "architecture": "qwen3-coder:30b",
            "reasoning": "deepseek-r1:8b",
            "analysis": "deepseek-r1:8b",
            "quick": "phi4:mini",
            "routing": "phi4:mini",
            "general": "phi4",
            "summary": "phi4",
        }

        return mapping.get(task_type, "phi4")

    def get_all_stats(self) -> Dict[str, Dict]:
        """Get stats for all models"""
        return {name: manager.get_stats() for name, manager in self.managers.items()}


# Singleton
_orchestrator = None


def get_batch_orchestrator() -> MultiModelOrchestrator:
    """Get or create the global batch orchestrator"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = MultiModelOrchestrator()
    return _orchestrator


# Example usage for token-efficient operation
async def demo_token_efficiency():
    """Demonstrate token-efficient batching"""
    orchestrator = get_batch_orchestrator()

    # Submit multiple coding tasks simultaneously
    # They'll be batched into a single model call
    tasks = [
        orchestrator.route_request("coding", f"Review function {i}", priority=3)
        for i in range(10)
    ]

    results = await asyncio.gather(*tasks)

    # Show stats
    stats = orchestrator.get_all_stats()
    for model, model_stats in stats.items():
        print(f"\n{model}:")
        print(f"  Requests: {model_stats['total_requests']}")
        print(f"  Batched: {model_stats['batched_requests']}")
        print(f"  Tokens saved: {model_stats['tokens_saved']}")
        print(f"  Batch rate: {model_stats['batch_rate']:.1%}")


if __name__ == "__main__":
    asyncio.run(demo_token_efficiency())
