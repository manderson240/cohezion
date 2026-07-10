"""Specialist model registry — task-aware routing for the local fleet.

Maps semantic task types to the best-fit model on the Strix Halo fleet,
with finely crafted recipe options per specialist.

Architecture (OI-MAS / Lin et al. 2605.30621 — harness-tier routing):
  1. Classifier (Qwen3-0.6B, 0.38GB CPU) → task_type, zero cost
  2. Registry lookup → specialist model_id + crafted recipe
  3. SmartOrchestrator dispatches via lemonade_chat MCP

Harness-tier routing findings (arXiv 2605.30621):
  - Harness-UPDATING is tier-flat → route SkillRefiner to cheap tier (Bonsai)
  - Mid-tier (Qwen3.6-35B-NoThinking) gains MOST from harness context → use for synthesis
  - NPU-1B must be harness-free (routing/classify only, no complex skills)
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SpecialistSpec:
    """A specialist model with its crafted recipe."""

    model_id: str
    task_type: str
    backend: str = "vulkan"
    ctx_size: int = 16384
    max_tokens: int = 4096
    temperature: float = 0.7
    llamacpp_args: str = ""
    description: str = ""
    labels: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Finely crafted recipes for each specialist
# These encode OPTIMAL inference parameters per task — not generic defaults.
# ---------------------------------------------------------------------------

SPECIALISTS: dict[str, SpecialistSpec] = {
    # ── Ultra-cheap router ─────────────────────────────────────────────────
    # 0.38GB, CPU-bound, deterministic classification.
    # NEVER give this model tool calls or complex skills (Lin et al. finding).
    "classify": SpecialistSpec(
        model_id="Qwen3-0.6B-GGUF",
        task_type="classify",
        backend="cpu",
        ctx_size=2048,
        max_tokens=64,
        temperature=0.0,  # fully deterministic for routing
        description="Zero-cost task classifier. Outputs one of: code, reason, vision, long, fast, synthesis, agent, embed.",
        labels=["router", "cheap"],
    ),
    # ── Code generation ────────────────────────────────────────────────────
    # Specialized coder with thinking mode enabled; low temperature for determinism.
    # Qwen3-Coder-30B trained on 7.5T code tokens (2026-06 hot model).
    "code": SpecialistSpec(
        model_id="Qwen3-Coder-30B-A3B-Instruct-GGUF",
        task_type="code",
        backend="vulkan",
        ctx_size=32768,  # 65K available but 32K balances VRAM vs need
        max_tokens=8192,  # code can be long
        temperature=0.15,  # low temp: deterministic code
        llamacpp_args="--top-k 40 --top-p 0.95 --min-p 0.01",
        description="Specialized code generation. Best for: write/debug/review code, algorithms, architecture.",
        labels=["coding", "tool-calling"],
    ),
    # ── Reasoning / math ──────────────────────────────────────────────────
    # DeepSeek-R1 variant — tool-calling + reasoning labels. Extended budget.
    "reasoning": SpecialistSpec(
        model_id="DeepSeek-Qwen3-8B-GGUF",
        task_type="reasoning",
        backend="vulkan",
        ctx_size=16384,
        max_tokens=6144,  # reasoning chains are long
        temperature=0.6,
        llamacpp_args="--top-k 20 --top-p 0.95",
        description="Chain-of-thought reasoning, math, logic proofs, step-by-step analysis.",
        labels=["reasoning", "tool-calling"],
    ),
    # ── Vision / multimodal ───────────────────────────────────────────────
    # Gemma-4-E4B: vision + tool-calling, fast on vulkan.
    "vision": SpecialistSpec(
        model_id="Gemma-4-E4B-it-GGUF",
        task_type="vision",
        backend="vulkan",
        ctx_size=8192,
        max_tokens=2048,
        temperature=0.7,
        description="Image analysis, chart reading, multimodal understanding.",
        labels=["vision", "tool-calling"],
    ),
    # ── Long-context tasks ────────────────────────────────────────────────
    # Llama-4-Scout: 10M context window — unique in the fleet for very long docs.
    "long_context": SpecialistSpec(
        model_id="Llama-4-Scout-17B-16E-Instruct-GGUF-Q4_K_M",
        task_type="long_context",
        backend="vulkan",
        ctx_size=131072,  # 128K — practical ceiling for RAM
        max_tokens=4096,
        temperature=0.7,
        description="Very long documents, codebases, extended context synthesis (up to 128K tokens).",
        labels=["vision", "tool-calling", "long-context"],
    ),
    # ── Synthesis / main interactive ──────────────────────────────────────
    # Qwen3.6-35B-A3B-NoThinking: already has a finely crafted recipe in Lemonade
    # (presence-penalty=2.0, enable_thinking=false, batch=4096). The model that gains
    # MOST from harness context per Lin et al. — use for skill-rich agentic tasks.
    "synthesis": SpecialistSpec(
        model_id="Qwen3.6-35B-A3B-NoThinking",
        task_type="synthesis",
        backend="vulkan",
        ctx_size=16384,
        max_tokens=6144,
        temperature=1.0,  # matches the crafted NoThinking recipe
        llamacpp_args="--top-p 1.0 --top-k 40 --min-p 0.00 --presence-penalty 2.0 --repeat-penalty 1.0 -b 4096 -ub 1024",
        description="General synthesis, writing, agentic orchestration, harness-aware tasks.",
        labels=["synthesis", "tool-calling", "hot"],
    ),
    # ── MTP speculative: fast large model ────────────────────────────────
    # Qwen3.6-35B-A3B-MTP-GGUF: internal draft heads → ~1.7-1.9x speedup.
    # Note: requires llama-server with --spec-type draft-mtp; use via direct recipe.
    "fast_large": SpecialistSpec(
        model_id="Qwen3.6-35B-A3B-MTP-GGUF",
        task_type="fast_large",
        backend="vulkan",
        ctx_size=16384,
        max_tokens=4096,
        temperature=0.7,
        description="Large model with MTP speculative decoding (~1.7-1.9x faster). Best for high-quality fast output.",
        labels=["mtp", "tool-calling"],
    ),
    # ── Agentic coordinator ───────────────────────────────────────────────
    # Bonsai-8B: tool-calling, lightweight, designed to CALL other models as tools.
    "agent": SpecialistSpec(
        model_id="Bonsai-8B-gguf",
        task_type="agent",
        backend="cpu",
        ctx_size=16384,
        max_tokens=2048,
        temperature=0.7,
        description="Thin coordinator that dispatches to specialist models via tool calls.",
        labels=["tool-calling", "coordinator"],
    ),
    # ── Fast answers ──────────────────────────────────────────────────────
    # Bonsai-4B: smaller + faster for simple lookup/QA tasks.
    "fast": SpecialistSpec(
        model_id="Bonsai-4B-gguf",
        task_type="fast",
        backend="cpu",
        ctx_size=8192,
        max_tokens=512,
        temperature=0.7,
        description="Quick lookup, simple Q&A, yes/no, short structured output.",
        labels=["tool-calling"],
    ),
    # ── Deep thinking + code ──────────────────────────────────────────────
    # Qwen3.6-35B-A3B-ThinkingCoder: thinking mode enabled for hard problems.
    "thinking_code": SpecialistSpec(
        model_id="Qwen3.6-35B-A3B-ThinkingCoder",
        task_type="thinking_code",
        backend="vulkan",
        ctx_size=16384,
        max_tokens=8192,
        temperature=0.6,
        llamacpp_args="--top-p 0.95 --top-k 20",
        description="Hard algorithmic problems requiring deep reasoning AND code output.",
        labels=["coding", "tool-calling"],
    ),
    # ── Embeddings ────────────────────────────────────────────────────────
    "embed": SpecialistSpec(
        model_id="nomic-embed-text-v2-moe-GGUF",
        task_type="embed",
        backend="cpu",
        ctx_size=512,
        max_tokens=1,
        temperature=0.0,
        description="768D semantic embeddings for similarity search and caching.",
        labels=["embeddings"],
    ),
    # ── NPU reasoning (FLM, fast draft) ──────────────────────────────────
    "npu_reasoning": SpecialistSpec(
        model_id="deepseek-r1-0528-8b-FLM",
        task_type="npu_reasoning",
        backend="flm",
        ctx_size=8192,
        max_tokens=512,  # fast draft, escalate if insufficient
        temperature=0.6,
        description="NPU-accelerated reasoning draft (10.6 TPS on XDNA2). Quick first pass.",
        labels=["reasoning", "npu"],
    ),
}

# Default fallback when task type is unknown or unclassified
DEFAULT_SPECIALIST = "synthesis"


def get_specialist(task_type: str) -> SpecialistSpec:
    """Return the specialist spec for a given task type."""
    return SPECIALISTS.get(task_type, SPECIALISTS[DEFAULT_SPECIALIST])


def list_task_types() -> list[str]:
    """Return all registered task types."""
    return list(SPECIALISTS.keys())


# Classification prompt used by Qwen3-0.6B to classify incoming tasks.
# Outputs EXACTLY one of the task type tokens — no prose, no explanation.
CLASSIFICATION_PROMPT = """\
Classify this task into exactly ONE category. Reply with only the category name.

Categories:
  code          — write, debug, review, or analyze code
  reasoning     — math, logic, proofs, step-by-step analysis
  vision        — analyze images, charts, visual content
  long_context  — process very long documents or codebases (>10K tokens)
  synthesis     — general writing, summarize, explain, agentic orchestration
  fast          — quick lookup, yes/no, short structured answer
  agent         — multi-step plan requiring tool use
  thinking_code — hard algorithmic problem needing deep reasoning + code
  embed         — compute semantic embeddings
  npu_reasoning — fast draft reasoning (will be refined)

Task: {prompt}

Category:"""
