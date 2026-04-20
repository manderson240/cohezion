#!/usr/bin/env python
"""Example: ngrok AI Gateway Integration with Cohezion.

This example demonstrates:
- Multi-provider routing via ngrok AI Gateway
- Automatic failover to local Ollama
- Response caching (4th tier)
- Cost tracking and optimization
- Feature flag controls for gradual rollout

Usage:
    # Set up environment
    export NGROK_ENDPOINT="https://xxxxx.ngrok.app/v1"
    export NGROK_API_KEY="your-ngrok-key"

    # Run example
    uv run python scripts/example_ngrok_integration.py
"""

import asyncio
import logging

from cohezion.deployment.feature_flags import (
    FeatureFlag,
    get_feature_flag_manager,
)
from cohezion.gateway import NgrokAIGateway
from cohezion.swarm.token_client import TokenEfficientClient


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_1_basic_generation():
    """Example 1: Basic generation with ngrok gateway."""
    print("\n=== Example 1: Basic Generation ===\n")

    client = TokenEfficientClient(
        ngrok_endpoint="https://xxxxx.ngrok.app/v1",  # Replace with your endpoint
        ngrok_api_key="your-ngrok-key",  # Replace with your API key
        enable_ngrok_failover=True,
    )

    prompt = "Explain quantum computing in 100 words."

    print(f"Prompt: {prompt}\n")

    try:
        response, tokens = await client.generate(
            prompt=prompt,
            model="gpt-3.5-turbo",  # Cheap model
        )

        print(f"Response: {response}\n")
        print(f"Tokens used: {tokens}\n")

        metrics = client.get_metrics()
        print(f"Cost: ${metrics['total_cost']:.6f}\n")

    except Exception as e:
        print(f"Error: {e}\n")


async def example_2_cost_optimization():
    """Example 2: Cost optimization routing."""
    print("\n=== Example 2: Cost Optimization ===\n")

    client = TokenEfficientClient(
        ngrok_endpoint="https://xxxxx.ngrok.app/v1",
        ngrok_api_key="your-ngrok-key",
    )

    # Different tasks with optimal models
    tasks = [
        {
            "prompt": "What is 2+2?",
            "model": "gpt-3.5-turbo",  # Simple → cheap
            "description": "Simple math",
        },
        {
            "prompt": "Write a Python function to solve the traveling salesman problem.",
            "model": "gpt-4o",  # Complex → powerful
            "description": "Complex coding",
        },
        {
            "prompt": "Write a haiku about nature.",
            "model": "claude-3.5-sonnet",  # Creative → good at creative
            "description": "Creative task",
        },
    ]

    for task in tasks:
        try:
            _response, tokens = await client.generate(
                prompt=task["prompt"],
                model=task["model"],
            )
            print(f"Task: {task['description']}")
            print(f"Model: {task['model']}")
            print(f"Tokens: {tokens}\n")

        except Exception as e:
            print(f"Error on {task['description']}: {e}\n")

    metrics = client.get_metrics()
    print("\n--- Cost Summary ---")
    print(f"Total cost: ${metrics['total_cost']:.6f}")
    print(f"Average cost per request: ${metrics['average_cost_per_request']:.6f}")
    print(f"Total tokens: {metrics['total_tokens']}\n")


async def example_3_failover_behavior():
    """Example 3: Automatic failover to Ollama."""
    print("\n=== Example 3: Failover Behavior ===\n")

    # With failover enabled (default)
    gateway = NgrokAIGateway(
        ngrok_endpoint="https://xxxxx.ngrok.app/v1",
        ngrok_api_key="your-ngrok-key",
        fallback_ollama_url="http://localhost:11434",
        enable_failover=True,  # Automatic Ollama fallback
    )

    print("Failover enabled: ngrok → Ollama\n")

    try:
        response, _tokens = await gateway.generate(
            prompt="Test prompt",
            model="gpt-4o",
        )

        print(f"Response: {response}\n")

        metrics = gateway.get_metrics()
        print("Provider stats:")
        print(f"  ngrok requests: {metrics['ngrok_requests']}")
        print(f"  ollama requests: {metrics['ollama_requests']}")
        print(f"  fallback requests: {metrics['fallback_requests']}\n")

    except Exception as e:
        print(f"Error: {e}\n")


async def example_4_feature_flags():
    """Example 4: Feature flag gradual rollout."""
    print("\n=== Example 4: Feature Flag Gradual Rollout ===\n")

    manager = get_feature_flag_manager()

    # Start with ngrok disabled (safe)
    print("Initial status:")
    status = manager.get_status()
    ngrok_flag = status.get("ngrok_ai_gateway")
    print(f"  NGROK_AI_GATEWAY: enabled={ngrok_flag['enabled']}, rollout={ngrok_flag['rollout_percentage']}%\n")

    # Enable canary (5%)
    manager.set_flag(FeatureFlag.NGROK_AI_GATEWAY, True)
    manager.ramp_up(FeatureFlag.NGROK_AI_GATEWAY, 5.0)
    print("After canary rollout (5%):")
    status = manager.get_status()
    ngrok_flag = status.get("ngrok_ai_gateway")
    print(f"  NGROK_AI_GATEWAY: enabled={ngrok_flag['enabled']}, rollout={ngrok_flag['rollout_percentage']}%\n")

    # Ramp up (25%)
    manager.ramp_up(FeatureFlag.NGROK_AI_GATEWAY, 25.0)
    print("After ramp up (25%):")
    status = manager.get_status()
    ngrok_flag = status.get("ngrok_ai_gateway")
    print(f"  NGROK_AI_GATEWAY: enabled={ngrok_flag['enabled']}, rollout={ngrok_flag['rollout_percentage']}%\n")

    # Full rollout (100%)
    manager.ramp_up(FeatureFlag.NGROK_AI_GATEWAY, 100.0)
    print("After full rollout (100%):")
    status = manager.get_status()
    ngrok_flag = status.get("ngrok_ai_gateway")
    print(f"  NGROK_AI_GATEWAY: enabled={ngrok_flag['enabled']}, rollout={ngrok_flag['rollout_percentage']}%\n")

    # Emergency rollback
    manager.rollback(FeatureFlag.NGROK_AI_GATEWAY)
    print("After emergency rollback:")
    status = manager.get_status()
    ngrok_flag = status.get("ngrok_ai_gateway")
    print(f"  NGROK_AI_GATEWAY: enabled={ngrok_flag['enabled']}, rollout={ngrok_flag['rollout_percentage']}%\n")


async def example_5_metrics_monitoring():
    """Example 5: Monitor metrics and performance."""
    print("\n=== Example 5: Metrics Monitoring ===\n")

    gateway = NgrokAIGateway(
        ngrok_endpoint="https://xxxxx.ngrok.app/v1",
        ngrok_api_key="your-ngrok-key",
    )

    # Simulate some requests
    gateway.metrics.total_requests = 100
    gateway.metrics.successful_requests = 95
    gateway.metrics.failed_requests = 5
    gateway.metrics.fallback_requests = 3
    gateway.metrics.ngrok_requests = 92
    gateway.metrics.ollama_requests = 3
    gateway.metrics.cache_hits = 45
    gateway.metrics.total_tokens = 5000
    gateway.metrics.total_cost = 0.075

    metrics = gateway.get_metrics()

    print("=== ngrok AI Gateway Metrics ===\n")
    print("Requests:")
    print(f"  Total:      {metrics['total_requests']}")
    print(f"  Successful: {metrics['successful_requests']}")
    print(f"  Failed:     {metrics['failed_requests']}")
    print(f"  Fallbacks:  {metrics['fallback_requests']}\n")

    print("Providers:")
    print(f"  ngrok:      {metrics['ngrok_requests']} requests")
    print(f"  ollama:     {metrics['ollama_requests']} requests\n")

    print("Performance:")
    print(f"  Success rate: {metrics['success_rate']}%")
    print(f"  Cache hits:   {metrics['cache_hits']}")
    print(f"  Uptime:       {metrics['uptime_seconds']}s")
    print(f"  Throughput:   {metrics['requests_per_minute']} req/min\n")

    print("Cost & Tokens:")
    print(f"  Total cost:          ${metrics['total_cost']:.4f}")
    print(f"  Avg cost/request:    ${metrics['average_cost_per_request']:.6f}")
    print(f"  Total tokens:        {metrics['total_tokens']}\n")


async def example_6_batch_processing():
    """Example 6: Batch processing with multiple models."""
    print("\n=== Example 6: Batch Processing ===\n")

    from cohezion.swarm.batch_processor import BatchItem

    client = TokenEfficientClient(
        ngrok_endpoint="https://xxxxx.ngrok.app/v1",
        ngrok_api_key="your-ngrok-key",
    )

    # Create batch items with different models
    items = [
        BatchItem(id="1", prompt="What is AI?", model="gpt-3.5-turbo", system=""),
        BatchItem(id="2", prompt="Write code to sort a list", model="gpt-4o", system=""),
        BatchItem(id="3", prompt="Write a poem about AI", model="claude-3.5-sonnet", system=""),
    ]

    print(f"Processing {len(items)} items in batch...\n")

    try:
        result = await client.batch_generate(items)

        print("Batch result:")
        print(f"  Items processed: {result.total_items if hasattr(result, 'total_items') else len(result.items)}")
        print(f"  Total tokens:    {result.total_tokens}")
        print(f"  Cache hits:      {result.cache_hits}")
        print(f"  Duration:        {result.total_duration_ms:.1f}ms\n")

        metrics = client.get_metrics()
        print("Overall metrics:")
        print(f"  Total cost: ${metrics['total_cost']:.6f}")
        print(f"  Success rate: {metrics['success_rate']}%\n")

    except Exception as e:
        print(f"Error: {e}\n")


async def main():
    """Run all examples."""
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║          ngrok AI Gateway Integration Examples                             ║
║                                                                            ║
║  Before running:                                                           ║
║  1. Enable ngrok AI Gateway at https://dashboard.ngrok.com/ai-gateways    ║
║  2. Copy your endpoint (https://xxxxx.ngrok.app/v1)                       ║
║  3. Set environment variables:                                             ║
║     export NGROK_ENDPOINT="https://xxxxx.ngrok.app/v1"                    ║
║     export NGROK_API_KEY="your-api-key"                                   ║
║                                                                            ║
║  Features demonstrated:                                                    ║
║  - Multi-provider routing (OpenAI, Anthropic, Google)                     ║
║  - Automatic failover to Ollama                                           ║
║  - Response caching (4th tier)                                            ║
║  - Cost tracking and optimization                                         ║
║  - Feature flag gradual rollout                                           ║
║  - Metrics monitoring and observability                                   ║
╚════════════════════════════════════════════════════════════════════════════╝
    """)

    # Uncomment examples to run (requires valid ngrok credentials)
    # await example_1_basic_generation()
    # await example_2_cost_optimization()
    # await example_3_failover_behavior()
    await example_4_feature_flags()
    await example_5_metrics_monitoring()
    # await example_6_batch_processing()

    print("\n✓ Examples complete. See docs/ngrok_ai_gateway_integration.md for details.\n")


if __name__ == "__main__":
    asyncio.run(main())
