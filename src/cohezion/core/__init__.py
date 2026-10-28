"""Cohezion core infrastructure.

Public names are resolved LAZILY (PEP 562). This package used to import all 59 of them eagerly
inside ``contextlib.suppress(Exception)`` blocks, so ``import cohezion.core.event_bus`` (105
cross-package import sites) first executed this file and loaded 498 cohezion modules plus torch:
5.2 s / 593 MB, versus 43 ms / 11 MB for event_bus itself. The suppress blocks also hid real
import errors. See docs/audits/DYNAMIC_MODULARITY_AUDIT_2026-09-24.md (F1-F3).

Now nothing is imported until a name is first used; ``from cohezion.core import X`` and
``cohezion.core.X`` behave as before, and a broken submodule raises where it is used.
"""

from __future__ import annotations

import importlib
from typing import Any


# public name -> (submodule relative to cohezion.core, attribute in that submodule)
_LAZY: dict[str, tuple[str, str]] = {
    "CohezionConfig": ("config", "CohezionConfig"),
    "ContextEngineeringInfrastructure": ("context_engineering", "ContextEngineeringInfrastructure"),
    "MCPAuthenticationError": ("mcp_client", "MCPAuthenticationError"),
    "MCPClient": ("mcp_client", "MCPClient"),
    "MCPClientError": ("mcp_client", "MCPClientError"),
    "MCPConfig": ("mcp_client", "MCPConfig"),
    "MCPConnectionError": ("mcp_client", "MCPConnectionError"),
    "MCPToolError": ("mcp_client", "MCPToolError"),
    "create_mcp_client": ("mcp_client", "create_mcp_client"),
    "VaultChangeEvent": ("vault_subscription", "VaultEvent"),
    "VaultSubscriptionClient": ("vault_subscription", "VaultSubscriptionClient"),
    "TokenClient": ("plan_executor", "TokenClient"),
    "StepResult": ("plan_executor", "StepResult"),
    "ExecutionResult": ("plan_executor", "ExecutionResult"),
    "NodeStatus": ("heterogeneous_sharding", "NodeStatus"),
    "ComputeNode": ("heterogeneous_sharding", "ComputeNode"),
    "Shard": ("heterogeneous_sharding", "Shard"),
    "TypeMismatchError": ("zero_copy_validator", "TypeMismatchError"),
    "ChecksumValidationError": ("zero_copy_validator", "ChecksumValidationError"),
    "SHMBuffer": ("zero_copy_validator", "SHMBuffer"),
    "PlanStep": ("instruction_expander", "PlanStep"),
    "ExecutablePlan": ("instruction_expander", "ExecutablePlan"),
    "InstructionExpander": ("instruction_expander", "InstructionExpander"),
    "LoomMode": ("substrate_loom", "LoomMode"),
    "SHMSnapshot": ("substrate_loom", "SHMSnapshot"),
    "SubstrateLoom": ("substrate_loom", "SubstrateLoom"),
    "PressureLevel": ("substrate_governor", "PressureLevel"),
    "DilationState": ("substrate_governor", "DilationState"),
    "GovernorEvent": ("substrate_governor", "GovernorEvent"),
    "TaskStatus": ("task_manager", "TaskStatus"),
    "TaskInfo": ("task_manager", "TaskInfo"),
    "TaskManager": ("task_manager", "TaskManager"),
    "PulseMode": ("manifold_sharding", "PulseMode"),
    "ManifoldShard": ("manifold_sharding", "ManifoldShard"),
    "HolographicCoherenceReport": ("manifold_sharding", "HolographicCoherenceReport"),
    "EventType": ("event_bus", "EventType"),
    "Event": ("event_bus", "Event"),
    "EventBus": ("event_bus", "EventBus"),
    "CacheManager": ("cache_manager", "CacheManager"),
    "ConfigTemplateManager": ("config_templates", "ConfigTemplateManager"),
    "CreditManager": ("credit_manager", "CreditManager"),
    "JourneyPersistenceManager": ("journey_persistence_manager", "JourneyPersistenceManager"),
    "TrajectoryNode": ("journey_persistence_manager", "TrajectoryNode"),
    "JourneyWorker": ("journey_worker", "JourneyWorker"),
    "LocalRegistry": ("local_registry", "LocalRegistry"),
    "retry_sync": ("mcp_retry", "retry_sync"),
    "ResourceMonitor": ("resource_monitor", "ResourceMonitor"),
    "LocalExpertRouter": ("routing.router", "LocalExpertRouter"),
    "ManifoldBridge": ("routing.manifold_bridge", "ManifoldBridge"),
    "SiliconGuard": ("silicon_guard", "SiliconGuard"),
    "HardwarePressure": ("silicon_guard", "HardwarePressure"),
    "SymmetryHardwareBridge": ("symmetry_hardware_bridge", "SymmetryHardwareBridge"),
    "TelemetryBus": ("telemetry_bus", "TelemetryBus"),
    "TemplateEngine": ("template_engine", "TemplateEngine"),
    "SkillSpec": ("template_engine", "SkillSpec"),
    "TimeKeeper": ("time_keeper", "TimeKeeper"),
    "TimeitStats": ("timeit", "TimeitStats"),
    "ZVOLSwapPipeline": ("zvol_swap", "ZVOLSwapPipeline"),
    "SwapEventType": ("zvol_swap", "SwapEventType"),
}

__all__ = [
    "CohezionConfig",
    "ContextEngineeringInfrastructure",
    "MCPAuthenticationError",
    "MCPClient",
    "MCPClientError",
    "MCPConfig",
    "MCPConnectionError",
    "MCPToolError",
    "VaultChangeEvent",
    "VaultSubscriptionClient",
    "create_mcp_client",
]


def __getattr__(name: str) -> Any:
    target = _LAZY.get(name)
    if target is None:
        # Previously every eager import also bound its submodule as a package attribute, so
        # `cohezion.core.<submodule>` worked after a bare `import cohezion.core`. Keep that.
        try:
            return importlib.import_module(f"{__name__}.{name}")
        except ModuleNotFoundError as e:
            if e.name != f"{__name__}.{name}":
                raise
            raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    module, attr = target
    try:
        value = getattr(importlib.import_module(f"{__name__}.{module}"), attr)
    except ImportError as e:
        # AttributeError keeps the old contract (hasattr() -> False, `from ... import` ->
        # ImportError); chaining keeps the real cause visible instead of suppressing it.
        raise AttributeError(
            f"module {__name__!r} attribute {name!r} unavailable: "
            f"cohezion.core.{module} failed to import ({e})"
        ) from e
    globals()[name] = value  # cache: later lookups skip __getattr__
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_LAZY))
