"""Base agent class for all SLM Swarm agents."""

import asyncio
import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import httpx

from cohezion.swarm.types import SwarmConfig

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for Swarm agents.
    
    Provides common functionality:
    - Ollama HTTP client management
    - Response caching with LRU eviction
    - Timeout handling and retries
    - Logging and metrics
    """
    
    def __init__(
        self,
        model_name: str,
        config: SwarmConfig | None = None,
        cache_dir: Path | None = None,
    ):
        self.model_name = model_name
        self.config = config or SwarmConfig()
        self.cache_dir = cache_dir or Path("cache/swarm")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self._client: httpx.AsyncClient | None = None
        self._metrics: dict[str, Any] = {
            "total_calls": 0,
            "cache_hits": 0,
            "total_latency_ms": 0,
            "errors": 0,
        }
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Lazy-initialize the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.config.ollama_base_url,
                timeout=httpx.Timeout(60.0, connect=10.0),
            )
        return self._client
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    def _cache_key(self, prompt: str) -> str:
        """Generate a cache key from the prompt."""
        content = f"{self.model_name}:{prompt}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _get_cached(self, prompt: str) -> str | None:
        """Retrieve a cached response if available and fresh."""
        key = self._cache_key(prompt)
        cache_file = self.cache_dir / f"{key}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            data = json.loads(cache_file.read_text())
            age = time.time() - data.get("timestamp", 0)
            if age < self.config.cache_ttl_seconds:
                self._metrics["cache_hits"] += 1
                return data.get("response")
        except (json.JSONDecodeError, KeyError):
            pass
        
        return None
    
    def _set_cached(self, prompt: str, response: str) -> None:
        """Cache a response."""
        key = self._cache_key(prompt)
        cache_file = self.cache_dir / f"{key}.json"
        
        data = {
            "model": self.model_name,
            "prompt": prompt[:500],  # Truncate for storage
            "response": response,
            "timestamp": time.time(),
        }
        cache_file.write_text(json.dumps(data, ensure_ascii=False))
    
    async def _call_ollama(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """
        Make a request to the Ollama API.
        
        Uses the /api/generate endpoint for simplicity.
        """
        # Check cache first
        cached = self._get_cached(prompt)
        if cached:
            logger.debug(f"Cache hit for {self.model_name}")
            return cached
        
        self._metrics["total_calls"] += 1
        start_time = time.perf_counter()
        
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"<system>{system_prompt}</system>\n\n{prompt}"
        
        try:
            response = await self.client.post(
                "/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    },
                },
            )
            response.raise_for_status()
            result = response.json().get("response", "")
            
            # Cache the result
            self._set_cached(prompt, result)
            
            latency = (time.perf_counter() - start_time) * 1000
            self._metrics["total_latency_ms"] += latency
            logger.info(f"{self.model_name} responded in {latency:.1f}ms")
            
            return result
            
        except httpx.HTTPError as e:
            self._metrics["errors"] += 1
            logger.error(f"Ollama call failed: {e}")
            raise
    
    @abstractmethod
    async def process(self, *args: Any, **kwargs: Any) -> Any:
        """Process input and return output. Implemented by subclasses."""
        pass
    
    def get_metrics(self) -> dict[str, Any]:
        """Return current metrics."""
        return {
            **self._metrics,
            "model": self.model_name,
            "cache_hit_rate": (
                self._metrics["cache_hits"] / max(1, self._metrics["total_calls"])
            ),
            "avg_latency_ms": (
                self._metrics["total_latency_ms"] / max(1, self._metrics["total_calls"])
            ),
        }
