#!/usr/bin/env python
"""Example: Experience-Guided Skill Selection with CompoundExecutor.

Demonstrates the intelligent skill selection system that learns from vault
execution history to choose the best-performing skills for new tasks.

This example shows:
  1. How to query vault for prior skill performance
  2. Select best skill based on coherence, efficiency, and success rate
  3. Use selected skill for execution
  4. Log results back to vault for future guidance
"""

import logging
import sys

from cohezion.compound import CompoundExecutor, SkillSelector
from cohezion.core.mcp_client import MCPClient, MCPConfig


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Run experience-guided skill selection example."""
    # Initialize MCP client for vault access
    config = MCPConfig(
        server_url="http://localhost:8360/mcp",
        api_key="",  # No auth for local vault
    )
    mcp_client = MCPClient(config)

    # Create compound executor with vault integration
    executor = CompoundExecutor(mcp_client=mcp_client)

    # Example task
    task_description = "Analyze customer feedback and generate summary insights"
    operation_type = "analyze"

    logger.info("=" * 70)
    logger.info("EXPERIENCE-GUIDED SKILL SELECTION EXAMPLE")
    logger.info("=" * 70)
    logger.info("Task: %s", task_description)
    logger.info("Operation Type: %s", operation_type)
    logger.info("")

    # Step 1: Query vault for skill suggestions
    logger.info("Step 1: Querying vault for skill recommendations...")
    logger.info("-" * 70)

    skill_suggestions = executor.suggest_skills(
        task_description=task_description,
        operation_type=operation_type,
        project="cohezion",
        top_k=5,  # Get top 5 skill candidates
    )

    if skill_suggestions:
        logger.info("Found %d recommended skills:", len(skill_suggestions))
        for i, (skill_name, score) in enumerate(skill_suggestions, 1):
            logger.info("  %d. %s (score: %.3f)", i, skill_name, score)
    else:
        logger.info("No skill recommendations found in vault (vault may be empty)")
        logger.info("In production, this would suggest best skills based on history")

    logger.info("")

    # Step 2: Demonstrate detailed skill selector with metrics
    logger.info("Step 2: Detailed skill analysis with performance metrics...")
    logger.info("-" * 70)

    skill_selector = SkillSelector(
        mcp_client=mcp_client,
        coherence_weight=0.5,  # Weight for output quality
        efficiency_weight=0.3,  # Weight for token efficiency
        success_weight=0.2,  # Weight for success rate
    )

    detailed_suggestions = skill_selector.select_skills(
        task_description=task_description,
        operation_type=operation_type,
        project="cohezion",
        top_k=3,
    )

    if detailed_suggestions:
        logger.info("Detailed skill analysis (with metrics):")
        for skill_score in detailed_suggestions:
            logger.info("")
            logger.info("  Skill: %s", skill_score.skill_name)
            logger.info("    Composite Score: %.3f", skill_score.composite_score)
            logger.info("    Coherence Score: %.2f", skill_score.coherence_score)
            logger.info("    Token Efficiency: %.2f", skill_score.token_efficiency)
            logger.info("    Success Rate: %.2f", skill_score.success_rate)
            logger.info("    Times Used: %d", skill_score.times_used)
    else:
        logger.info("No detailed suggestions available")

    logger.info("")

    # Step 3: Show how this integrates with team execution
    logger.info("Step 3: Integration with Team Execution...")
    logger.info("-" * 70)
    logger.info("In team execution scenarios:")
    logger.info("  - Each task gets intelligent skill recommendations")
    logger.info("  - Best-performing skills selected based on vault history")
    logger.info("  - Execution results feed back into vault")
    logger.info("  - Future runs benefit from accumulated experience")
    logger.info("")

    # Step 4: Show decision factors
    logger.info("Step 4: How Skills Are Ranked (Scoring Factors)...")
    logger.info("-" * 70)
    logger.info("Skills are scored using a composite metric:")
    logger.info("  - Coherence (50%): Quality/correctness of output")
    logger.info("  - Efficiency (30%): Token usage relative to quality")
    logger.info("  - Success Rate (20%): Historical success percentage")
    logger.info("")
    logger.info("Example scoring:")
    logger.info("  Skill A: coherence=0.92, efficiency=0.85, success=0.95")
    logger.info("    → composite = (0.50×0.92) + (0.30×0.85) + (0.20×0.95)")
    logger.info("    → composite = 0.894")
    logger.info("")

    # Step 5: Vault learning loop
    logger.info("Step 5: Vault Learning Loop...")
    logger.info("-" * 70)
    logger.info("The system learns by:")
    logger.info("  1. Vault stores all execution patterns and metrics")
    logger.info("  2. SkillSelector queries vault for similar past tasks")
    logger.info("  3. Extracts coherence, efficiency, and success rates")
    logger.info("  4. Ranks skills and selects best candidate")
    logger.info("  5. Executor runs selected skill and logs results")
    logger.info("  6. Next similar task benefits from this learning")
    logger.info("")

    logger.info("=" * 70)
    logger.info("EXAMPLE COMPLETE")
    logger.info("=" * 70)
    logger.info("")
    logger.info("Key Takeaways:")
    logger.info("  ✓ Experience-guided selection optimizes skill choice")
    logger.info("  ✓ Vault serves as institutional memory for skills")
    logger.info("  ✓ Multiple metrics considered for ranking")
    logger.info("  ✓ System improves over time with more executions")
    logger.info("")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error("Error: %s", e, exc_info=True)
        sys.exit(1)
