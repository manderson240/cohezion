"""Experiential Distillation Pipeline for Cohezion.

This script runs nightly to harvest ExperienceTrace data from
tier-escalated models (Gemini/Claude) and convert them into DPO
preference pairs for fine-tuning the local SiliconSwarm (phi4-mini, qwen3).
"""

import asyncio
import logging
import time
from pathlib import Path

from cohezion.compound.evolution_training_bridge import (
    EvolutionTrainingConfig,
    EvolutionTrainingPipeline,
)
from cohezion.compound.group_evolution import (
    ExperienceTrace,
    GroupEvolutionEngine,
    TraceType,
)
from cohezion.integrations.telegram_bot import TelegramCommunicationHub


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_distillation() -> None:
    """Run the nightly distillation pipeline."""
    logger.info("Starting Nightly Experiential Distillation Pipeline")
    start_time = time.time()

    # In a fully deployed system, this would fetch from Genesis Persistence or VaultLogger.
    # For now, we seed the pipeline with traces demonstrating recent successes.
    mock_traces = {
        "claude-opus": [
            ExperienceTrace(
                trace_id="trc_001",
                agent_id="claude-opus",
                prompt_hash="hash_a",
                trace_type=TraceType.REASONING_CHAIN,
                content="Definitive logic flow...",
                quality_score=0.95,
                metadata={"complexity": "high", "success": True},
            )
        ],
        "gemini-pro": [
            ExperienceTrace(
                trace_id="trc_002",
                agent_id="gemini-pro",
                prompt_hash="hash_b",
                trace_type=TraceType.EXECUTION_RESULT,
                content="Optimal code generation...",
                quality_score=0.92,
                metadata={"complexity": "high", "success": True},
            )
        ],
        "phi4-mini": [
            ExperienceTrace(
                trace_id="trc_003",
                agent_id="phi4-mini",
                prompt_hash="hash_c",
                trace_type=TraceType.EXECUTION_RESULT,
                content="Failed loop...",
                quality_score=0.30,
                metadata={"complexity": "high", "success": False},
            )
        ],
    }

    mock_agents = [
        {"agent_id": "claude-opus", "execution_results": [True], "coherence": 0.5, "novelty": 0.8},
        {"agent_id": "gemini-pro", "execution_results": [True], "coherence": 0.6, "novelty": 0.7},
        {"agent_id": "phi4-mini", "execution_results": [False], "coherence": 0.2, "novelty": 0.1},
    ]

    task_ids = ["task_alpha"]

    # Initialize Engine and Pipeline
    engine = GroupEvolutionEngine(generation_size=3)
    config = EvolutionTrainingConfig(output_dir=Path("data/training/evolution"))
    pipeline = EvolutionTrainingPipeline(config=config)

    # Process round
    logger.info("Processing evolution history and extracting latent signals...")
    result = pipeline.run_round(
        engine=engine,
        trace_sources=mock_traces,
        task_ids=task_ids,
        agents=mock_agents,
    )

    elapsed = time.time() - start_time
    dpo_count = len(result.training_signals.dpo_pairs)

    summary = (
        f"🧪 <b>Experiential Distillation Complete</b>\n"
        f"Time: <code>{elapsed:.2f}s</code>\n"
        f"New DPO Pairs: <code>{dpo_count}</code>\n"
        f"Paths:\n<code>{result.exported_paths}</code>"
    )
    logger.info(f"Distillation complete. {dpo_count} DPO pairs generated.")

    # Hook into TelegramHub to report
    try:
        hub = TelegramCommunicationHub()
        if hub.is_configured():
            await hub._send_msg(summary)
            logger.info("Sent summary to Telegram.")
        else:
            logger.info("Telegram hub not configured, skipping notification.")
    except Exception as e:
        logger.warning(f"Could not send Telegram notification: {e}")


if __name__ == "__main__":
    asyncio.run(run_distillation())
