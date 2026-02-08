#!/usr/bin/env python
"""Example: Using CompoundExecutor with vault integration.

Demonstrates the closed-loop compound engineering pipeline:
  1. Query vault for experience guidance
  2. Execute task with logging
  3. Vault persists trajectory and patterns
  4. Future runs can use prior learnings
"""

import logging
import sys

from cohezion.compound import CompoundExecutor
from cohezion.core.mcp_client import MCPClient, MCPConfig


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def example_skill_execution(guidance: dict) -> tuple[str, dict]:
    """Example skill that uses experience guidance.

    Args:
        guidance: Experience guidance from vault (prior similar runs)

    Returns:
        Tuple of (output, metrics)
    """
    # Use guidance to seed execution parameters
    relevant_context = guidance.get("relevant_context", [])
    logger.info("Found %d relevant prior runs in vault", len(relevant_context))

    if relevant_context:
        logger.info("Using guidance from prior runs to optimize execution")
        # Could extract best_coherence, best_tokens, etc. from prior runs
        best_run = relevant_context[0]
        logger.info("Best prior run: %s", best_run)

    # Simulate skill execution
    output = """
    Executed skill with guidance from vault.
    - Analyzed 3 prior similar tasks
    - Found optimal token budget from experience: 150 tokens
    - Achieved coherence: 0.92
    - Execution time: 1.2s
    """

    metrics = {
        "tokens_used": 145,
        "latency_seconds": 1.2,
        "coherence": 0.92,
        "guided_by_vault": len(relevant_context) > 0,
    }

    return output, metrics


def main():
    """Run example compound execution with vault integration."""
    logger.info("=== Compound Engineering Example ===")

    # Step 1: Initialize MCP client
    try:
        config = MCPConfig(
            server_url="http://localhost:8360",
            api_key="test-key",  # Can be any non-empty string for localhost
        )
        mcp_client = MCPClient(config)
        mcp_client.connect()
        logger.info("Connected to Cloud Vault MCP server")
    except Exception as e:
        logger.error("Failed to connect to vault: %s", e)
        logger.info("Tip: Ensure cloud-vault-mcp server is running on port 8360")
        return 1

    # Step 2: Create compound executor
    executor = CompoundExecutor(mcp_client)
    logger.info("Initialized CompoundExecutor with vault integration")

    # Step 3: Get experience guidance
    logger.info("\n--- Phase 1: Experience Guidance ---")
    guidance = executor.get_experience_guidance(
        task_description="Optimize token efficiency for LLM inference",
        project="cohezion",
    )
    logger.info("Experience guidance: %s", guidance)

    # Step 4: Execute task with full vault integration
    logger.info("\n--- Phase 2: Execute Task ---")
    result = executor.execute_task(
        task_description="Optimize token efficiency for inference with coherence >0.9",
        skill_name="token_optimizer",
        operation_type="generate",
        execute_fn=example_skill_execution,
        project="cohezion",
    )

    # Step 5: Display results
    logger.info("\n--- Phase 3: Results ---")
    logger.info("Success: %s", result.success)
    logger.info("Output:\n%s", result.output)
    logger.info("Metrics: %s", result.metrics)
    logger.info("Duration: %.2fs", result.duration_seconds)
    logger.info("Experiment path: %s", result.vault_experiment_path)
    logger.info("Pattern paths: %s", result.vault_decision_paths)

    # Step 6: Log inflection point (optional)
    logger.info("\n--- Phase 4: Log Decision Point ---")
    if result.success and result.metrics["coherence"] > 0.9:
        decision_path = executor.log_inflection_point(
            title="High coherence achieved with token optimization",
            context=f"Token efficiency execution: {result.metrics}",
            decision="Lock in optimized parameters for future runs",
            rationale="Achieved target coherence >0.9 with reasonable token usage",
        )
        logger.info("Decision logged: %s", decision_path)

    # Step 7: Demonstrate experience-guided future execution
    logger.info("\n--- Phase 5: Experience-Guided Future Run ---")
    logger.info("Running same task again to use vault learnings...")

    result2 = executor.execute_task(
        task_description="Optimize token efficiency for inference with coherence >0.9",
        skill_name="token_optimizer",
        operation_type="generate",
        execute_fn=example_skill_execution,
        project="cohezion",
    )

    logger.info("Second execution metrics: %s", result2.metrics)
    logger.info(
        "Experience guidance was used: %s",
        result2.metrics.get("guided_by_vault", False),
    )

    logger.info("\n=== Closed-Loop Compound Engineering Complete ===")
    logger.info("Vault now contains:")
    logger.info("  - 2 execution experiments")
    logger.info("  - 1 decision point (high coherence achieved)")
    logger.info("  - 2 patterns (token_optimizer_generate_success)")
    logger.info("\nFuture runs can query vault for experience guidance!")

    mcp_client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
