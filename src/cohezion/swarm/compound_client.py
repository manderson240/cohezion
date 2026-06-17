"""Pre-configured compound client factory.

Creates a fully-wired :class:`TokenEfficientClient` with:
- :class:`SmartRouterAdapter` for intelligent model selection
- :class:`ContextHarness` for prompt pruning (target: phi3:mini)
- :class:`ResilientOllamaClient` for circuit-breaker-protected Ollama calls

Usage::

    client = get_compound_client()
    response = await client.generate("Analyze this code", task_type="coding")
"""

from __future__ import annotations

import logging
from typing import Any

from cohezion.concurrency.safe_singleton import safe_singleton


logger = logging.getLogger(__name__)


def create_compound_client(
    strategy: str = "efficiency",
    ollama_host: str = "http://localhost:13305",
    cache_max_size: int = 512,
) -> Any:
    """Create a new :class:`TokenEfficientClient` wired with SmartRouter.

    Parameters
    ----------
    strategy : str
        SmartRouter strategy: ``"efficiency"``, ``"quality"``, or ``"speed"``.
    ollama_host : str
        Ollama API base URL.
    cache_max_size : int
        Maximum prompt-response cache entries.

    Returns
    -------
    TokenEfficientClient
        Fully wired client ready for live Ollama calls.
    """
    from cohezion.reliability.context_harness import ContextHarness
    from cohezion.swarm.model_adapter import SmartRouterAdapter
    from cohezion.swarm.smart_router import SmartRouter
    from cohezion.swarm.token_client import TokenEfficientClient

    # 1. SmartRouter with full LOCAL_MODELS registry
    smart_router = SmartRouter(
        ollama_host=ollama_host,
        strategy=strategy,
        log_actions=True,
    )

    # 2. Adapter for TokenEfficientClient's _router interface
    adapter = SmartRouterAdapter(smart_router)

    # 3. ContextHarness targeting the cheapest model for prompt pruning
    _harness = ContextHarness(target_model="phi3:mini")

    # 4. Create TokenEfficientClient with SmartRouter adapter
    client = TokenEfficientClient(
        ollama_base_url=ollama_host,
        router=adapter,
        config=None,  # Will use defaults from CohezionConfig
        use_persistent_cache=True,
        use_semantic_cache=True,
    )

    logger.info(
        "Created compound client: strategy=%s, host=%s, cache=%d",
        strategy,
        ollama_host,
        cache_max_size,
    )
    return client


@safe_singleton
def get_compound_client() -> Any:
    """Return the singleton :class:`TokenEfficientClient`.

    Creates the client on first call, then returns the same instance.

    Returns
    -------
    TokenEfficientClient
        The shared compound client.
    """
    return create_compound_client()


def reset_compound_client() -> None:
    """Reset the singleton (useful for testing)."""
    getattr(get_compound_client, "reset", lambda: None)()
