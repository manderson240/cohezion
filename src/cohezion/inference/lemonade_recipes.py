"""Lemonade model recipes — capability profiles + inference parameters for the local fleet.

This module is the single source of truth for *recipe-shaped* model metadata:
capability scores, lane affinity, optimal sampling parameters, system prompts,
and thinking-mode budgets.  It is intentionally separate from
``cohezion.inference.registry`` (which owns the fleet topology) and from
``cohezion.inference.context_engineering`` (which owns prompt engineering), so
recipes can be researched and tuned in isolation.

Design choices
--------------
* ``ModelRecipe`` is a plain dataclass with defaults so it can be instantiated
  from live API data or hand-curated entries.
* ``LEMONADE_RECIPES`` contains all *known* Lemonade-downloaded text models.
  Unknown models discovered at runtime can be registered via ``register_recipe``.
* Capability scores are on [0, 1]; they are conservative blends of published
  benchmarks and local-fleet observations (small-N, not a replacement for a full
  eval harness).
* Lane affinity follows the Strix Halo Symphony mapping:
  NPU 13306, iGPU ROCWMMA 13307, iGPU Unified 13308, CPU 13309.
* ``task_scores`` maps each ``Task`` enum to a suitability score so
  ``best_model_for_task`` can pick the right default without a live API call.

Measurement notes
-----------------
Empirical probes were run against ``http://localhost:13305/v1/chat/completions``
with non-streaming requests and a small prompt set.  Metrics are noisy (n≈1-5);
they are used for *relative* ordering and budget estimation, not as ground-truth
benchmarks.  Where live probing failed or a model was not loaded, values are
marked ``estimated=True`` and derived from model-card claims.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from cohezion.inference.registry import Lane, Task


logger = logging.getLogger(__name__)

# Default recipe-scoped parameters that the model card harness uses.
_DEFAULT_TEMPERATURE = 0.7
_DEFAULT_TOP_P = 0.9
_DEFAULT_TOP_K = 40


@dataclass
class CapabilityProfile:
    """Capability scoring for a model on a 0-1 scale."""

    reasoning: float = 0.5
    coding: float = 0.5
    creativity: float = 0.5
    instruction_following: float = 0.5
    long_context: float = 0.5
    multilingual: float = 0.5


@dataclass
class SystemPromptBank:
    """System prompt templates keyed by task type."""

    default: str = "You are a helpful assistant."
    reasoning: str | None = None
    coding: str | None = None
    creative: str | None = None
    summarization: str | None = None
    structured: str | None = None


@dataclass
class OutputBudgets:
    """Max-token budgets per output type.  Values are *headroom* for the final
    answer and do NOT include thinking/reasoning overhead.  The harness adds
    overhead automatically for thinking models."""

    short_categorical: int = 50
    short_answer: int = 150
    medium_generation: int = 400
    long_generation: int = 800
    code: int = 600
    math_reasoning: int = 800


@dataclass
class EmpiricalMetrics:
    """Measured (or estimated) runtime behavior.

    Fields may be ``None`` when not yet measured.  ``estimated`` flags values that
    were not observed directly on this fleet.
    """

    ttft_ms: float | None = None
    tokens_per_sec: float | None = None
    thinking_overhead_tokens: int | None = None
    estimated: bool = True


@dataclass
class ModelRecipe:
    """A finely-tuned recipe for a single Lemonade model.

    The recipe is designed to be consumed by both ``fleet.py`` (for routing) and
    ``model_card_harness.py`` (for inference-parameter resolution).
    """

    model_id: str
    family: str
    variant: str
    lane: Lane
    capabilities: CapabilityProfile = field(default_factory=CapabilityProfile)

    # Optimal sampling parameters
    temperature: float = _DEFAULT_TEMPERATURE
    top_p: float = _DEFAULT_TOP_P
    top_k: int = _DEFAULT_TOP_K
    max_tokens_default: int = 512
    context_window: int = 4096

    # Task suitability: Task enum -> score in [0, 1]
    task_scores: dict[Task, float] = field(default_factory=dict)

    # System prompts per task type
    system_prompts: SystemPromptBank = field(default_factory=SystemPromptBank)

    # Special API behaviour
    supports_reasoning: bool = False
    supports_thinking: bool = False
    requires_special_api: bool = False
    special_api_params: dict[str, Any] = field(default_factory=dict)

    # Output budgets and empirical measurements
    output_budgets: OutputBudgets = field(default_factory=OutputBudgets)
    metrics: EmpiricalMetrics = field(default_factory=EmpiricalMetrics)

    def score_for_task(self, task: Task) -> float:
        """Return a suitability score for ``task``.

        Falls back to the model's overall instruction-following score when no
        explicit task score is registered.
        """
        return self.task_scores.get(task, self.capabilities.instruction_following)

    def system_prompt(self, task_type: str = "default") -> str:
        """Return the best system prompt for ``task_type``."""
        return getattr(self.system_prompts, task_type, None) or self.system_prompts.default


# ── Recipe builder helpers ───────────────────────────────────────────────────

def _cap(
    reasoning: float = 0.5,
    coding: float = 0.5,
    creativity: float = 0.5,
    instruction_following: float = 0.5,
    long_context: float = 0.5,
    multilingual: float = 0.5,
) -> CapabilityProfile:
    return CapabilityProfile(
        reasoning=reasoning,
        coding=coding,
        creativity=creativity,
        instruction_following=instruction_following,
        long_context=long_context,
        multilingual=multilingual,
    )


def _tasks(**scores: float) -> dict[Task, float]:
    """Build a task-score dict from keyword arguments.

    Unknown keys are ignored so the recipe file stays lenient if ``Task``
    evolves.
    """
    result: dict[Task, float] = {}
    for key, value in scores.items():
        try:
            result[Task(key)] = float(value)
        except ValueError:
            logger.debug("Ignoring unknown task %r in recipe", key)
    return result


def _prompts(
    default: str = "You are a helpful assistant.",
    reasoning: str | None = None,
    coding: str | None = None,
    creative: str | None = None,
    summarization: str | None = None,
    structured: str | None = None,
) -> SystemPromptBank:
    return SystemPromptBank(
        default=default,
        reasoning=reasoning,
        coding=coding,
        creative=creative,
        summarization=summarization,
        structured=structured,
    )


def _budgets(
    short_categorical: int = 50,
    short_answer: int = 150,
    medium_generation: int = 400,
    long_generation: int = 800,
    code: int = 600,
    math_reasoning: int = 800,
) -> OutputBudgets:
    return OutputBudgets(
        short_categorical=short_categorical,
        short_answer=short_answer,
        medium_generation=medium_generation,
        long_generation=long_generation,
        code=code,
        math_reasoning=math_reasoning,
    )


def _metrics(
    ttft_ms: float | None = None,
    tokens_per_sec: float | None = None,
    thinking_overhead_tokens: int | None = None,
    estimated: bool = True,
) -> EmpiricalMetrics:
    return EmpiricalMetrics(
        ttft_ms=ttft_ms,
        tokens_per_sec=tokens_per_sec,
        thinking_overhead_tokens=thinking_overhead_tokens,
        estimated=estimated,
    )


# ── Curated Lemonade recipes ───────────────────────────────────────────────────

LEMONADE_RECIPES: dict[str, ModelRecipe] = {}


def _register(recipe: ModelRecipe) -> None:
    LEMONADE_RECIPES[recipe.model_id] = recipe


# NPU lane: small, fast, direct models
_register(
    ModelRecipe(
        model_id="llama3.2-1b-FLM",
        family="llama",
        variant="1b-flm",
        lane=Lane.NPU,
        capabilities=_cap(
            reasoning=0.40,
            coding=0.35,
            creativity=0.45,
            instruction_following=0.70,
            long_context=0.30,
            multilingual=0.50,
        ),
        temperature=0.5,
        top_p=0.9,
        top_k=40,
        max_tokens_default=80,
        context_window=4096,
        task_scores=_tasks(
            sensing=0.85,
            routing=0.80,
            summarization=0.55,
            structured=0.50,
            general=0.60,
        ),
        system_prompts=_prompts(default="You are a fast, concise assistant. Give short, direct answers."),
        output_budgets=_budgets(
            short_categorical=20,
            short_answer=60,
            medium_generation=150,
            long_generation=300,
            code=250,
            math_reasoning=200,
        ),
        metrics=_metrics(ttft_ms=1400.0, tokens_per_sec=45.0, estimated=False),
    )
)

_register(
    ModelRecipe(
        model_id="gemma3-4b-FLM",
        family="gemma",
        variant="3-4b-flm",
        lane=Lane.NPU,
        capabilities=_cap(
            reasoning=0.60,
            coding=0.55,
            creativity=0.55,
            instruction_following=0.70,
            long_context=0.40,
            multilingual=0.65,
        ),
        temperature=0.5,
        top_p=0.9,
        max_tokens_default=150,
        context_window=8192,
        task_scores=_tasks(
            sensing=0.80,
            routing=0.75,
            summarization=0.60,
            general=0.65,
        ),
        system_prompts=_prompts(default="You are a fast, concise assistant."),
        metrics=_metrics(ttft_ms=900.0, tokens_per_sec=55.0, thinking_overhead_tokens=0, estimated=True),
    )
)

_register(
    ModelRecipe(
        model_id="gemma4-it-e2b-FLM",
        family="gemma",
        variant="4-e2b-flm",
        lane=Lane.NPU,
        capabilities=_cap(
            reasoning=0.55,
            coding=0.50,
            creativity=0.50,
            instruction_following=0.65,
            long_context=0.35,
            multilingual=0.60,
        ),
        temperature=0.5,
        top_p=0.9,
        max_tokens_default=100,
        context_window=4096,
        supports_thinking=True,
        task_scores=_tasks(
            sensing=0.75,
            routing=0.70,
            general=0.60,
        ),
        system_prompts=_prompts(default="You are a fast, helpful assistant."),
        output_budgets=_budgets(
            short_categorical=25,
            short_answer=75,
            medium_generation=150,
            long_generation=250,
            code=200,
            math_reasoning=200,
        ),
        metrics=_metrics(ttft_ms=1200.0, tokens_per_sec=50.0, thinking_overhead_tokens=450, estimated=True),
    )
)

_register(
    ModelRecipe(
        model_id="qwen3.5-4b-FLM",
        family="qwen",
        variant="3.5-4b-flm",
        lane=Lane.NPU,
        capabilities=_cap(
            reasoning=0.65,
            coding=0.60,
            creativity=0.60,
            instruction_following=0.72,
            long_context=0.45,
            multilingual=0.75,
        ),
        temperature=0.5,
        top_p=0.9,
        max_tokens_default=200,
        context_window=8192,
        supports_reasoning=True,
        task_scores=_tasks(
            sensing=0.75,
            routing=0.75,
            reasoning=0.65,
            code_gen=0.60,
            general=0.70,
        ),
        system_prompts=_prompts(default="You are a fast, accurate assistant."),
        metrics=_metrics(ttft_ms=1100.0, tokens_per_sec=52.0, thinking_overhead_tokens=350, estimated=True),
    )
)

_register(
    ModelRecipe(
        model_id="deepseek-r1-0528-8b-FLM",
        family="deepseek",
        variant="8b-flm",
        lane=Lane.NPU,
        capabilities=_cap(
            reasoning=0.85,
            coding=0.75,
            creativity=0.55,
            instruction_following=0.80,
            long_context=0.60,
            multilingual=0.80,
        ),
        temperature=0.6,
        top_p=0.95,
        max_tokens_default=400,
        context_window=40960,
        supports_reasoning=True,
        requires_special_api=True,
        special_api_params={"reasoning_format": "auto"},
        task_scores=_tasks(
            reasoning=0.90,
            code_gen=0.75,
            math=0.80,
            architect=0.65,
        ),
        system_prompts=_prompts(
            default="You are a helpful assistant with strong reasoning capabilities.",
            reasoning="You are a reasoning specialist. Think step-by-step and show your work.",
            coding="You are a coding expert. Write clean, efficient, well-commented code.",
        ),
        metrics=_metrics(ttft_ms=2500.0, tokens_per_sec=35.0, thinking_overhead_tokens=700, estimated=True),
    )
)

# iGPU ROCWMMA lane (13307)
_register(
    ModelRecipe(
        model_id="Gemma-4-E4B-it-GGUF",
        family="gemma",
        variant="4b",
        lane=Lane.IGPU_ROCWMMA,
        capabilities=_cap(
            reasoning=0.75,
            coding=0.70,
            creativity=0.65,
            instruction_following=0.80,
            long_context=0.70,
            multilingual=0.75,
        ),
        temperature=0.7,
        top_p=0.9,
        top_k=64,
        max_tokens_default=600,
        context_window=131072,
        supports_thinking=True,
        task_scores=_tasks(
            structured=0.90,
            governance=0.85,
            routing=0.80,
            reasoning=0.75,
            code_gen=0.70,
            general=0.80,
        ),
        system_prompts=_prompts(
            default="You are a helpful, accurate assistant.",
            coding="You are a coding assistant. Write correct, efficient code.",
            reasoning="You are a reasoning assistant. Think step by step.",
            structured="You are a structured-output assistant. Return only valid JSON.",
        ),
        output_budgets=_budgets(
            short_categorical=40,
            short_answer=120,
            medium_generation=350,
            long_generation=700,
            code=500,
            math_reasoning=700,
        ),
        metrics=_metrics(
            ttft_ms=3800.0,
            tokens_per_sec=35.0,
            thinking_overhead_tokens=2260,
            estimated=False,
        ),
    )
)

# iGPU Unified lane (13308) — large MoE / dense models
_register(
    ModelRecipe(
        model_id="Gemma-4-26B-A4B-it-GGUF",
        family="gemma",
        variant="26b-moe",
        lane=Lane.IGPU_UNIFIED,
        capabilities=_cap(
            reasoning=0.90,
            coding=0.80,
            creativity=0.75,
            instruction_following=0.85,
            long_context=0.95,
            multilingual=0.90,
        ),
        temperature=0.7,
        top_p=0.95,
        top_k=64,
        max_tokens_default=800,
        context_window=262144,
        supports_thinking=True,
        supports_reasoning=True,
        task_scores=_tasks(
            reasoning=0.92,
            code_gen=0.85,
            long_horizon=0.90,
            architect=0.85,
            general=0.88,
            math=0.80,
        ),
        system_prompts=_prompts(
            default="You are a helpful, harmless, and honest assistant.",
            reasoning="You are an expert analyst with strong reasoning capabilities. Provide structured, thorough responses.",
            creative="You are a creative assistant with good judgment. Balance creativity with accuracy.",
            coding="You are a coding specialist. Ensure all code is complete and syntactically correct.",
        ),
        metrics=_metrics(
            ttft_ms=6000.0,
            tokens_per_sec=30.0,
            thinking_overhead_tokens=1200,
            estimated=False,
        ),
    )
)

# CPU lane (13309) — dense large models
_register(
    ModelRecipe(
        model_id="Gemma-4-31B-it-GGUF",
        family="gemma",
        variant="31b",
        lane=Lane.CPU,
        capabilities=_cap(
            reasoning=0.80,
            coding=0.75,
            creativity=0.70,
            instruction_following=0.85,
            long_context=0.85,
            multilingual=0.80,
        ),
        temperature=0.7,
        top_p=0.9,
        max_tokens_default=800,
        context_window=262144,
        supports_thinking=True,
        task_scores=_tasks(
            architect=0.90,
            long_horizon=0.88,
            reasoning=0.80,
            general=0.82,
        ),
        system_prompts=_prompts(default="You are a knowledgeable, accurate assistant."),
        metrics=_metrics(ttft_ms=12000.0, tokens_per_sec=12.0, thinking_overhead_tokens=800, estimated=False),
    )
)

# Small CPU / edge models
_register(
    ModelRecipe(
        model_id="Qwen3-0.6B-GGUF",
        family="qwen",
        variant="0.6b",
        lane=Lane.CPU,
        capabilities=_cap(
            reasoning=0.50,
            coding=0.60,
            creativity=0.60,
            instruction_following=0.70,
            long_context=0.30,
            multilingual=0.70,
        ),
        temperature=0.5,
        top_p=0.9,
        max_tokens_default=128,
        context_window=8192,
        supports_reasoning=True,
        task_scores=_tasks(
            routing=0.70,
            general=0.65,
            code_gen=0.60,
        ),
        system_prompts=_prompts(default="You are a fast, efficient assistant. Give direct, concise answers."),
        metrics=_metrics(ttft_ms=350.0, tokens_per_sec=90.0, thinking_overhead_tokens=120, estimated=False),
    )
)

_register(
    ModelRecipe(
        model_id="Qwen3-8B-GGUF",
        family="qwen",
        variant="8b",
        lane=Lane.CPU,
        capabilities=_cap(
            reasoning=0.80,
            coding=0.90,
            creativity=0.70,
            instruction_following=0.85,
            long_context=0.80,
            multilingual=0.95,
        ),
        temperature=0.3,
        top_p=0.9,
        top_k=40,
        max_tokens_default=512,
        context_window=4096,
        supports_reasoning=True,
        task_scores=_tasks(
            code_gen=0.92,
            reasoning=0.82,
            math=0.80,
            general=0.80,
        ),
        system_prompts=_prompts(
            default="You are a helpful assistant.",
            coding="You are a coding specialist. Write correct, efficient code with proper error handling.",
            reasoning="You are a logical reasoning assistant. Think step by step.",
        ),
        metrics=_metrics(ttft_ms=1500.0, tokens_per_sec=50.0, thinking_overhead_tokens=400, estimated=True),
    )
)

_register(
    ModelRecipe(
        model_id="DeepSeek-Qwen3-8B-GGUF",
        family="deepseek",
        variant="8b",
        lane=Lane.CPU,
        capabilities=_cap(
            reasoning=0.90,
            coding=0.85,
            creativity=0.65,
            instruction_following=0.85,
            long_context=0.75,
            multilingual=0.90,
        ),
        temperature=0.6,
        top_p=0.95,
        max_tokens_default=400,
        context_window=131072,
        supports_reasoning=True,
        requires_special_api=True,
        special_api_params={"reasoning_format": "auto"},
        task_scores=_tasks(
            reasoning=0.92,
            code_gen=0.85,
            math=0.85,
            architect=0.75,
            general=0.82,
        ),
        system_prompts=_prompts(
            default="You are a helpful, accurate assistant with strong reasoning capabilities.",
            reasoning="You are an expert reasoning assistant. Think step by step and verify your answers.",
            coding="You are a skilled coding assistant. Write efficient, well-structured code.",
        ),
        metrics=_metrics(
            ttft_ms=8000.0,
            tokens_per_sec=20.0,
            thinking_overhead_tokens=900,
            estimated=False,
        ),
    )
)

_register(
    ModelRecipe(
        model_id="DeepSeek-R1-0528-Qwen3-8B-Q4_1",
        family="deepseek",
        variant="8b-q4",
        lane=Lane.CPU,
        capabilities=_cap(
            reasoning=0.95,
            coding=0.85,
            creativity=0.50,
            instruction_following=0.90,
            long_context=0.70,
            multilingual=0.80,
        ),
        temperature=0.6,
        top_p=0.95,
        max_tokens_default=600,
        context_window=32768,
        supports_reasoning=True,
        requires_special_api=True,
        special_api_params={"reasoning_format": "auto"},
        task_scores=_tasks(
            reasoning=0.95,
            math=0.90,
            code_gen=0.85,
            architect=0.80,
        ),
        system_prompts=_prompts(
            default="You are a helpful assistant with strong reasoning capabilities.",
            reasoning="You are a reasoning specialist. Think step-by-step and show your work.",
            coding="You are a coding expert. Write clean, efficient, well-commented code.",
        ),
        metrics=_metrics(ttft_ms=9000.0, tokens_per_sec=18.0, thinking_overhead_tokens=1200, estimated=True),
    )
)

_register(
    ModelRecipe(
        model_id="Qwen3.5-35B-A3B-GGUF",
        family="qwen",
        variant="35b-moe",
        lane=Lane.CPU,
        capabilities=_cap(
            reasoning=0.90,
            coding=0.85,
            creativity=0.75,
            instruction_following=0.90,
            long_context=0.90,
            multilingual=0.95,
        ),
        temperature=0.6,
        top_p=0.95,
        top_k=20,
        max_tokens_default=600,
        context_window=262144,
        supports_reasoning=True,
        task_scores=_tasks(
            reasoning=0.90,
            code_gen=0.88,
            long_horizon=0.90,
            architect=0.85,
            math=0.85,
            general=0.88,
        ),
        system_prompts=_prompts(
            default="You are a highly capable assistant.",
            reasoning="You are an expert with strong reasoning capabilities. Think thoroughly.",
        ),
        metrics=_metrics(ttft_ms=7000.0, tokens_per_sec=22.0, thinking_overhead_tokens=700, estimated=False),
    )
)

_register(
    ModelRecipe(
        model_id="Qwen3.6-27B-GGUF",
        family="qwen",
        variant="27b",
        lane=Lane.CPU,
        capabilities=_cap(
            reasoning=0.88,
            coding=0.88,
            creativity=0.72,
            instruction_following=0.88,
            long_context=0.85,
            multilingual=0.95,
        ),
        temperature=0.6,
        top_p=0.8,
        top_k=20,
        max_tokens_default=600,
        context_window=262144,
        supports_reasoning=True,
        task_scores=_tasks(
            code_gen=0.90,
            reasoning=0.88,
            long_horizon=0.85,
            general=0.85,
        ),
        system_prompts=_prompts(default="You are a highly capable assistant."),
        metrics=_metrics(ttft_ms=6500.0, tokens_per_sec=25.0, thinking_overhead_tokens=600, estimated=True),
    )
)

_register(
    ModelRecipe(
        model_id="Qwen3.6-35B-A3B-GGUF",
        family="qwen",
        variant="35b-moe",
        lane=Lane.CPU,
        capabilities=_cap(
            reasoning=0.90,
            coding=0.88,
            creativity=0.75,
            instruction_following=0.90,
            long_context=0.90,
            multilingual=0.95,
        ),
        temperature=0.6,
        top_p=0.8,
        top_k=20,
        max_tokens_default=600,
        context_window=262144,
        supports_reasoning=True,
        task_scores=_tasks(
            reasoning=0.91,
            code_gen=0.90,
            long_horizon=0.90,
            architect=0.86,
            math=0.86,
            general=0.89,
        ),
        system_prompts=_prompts(default="You are a highly capable assistant."),
        metrics=_metrics(ttft_ms=7200.0, tokens_per_sec=23.0, thinking_overhead_tokens=650, estimated=True),
    )
)

_register(
    ModelRecipe(
        model_id="Qwen3-Coder-30B-A3B-Instruct-GGUF",
        family="qwen",
        variant="30b-coder",
        lane=Lane.CPU,
        capabilities=_cap(
            reasoning=0.85,
            coding=0.95,
            creativity=0.60,
            instruction_following=0.88,
            long_context=0.85,
            multilingual=0.85,
        ),
        temperature=0.3,
        top_p=0.9,
        max_tokens_default=800,
        context_window=262144,
        supports_reasoning=True,
        task_scores=_tasks(
            code_gen=0.96,
            reasoning=0.82,
            long_horizon=0.80,
            architect=0.80,
        ),
        system_prompts=_prompts(
            default="You are an expert coding assistant.",
            coding="You are a coding specialist. Write correct, efficient, well-structured code.",
        ),
        metrics=_metrics(ttft_ms=6000.0, tokens_per_sec=28.0, thinking_overhead_tokens=500, estimated=True),
    )
)

_register(
    ModelRecipe(
        model_id="Qwen3.6-35B-A3B-ThinkingCoder",
        family="qwen",
        variant="35b-moe-thinking-coder",
        lane=Lane.CPU,
        capabilities=_cap(
            reasoning=0.92,
            coding=0.95,
            creativity=0.65,
            instruction_following=0.90,
            long_context=0.85,
            multilingual=0.85,
        ),
        temperature=0.6,
        top_p=0.95,
        top_k=20,
        max_tokens_default=800,
        context_window=262144,
        supports_reasoning=True,
        supports_thinking=True,
        task_scores=_tasks(
            code_gen=0.97,
            reasoning=0.90,
            math=0.88,
            architect=0.85,
        ),
        system_prompts=_prompts(
            default="You are an expert coding and reasoning assistant.",
            coding="You are a coding specialist. Think step by step, then write correct, efficient code.",
        ),
        metrics=_metrics(ttft_ms=7500.0, tokens_per_sec=24.0, thinking_overhead_tokens=800, estimated=True),
    )
)

_register(
    ModelRecipe(
        model_id="Qwen3.6-35B-A3B-NoThinking",
        family="qwen",
        variant="35b-moe-no-think",
        lane=Lane.CPU,
        capabilities=_cap(
            reasoning=0.82,
            coding=0.85,
            creativity=0.75,
            instruction_following=0.90,
            long_context=0.90,
            multilingual=0.95,
        ),
        temperature=0.6,
        top_p=0.8,
        top_k=20,
        max_tokens_default=600,
        context_window=262144,
        supports_reasoning=False,
        supports_thinking=False,
        task_scores=_tasks(
            general=0.90,
            routing=0.88,
            summarization=0.85,
            structured=0.85,
            code_gen=0.82,
        ),
        system_prompts=_prompts(default="You are a helpful, efficient assistant."),
        metrics=_metrics(ttft_ms=5000.0, tokens_per_sec=30.0, thinking_overhead_tokens=0, estimated=True),
    )
)

_register(
    ModelRecipe(
        model_id="Bonsai-1.7B-gguf",
        family="bonsai",
        variant="1.7b",
        lane=Lane.CPU,
        capabilities=_cap(
            reasoning=0.45,
            coding=0.50,
            creativity=0.55,
            instruction_following=0.65,
            long_context=0.40,
            multilingual=0.50,
        ),
        temperature=0.6,
        top_p=0.9,
        max_tokens_default=200,
        context_window=32768,
        task_scores=_tasks(
            routing=0.70,
            general=0.65,
            structured=0.60,
        ),
        system_prompts=_prompts(default="You are a helpful assistant."),
        metrics=_metrics(ttft_ms=300.0, tokens_per_sec=70.0, estimated=True),
    )
)

_register(
    ModelRecipe(
        model_id="Bonsai-4B-gguf",
        family="bonsai",
        variant="4b",
        lane=Lane.CPU,
        capabilities=_cap(
            reasoning=0.55,
            coding=0.60,
            creativity=0.60,
            instruction_following=0.70,
            long_context=0.50,
            multilingual=0.55,
        ),
        temperature=0.6,
        top_p=0.9,
        max_tokens_default=300,
        context_window=32768,
        task_scores=_tasks(
            routing=0.75,
            general=0.70,
            structured=0.65,
            reasoning=0.60,
        ),
        system_prompts=_prompts(default="You are a helpful assistant."),
        metrics=_metrics(ttft_ms=500.0, tokens_per_sec=55.0, estimated=True),
    )
)

_register(
    ModelRecipe(
        model_id="Bonsai-8B-gguf",
        family="bonsai",
        variant="8b",
        lane=Lane.CPU,
        capabilities=_cap(
            reasoning=0.65,
            coding=0.70,
            creativity=0.65,
            instruction_following=0.75,
            long_context=0.60,
            multilingual=0.60,
        ),
        temperature=0.6,
        top_p=0.9,
        max_tokens_default=400,
        context_window=65536,
        task_scores=_tasks(
            reasoning=0.70,
            code_gen=0.70,
            general=0.75,
            structured=0.70,
        ),
        system_prompts=_prompts(default="You are a helpful assistant."),
        metrics=_metrics(ttft_ms=800.0, tokens_per_sec=45.0, estimated=True),
    )
)

_register(
    ModelRecipe(
        model_id="Nemotron-3-Nano-30B-A3B-GGUF",
        family="nemotron",
        variant="30b-moe",
        lane=Lane.CPU,
        capabilities=_cap(
            reasoning=0.80,
            coding=0.75,
            creativity=0.60,
            instruction_following=0.85,
            long_context=0.80,
            multilingual=0.75,
        ),
        temperature=0.7,
        top_p=0.9,
        max_tokens_default=600,
        context_window=1048576,
        task_scores=_tasks(
            reasoning=0.82,
            code_gen=0.78,
            long_horizon=0.85,
            general=0.80,
        ),
        system_prompts=_prompts(default="You are a helpful, accurate assistant."),
        metrics=_metrics(ttft_ms=8000.0, tokens_per_sec=20.0, estimated=True),
    )
)

_register(
    ModelRecipe(
        model_id="Llama-4-Scout-17B-16E-Instruct-GGUF-Q4_K_M",
        family="llama",
        variant="17b-moe",
        lane=Lane.CPU,
        capabilities=_cap(
            reasoning=0.82,
            coding=0.78,
            creativity=0.70,
            instruction_following=0.85,
            long_context=0.90,
            multilingual=0.80,
        ),
        temperature=0.6,
        top_p=0.9,
        max_tokens_default=600,
        context_window=131072,
        task_scores=_tasks(
            reasoning=0.83,
            code_gen=0.80,
            long_horizon=0.85,
            general=0.82,
        ),
        system_prompts=_prompts(default="You are a helpful, accurate assistant."),
        metrics=_metrics(ttft_ms=7000.0, tokens_per_sec=22.0, estimated=True),
    )
)


# ── Public API ────────────────────────────────────────────────────────────────


def get_recipe(model_id: str) -> ModelRecipe | None:
    """Return a recipe by exact model ID, or ``None`` if unknown."""
    return LEMONADE_RECIPES.get(model_id)


def best_model_for_task(
    task: Task | str,
    lane: Lane | None = None,
    prefer_downloaded: set[str] | None = None,
) -> str | None:
    """Return the model_id with the highest task score, optionally filtered by lane.

    ``prefer_downloaded`` is a set of IDs known to be available.  If provided,
    only those IDs are considered; otherwise all recipes are eligible.
    """
    if isinstance(task, str):
        try:
            task = Task(task)
        except ValueError as exc:
            raise ValueError(f"Unknown task {task!r}") from exc

    candidates = LEMONADE_RECIPES.values()
    if lane is not None:
        candidates = [r for r in candidates if r.lane == lane]
    if prefer_downloaded is not None:
        candidates = [r for r in candidates if r.model_id in prefer_downloaded]

    if not candidates:
        return None

    best = max(candidates, key=lambda r: r.score_for_task(task))
    return best.model_id


def get_inference_params(
    model_id: str,
    output_type: str = "medium_generation",
    task_type: str = "default",
) -> dict[str, Any]:
    """Build an OpenAI-compatible payload fragment for ``model_id``.

    This is a convenience wrapper used by ``model_card_harness.py`` and by
    callers that want a quick parameter bundle without importing the full
    context engineer.

    The returned dict contains: ``model``, ``temperature``, ``top_p``,
    ``max_tokens``, ``system`` (the selected system prompt), and
    ``extra_body`` (thinking budgets / special API params).  It intentionally
    does NOT include ``messages`` — the caller must still provide the
    conversation.
    """
    recipe = get_recipe(model_id)
    if recipe is None:
        return {
            "model": model_id,
            "temperature": _DEFAULT_TEMPERATURE,
            "top_p": _DEFAULT_TOP_P,
            "top_k": _DEFAULT_TOP_K,
            "max_tokens": 512,
            "system": "You are a helpful assistant.",
            "extra_body": {},
        }

    budget = getattr(recipe.output_budgets, output_type, recipe.output_budgets.medium_generation)
    if recipe.supports_thinking and recipe.metrics.thinking_overhead_tokens:
        # Leave room for thinking tokens without blowing up the context window.
        max_tokens = min(
            budget + recipe.metrics.thinking_overhead_tokens,
            recipe.context_window - 512,
        )
    else:
        max_tokens = budget

    extra_body: dict[str, Any] = dict(recipe.special_api_params)
    if recipe.supports_thinking and recipe.metrics.thinking_overhead_tokens:
        # Use a bounded thinking budget; the output headroom is already added above.
        extra_body["thinking"] = {
            "type": "enabled",
            "budget_tokens": min(recipe.metrics.thinking_overhead_tokens, max_tokens - 50),
        }

    system = recipe.system_prompt(task_type)

    return {
        "model": model_id,
        "temperature": recipe.temperature,
        "top_p": recipe.top_p,
        "top_k": recipe.top_k,
        "max_tokens": max(max_tokens, 64),
        "system": system,
        "extra_body": extra_body,
    }


def register_recipe(recipe: ModelRecipe) -> None:
    """Register or overwrite a recipe at runtime (e.g. from live discovery)."""
    LEMONADE_RECIPES[recipe.model_id] = recipe


def probe_live_models(port: int = 13305, timeout: float = 3.0) -> list[dict]:
    """Fetch the list of models from the Lemonade /v1/models endpoint.

    Returns an empty list if the server is unreachable so callers can degrade
    gracefully.  This is the live I/O boundary that tests should mock.
    """
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/v1/models", timeout=timeout
        ) as response:
            data = json.loads(response.read())
        return data.get("data", [])
    except Exception:
        logger.debug("probe_live_models: Lemonade unavailable on port %d", port)
        return []


def discover_from_live_models(models: list[dict]) -> list[str]:
    """Add minimal recipes for downloaded models not already in ``LEMONADE_RECIPES``.

    Returns the list of newly-registered model IDs.  Existing recipes are never
    overwritten.
    """
    added: list[str] = []
    for model in models:
        model_id = model.get("id")
        if not model_id or model_id in LEMONADE_RECIPES:
            continue
        if not model.get("downloaded"):
            continue
        labels = model.get("labels", [])
        family = "unknown"
        for prefix, fam in [
            ("Gemma", "gemma"),
            ("Qwen", "qwen"),
            ("llama", "llama"),
            ("DeepSeek", "deepseek"),
            ("Bonsai", "bonsai"),
            ("Nemotron", "nemotron"),
            ("Granite", "granite"),
            ("Llama-4", "llama"),
        ]:
            if model_id.startswith(prefix):
                family = fam
                break
        ctx = model.get("max_context_window") or 4096
        recipe = ModelRecipe(
            model_id=model_id,
            family=family,
            variant="auto",
            lane=Lane.CPU,
            context_window=int(ctx),
            supports_reasoning="reasoning" in labels,
            supports_thinking="reasoning" in labels and family in {"gemma", "qwen"},
            system_prompts=_prompts(default="You are a helpful assistant."),
            metrics=_metrics(estimated=True),
        )
        LEMONADE_RECIPES[model_id] = recipe
        added.append(model_id)
    return added
