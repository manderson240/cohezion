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
    ollama_host: str = "http://localhost:11434",
    cache_max_size: int = 512,
    use_task_type_router: bool = False,
) -> Any:
    """Create a compound client for model inference.

    Parameters
    ----------
    strategy : str
        SmartRouter strategy: ``"efficiency"``, ``"quality"``, or ``"speed"``.
    ollama_host : str
        Ollama API base URL.
    cache_max_size : int
        Maximum prompt-response cache entries.
    use_task_type_router : bool
        If True, returns a :class:`TaskTypeRouter` with three-tier routing
        (Anthropic + Ollama Cloud + Local). Default False for backwards compat.

    Returns
    -------
    TokenEfficientClient or TaskTypeRouter
        Fully wired client ready for inference calls.
    """
    if use_task_type_router:
        return _create_task_type_router(ollama_host)

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


def _create_task_type_router(ollama_host: str) -> Any:
    """Create a TaskTypeRouter with available providers based on env vars."""
    import os

    from cohezion.swarm.providers.ollama_provider import OllamaProvider
    from cohezion.swarm.task_type_router import ProviderTier, TaskTypeRouter

    router = TaskTypeRouter()

    # Tier 3: Local Ollama (always available)
    router.register_provider(
        ProviderTier.LOCAL,
        OllamaProvider(config={"base_url": ollama_host}),
    )

    # Tier 1: Anthropic Claude (if API key set)
    if os.environ.get("ANTHROPIC_API_KEY"):
        from cohezion.swarm.providers.anthropic_provider import AnthropicProvider

        router.register_provider(ProviderTier.ANTHROPIC, AnthropicProvider())
        logger.info("TaskTypeRouter: Anthropic tier enabled")

    # Tier 2: Ollama Cloud (if URL set)
    if os.environ.get("OLLAMA_CLOUD_URL"):
        from cohezion.swarm.providers.ollama_cloud_provider import OllamaCloudProvider

        router.register_provider(ProviderTier.OLLAMA_CLOUD, OllamaCloudProvider())
        logger.info("TaskTypeRouter: Ollama Cloud tier enabled")

    logger.info("Created TaskTypeRouter with %d providers", len(router._providers))
    return router


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
    get_compound_client.reset()
