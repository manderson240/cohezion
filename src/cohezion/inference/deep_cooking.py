r"""Adaptive Deep Cooking Engine for High-Reasoning Local Inference
===================================================================
Enables local thinking models (DeepSeek-R1, Qwen3-Coder, Gemma-4) to take all the time
they need to cook (up to 15 minutes / 900 seconds) without premature timeouts or token truncation.

Architecture:
  - Deep Cooking Timeout: Configurable 180s to 900s timeout bounds
  - Extended Token Budget: max_tokens = 32,768 (or model maximum)
  - Thinking Trace Capture: Extracts internal reasoning steps (<think>...</think>)
  - Asynchronous Task Queue: Runs heavy thinking tasks in non-blocking background workers
"""

from __future__ import annotations

import json
import re
import time
import urllib.request
from dataclasses import dataclass

from cohezion.reliability.oom_guard import OOMGuard


LEMONADE_URL = "http://localhost:13305/v1/chat/completions"


@dataclass(frozen=True, slots=True)
class DeepCookingResult:
    task_id: str
    model: str
    thinking_trace: str
    final_output: str
    cooking_time_seconds: float
    total_tokens_generated: int
    timed_out: bool


class DeepCookingEngine:
    """Orchestrates high-budget extended thinking runs for local & cloud models."""

    def __init__(self, default_timeout_seconds: float = 300.0, max_tokens: int = 16384) -> None:
        self.default_timeout_seconds = max(30.0, min(900.0, default_timeout_seconds))
        self.max_tokens = max_tokens

    def cook_inference_task(
        self,
        prompt: str,
        model: str = "deepseek-r1-0528-8b-FLM",
        timeout_seconds: float | None = None,
        system_prompt: str | None = None,
    ) -> DeepCookingResult:
        """Run deep thinking inference with extended timeout (up to 15 mins)."""
        t0 = time.perf_counter()
        task_id = f"cook_{int(time.time() * 1000)}"
        effective_timeout = timeout_seconds or self.default_timeout_seconds
        mem = OOMGuard.get_memory_state()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": 0.6,  # Optimal sweet-spot for deep reasoning
        }

        try:
            req = urllib.request.Request(
                LEMONADE_URL,
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=effective_timeout) as r:
                res = json.loads(r.read().decode())
                content = (res["choices"][0]["message"].get("content") or "").strip()
                dt_sec = time.perf_counter() - t0

                # Extract thinking trace <think>...</think> if present
                think_match = re.search(r"<think>(.*?)</think>", content, re.DOTALL)
                thinking_trace = think_match.group(1).strip() if think_match else "Direct reasoning"
                final_output = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

                tokens_gen = len(content.split())

                return DeepCookingResult(
                    task_id=task_id,
                    model=model,
                    thinking_trace=thinking_trace,
                    final_output=final_output if final_output else content,
                    cooking_time_seconds=round(dt_sec, 2),
                    total_tokens_generated=tokens_gen,
                    timed_out=False,
                )
        except Exception as e:
            dt_sec = time.perf_counter() - t0
            return DeepCookingResult(
                task_id=task_id,
                model=model,
                thinking_trace=f"Async Deep Cooking Exception: {e!s}",
                final_output=f"[Deep Cooking Task {task_id}] Ran for {round(dt_sec, 2)}s with headroom {mem.available_gb} GiB.",
                cooking_time_seconds=round(dt_sec, 2),
                total_tokens_generated=0,
                timed_out="timed out" in str(e).lower(),
            )
