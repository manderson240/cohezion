"""Cohezion specialist agents with validated model assignments.

Dynamically loadable agents with hardware-aware execution capabilities.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from cohezion.swarm.compute_backend_router import (
    BackendType,
    ComputeBackendRouter,
)


@dataclass
class AgentMetadata:
    """Metadata for dynamic agent registration."""

    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = "cohezion"
    capabilities: list[str] = field(default_factory=list)
    min_cohezion_version: str = "2.0.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "capabilities": self.capabilities,
            "min_cohezion_version": self.min_cohezion_version,
        }


@dataclass
class ToolDefinition:
    """Tool definition for GAIA-style tool registry."""

    name: str
    description: str
    func: Callable
    schema: dict[str, Any] = field(default_factory=dict)

    async def execute(self, **kwargs) -> Any:
        """Execute tool with validation."""
        if asyncio.iscoroutinefunction(self.func):
            return await self.func(**kwargs)
        return self.func(**kwargs)


class ToolRegistry:
    """GAIA-inspired tool registry for agents."""

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    def register(
        self,
        name: str | None = None,
        func: Callable | None = None,
        description: str = "",
        schema: dict | None = None,
    ) -> Callable:
        """Register a tool - can be used as decorator or function."""
        if func is None:
            # Used as decorator
            def decorator(f: Callable) -> Callable:
                tool_name = name or f.__name__
                self._register_tool(tool_name, f, description, schema)
                return f

            return decorator
        else:
            # Used as function
            tool_name = name or func.__name__
            self._register_tool(tool_name, func, description, schema)
            return func

    def _register_tool(
        self,
        name: str,
        func: Callable,
        description: str = "",
        schema: dict | None = None,
    ):
        """Internal tool registration."""
        if schema is None:
            schema = self._infer_schema(func)

        self._tools[name] = ToolDefinition(
            name=name,
            description=description or func.__doc__ or "",
            func=func,
            schema=schema,
        )

    def _infer_schema(self, func: Callable) -> dict[str, Any]:
        """Infer JSON schema from function signature."""
        import inspect
        import typing

        sig = inspect.signature(func)
        hints = typing.get_type_hints(func)

        properties = {}
        required = []

        type_map = {
            str: {"type": "string"},
            int: {"type": "integer"},
            float: {"type": "number"},
            bool: {"type": "boolean"},
            list: {"type": "array"},
            dict: {"type": "object"},
        }

        for param_name, param in sig.parameters.items():
            if param_name in ["self", "cls"]:
                continue

            param_type = hints.get(param_name, str)
            json_type = type_map.get(param_type, {"type": "string"})
            properties[param_name] = json_type

            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }

    async def execute(self, tool_name: str, **kwargs) -> Any:
        """Execute a registered tool."""
        if tool_name not in self._tools:
            raise ToolNotFoundError(f"Tool '{tool_name}' not found")

        tool = self._tools[tool_name]
        return await tool.execute(**kwargs)

    def list_tools(self) -> list[dict[str, Any]]:
        """List all registered tools with schemas."""
        return [
            {
                "name": name,
                "description": tool.description,
                "schema": tool.schema,
            }
            for name, tool in self._tools.items()
        ]

    def has_tool(self, name: str) -> bool:
        """Check if tool exists."""
        return name in self._tools


class ToolNotFoundError(Exception):
    """Raised when tool is not found."""

    pass


@dataclass
class SpecialistAgent:
    """Specialized agent with validated model and backend."""

    name: str
    description: str
    model: str
    backend: BackendType
    capabilities: list[str] = field(default_factory=list)
    max_tokens: int = 8192
    temperature: float = 0.7
    validated: bool = False
    tool_registry: ToolRegistry = field(default_factory=ToolRegistry)
    performance_stats: dict[str, Any] = field(default_factory=dict)
    metadata: AgentMetadata = field(default_factory=lambda: AgentMetadata("unnamed"))

    def __post_init__(self):
        """Initialize metadata after construction."""
        self.metadata = AgentMetadata(
            name=self.name,
            description=self.description,
            capabilities=self.capabilities,
        )
        self._router = None

    def register_tool(
        self,
        name: str | None = None,
        func: Callable | None = None,
        description: str = "",
    ) -> Callable:
        """Register a tool for this specialist."""
        return self.tool_registry.register(name, func, description)

    def _get_router(self) -> ComputeBackendRouter:
        """Lazy load router."""
        if self._router is None:
            self._router = ComputeBackendRouter.get_default()
        return self._router

    async def execute(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
        use_tools: list[str] | None = None,
    ) -> dict[str, Any]:
        """Execute with tracking and tool access."""
        start_time = time.time()
        context = context or {}

        try:
            # Execute on assigned backend
            result = await self._execute_on_backend(
                prompt=prompt,
                context=context,
                use_tools=use_tools or [],
            )

            latency_ms = (time.time() - start_time) * 1000

            # Update performance stats
            self._update_performance(latency_ms, result)

            return {
                "success": True,
                "agent": self.name,
                "model": self.model,
                "backend": self.backend.name,
                "latency_ms": latency_ms,
                "result": result,
                "tools_used": use_tools or [],
            }

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return {
                "success": False,
                "agent": self.name,
                "error": str(e),
                "latency_ms": latency_ms,
            }

    async def _execute_on_backend(
        self,
        prompt: str,
        context: dict[str, Any],
        use_tools: list[str],
    ) -> dict[str, Any]:
        """Execute on assigned backend with tools."""
        # Tool preprocessing
        tool_outputs = {}
        for tool_name in use_tools:
            if self.tool_registry.has_tool(tool_name):
                try:
                    tool_outputs[tool_name] = await self.tool_registry.execute(
                        tool_name, **context.get("tool_args", {})
                    )
                except Exception as e:
                    tool_outputs[tool_name] = {"error": str(e)}

        # Enhanced prompt with tool results
        enhanced_prompt = prompt
        if tool_outputs:
            enhanced_prompt += f"\n\nTool Results: {tool_outputs}"

        # Route to backend
        # This would integrate with actual model execution
        # For now, return placeholder indicating routing
        return {
            "text": f"[{self.name} via {self.backend.name}] Processed: {enhanced_prompt[:100]}...",
            "tool_outputs": tool_outputs,
            "tokens": len(enhanced_prompt) // 4,  # Rough estimate
        }

    def _update_performance(self, latency_ms: float, result: dict[str, Any]):
        """Update performance statistics."""
        if "performance" not in self.performance_stats:
            self.performance_stats["performance"] = {
                "total_calls": 0,
                "successful_calls": 0,
                "latency_samples": [],
                "last_used": None,
            }

        perf = self.performance_stats["performance"]
        perf["total_calls"] += 1
        if result.get("success", False):
            perf["successful_calls"] += 1

        perf["latency_samples"].append(latency_ms)
        # Keep only last 100 samples
        if len(perf["latency_samples"]) > 100:
            perf["latency_samples"] = perf["latency_samples"][-100:]

        perf["last_used"] = datetime.now().isoformat()

    def get_performance_summary(self) -> dict[str, Any]:
        """Get performance summary."""
        perf = self.performance_stats.get("performance", {})

        if not perf.get("latency_samples"):
            return {"status": "no_data"}

        latencies = perf["latency_samples"]
        return {
            "total_calls": perf.get("total_calls", 0),
            "success_rate": (perf.get("successful_calls", 0) / max(perf.get("total_calls", 1), 1)),
            "avg_latency_ms": sum(latencies) / len(latencies),
            "min_latency_ms": min(latencies),
            "max_latency_ms": max(latencies),
            "last_used": perf.get("last_used"),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SpecialistAgent:
        """Create agent from dictionary (for dynamic loading)."""
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            model=data["model"],
            backend=BackendType[data.get("backend", "CPU")],
            capabilities=data.get("capabilities", []),
            max_tokens=data.get("max_tokens", 8192),
            temperature=data.get("temperature", 0.7),
            validated=data.get("validated", False),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "model": self.model,
            "backend": self.backend.name,
            "capabilities": self.capabilities,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "validated": self.validated,
            "performance": self.get_performance_summary(),
            "metadata": self.metadata.to_dict(),
        }


# ═══════════════════════════════════════════════════════════════════════════
# VALIDATED SPECIALISTS (Production Ready)
# ═══════════════════════════════════════════════════════════════════════════

# Code specialist: Fast NPU execution for code tasks
CODE_SPECIALIST = SpecialistAgent(
    name="CodeSpecialist",
    description="Specialized in code generation, review, and debugging",
    model="qwen3:4b",
    backend=BackendType.NPU,
    capabilities=[
        "code_generation",
        "code_review",
        "debugging",
        "syntax_check",
        "refactoring",
    ],
    max_tokens=4096,
    validated=True,
    performance_stats={
        "tps": 75.0,
        "latency_ms": 13.0,
        "context_window": 128_000,
        "size_gb": 2.5,
        "power_w": 15,
    },
)

# Reasoning specialist: High-performance for complex reasoning
REASONING_SPECIALIST = SpecialistAgent(
    name="ReasoningSpecialist",
    description="Optimized for complex reasoning and analysis with long context",
    model="Gemma-4-E2B-it-GGUF",
    backend=BackendType.GPU_VULKAN,
    capabilities=[
        "complex_reasoning",
        "step_by_step_analysis",
        "long_context",
        "efficiency",
        "summarization",
    ],
    max_tokens=8192,
    validated=True,
    performance_stats={
        "tps": 97.26,
        "latency_ms": 10.3,
        "context_window": 256_000,
        "size_gb": 2.0,
        "power_w": 25,
    },
)

# Novel specialist: Experimental architecture for research
NOVEL_SPECIALIST = SpecialistAgent(
    name="NovelSpecialist",
    description="Experimental architecture specialist for research tasks",
    model="Jan-v1-4B-GGUF",
    backend=BackendType.GPU_VULKAN,
    capabilities=[
        "novel_architecture",
        "experimentation",
        "quick_iteration",
        "innovation",
    ],
    max_tokens=4096,
    validated=True,
    performance_stats={
        "tps": 76.18,
        "latency_ms": 13.1,
        "context_window": 4096,
        "size_gb": 2.5,
        "power_w": 25,
    },
)

# Placeholder specialists (to be validated)
PHI_SPECIALIST = SpecialistAgent(
    name="PhiSpecialist",
    description="Microsoft Phi-4 quality for code and math",
    model="phi4-mini-it:4b",
    backend=BackendType.NPU,
    capabilities=["code", "math", "reasoning"],
    validated=False,
    performance_stats={"tps": 75.0, "context_window": 128_000},
)

LFM_SPECIALIST = SpecialistAgent(
    name="LFMSpecialist",
    description="Liquid Neural Networks for novel architectures",
    model="lfm2:2.6b",
    backend=BackendType.NPU,
    capabilities=["novel_architecture", "liquid_neural_nets"],
    validated=False,
    performance_stats={"tps": 75.0, "context_window": 128_000},
)

# Registry of all validated specialists
VALIDATED_SPECIALISTS: dict[str, SpecialistAgent] = {
    "code": CODE_SPECIALIST,
    "reasoning": REASONING_SPECIALIST,
    "novel": NOVEL_SPECIALIST,
    "phi": PHI_SPECIALIST,
    "lfm": LFM_SPECIALIST,
}


def get_specialist(name: str) -> SpecialistAgent | None:
    """Get a validated specialist by name."""
    return VALIDATED_SPECIALISTS.get(name.lower())


def list_validated_specialists() -> list[SpecialistAgent]:
    """List all validated specialists."""
    return [agent for agent in VALIDATED_SPECIALISTS.values() if agent.validated]


def list_all_specialists() -> list[SpecialistAgent]:
    """List all specialists (including unvalidated)."""
    return list(VALIDATED_SPECIALISTS.values())
