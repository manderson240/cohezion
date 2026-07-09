"""Adapter between legacy agent inference and the token-efficient local fleet.

The goal of this module is to make every agent call Lemonade-first by default:

1. ``call_local_first()`` is the async path used by ``BaseAgent._call_ollama()``.
   It routes through ``cohezion.inference.route()`` with ``budget_usd=0.0`` so
   only the local NPU/iGPU/CPU lanes are considered first.  If all local lanes
   fail or return poor-quality output, it escalates to a cloud/Ollama fallback.

2. ``run_task_sync()`` is the synchronous path used by
   ``CompoundExecutor.execute_task()`` when the caller does not supply an
   explicit ``execute_fn``.  Because the executor interface is synchronous, this
   helper uses a bounded synchronous ``httpx.Client`` call to the Lemonade
   :13305 OpenAI-compatible endpoint.

3. ``get_default_execute_fn()`` returns a closure matching the
   ``execute_fn(guidance) -> (output, metrics)`` contract expected by
   ``CompoundExecutor.execute_task()``.

All paths prefer Lemonade recipes (``lemonade_recipes.py``) for model selection,
sampling parameters, system prompts, and output budgets.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

from cohezion.inference import route
from cohezion.inference.lemonade_recipes import (
    _DEFAULT_TEMPERATURE,
    get_inference_params,
    get_recipe,
)
from cohezion.inference.registry import Lane, Task


logger = logging.getLogger(__name__)

_DEFAULT_LEMONADE_URL = "http://localhost:13305"
_MIN_QUALITY_LENGTH = 20


def _classify_task(prompt: str, explicit: str | None = None) -> Task:
    """Map a prompt (and optional hint) to a ``Task`` enum value."""
    if explicit:
        try:
            return Task(explicit)
        except ValueError:
            pass
    if prompt:
        lowered = prompt.lower()
        if "def " in prompt or "class " in prompt or "import " in prompt:
            return Task.CODE_GEN
        if any(w in lowered for w in ("reason", "why", "explain", "analyze", "compare")):
            return Task.REASONING
        if any(w in lowered for w in ("summarize", "summary", "tl;dr")):
            return Task.SUMMARIZATION
        if any(w in lowered for w in ("json", "schema", "extract", "parse")):
            return Task.STRUCTURED
    return Task.GENERAL


def _output_type_for_task(task: Task) -> str:
    """Select an output-budget key from the recipe."""
    mapping = {
        Task.CODE_GEN: "code",
        Task.REASONING: "math_reasoning",
        Task.SUMMARIZATION: "medium_generation",
        Task.STRUCTURED: "short_categorical",
    }
    return mapping.get(task, "medium_generation")


def _is_local_lane(lane: str) -> bool:
    """Return True if the lane is one of the on-premise Lemonade lanes."""
    return lane in {
        Lane.NPU.value,
        Lane.IGPU_ROCWMMA.value,
        Lane.IGPU_UNIFIED.value,
        Lane.CPU.value,
    }


async def call_local_first(
    prompt: str,
    *,
    model: str | None = None,
    system_prompt: str | None = None,
    temperature: float | None = None,
    max_tokens: int = 2048,
    task_type: str | None = None,
    allow_cloud_fallback: bool = True,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Async Lemonade-first inference for a single prompt.

    Returns a dict with at least:
      - ``text``: generated text (empty on failure)
      - ``model``: model_id that produced the text
      - ``lane``: lane name
      - ``error``: error string or None
      - ``latency_ms``: end-to-end latency
      - ``escalated_to_cloud``: bool
      - ``attempts``: list of model_ids tried
    """
    if not prompt or not prompt.strip():
        return {
            "text": "",
            "model": "",
            "lane": "",
            "error": "empty prompt rejected",
            "latency_ms": 0.0,
            "escalated_to_cloud": False,
            "attempts": [],
        }

    task = _classify_task(prompt, task_type)
    if model:
        recipe = get_recipe(model)
        if recipe:
            params = get_inference_params(
                model,
                output_type=_output_type_for_task(task),
                task_type=task.value,
            )
            recipe_max_tokens = max(params.get("max_tokens", max_tokens), max_tokens)
            recipe_system = params.get("system")
            recipe_temperature = params.get("temperature", _DEFAULT_TEMPERATURE)
        else:
            recipe_max_tokens = max_tokens
            recipe_system = None
            recipe_temperature = _DEFAULT_TEMPERATURE
    else:
        recipe = None
        recipe_max_tokens = max_tokens
        recipe_system = None
        recipe_temperature = _DEFAULT_TEMPERATURE

    prefer = model if (recipe is not None) else None

    final_max_tokens = max(recipe_max_tokens, max_tokens)

    # Recipe system/temperature cannot be injected through route() today; the
    # sync path (run_task_sync) consumes them directly.  Async integration is
    # deferred to a fleet.py route() enhancement pass.
    del system_prompt, recipe_system, temperature, recipe_temperature

    # --- Local-only attempt ---------------------------------------------------
    local_result = await route(
        prompt,
        task=task.value,
        prefer=prefer,
        budget_usd=0.0,  # force local lanes only
        timeout=timeout,
        max_tokens=final_max_tokens,
    )

    quality_ok = (
        local_result.error is None
        and len(local_result.text) >= _MIN_QUALITY_LENGTH
        and _is_local_lane(local_result.lane)
    )

    if quality_ok:
        return {
            "text": local_result.text,
            "model": local_result.model,
            "lane": local_result.lane,
            "error": None,
            "latency_ms": local_result.latency_ms,
            "escalated_to_cloud": False,
            "attempts": local_result.attempts,
        }

    if not allow_cloud_fallback:
        return {
            "text": local_result.text or "",
            "model": local_result.model,
            "lane": local_result.lane,
            "error": local_result.error or "local quality gate failed",
            "latency_ms": local_result.latency_ms,
            "escalated_to_cloud": False,
            "attempts": local_result.attempts,
        }

    # --- Escalation -----------------------------------------------------------
    cloud_prefer = prefer
    if not cloud_prefer:
        # Prefer a known cloud-capable model if available in the registry.
        from cohezion.inference.registry import get_registry

        registry = get_registry()
        for model_id in ("claude-sonnet-4-6", "claude-haiku-4-5", "gpt-4o-mini"):
            if model_id in registry.models:
                cloud_prefer = model_id
                break

    cloud_result = await route(
        prompt,
        task=task.value,
        prefer=cloud_prefer,
        timeout=timeout,
        max_tokens=final_max_tokens,
    )
    cloud_result.escalated_to_cloud = True

    return {
        "text": cloud_result.text,
        "model": cloud_result.model,
        "lane": cloud_result.lane,
        "error": cloud_result.error,
        "latency_ms": cloud_result.latency_ms,
        "escalated_to_cloud": cloud_result.escalated_to_cloud,
        "attempts": (local_result.attempts or []) + (cloud_result.attempts or []),
    }


def _build_messages(guidance: dict[str, Any]) -> list[dict[str, str]]:
    """Flatten a CompoundExecutor guidance dict into OpenAI-style messages."""
    messages: list[dict[str, str]] = []
    relevant_context = guidance.get("relevant_context", {}) if isinstance(guidance, dict) else {}

    system = "You are a helpful assistant."
    if isinstance(relevant_context, dict):
        system = relevant_context.get("system_prompt") or system
        background = relevant_context.get("background", "")
        if background:
            messages.append({"role": "system", "content": f"{system}\n\n{background}"})
        else:
            messages.append({"role": "system", "content": system})

        task_description = relevant_context.get("task_description", "")
        if task_description:
            messages.append({"role": "user", "content": task_description})
    else:
        # guidance is not a dict; treat the whole thing as a raw user prompt
        messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": str(guidance)})

    return messages


def run_task_sync(
    guidance: dict[str, Any],
    *,
    base_url: str = _DEFAULT_LEMONADE_URL,
    model: str | None = None,
    timeout: float = 30.0,
    max_tokens: int = 2048,
) -> tuple[str, dict[str, Any]]:
    """Synchronous Lemonade call for ``CompoundExecutor.execute_task()``.

    Because ``execute_task()`` is synchronous, this helper uses ``httpx.Client``
    rather than the async ``route()`` function.  It still consults
    ``lemonade_recipes`` for sampling parameters when ``model`` is provided.
    """
    messages = _build_messages(guidance)
    user_content = messages[-1].get("content", "") if messages else ""
    task = _classify_task(user_content)

    active_model = model
    system = "You are a helpful assistant."
    temperature = _DEFAULT_TEMPERATURE

    if active_model:
        recipe = get_recipe(active_model)
        if recipe:
            params = get_inference_params(
                active_model,
                output_type=_output_type_for_task(task),
                task_type=task.value,
            )
            system = params.get("system", system)
            temperature = params.get("temperature", temperature)
            recipe_max_tokens = params.get("max_tokens", max_tokens)
            max_tokens = max(max_tokens, recipe_max_tokens)
    else:
        # Default to a small, cheap local model when the caller did not specify one.
        active_model = "gemma-4-e2b-it-gguf"

    # Ensure system prompt is set from recipe or first message.
    if messages and messages[0]["role"] == "system":
        messages[0]["content"] = system
    else:
        messages.insert(0, {"role": "system", "content": system})

    payload: dict[str, Any] = {
        "model": active_model,
        "messages": messages,
        "max_tokens": max(max_tokens, 64),
        "temperature": temperature,
        "stream": False,
    }

    start = time.perf_counter()
    error: str | None = None
    response_text = ""
    lane = "local_lemonade"

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(f"{base_url}/v1/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        response_text = message.get("content", "")
    except httpx.TimeoutException:
        error = f"Lemonade request timed out after {timeout}s"
        logger.warning("run_task_sync: %s", error)
    except httpx.HTTPStatusError as exc:
        error = f"Lemonade HTTP {exc.response.status_code}"
        logger.warning("run_task_sync: %s", error)
    except Exception as exc:
        error = f"Lemonade sync call failed: {exc}"
        logger.warning("run_task_sync: %s", error)

    latency_ms = (time.perf_counter() - start) * 1000
    metrics = {
        "model": active_model,
        "lane": lane,
        "latency_ms": latency_ms,
        "error": error,
        "tokens_used": _approximate_tokens(payload) + _approximate_tokens(response_text),
    }

    return response_text, metrics


def _approximate_tokens(obj: Any) -> int:
    """Very rough token estimator for telemetry; not a real tokenizer."""
    if obj is None:
        return 0
    text = obj if isinstance(obj, str) else json.dumps(obj)
    # A crude heuristic: ~4 chars per token for English/JSON text.
    return max(1, len(text) // 4)


def get_default_execute_fn(
    *,
    base_url: str = _DEFAULT_LEMONADE_URL,
    model: str | None = None,
    timeout: float = 30.0,
    max_tokens: int = 2048,
) -> Any:
    """Return an ``execute_fn`` closure for ``CompoundExecutor.execute_task()``.

    The closure signature is ``(guidance) -> (output, metrics)`` and is
    intentionally synchronous so it can be dropped into the existing executor
    without changing the method contract.
    """

    def _execute_fn(guidance: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        return run_task_sync(
            guidance,
            base_url=base_url,
            model=model,
            timeout=timeout,
            max_tokens=max_tokens,
        )

    return _execute_fn
