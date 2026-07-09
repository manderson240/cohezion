"""Smart task-aware orchestrator for Cohezion compound loop.

Replaces fixed-tier escalation with:
  1. classify(prompt) → task_type   (Qwen3-0.6B, CPU, ~50ms, $0)
  2. get_specialist(task_type)      → model_id + crafted recipe
  3. dispatch(model_id, prompt)     → result via lemonade_chat MCP

Models-as-Tools pattern:
  The coordinator model (Bonsai-8B) is given tool definitions for each
  specialist. It calls them by name; the handler routes to lemonade_chat.
  This gives us model-council orchestration without hard-coded tiers.

Usage:
    from cohezion.inference.smart_orchestrator import SmartOrchestrator
    orch = SmartOrchestrator()
    result = await orch.run("Implement a B-tree insertion in Python")
    # → routes to Qwen3-Coder-30B automatically
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

import httpx

from cohezion.inference.specialist_registry import (  # type: ignore[import-untyped]
    CLASSIFICATION_PROMPT,
    DEFAULT_SPECIALIST,
    SPECIALISTS,
    SpecialistSpec,
    get_specialist,
)


logger = logging.getLogger(__name__)

_OMNI_URL = "http://localhost:13305"


@dataclass
class SmartResult:
    text: str
    task_type: str
    model_id: str
    latency_ms: float
    cost_usd: float = 0.0
    error: str | None = None


class SmartOrchestrator:
    """Task-aware orchestrator: classify → route → dispatch.

    Flow:
        classify (Qwen3-0.6B, sync, ~50ms)
            → specialist lookup
                → lemonade_chat dispatch (async)
    """

    def __init__(self, base_url: str = _OMNI_URL, timeout_s: float = 600.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout_s

    # ------------------------------------------------------------------
    # Internal: raw OpenAI-compat chat/completions call to lemonade
    # ------------------------------------------------------------------

    async def _chat(
        self,
        model_id: str,
        prompt: str,
        *,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        tools: list[dict] | None = None,
    ) -> dict:
        payload: dict = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = tools
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()

    # ------------------------------------------------------------------
    # Classification (synchronous, uses tiny Qwen3-0.6B)
    # ------------------------------------------------------------------

    async def classify(self, prompt: str) -> str:
        """Return a task_type string using the 0.38GB CPU classifier."""
        classifier = SPECIALISTS["classify"]
        filled = CLASSIFICATION_PROMPT.format(prompt=prompt[:800])
        try:
            raw = await self._chat(
                classifier.model_id,
                filled,
                max_tokens=classifier.max_tokens,
                temperature=classifier.temperature,
            )
            choice = raw["choices"][0]["message"].get("content", "").strip().lower()
            # Accept first word only (classifier sometimes adds a period)
            first_word = choice.split()[0].rstrip(".,;") if choice else ""
            if first_word in SPECIALISTS:
                return first_word
        except Exception as exc:
            logger.debug("Classification failed (%s), using default", exc)
        return DEFAULT_SPECIALIST

    # ------------------------------------------------------------------
    # Dispatch to specialist
    # ------------------------------------------------------------------

    async def dispatch(self, spec: SpecialistSpec, prompt: str) -> SmartResult:
        t0 = time.perf_counter()
        try:
            raw = await self._chat(
                spec.model_id,
                prompt,
                max_tokens=spec.max_tokens,
                temperature=spec.temperature,
            )
            text = raw["choices"][0]["message"].get("content", "") or ""
            return SmartResult(
                text=text,
                task_type=spec.task_type,
                model_id=spec.model_id,
                latency_ms=(time.perf_counter() - t0) * 1000,
            )
        except Exception as exc:
            return SmartResult(
                text="",
                task_type=spec.task_type,
                model_id=spec.model_id,
                latency_ms=(time.perf_counter() - t0) * 1000,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def run(self, prompt: str, *, task_type: str | None = None) -> SmartResult:
        """Classify prompt and dispatch to the right specialist.

        Pass ``task_type`` to skip classification (saves ~50ms + classifier cost).
        """
        if task_type is None:
            task_type = await self.classify(prompt)
            logger.debug("Classified as: %s", task_type)

        spec = get_specialist(task_type)
        logger.info(
            "Routing task_type=%s → model=%s (backend=%s, ctx=%d)",
            task_type,
            spec.model_id,
            spec.backend,
            spec.ctx_size,
        )
        return await self.dispatch(spec, prompt)

    # ------------------------------------------------------------------
    # Models-as-Tools: coordinator orchestrates specialists via tool calls
    # ------------------------------------------------------------------

    def get_model_tools(self) -> list[dict]:
        """OpenAI-style tool definitions — one per specialist.

        Passes to lemonade_chat ``tools`` param so a coordinator model
        (Bonsai-8B) can call specialized models as tools.
        """
        tools = []
        for task_type, spec in SPECIALISTS.items():
            if task_type in ("classify", "embed"):
                continue  # not useful as callable tools
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": f"call_{task_type}_specialist",
                        "description": spec.description,
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "task": {
                                    "type": "string",
                                    "description": "The specific task to delegate to this specialist.",
                                }
                            },
                            "required": ["task"],
                        },
                    },
                }
            )
        return tools

    async def handle_tool_call(self, tool_name: str, task: str) -> str:
        """Execute a tool call from the coordinator model.

        The coordinator calls ``call_code_specialist(task="...")`` and this
        method routes to the appropriate lemonade model.
        """
        # Extract task_type from tool name: "call_code_specialist" → "code"
        prefix = "call_"
        suffix = "_specialist"
        if tool_name.startswith(prefix) and tool_name.endswith(suffix):
            task_type = tool_name[len(prefix) : -len(suffix)]
        else:
            task_type = DEFAULT_SPECIALIST

        result = await self.run(task, task_type=task_type)
        return result.text or f"[{result.model_id} returned empty: {result.error}]"

    async def run_with_coordinator(self, prompt: str) -> SmartResult:
        """Full models-as-tools run: coordinator → specialist tool calls → synthesize.

        Bonsai-8B acts as the coordinator. It sees the full fleet as tools,
        decides which specialists to call, and composes the final answer.
        """
        coordinator = SPECIALISTS["agent"]
        tools = self.get_model_tools()
        t0 = time.perf_counter()

        # Round 1: coordinator decides which specialists to invoke
        raw = await self._chat(
            coordinator.model_id,
            prompt,
            max_tokens=coordinator.max_tokens,
            temperature=coordinator.temperature,
            tools=tools,
        )
        message = raw["choices"][0]["message"]
        tool_calls = message.get("tool_calls") or []

        if not tool_calls:
            # Coordinator answered directly — no specialist delegation needed
            return SmartResult(
                text=message.get("content", ""),
                task_type="agent",
                model_id=coordinator.model_id,
                latency_ms=(time.perf_counter() - t0) * 1000,
            )

        # Round 2: execute all specialist tool calls in parallel
        specialist_results = await asyncio.gather(
            *[
                self.handle_tool_call(
                    tc["function"]["name"],
                    tc["function"]["arguments"].get("task", prompt)
                    if isinstance(tc["function"]["arguments"], dict)
                    else prompt,
                )
                for tc in tool_calls
            ],
            return_exceptions=True,
        )

        # Round 3: coordinator synthesizes all specialist outputs
        synthesis_prompt = (
            f"Original request: {prompt}\n\n"
            + "\n\n".join(
                f"[{tc['function']['name']}]:\n{r}"
                for tc, r in zip(tool_calls, specialist_results)
                if not isinstance(r, BaseException)
            )
            + "\n\nSynthesize the above into a complete, coherent final answer."
        )

        synthesis_spec = get_specialist("synthesis")
        synthesis = await self.dispatch(synthesis_spec, synthesis_prompt)
        synthesis.latency_ms += (time.perf_counter() - t0) * 1000
        return synthesis


def build_smart_orchestrator(base_url: str = _OMNI_URL) -> SmartOrchestrator:
    """Factory — matches the build_*_orchestrator() convention."""
    return SmartOrchestrator(base_url=base_url)
