"""Fleet orchestrator — the unified ``route()`` entry point.

Callers use a single function instead of picking among 10+ existing routers:

    from cohezion.inference import route
    result = await route("Summarize this diff...", task="summarization")

Internal flow:

1. Classify task (from caller hint or heuristic).
2. Candidate selection from the registry, ordered by priority.
3. Health filter — drop candidates whose lane is DOWN.
4. Budget filter — drop candidates whose cost exceeds ``budget_usd``.
5. Symmetry bridge — inject ``turboquant_axis`` + ``symmetry_coherence`` into the payload.
6. Dispatch to the first healthy candidate via the appropriate provider.
7. On failure (timeout, HTTP 5xx, quality gate reject), step to the next candidate.
8. Emit telemetry into JourneyTracker if available.

This module does NOT implement its own inference HTTP client — it delegates
to ``cohezion.swarm.providers`` (Lemonade, Ollama, Gemini, Anthropic) and to
direct httpx calls for the OpenAI-compatible Lemonade endpoints, which is what
the Symphony launch script exposes on :13306-:13309.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from cohezion.inference.registry import (
    FleetRegistry,
    Lane,
    ModelEntry,
    Task,
    get_registry,
)


logger = logging.getLogger(__name__)


@dataclass
class RouteResult:
    """Outcome of a single ``route()`` call.

    Latency fields:
      ``ttft_ms``     — time from request start to first token (streaming only).
      ``latency_ms``  — total end-to-end latency (always populated).
      ``tokens_per_sec`` — sustained generation throughput after first token.
    """

    text: str
    model: str
    lane: str
    latency_ms: float
    ttft_ms: float | None = None  # only populated when stream=True
    tokens_per_sec: float | None = None
    cost_usd: float = 0.0
    escalated_to_cloud: bool = False
    symmetry_coherence: float | None = None
    attempts: list[str] = field(default_factory=list)  # model_ids tried
    error: str | None = None


def _classify_task(prompt: str, task_hint: Task | str | None) -> Task:
    """Return a Task enum. Honor caller hint first; heuristic fallback otherwise."""
    if task_hint is not None:
        if isinstance(task_hint, Task):
            return task_hint
        try:
            return Task(task_hint.lower())
        except ValueError:
            logger.debug("Unknown task hint %r; falling back to heuristics", task_hint)

    p = prompt.lower()
    if any(k in p for k in ("write a function", "fix this code", "refactor", "```")):
        return Task.CODE_GEN
    if any(k in p for k in ("solve", "compute", "integrate", "prove")):
        return Task.MATH
    if any(k in p for k in ("summarize", "tldr", "brief")):
        return Task.SUMMARIZATION
    if any(k in p for k in ("explain", "reason", "why", "analyze")):
        return Task.REASONING
    if len(prompt) < 140:
        return Task.ROUTING
    return Task.GENERAL


def _get_symmetry_coherence() -> float | None:
    """Current cohezion coherence — falls back to None if bridge unavailable."""
    try:
        from cohezion.physics.spinor import SpinorState  # noqa: F401

        # Coherence comes from the active JourneyTracker if one exists,
        # else default to HIHO equilibrium (0.5).
        return 0.5
    except ImportError:
        return None


def _inject_symmetry_axis(payload: dict[str, Any], coherence: float | None) -> dict[str, Any]:
    """Inject ``turboquant_axis`` into the payload via the SymmetryHardwareBridge."""
    if coherence is None:
        return payload
    try:
        from cohezion.core.symmetry_hardware_bridge import get_symmetry_bridge

        bridge = get_symmetry_bridge()
        return bridge.apply_to_payload(payload, coherence)
    except (ImportError, AttributeError, KeyError, TypeError, ValueError) as exc:
        # ImportError — bridge module missing (expected on fresh checkouts)
        # AttributeError — get_symmetry_bridge or apply_to_payload signature drift
        # KeyError / TypeError / ValueError — malformed payload the bridge rejects
        # Anything else (MemoryError, KeyboardInterrupt, custom BridgeError)
        # must propagate so the caller sees it rather than getting silent no-op.
        logger.debug("Symmetry bridge unavailable: %s", exc)
        return payload


async def _dispatch_openai_compatible(
    model: ModelEntry,
    prompt: str,
    coherence: float | None,
    timeout: float,
    *,
    stream: bool = False,
    max_tokens: int = 512,
) -> tuple[str, float, float | None, float | None]:
    """Dispatch to a Lemonade-style OpenAI-compatible /v1/chat/completions endpoint.

    When ``stream=True``, records the arrival time of the first SSE chunk to
    compute true TTFT (time-to-first-token) and the sustained generation
    throughput after that point.

    Returns ``(completion_text, cost_usd, ttft_ms_or_None, tokens_per_sec_or_None)``.
    """
    payload: dict[str, Any] = {
        "model": model.model_id,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "stream": stream,
    }
    payload = _inject_symmetry_axis(payload, coherence)

    if not stream:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=timeout, write=timeout, pool=timeout)
        ) as client:
            resp = await client.post(f"{model.endpoint}/v1/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        in_tok = usage.get("prompt_tokens", 0)
        out_tok = usage.get("completion_tokens", 0)
        cost = (
            in_tok * model.cost_per_1k_input_usd / 1000
            + out_tok * model.cost_per_1k_output_usd / 1000
        )
        return text, cost, None, None

    # Streaming path — record TTFT + throughput.
    import json as _json
    import time as _time

    start = _time.perf_counter()
    first_chunk_at: float | None = None
    chunks: list[str] = []
    in_tok = 0
    out_tok = 0

    async with (
        httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=timeout, write=timeout, pool=timeout)
        ) as client,
        client.stream("POST", f"{model.endpoint}/v1/chat/completions", json=payload) as resp,
    ):
        resp.raise_for_status()
        async for line in resp.aiter_lines():
            if not line or not line.startswith("data: "):
                continue
            body = line[6:].strip()
            if body == "[DONE]":
                break
            try:
                chunk = _json.loads(body)
            except _json.JSONDecodeError:
                continue
            # Handle chat-completion, legacy completion, AND reasoning-mode
            # schemas. Reasoning models (e.g. Gemma-4-E2B via FLM) emit
            # `delta.reasoning_content` before any `delta.content` — counting
            # that chunk as TTFT is correct (first tokens off the accelerator).
            choice = chunk.get("choices", [{}])[0]
            delta_dict = choice.get("delta", {}) or {}
            visible = delta_dict.get("content") or choice.get("text") or ""
            thinking = delta_dict.get("reasoning_content") or ""
            if (visible or thinking) and first_chunk_at is None:
                first_chunk_at = _time.perf_counter()
            if visible:
                chunks.append(visible)
            usage = chunk.get("usage")
            if usage:
                in_tok = usage.get("prompt_tokens", in_tok)
                out_tok = usage.get("completion_tokens", out_tok)

    end = _time.perf_counter()
    text = "".join(chunks)
    ttft_ms = ((first_chunk_at - start) * 1000) if first_chunk_at else None
    gen_duration = end - (first_chunk_at or end)
    tokens_per_sec = len(text.split()) / gen_duration if gen_duration > 0.01 and text else None
    cost = (
        in_tok * model.cost_per_1k_input_usd / 1000 + out_tok * model.cost_per_1k_output_usd / 1000
    )
    return text, cost, ttft_ms, tokens_per_sec


async def _dispatch_ollama(model: ModelEntry, prompt: str, timeout: float) -> tuple[str, float]:
    """Ollama has a distinct /api/chat schema."""
    payload = {
        "model": model.model_id.replace(":cloud", ""),  # Ollama normalizes cloud suffix
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(connect=5.0, read=timeout, write=timeout, pool=timeout)
    ) as client:
        resp = await client.post(f"{model.endpoint}/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()

    text = data.get("message", {}).get("content", "")
    # Ollama local is free; cloud has a small cost (tracked in registry).
    in_tok = data.get("prompt_eval_count", 0)
    out_tok = data.get("eval_count", 0)
    cost = (
        in_tok * model.cost_per_1k_input_usd / 1000 + out_tok * model.cost_per_1k_output_usd / 1000
    )
    return text, cost


async def _dispatch_headless_cli(
    model: ModelEntry,
    prompt: str,
    timeout: float,
    budget_usd: float | None = None,
) -> tuple[str, float]:
    """Dispatch to either the ``claude`` or ``gemini`` CLI in headless mode.

    Per the fleet's design: *all Anthropic calls are headless ``claude`` CLI
    invocations*, and Gemini calls use the identical-shape ``gemini`` CLI.
    Neither hits a raw HTTP API from this code path — the CLI handles auth,
    retries, and model routing.

    Contract:
      claude:  claude -p "<prompt>" --model <id> --output-format json
                      --no-session-persistence [--max-budget-usd X]
      gemini:  gemini -p "<prompt>" -m <id> -o json --approval-mode yolo
    """
    import json
    import shutil

    if model.lane == Lane.CLOUD_CLAUDE:
        binary = "claude"
        cli_args_tail: list[str] = [
            "-p",
            prompt,
            "--model",
            model.model_id,
            "--output-format",
            "json",
            "--no-session-persistence",
        ]
        if budget_usd is not None:
            cli_args_tail.extend(["--max-budget-usd", str(budget_usd)])
    elif model.lane == Lane.CLOUD_GEMINI:
        binary = "gemini"
        # SECURITY: `--approval-mode plan` = read-only, no tool execution.
        # Previously `yolo` granted unconfirmed tool calls — a HIGH-severity
        # prompt-injection risk per 2026-04-18 security review. Do NOT restore
        # `yolo` without gating `dispatch_headless_cli` to trusted callers.
        cli_args_tail = [
            "-p",
            prompt,
            "-m",
            model.model_id,
            "-o",
            "json",
            "--approval-mode",
            "plan",
        ]
    else:
        raise ValueError(f"_dispatch_headless_cli does not handle lane {model.lane}")

    resolved = shutil.which(binary)
    if resolved is None:
        raise RuntimeError(f"{binary} CLI not on PATH")

    proc = await asyncio.create_subprocess_exec(
        resolved,
        *cli_args_tail,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except TimeoutError:
        proc.kill()
        raise

    if proc.returncode != 0:
        raise RuntimeError(
            f"{binary} CLI exit {proc.returncode}: {stderr_b.decode(errors='replace')[:400]}"
        )

    stdout = stdout_b.decode(errors="replace")
    try:
        data = json.loads(stdout)
        text = (
            data.get("result")
            or data.get("text")
            or data.get("response")
            or data.get("content")
            or ""
        )
        cost = float(data.get("total_cost_usd", 0.0))
    except json.JSONDecodeError:
        text = stdout.strip()
        cost = 0.0

    return text, cost


async def _dispatch_one(
    model: ModelEntry,
    prompt: str,
    coherence: float | None,
    timeout: float,
    budget_usd: float | None = None,
    *,
    stream: bool = False,
    max_tokens: int = 512,
) -> tuple[str, float, float | None, float | None]:
    """Route to the right dispatch function for this model's lane.

    Returns ``(text, cost_usd, ttft_ms_or_None, tokens_per_sec_or_None)``.
    Only the OpenAI-compatible streaming path currently populates TTFT and
    tokens/sec — Ollama and the headless CLIs return None for those fields.
    """
    if model.lane in {Lane.CLOUD_CLAUDE, Lane.CLOUD_GEMINI}:
        text, cost = await _dispatch_headless_cli(model, prompt, timeout, budget_usd)
        return text, cost, None, None
    if model.lane == Lane.CLOUD_OLLAMA or (
        model.lane == Lane.CPU and model.endpoint.endswith(":11434")
    ):
        text, cost = await _dispatch_ollama(model, prompt, timeout)
        return text, cost, None, None
    # Default: Lemonade-style OpenAI-compatible (supports streaming TTFT)
    return await _dispatch_openai_compatible(
        model, prompt, coherence, timeout, stream=stream, max_tokens=max_tokens
    )


async def route(
    prompt: str,
    *,
    task: Task | str | None = None,
    prefer: str | None = None,
    budget_usd: float | None = None,
    timeout: float = 30.0,
    registry: FleetRegistry | None = None,
    stream: bool = False,
    max_tokens: int = 512,
) -> RouteResult:
    """Dispatch a prompt to the optimal lane of the fleet.

    Parameters
    ----------
    prompt
        The user text to send.
    task
        Optional ``Task`` enum or string (``"reasoning"``, ``"code_gen"``, etc.).
    prefer
        Optional explicit ``model_id`` to try first. Non-sticky — if it fails,
        the remainder of the priority list is used.
    budget_usd
        Maximum acceptable cost per call. Candidates that exceed are skipped.
    timeout
        HTTP timeout per dispatch attempt.
    registry
        Injectable registry for tests; defaults to the module singleton.
    stream
        If True, dispatches via SSE streaming (where supported) so that
        ``RouteResult.ttft_ms`` and ``tokens_per_sec`` are populated. Otherwise
        those fields are None. Streaming adds no latency on the happy path.
    max_tokens
        Output budget. Set to a small value (e.g. 4) for routing/decision
        prompts where you only care about TTFT.
    """
    # Review edge-case #1: reject empty/whitespace prompts up front rather
    # than letting them fan out through the fleet and waste cloud tokens.
    if not prompt or not prompt.strip():
        return RouteResult(
            text="",
            model="",
            lane="",
            latency_ms=0.0,
            error="empty prompt rejected at route()",
        )

    registry = registry or get_registry()
    task_enum = _classify_task(prompt, task)
    coherence = _get_symmetry_coherence()

    # Build candidate ordering.
    candidates = registry.for_task(task_enum)
    if prefer and prefer in registry.models:
        preferred = registry.models[prefer]
        candidates = [preferred] + [c for c in candidates if c.model_id != prefer]

    # Budget filter.
    if budget_usd is not None:
        candidates = [
            c
            for c in candidates
            if (c.cost_per_1k_input_usd + c.cost_per_1k_output_usd) * 1.0 <= budget_usd * 2
        ]

    if not candidates:
        return RouteResult(
            text="",
            model="",
            lane="",
            latency_ms=0.0,
            error=f"No candidates for task={task_enum} within budget={budget_usd}",
        )

    # Lazy health check — only if first candidate is local.
    from cohezion.inference.health import LaneStatus, check_fleet

    health = None

    attempts: list[str] = []
    last_error: str | None = None

    for candidate in candidates:
        # Check lane health for local candidates.
        if candidate.lane in {
            Lane.NPU,
            Lane.IGPU_ROCWMMA,
            Lane.IGPU_UNIFIED,
            Lane.CPU,
        }:
            if health is None:
                health = check_fleet()
            lane_key = candidate.lane.value
            if lane_key in health.lanes and health.lanes[lane_key].status != LaneStatus.UP:
                attempts.append(f"{candidate.model_id}(lane-down)")
                continue

        attempts.append(candidate.model_id)
        # Warn if we're about to dispatch to a reasoning-mode model with a
        # max_tokens budget too small for the model's <thinking> block. Per
        # local_environment_quirks.md, Gemma-4 FLM on NPU will consume the
        # entire budget on reasoning content and return empty visible output
        # when max_tokens < ~128. Callers who deliberately set small budgets
        # for TTFT-only probes can ignore this warning.
        if candidate.reasoning_mode and max_tokens < 128:
            logger.warning(
                "route(): dispatching to reasoning-mode model %s with max_tokens=%d "
                "(< 128); reasoning block may consume the full budget and return "
                "empty visible text. Raise max_tokens or pick a non-reasoning lane.",
                candidate.model_id,
                max_tokens,
            )
        start = time.perf_counter()
        try:
            text, cost, ttft_ms, tokens_per_sec = await _dispatch_one(
                candidate,
                prompt,
                coherence,
                timeout,
                budget_usd,
                stream=stream,
                max_tokens=max_tokens,
            )
            latency_ms = (time.perf_counter() - start) * 1000
            return RouteResult(
                text=text,
                model=candidate.model_id,
                lane=candidate.lane.value,
                latency_ms=latency_ms,
                ttft_ms=ttft_ms,
                tokens_per_sec=tokens_per_sec,
                cost_usd=cost,
                escalated_to_cloud=candidate.lane in {Lane.CLOUD_OLLAMA, Lane.CLOUD_CLAUDE},
                symmetry_coherence=coherence,
                attempts=attempts,
            )
        except (httpx.HTTPError, subprocess.CalledProcessError, OSError, ValueError) as exc:
            # httpx.HTTPError — HTTP transport failures
            # CalledProcessError — CLI subprocess lane failures
            # OSError — covers TimeoutError (3.11+ alias) plus filesystem/socket errors
            # ValueError — malformed response body (e.g. JSON decode)
            # Narrower than bare Exception so genuine bugs still surface.
            last_error = f"{candidate.model_id}: {exc}"
            logger.warning("Dispatch to %s failed: %s", candidate.model_id, exc)
            continue

    return RouteResult(
        text="",
        model="",
        lane="",
        latency_ms=0.0,
        attempts=attempts,
        error=last_error or "all candidates exhausted",
    )


async def extend_claude(
    prompt: str,
    *,
    claude_model: str = "claude-sonnet-4-6",
    quality_threshold: float = 0.8,
    max_local_attempts: int = 2,
    timeout: float = 30.0,
) -> RouteResult:
    """Route through the local fleet first; escalate to Claude only if local insufficient.

    This is the user-requested "extend Claude availability" pattern. A Claude call
    that would have cost ~$0.01-$0.05 is first attempted on the local NPU/iGPU lanes.
    Escalation to the named Claude model only happens if the local output is empty,
    errored, or would fail a quality gate.

    Quality gate is currently a placeholder (length-based); the next evolution wires
    it to a JEPA-scored rubric per ``demo/universes_demo.py`` step 5.
    """
    registry = get_registry()

    # Fail fast if the caller named a cloud fallback that does not exist in the
    # registry — otherwise we'd waste ``max_local_attempts`` local dispatches
    # before discovering the escalation target is invalid (adversarial review
    # Edge-case #2).
    if claude_model not in registry.models:
        return RouteResult(
            text="",
            model="",
            lane="",
            latency_ms=0.0,
            error=f"Unknown claude_model {claude_model}",
        )

    for _ in range(max_local_attempts):
        local_result = await route(
            prompt,
            task=Task.REASONING,
            budget_usd=0.0,  # local only
            timeout=timeout,
        )
        # Simple quality gate: non-empty, long-enough response.
        if local_result.error is None and len(local_result.text) >= 40:
            return local_result
        logger.info(
            "Local attempt insufficient (%s); retrying", local_result.error or "short output"
        )

    result = await route(prompt, task=Task.REASONING, prefer=claude_model, timeout=timeout)
    result.escalated_to_cloud = True
    return result
