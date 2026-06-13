"""Smart router — picks a (ModelEntry, InferenceParams) pair by capability.

Selection algorithm (per the plan, no vibes — explicit ranking):

1. Filter registry by `task_affinity ⊇ {task}`.
2. Drop candidates whose `profile` is None (RecipeGuard.assert_card_present
   would reject them anyway; fail fast here).
3. Drop candidates whose `profile.min_ctx > prompt_estimate_tokens * 1.2`
   (the model can't safely hold the prompt + output).
4. Drop candidates whose `supported_modes` is missing any of
   `required_modes` (e.g. tool_use is required → filter out chat-only).
5. Score survivors by:
   - +1 per `strength` that overlaps the task's "intent words"
   - -2 per `weakness` that overlaps the task's intent words
   - (intent words are derived from the Task enum's name)
6. Among survivors, prefer local lanes (NPU/iGPU/CPU) over cloud
   UNLESS a card weakness explicitly matches the task — in which case
   the cloud may be the better choice.
7. Return (entry, aligned_params) for the best survivor, or None.

Aligned params are built from the card's `sampling_sweet_spot` plus the
existing model_card_harness rules for thinking-mode / Qwen3 prefix.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cohezion.inference.model_card_harness import InferenceParams
from cohezion.inference.recipe_guard import RecipeGuard
from cohezion.inference.registry import (
    Lane,
    ModelEntry,
    Task,
    get_registry,
)


# Local lane values (vs cloud)
_LOCAL_LANES = {Lane.NPU, Lane.IGPU_ROCWMMA, Lane.IGPU_UNIFIED, Lane.CPU}
_CLOUD_LANES = {Lane.CLOUD_OLLAMA, Lane.CLOUD_CLAUDE, Lane.CLOUD_GEMINI}


# Map Task → list of "intent words" the router uses to score strengths/weaknesses.
# A weakness that matches an intent word counts as a hard signal to de-prioritize.
_TASK_INTENT_WORDS: dict[Task, frozenset[str]] = {
    Task.SENSING: frozenset({"sensing", "classification", "perception"}),
    Task.ROUTING: frozenset({"routing", "classification", "low_latency"}),
    Task.SUMMARIZATION: frozenset({"summarization", "low_latency", "general_chat"}),
    Task.STRUCTURED: frozenset({"structured", "json", "instruction_following"}),
    Task.GOVERNANCE: frozenset({"governance", "instruction_following"}),
    Task.REASONING: frozenset({"reasoning", "math", "architect", "long_horizon"}),
    Task.CODE_GEN: frozenset({"code", "code_completion", "code_gen", "fim", "bug_fixing"}),
    Task.MATH: frozenset({"math", "reasoning"}),
    Task.LONG_HORIZON: frozenset({"long_horizon", "long_context", "architect"}),
    Task.ARCHITECT: frozenset({"architect", "reasoning", "long_horizon"}),
    Task.GENERAL: frozenset({"general_chat", "low_latency"}),
}


def _task_intent_words(task: Task) -> frozenset[str]:
    return _TASK_INTENT_WORDS.get(task, frozenset({task.value}))


def _score(entry: ModelEntry, task: Task) -> float:
    """Higher score = better fit. Can be negative."""
    if entry.profile is None:
        return float("-inf")
    intent = _task_intent_words(task)
    strengths_hit = sum(1 for s in entry.profile.strengths if s in intent or any(i in s for i in intent))
    weaknesses_hit = sum(1 for w in entry.profile.weaknesses if w in intent or any(i in w for i in intent))
    return float(strengths_hit) - 2.0 * float(weaknesses_hit)


def _build_aligned_params(entry: ModelEntry, task: Task) -> InferenceParams:
    """Build an InferenceParams that carries the card's sweet-spot + the
    existing model_card_harness rules for thinking-mode and Qwen3 prefix.

    This is the spine of "default params are a bug": if a card lists a
    sweet-spot, it goes into extra_body; the thinking-mode flag is set
    per the model_card_harness rules; the Qwen3 /no_think prefix is set
    when applicable.
    """
    profile = entry.profile
    if profile is None:
        raise ValueError(
            f"route_by_capability._build_aligned_params: entry {entry.model_id!r} "
            f"has no profile; caller should have filtered this out"
        )

    # Base max_tokens by task
    max_tokens_by_task = {
        Task.CODE_GEN: 600,
        Task.REASONING: 800,
        Task.ARCHITECT: 800,
        Task.LONG_HORIZON: 1200,
        Task.MATH: 800,
        Task.SUMMARIZATION: 400,
        Task.SENSING: 100,
        Task.ROUTING: 100,
        Task.STRUCTURED: 400,
        Task.GOVERNANCE: 400,
        Task.GENERAL: 400,
    }
    max_tokens = max_tokens_by_task.get(task, 400)

    extra_body: dict[str, Any] = dict(profile.sampling_sweet_spot)

    prompt_prefix = ""

    # Qwen3 /no_think for non-reasoning tasks
    qwen3_prefixes = ("Qwen3", "DeepSeek-Qwen3", "qwen3", "qwen3-coder")
    is_qwen3 = any(entry.model_id.startswith(p) for p in qwen3_prefixes)
    if is_qwen3 and task not in {Task.REASONING, Task.MATH, Task.ARCHITECT}:
        prompt_prefix = "/no_think\n"

    # Thinking-mode models: bound reasoning via budget_tokens
    if profile.thinking_mode == "always":
        # Per the existing model_card_harness measurement: Gemma-4 needs
        # ~2260 thinking tokens. Use a conservative default.
        overhead = 2260 if "E4B" in entry.model_id else 500
        budget = min(400, max(50, max_tokens - 100))
        if task == Task.CODE_GEN:
            max_tokens = overhead + 400
            budget = min(400, overhead)
        extra_body["thinking"] = {"type": "enabled", "budget_tokens": budget}

    params = InferenceParams(
        model_id=entry.model_id,
        max_tokens=max_tokens,
        prompt_prefix=prompt_prefix,
        extra_body=extra_body,
    )
    # Self-check: the params we just built MUST pass RecipeGuard.assert_aligned
    RecipeGuard.assert_aligned(params)
    return params


@dataclass(frozen=True)
class _Scored:
    entry: ModelEntry
    score: float
    is_local: bool


def route_by_capability(
    *,
    task: Task,
    required_modes: frozenset[str] = frozenset(),
    prompt_estimate_tokens: int = 1024,
    registry: Any | None = None,
) -> tuple[ModelEntry, InferenceParams] | None:
    """Pick a (ModelEntry, InferenceParams) pair by capability.

    Returns None if no candidate clears the filters. The caller is
    responsible for falling back (e.g. to extend_claude on a different
    task) when None is returned.
    """
    reg = registry if registry is not None else get_registry()
    # A prompt needs 1.2× its token estimate of context room (estimate
    # plus 20% headroom for the model's own preamble + output). If a
    # candidate's optimal_ctx is less than that, it can't safely serve
    # the prompt. We use optimal_ctx (not min_ctx) here because the
    # min_ctx is the floor for which the model has been *trained* to
    # work — running above it is fine. optimal_ctx is the model-card
    # upper bound on safe inference.
    ctx_budget = int(prompt_estimate_tokens * 1.2)

    scored: list[_Scored] = []
    for entry in reg.models.values():
        # 1. task affinity
        if task not in entry.task_affinity:
            continue
        # 2. cardless → reject
        if entry.profile is None:
            continue
        # 3. ctx budget: if the prompt + headroom exceeds the model's
        #    card-stated optimal_ctx, drop it.
        if entry.profile.optimal_ctx < ctx_budget:
            continue
        # 4. required modes
        if not required_modes.issubset(entry.profile.supported_modes):
            continue
        # 5. score
        s = _score(entry, task)
        if s == float("-inf"):
            continue
        scored.append(_Scored(entry=entry, score=s, is_local=entry.lane in _LOCAL_LANES))

    if not scored:
        return None

    # 6. local preference: among the top score, prefer local over cloud
    # (a card weakness that matches intent already lowered the score).
    best_score = max(s.score for s in scored)
    top = [s for s in scored if s.score == best_score]
    top.sort(key=lambda s: (not s.is_local, s.entry.model_id))  # local first
    chosen = top[0].entry
    return chosen, _build_aligned_params(chosen, task)
