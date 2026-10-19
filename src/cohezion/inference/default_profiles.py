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


_CLAUDE_HAIKU_55 = CapabilityProfile(
    model_id="claude-haiku-5-5",
    family="claude",
    supported_modes=frozenset({"chat", "summarization", "tool_use"}),
    optimal_ctx=200000,
    min_ctx=1024,
    strengths=frozenset({"general_chat", "summarization", "low_latency", "speed"}),
    weaknesses=frozenset({"deep_math"}),
    sampling_sweet_spot={"temperature": 0.7, "top_p": 0.95},
    prompt_template_fingerprint="claude",
    thinking_mode="never",
    known_failure_modes=(),
    source_url="https://code.claude.com/docs/en/headless",
    read_at=_READ_AT,
)


_CLAUDE_SONNET_55 = CapabilityProfile(
    model_id="claude-sonnet-5-5",
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
    source_url="https://code.claude.com/docs/en/headless",
    read_at=_READ_AT,
)


_CLAUDE_OPUS_55 = CapabilityProfile(
    model_id="claude-opus-5-5",
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
    source_url="https://code.claude.com/docs/en/headless",
    read_at=_READ_AT,
)


_CLAUDE_FABLE = CapabilityProfile(
    model_id="claude-fable-5",
    family="claude",
    supported_modes=frozenset({"chat", "tool_use", "reasoning", "long_horizon", "adversarial"}),
    optimal_ctx=200000,
    min_ctx=1024,
    strengths=frozenset(
        {"reasoning", "code_gen", "long_horizon", "architect", "adversarial_review"}
    ),
    weaknesses=frozenset(),
    sampling_sweet_spot={"temperature": 0.7, "top_p": 0.95},
    prompt_template_fingerprint="claude",
    thinking_mode="never",
    known_failure_modes=(),
    source_url="https://code.claude.com/docs/en/headless",
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


_NEMOTRON_3_SUPER = CapabilityProfile(
    model_id="nemotron-3-super:cloud",
    family="nemotron",
    supported_modes=frozenset({"chat", "tool_use", "summarization"}),
    optimal_ctx=262144,
    min_ctx=1024,
    strengths=frozenset({"sentinel", "low_cost", "monitoring", "high_throughput"}),
    weaknesses=frozenset({"deep_math"}),
    sampling_sweet_spot={"temperature": 0.1, "top_p": 0.9},
    prompt_template_fingerprint="chatml",
    thinking_mode="never",
    known_failure_modes=(),
    source_url="https://ollama.com/library/nemotron-3-super",
    read_at=_READ_AT,
)


_GPT_OSS_20B = CapabilityProfile(
    model_id="gpt-oss:20b-cloud",
    family="gpt-oss",
    supported_modes=frozenset({"chat", "code", "reasoning"}),
    optimal_ctx=131072,
    min_ctx=1024,
    strengths=frozenset({"reasoning", "code", "low_cost", "general_chat"}),
    weaknesses=frozenset({"long_horizon"}),
    sampling_sweet_spot={"temperature": 0.2, "top_p": 0.95},
    prompt_template_fingerprint="chatml",
    thinking_mode="optional_prefix",
    known_failure_modes=(),
    source_url="https://ollama.com/library/gpt-oss",
    read_at=_READ_AT,
)


_CLEF = CapabilityProfile(
    model_id="clef:cloud",
    family="audio",
    supported_modes=frozenset({"audio", "music", "analysis"}),
    optimal_ctx=131072,
    min_ctx=1024,
    strengths=frozenset({"audio_analysis", "music_understanding", "sonification"}),
    weaknesses=frozenset({"code_gen"}),
    sampling_sweet_spot={"temperature": 0.3, "top_p": 0.9},
    prompt_template_fingerprint="clef",
    thinking_mode="never",
    known_failure_modes=(),
    source_url="https://ollama.com/library/clef",
    read_at=_READ_AT,
)


_GEMMA_4_31B_CLOUD = CapabilityProfile(
    model_id="gemma4:31b-cloud",
    family="gemma4",
    supported_modes=frozenset({"chat", "tool_use", "reasoning", "multimodal"}),
    optimal_ctx=262144,
    min_ctx=1024,
    strengths=frozenset({"reasoning", "container_emulation", "embeddings", "kaggle_agent"}),
    weaknesses=frozenset(),
    sampling_sweet_spot={"temperature": 0.5, "top_p": 0.95},
    prompt_template_fingerprint="gemma",
    thinking_mode="always",
    known_failure_modes=(),
    source_url="https://ollama.com/library/gemma4",
    read_at=_READ_AT,
)


_GLM_53_FLASH = CapabilityProfile(
    model_id="glm-5.3-flash:cloud",
    family="glm",
    supported_modes=frozenset({"chat", "tool_use", "summarization", "low_latency"}),
    optimal_ctx=1048576,
    min_ctx=1024,
    strengths=frozenset({"fast_qa", "retrieval", "low_cost", "high_throughput"}),
    weaknesses=frozenset({"formal_proofs"}),
    sampling_sweet_spot={"temperature": 0.2, "top_p": 0.9},
    prompt_template_fingerprint="chatml",
    thinking_mode="never",
    known_failure_modes=(),
    source_url="https://ollama.com/library/glm-5.3-flash",
    read_at=_READ_AT,
)


_MINIMAX_M31_FLASH = CapabilityProfile(
    model_id="minimax-m3.1-flash:cloud",
    family="minimax",
    supported_modes=frozenset({"chat", "summarization", "tool_use"}),
    optimal_ctx=1048576,
    min_ctx=1024,
    strengths=frozenset({"conversational", "speed", "tool_use", "low_cost"}),
    weaknesses=frozenset({"deep_math"}),
    sampling_sweet_spot={"temperature": 0.3, "top_p": 0.95},
    prompt_template_fingerprint="chatml",
    thinking_mode="never",
    known_failure_modes=(),
    source_url="https://ollama.com/library/minimax-m3.1-flash",
    read_at=_READ_AT,
)


_GPT_OSS_120B = CapabilityProfile(
    model_id="gpt-oss:120b-cloud",
    family="gpt-oss",
    supported_modes=frozenset({"chat", "reasoning", "code", "paper_track"}),
    optimal_ctx=131072,
    min_ctx=1024,
    strengths=frozenset({"academic_papers", "verifiable_theorems", "open_weights", "reasoning"}),
    weaknesses=frozenset({"latency"}),
    sampling_sweet_spot={"temperature": 0.3, "top_p": 0.95},
    prompt_template_fingerprint="chatml",
    thinking_mode="optional_prefix",
    known_failure_modes=(),
    source_url="https://ollama.com/library/gpt-oss",
    read_at=_READ_AT,
)


_DEEPSEEK_V4_FLASH = CapabilityProfile(
    model_id="deepseek-v4-flash:cloud",
    family="deepseek",
    supported_modes=frozenset({"chat", "summarization", "fast_qa"}),
    optimal_ctx=131072,
    min_ctx=1024,
    strengths=frozenset({"fast_qa", "low_latency", "draft"}),
    weaknesses=frozenset({"deep_reasoning"}),
    sampling_sweet_spot={"temperature": 0.2, "top_p": 0.9},
    prompt_template_fingerprint="chatml",
    thinking_mode="never",
    known_failure_modes=(),
    source_url="https://ollama.com/library/deepseek-v4-flash",
    read_at=_READ_AT,
)


_MUSE_SPARK_OPEN = CapabilityProfile(
    model_id="muse-spark-open:cloud",
    family="creative",
    supported_modes=frozenset({"chat", "creative", "ideation"}),
    optimal_ctx=131072,
    min_ctx=1024,
    strengths=frozenset({"creative_synthesis", "brainstorming", "ideation"}),
    weaknesses=frozenset({"code_execution"}),
    sampling_sweet_spot={"temperature": 0.7, "top_p": 0.95},
    prompt_template_fingerprint="chatml",
    thinking_mode="never",
    known_failure_modes=(),
    source_url="https://ollama.com/library/muse-spark-open",
    read_at=_READ_AT,
)


_DEEPSEEK_V41_FLASH = CapabilityProfile(
    model_id="deepseek-v4.1-flash:cloud",
    family="deepseek",
    supported_modes=frozenset({"chat", "search", "reasoning", "triage"}),
    optimal_ctx=1048576,
    min_ctx=1024,
    strengths=frozenset({"deep_search", "invariant_triage", "low_cost", "reasoning"}),
    weaknesses=frozenset(),
    sampling_sweet_spot={"temperature": 0.2, "top_p": 0.95},
    prompt_template_fingerprint="chatml",
    thinking_mode="optional_prefix",
    known_failure_modes=(),
    source_url="https://ollama.com/library/deepseek-v4.1-flash",
    read_at=_READ_AT,
)


_MINIMAX_M27 = CapabilityProfile(
    model_id="minimax-m2.7:cloud",
    family="minimax",
    supported_modes=frozenset({"chat", "tool_use", "agent"}),
    optimal_ctx=262144,
    min_ctx=1024,
    strengths=frozenset({"tool_use", "fast_patch", "agentic_workflows"}),
    weaknesses=frozenset(),
    sampling_sweet_spot={"temperature": 0.2, "top_p": 0.9},
    prompt_template_fingerprint="chatml",
    thinking_mode="never",
    known_failure_modes=(),
    source_url="https://ollama.com/library/minimax-m2.7",
    read_at=_READ_AT,
)


_NEMOTRON_3_ULTRA = CapabilityProfile(
    model_id="nemotron-3-ultra:cloud",
    family="nemotron",
    supported_modes=frozenset({"chat", "reasoning", "verification"}),
    optimal_ctx=262144,
    min_ctx=1024,
    strengths=frozenset({"continuous_verification", "ci_cd", "hypothesis_testing", "reasoning"}),
    weaknesses=frozenset(),
    sampling_sweet_spot={"temperature": 0.1, "top_p": 0.9},
    prompt_template_fingerprint="chatml",
    thinking_mode="optional_prefix",
    known_failure_modes=(),
    source_url="https://ollama.com/library/nemotron-3-ultra",
    read_at=_READ_AT,
)


_MISTRAL_LARGE_4 = CapabilityProfile(
    model_id="mistral-large-4:cloud",
    family="mistral",
    supported_modes=frozenset({"chat", "multimodal", "tool_use", "reasoning"}),
    optimal_ctx=1048576,
    min_ctx=1024,
    strengths=frozenset({"multimodal", "enterprise", "reasoning", "tool_use"}),
    weaknesses=frozenset(),
    sampling_sweet_spot={"temperature": 0.3, "top_p": 0.95},
    prompt_template_fingerprint="mistral",
    thinking_mode="never",
    known_failure_modes=(),
    source_url="https://ollama.com/library/mistral-large-4",
    read_at=_READ_AT,
)


_GLM_52 = CapabilityProfile(
    model_id="glm-5.2:cloud",
    family="glm",
    supported_modes=frozenset({"chat", "science", "reasoning"}),
    optimal_ctx=1048576,
    min_ctx=1024,
    strengths=frozenset({"science_frontier", "physics", "mass_spectrometry", "reasoning"}),
    weaknesses=frozenset(),
    sampling_sweet_spot={"temperature": 0.2, "top_p": 0.9},
    prompt_template_fingerprint="chatml",
    thinking_mode="never",
    known_failure_modes=(),
    source_url="https://ollama.com/library/glm-5.2",
    read_at=_READ_AT,
)


_KIMI_K26 = CapabilityProfile(
    model_id="kimi-k2.6:cloud",
    family="kimi",
    supported_modes=frozenset({"chat", "reasoning", "tool_use"}),
    optimal_ctx=262144,
    min_ctx=1024,
    strengths=frozenset({"reasoning", "tool_use", "general_agent"}),
    weaknesses=frozenset(),
    sampling_sweet_spot={"temperature": 0.3, "top_p": 0.95},
    prompt_template_fingerprint="chatml",
    thinking_mode="never",
    known_failure_modes=(),
    source_url="https://ollama.com/library/kimi-k2.6",
    read_at=_READ_AT,
)


_MINIMAX_M3 = CapabilityProfile(
    model_id="minimax-m3:cloud",
    family="minimax",
    supported_modes=frozenset({"chat", "creative", "code"}),
    optimal_ctx=1048576,
    min_ctx=1024,
    strengths=frozenset({"creative_synthesis", "coding", "agentic_frontier"}),
    weaknesses=frozenset(),
    sampling_sweet_spot={"temperature": 0.7, "top_p": 0.98},
    prompt_template_fingerprint="chatml",
    thinking_mode="never",
    known_failure_modes=(),
    source_url="https://ollama.com/library/minimax-m3",
    read_at=_READ_AT,
)


_KIMI_K27_CODE = CapabilityProfile(
    model_id="kimi-k2.7-code:cloud",
    family="kimi",
    supported_modes=frozenset({"chat", "code", "tool_use"}),
    optimal_ctx=262144,
    min_ctx=1024,
    strengths=frozenset({"coding", "tool_use", "fast_patch", "ast_refactor"}),
    weaknesses=frozenset(),
    sampling_sweet_spot={"temperature": 0.05, "top_p": 0.85},
    prompt_template_fingerprint="chatml",
    thinking_mode="optional_prefix",
    known_failure_modes=(),
    source_url="https://ollama.com/library/kimi-k2.7-code",
    read_at=_READ_AT,
)


_DEEPSEEK_V4_PRO = CapabilityProfile(
    model_id="deepseek-v4-pro:cloud",
    family="deepseek",
    supported_modes=frozenset({"chat", "reasoning", "proof", "long_horizon"}),
    optimal_ctx=524288,
    min_ctx=1024,
    strengths=frozenset({"deep_reasoning", "formal_proofs", "grandmaster_logic", "invariant_proofs"}),
    weaknesses=frozenset(),
    sampling_sweet_spot={"temperature": 0.1, "top_p": 0.9},
    prompt_template_fingerprint="chatml",
    thinking_mode="always",
    known_failure_modes=(),
    source_url="https://ollama.com/library/deepseek-v4-pro",
    read_at=_READ_AT,
)


_GLM_53 = CapabilityProfile(
    model_id="glm-5.3:cloud",
    family="glm",
    supported_modes=frozenset({"chat", "code", "reasoning", "long_horizon"}),
    optimal_ctx=1048576,
    min_ctx=1024,
    strengths=frozenset({"coding", "long_horizon", "agentic_refactor", "flagship_coding"}),
    weaknesses=frozenset(),
    sampling_sweet_spot={"temperature": 0.1, "top_p": 0.9},
    prompt_template_fingerprint="chatml",
    thinking_mode="always",
    known_failure_modes=(),
    source_url="https://ollama.com/library/glm-5.3",
    read_at=_READ_AT,
)


_KIMI_K3 = CapabilityProfile(
    model_id="kimi-k3:cloud",
    family="kimi",
    supported_modes=frozenset({"chat", "multimodal", "reasoning", "game_affordance"}),
    optimal_ctx=1048576,
    min_ctx=1024,
    strengths=frozenset({"native_multimodal", "deep_reasoning", "arc3_game_affordance", "visual_dynamics"}),
    weaknesses=frozenset({"cost"}),
    sampling_sweet_spot={"temperature": 0.3, "top_p": 0.95},
    prompt_template_fingerprint="chatml",
    thinking_mode="always",
    known_failure_modes=(),
    source_url="https://ollama.com/library/kimi-k3",
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
    "claude-haiku-5-5": _CLAUDE_HAIKU_55,
    "claude-sonnet-5-5": _CLAUDE_SONNET_55,
    "claude-opus-5-5": _CLAUDE_OPUS_55,
    "claude-fable-5": _CLAUDE_FABLE,
    "gemini-3-flash": _GEMINI_3_FLASH,
    "gemini-3-pro": _GEMINI_3_PRO,
    # Ollama Cloud Roster (Pro Plan Active)
    "nemotron-3-super:cloud": _NEMOTRON_3_SUPER,
    "gpt-oss:20b-cloud": _GPT_OSS_20B,
    "clef:cloud": _CLEF,
    "gemma4:31b-cloud": _GEMMA_4_31B_CLOUD,
    "glm-5.3-flash:cloud": _GLM_53_FLASH,
    "minimax-m3.1-flash:cloud": _MINIMAX_M31_FLASH,
    "gpt-oss:120b-cloud": _GPT_OSS_120B,
    "deepseek-v4-flash:cloud": _DEEPSEEK_V4_FLASH,
    "muse-spark-open:cloud": _MUSE_SPARK_OPEN,
    "deepseek-v4.1-flash:cloud": _DEEPSEEK_V41_FLASH,
    "minimax-m2.7:cloud": _MINIMAX_M27,
    "nemotron-3-ultra:cloud": _NEMOTRON_3_ULTRA,
    "mistral-large-4:cloud": _MISTRAL_LARGE_4,
    "glm-5.2:cloud": _GLM_52,
    "kimi-k2.6:cloud": _KIMI_K26,
    "minimax-m3:cloud": _MINIMAX_M3,
    "kimi-k2.7-code:cloud": _KIMI_K27_CODE,
    "deepseek-v4-pro:cloud": _DEEPSEEK_V4_PRO,
    "glm-5.3:cloud": _GLM_53,
    "kimi-k3:cloud": _KIMI_K3,
}

_ALIASES: dict[str, str] = {
    "haiku": "claude-haiku-5-5",
    "sonnet": "claude-sonnet-5-5",
    "opus": "claude-opus-5-5",
    "fable": "claude-fable-5",
}


def get_profile(model_id: str) -> CapabilityProfile | None:
    """Return the default profile for `model_id`, or None if not registered."""
    resolved = _ALIASES.get(model_id, model_id)
    return DEFAULT_PROFILES.get(resolved)

