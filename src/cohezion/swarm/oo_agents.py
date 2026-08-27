"""Object-Oriented Agents (labs-OO-Agents) paradigm for Cohezion.

Treats agents as native Python objects where:
- Class fields hold agent state (Poincaré state, memory, session flags).
- Methods define agent capabilities with docstrings as LLM prompts and type hints as contracts.
- Deterministic methods execute standard Python code (0 ms latency).
- Dynamic methods (body = ...) are synthesized at runtime via local NPU models (e.g. qwen3.6-moe-35b-a3b-FLM) or AutoHarness AST bytecode.

Inspired by NVIDIA NeMo Labs `labs-OO-Agents` research preview.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any, TypeVar, get_type_hints

from pydantic import BaseModel, Field

from cohezion.core.event_bus import Event, EventBus
from cohezion.inference.unified_hybrid_router import TaskClass, UnifiedHybridRouter
from cohezion.reliability import (
    get_circuit,
)  # reconcile 2026-08-26: circuit_breaker retired on main (246249f6), get_circuit ported to reliability/__init__


T = TypeVar("T", bound="BaseOOAgent")


def capability(name: str = "", description: str = "") -> Callable[[Any], Any]:
    """Decorator marking a method as an agent capability contract."""

    def decorator(fn: Any) -> Any:
        fn.__is_agent_capability__ = True
        fn.__capability_name__ = name or fn.__name__
        fn.__capability_doc__ = description or fn.__doc__ or ""
        return fn

    return decorator


def dynamic(fn: Any) -> Any:
    """Decorator marking a method whose implementation is synthesized dynamically by LLM/AutoHarness."""
    fn.__is_dynamic_agent_method__ = True
    return fn


class OOAgentState(BaseModel):
    """Encapsulated state for an Object-Oriented Agent."""

    agent_id: str
    role: str
    state_vector: list[float] = Field(default_factory=lambda: [0.0] * 12)
    metadata: dict[str, Any] = Field(default_factory=dict)
    memory_store: list[dict[str, Any]] = Field(default_factory=list)


class BaseOOAgent:
    """Base class for Object-Oriented Agents in Cohezion.

    Subclasses define fields for state and methods for capabilities.
    """

    def __init__(
        self,
        agent_id: str,
        role: str,
        state_vector: list[float] | None = None,
        router: UnifiedHybridRouter | None = None,
    ) -> None:
        self.state = OOAgentState(
            agent_id=agent_id,
            role=role,
            state_vector=state_vector or [0.0] * 12,
        )
        self.router = router or UnifiedHybridRouter()
        self.event_bus = EventBus()

    def get_capabilities(self) -> dict[str, dict[str, Any]]:
        """Returns introspected capability contracts defined on this agent."""
        caps: dict[str, dict[str, Any]] = {}
        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if getattr(method, "__is_agent_capability__", False) or getattr(
                method, "__is_dynamic_agent_method__", False
            ):
                hints = get_type_hints(method)
                doc = inspect.getdoc(method) or ""
                caps[name] = {
                    "name": getattr(method, "__capability_name__", name),
                    "docstring": doc,
                    "type_hints": {k: str(v) for k, v in hints.items()},
                    "is_dynamic": getattr(method, "__is_dynamic_agent_method__", False),
                }
        return caps

    async def execute_dynamic_capability(
        self,
        method_name: str,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Executes a dynamic method (...) by prompting local NPU models (e.g. qwen3.6-moe-35b-a3b-FLM)."""
        method = getattr(self, method_name, None)
        if method is None:
            raise AttributeError(f"Agent {self.state.agent_id} has no capability '{method_name}'")

        doc = inspect.getdoc(method) or f"Execute capability {method_name}"
        hints = get_type_hints(method)

        prompt = (
            f"Role: {self.state.role}\n"
            f"Agent State: {self.state.model_dump_json()}\n"
            f"Capability Contract: {method_name}(args={args}, kwargs={kwargs})\n"
            f"Type Hints: {hints}\n"
            f"Instructions:\n{doc}\n"
            f"Synthesize deterministic response matching contract."
        )

        async def _invoke() -> Any:
            res = await self.router.route_by_capability(
                prompt=prompt,
                task_class=TaskClass.RESEARCH,
            )
            return res.content

        import time

        t0 = time.perf_counter()
        circuit_decorator = get_circuit(f"oo_agent_{method_name}")
        wrapped_invoke = circuit_decorator(_invoke)
        result = await wrapped_invoke()
        duration_ms = (time.perf_counter() - t0) * 1000.0

        await self.event_bus.publish(
            Event.agent_complete(
                agent_name=self.state.agent_id,
                result={"method": method_name, "status": "success"},
                duration_ms=duration_ms,
            )
        )
        return result
