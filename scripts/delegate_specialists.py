#!/usr/bin/env python3
import asyncio
import logging
from cohezion.swarm.team_orchestrator import TeamOrchestrator, TaskSpec
from cohezion.swarm.team_execution import TeamCompoundExecutor
from cohezion.integrations.agentverse.llm_executor import LLMExecutor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_specialist_delegation():
    print("=" * 60)
    print("DELEGATING SPECIALIST TEAMS (OLLAMA CLOUD MODELS)")
    print("=" * 60)
    
    # Extend with Ollama cloud models via LLMExecutor
    cloud_executor = LLMExecutor(model="qwen3.5:cloud")
    team_executor = TeamCompoundExecutor(compound_executor=cloud_executor, auto_feedback=True)
    orchestrator = TeamOrchestrator()
    
    tasks = [
        TaskSpec(
            id="arc-1",
            subject="ARC Prize - Phase 4 12D Manifold Transfer",
            description="Use DeepSeek-R1 logic to calculate 12D latent displacements for ARC-AGI-2 tasks.",
            tags=["flume", "reasoning", "physics"],
            dependencies=[]
        ),
        TaskSpec(
            id="agi-1",
            subject="AGI Benchmark - Phase 5",
            description="Run full cognitive kbench benchmark for executive function.",
            tags=["evaluation", "reasoning"],
            dependencies=[]
        ),
        TaskSpec(
            id="bird-1",
            subject="BirdCLEF 2026 - Feature Anomaly Detection",
            description="Project Mel-Spectrogram features into 12D manifold for anomaly detection.",
            tags=["vision", "physics", "signal_processing"],
            dependencies=[]
        )
    ]
    
    for task in tasks:
        logger.info(f"Delegating Task: {task.subject}")
        result = await team_executor.execute_task(task)
        logger.info(f"Result Status: {result['status']} | Model Used: {result.get('model', 'N/A')}")
        logger.info("-" * 40)

if __name__ == "__main__":
    asyncio.run(run_specialist_delegation())
