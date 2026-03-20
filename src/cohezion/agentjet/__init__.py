"""Agentjet: training lifecycle, context optimization, and OOM-safe Ollama management."""

from cohezion.agentjet.context_optimizer import (
    CONTEXT_PROFILES,
    ContextOptimizer,
    ModelContextProfile,
    OllamaContextManager,
)
from cohezion.agentjet.embeddings import (
    EmbeddingContext,
    EmbeddingOrchestrator,
    EmbeddingResult,
    FlumeVAEEmbeddingModel,
    GeminiEmbeddingModel,
)
from cohezion.agentjet.judger import PhiScoreJudger
from cohezion.agentjet.task_reader import JourneyTaskReader
from cohezion.agentjet.trainer import AgentJetTrainer, TrainingResult
from cohezion.agentjet.unsloth_bridge import UnslothBridge
from cohezion.agentjet.workflow import CohezionWorkflow

__all__ = [
    # Core workflow
    "AgentJetTrainer",
    "CohezionWorkflow",
    "JourneyTaskReader",
    "PhiScoreJudger",
    "TrainingResult",
    "UnslothBridge",
    # Context optimization
    "CONTEXT_PROFILES",
    "ContextOptimizer",
    "ModelContextProfile",
    "OllamaContextManager",
    # Embeddings
    "EmbeddingContext",
    "EmbeddingOrchestrator",
    "EmbeddingResult",
    "FlumeVAEEmbeddingModel",
    "GeminiEmbeddingModel",
]
