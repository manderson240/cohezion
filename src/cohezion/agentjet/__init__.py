"""Agentjet: training lifecycle, context optimization, and OOM-safe Ollama management."""

import contextlib

with contextlib.suppress(Exception):
    from cohezion.agentjet.context_optimizer import CONTEXT_PROFILES as CONTEXT_PROFILES
    from cohezion.agentjet.context_optimizer import ContextOptimizer as ContextOptimizer
    from cohezion.agentjet.context_optimizer import ModelContextProfile as ModelContextProfile
    from cohezion.agentjet.context_optimizer import OllamaContextManager as OllamaContextManager

with contextlib.suppress(Exception):
    from cohezion.agentjet.embeddings import EmbeddingContext as EmbeddingContext
    from cohezion.agentjet.embeddings import EmbeddingOrchestrator as EmbeddingOrchestrator
    from cohezion.agentjet.embeddings import EmbeddingResult as EmbeddingResult
    from cohezion.agentjet.embeddings import FlumeVAEEmbeddingModel as FlumeVAEEmbeddingModel
    from cohezion.agentjet.embeddings import GeminiEmbeddingModel as GeminiEmbeddingModel

with contextlib.suppress(Exception):
    from cohezion.agentjet.judger import PhiScoreJudger as PhiScoreJudger

with contextlib.suppress(Exception):
    from cohezion.agentjet.task_reader import JourneyTaskReader as JourneyTaskReader

with contextlib.suppress(Exception):
    from cohezion.agentjet.trainer import AgentJetTrainer as AgentJetTrainer
    from cohezion.agentjet.trainer import TrainingResult as TrainingResult

# UnslothBridge requires unsloth → torch + transformers (heavy deps, Strix Halo OOM risk)
with contextlib.suppress(Exception):
    from cohezion.agentjet.unsloth_bridge import UnslothBridge as UnslothBridge

with contextlib.suppress(Exception):
    from cohezion.agentjet.workflow import CohezionWorkflow as CohezionWorkflow
