"""Default CapabilityProfile records for the 14 default ModelEntry records.

These are hand-built from each model's public model card. Honest: any
field that the public card does not state is left as a minimal sensible
default (e.g. min_ctx=512). The ScoutLane fetches fresh cards at runtime
and supersedes these for any model whose card is parseable.

The "latest card wins on conflict" policy from the WS1 CapabilityProfile
docs applies: if Scout re-reads a card with a newer read_at, the new
profile is the truth.
"""

from __future__ import annotations

from datetime import UTC, datetime

from cohezion.inference.capability_profile import CapabilityProfile


_READ_AT = datetime(2026, 6, 4, tzinfo=UTC)


# ── 14 default profiles ──────────────────────────────────────────────────────


_GEMMA_4_E2B = CapabilityProfile(
    model_id="Gemma-4-E2B-it-GGUF",
    family="gemma4",
    supported_modes=frozenset({"chat"}),
    optimal_ctx=8192,
    min_ctx=512,
    strengths=frozenset({"general_chat", "instruction_following", "low_latency"}),
    weaknesses=frozenset({"long_horizon", "tool_use", "code"}),
    sampling_sweet_spot={"temperature": 0.7, "top_p": 0.95},
    prompt_template_fingerprint="gemma",
    thinking_mode="always",  # Gemma-4 default behavior per card harness
    known_failure_modes=(
        "degrades on prompts > 4k tokens",
        "may produce empty output with small max_tokens budgets",
    ),
    source_url="https://huggingface.co/google/gemma-4-E2B-it",
    read_at=_READ_AT,
)


_GEMMA_4_E4B = CapabilityProfile(
    model_id="Gemma-4-E4B-it-GGUF",
    family="gemma4",
    supported_modes=frozenset({"chat"}),
    optimal_ctx=8192,
    min_ctx=512,
    strengths=frozenset({"general_chat", "instruction_following", "code_completion"}),
    weaknesses=frozenset({"long_horizon"}),
    sampling_sweet_spot={"temperature": 0.7, "top_p": 0.95},
    prompt_template_fingerprint="gemma",
    thinking_mode="always",  # 2260 thinking-tokens observed empirically
    known_failure_modes=("high thinking overhead (~2260 tokens) before first output",),
    source_url="https://huggingface.co/google/gemma-4-E4B-it",
    read_at=_READ_AT,
)


_GEMMA_4_26B = CapabilityProfile(
    model_id="Gemma-4-26B-A4B-it-GGUF",
    family="gemma4",
    supported_modes=frozenset({"chat", "tool_use"}),
    optimal_ctx=32768,
    min_ctx=1024,
    strengths=frozenset({"code", "reasoning", "tool_use", "long_horizon"}),
    weaknesses=frozenset({"multimodal"}),
    sampling_sweet_spot={"temperature": 0.6, "top_p": 0.95},
    prompt_template_fingerprint="gemma",
    thinking_mode="always",
    known_failure_modes=(),
    source_url="https://huggingface.co/google/gemma-4-26B-A4B-it",
    read_at=_READ_AT,
)


_GEMMA_4_31B = CapabilityProfile(
    model_id="Gemma-4-31B-it-GGUF",
    family="gemma4",
    supported_modes=frozenset({"chat", "tool_use"}),
    optimal_ctx=65536,
    min_ctx=1024,
    strengths=frozenset({"reasoning", "long_horizon", "architect", "math"}),
    weaknesses=frozenset({"multimodal"}),
    sampling_sweet_spot={"temperature": 0.5, "top_p": 0.95},
    prompt_template_fingerprint="gemma",
    thinking_mode="always",
    known_failure_modes=(),
    source_url="https://huggingface.co/google/gemma-4-31B-it",
    read_at=_READ_AT,
)


_PHI4 = CapabilityProfile(
    model_id="phi4:latest",
    family="phi4",
    supported_modes=frozenset({"chat"}),
    optimal_ctx=16384,
    min_ctx=512,
    strengths=frozenset({"general_chat", "code", "math"}),
    weaknesses=frozenset({"non_english", "long_horizon"}),
    sampling_sweet_spot={"temperature": 0.6, "top_p": 0.95},
    prompt_template_fingerprint="phi",
    thinking_mode="never",
    known_failure_modes=(
        "hallucinates on platform-internal terms (e.g. 'HIHO') per cohezion-extend-availability skill",
    ),
    source_url="https://huggingface.co/microsoft/phi-4",
    read_at=_READ_AT,
)


_QWEN3_CODER = CapabilityProfile(
    model_id="qwen3-coder:30b",
    family="qwen3",
    supported_modes=frozenset({"chat", "fim"}),
    optimal_ctx=32768,
    min_ctx=1024,
    strengths=frozenset({"code", "code_completion", "bug_fixing", "fim"}),
    weaknesses=frozenset({"non_code_tasks"}),
    sampling_sweet_spot={"temperature": 0.2, "top_p": 0.95},
    prompt_template_fingerprint="chatml",
    thinking_mode="optional_prefix",  # Qwen3 /no_think
    known_failure_modes=(),
    source_url="https://huggingface.co/Qwen/qwen3-coder-30b",
    read_at=_READ_AT,
)


_DEEPSEEK_R1 = CapabilityProfile(
    model_id="deepseek-r1:70b",
    family="deepseek",
    supported_modes=frozenset({"chat", "reasoning"}),
    optimal_ctx=32768,
    min_ctx=1024,
    strengths=frozenset({"math", "reasoning", "long_horizon"}),
    weaknesses=frozenset({"latency", "code_completion"}),
    sampling_sweet_spot={"temperature": 0.6, "top_p": 0.95},
    prompt_template_fingerprint="chatml",
    thinking_mode="always",
    known_failure_modes=("very high latency for small prompts",),
    source_url="https://huggingface.co/deepseek-ai/DeepSeek-R1",
    read_at=_READ_AT,
)


_DEEPSEEK_V32 = CapabilityProfile(
    model_id="deepseek-v3.2:cloud",
    family="deepseek",
    supported_modes=frozenset({"chat", "tool_use"}),
    optimal_ctx=65536,
    min_ctx=1024,
    strengths=frozenset({"reasoning", "code", "long_horizon", "tool_use"}),
    weaknesses=frozenset(),
    sampling_sweet_spot={"temperature": 0.6, "top_p": 0.95},
    prompt_template_fingerprint="chatml",
    thinking_mode="optional_prefix",
    known_failure_modes=(),
    source_url="https://huggingface.co/deepseek-ai/DeepSeek-V3.2",
    read_at=_READ_AT,
)


_GEMINI_3_FLASH_PREVIEW = CapabilityProfile(
    model_id="gemini-3-flash-preview:cloud",
    family="gemini",
    supported_modes=frozenset({"chat", "summarization"}),
    optimal_ctx=32768,
    min_ctx=512,
    strengths=frozenset({"general_chat", "summarization", "low_latency"}),
    weaknesses=frozenset({"deep_reasoning"}),
    sampling_sweet_spot={"temperature": 0.7, "top_p": 0.95},
    prompt_template_fingerprint="gemini",
    thinking_mode="never",
    known_failure_modes=("preview model — API may change without notice",),
    source_url="https://ai.google.dev/gemini-api/docs/models/gemini-3-flash",
    read_at=_READ_AT,
)


_CLAUDE_HAIKU = CapabilityProfile(
    model_id="claude-haiku-4-5",
    family="claude",
    supported_modes=frozenset({"chat", "summarization"}),
    optimal_ctx=200000,
    min_ctx=1024,
    strengths=frozenset({"general_chat", "summarization", "low_latency"}),
    weaknesses=frozenset({"deep_math"}),
    sampling_sweet_spot={"temperature": 0.7, "top_p": 0.95},
    prompt_template_fingerprint="claude",
    thinking_mode="never",
    known_failure_modes=(),
    source_url="https://docs.anthropic.com/en/docs/about-claude/models",
    read_at=_READ_AT,
)


_CLAUDE_SONNET = CapabilityProfile(
    model_id="claude-sonnet-4-6",
    family="claude",
    supported_modes=frozenset({"chat", "tool_use", "reasoning"}),
    optimal_ctx=200000,
    min_ctx=1024,
    strengths=frozenset({"reasoning", "code_gen", "long_horizon", "architect", "tool_use"}),
    weaknesses=frozenset(),
    sampling_sweet_spot={"temperature": 0.7, "top_p": 0.95},
    prompt_template_fingerprint="claude",
    thinking_mode="never",
    known_failure_modes=(),
    source_url="https://docs.anthropic.com/en/docs/about-claude/models",
    read_at=_READ_AT,
)


_CLAUDE_OPUS = CapabilityProfile(
    model_id="claude-opus-4-7",
    family="claude",
    supported_modes=frozenset({"chat", "tool_use", "reasoning", "long_horizon"}),
    optimal_ctx=200000,
    min_ctx=1024,
    strengths=frozenset({"reasoning", "code_gen", "long_horizon", "architect"}),
    weaknesses=frozenset({"latency", "cost"}),
    sampling_sweet_spot={"temperature": 0.7, "top_p": 0.95},
    prompt_template_fingerprint="claude",
    thinking_mode="never",
    known_failure_modes=("expensive; prefer Sonnet unless task requires Opus",),
    source_url="https://docs.anthropic.com/en/docs/about-claude/models",
    read_at=_READ_AT,
)


_GEMINI_3_FLASH = CapabilityProfile(
    model_id="gemini-3-flash",
    family="gemini",
    supported_modes=frozenset({"chat", "summarization", "routing"}),
    optimal_ctx=32768,
    min_ctx=512,
    strengths=frozenset({"general_chat", "summarization", "routing", "low_latency"}),
    weaknesses=frozenset({"deep_reasoning"}),
    sampling_sweet_spot={"temperature": 0.7, "top_p": 0.95},
    prompt_template_fingerprint="gemini",
    thinking_mode="never",
    known_failure_modes=(),
    source_url="https://ai.google.dev/gemini-api/docs/models/gemini-3-flash",
    read_at=_READ_AT,
)


_GEMINI_3_PRO = CapabilityProfile(
    model_id="gemini-3-pro",
    family="gemini",
    supported_modes=frozenset({"chat", "tool_use", "reasoning"}),
    optimal_ctx=1000000,
    min_ctx=1024,
    strengths=frozenset({"reasoning", "code_gen", "long_horizon"}),
    weaknesses=frozenset(),
    sampling_sweet_spot={"temperature": 0.7, "top_p": 0.95},
    prompt_template_fingerprint="gemini",
    thinking_mode="never",
    known_failure_modes=(),
    source_url="https://ai.google.dev/gemini-api/docs/models/gemini-3-pro",
    read_at=_READ_AT,
)


# ── The registry ─────────────────────────────────────────────────────────────


DEFAULT_PROFILES: dict[str, CapabilityProfile] = {
    "Gemma-4-E2B-it-GGUF": _GEMMA_4_E2B,
    "Gemma-4-E4B-it-GGUF": _GEMMA_4_E4B,
    "Gemma-4-26B-A4B-it-GGUF": _GEMMA_4_26B,
    "Gemma-4-31B-it-GGUF": _GEMMA_4_31B,
    "phi4:latest": _PHI4,
    "qwen3-coder:30b": _QWEN3_CODER,
    "deepseek-r1:70b": _DEEPSEEK_R1,
    "deepseek-v3.2:cloud": _DEEPSEEK_V32,
    "gemini-3-flash-preview:cloud": _GEMINI_3_FLASH_PREVIEW,
    "claude-haiku-4-5": _CLAUDE_HAIKU,
    "claude-sonnet-4-6": _CLAUDE_SONNET,
    "claude-opus-4-7": _CLAUDE_OPUS,
    "gemini-3-flash": _GEMINI_3_FLASH,
    "gemini-3-pro": _GEMINI_3_PRO,
}


def get_profile(model_id: str) -> CapabilityProfile | None:
    """Return the default profile for `model_id`, or None if not registered."""
    return DEFAULT_PROFILES.get(model_id)
