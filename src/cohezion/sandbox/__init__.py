"""Sandbox execution framework for isolated operations.

Exports:
  - SandboxExecutor: Container-based execution with resource management
  - SafetyHarness: Pre-execution safety checks and monitoring
  - HookIntegration: Wire security hooks into sandbox lifecycle
  - Additional modules (isolation, rollback) available via direct import
"""

from cohezion.sandbox.executor import (
    ResourceLimits,
    ResourceMetrics,
    SandboxExecutor,
    SandboxRequest,
    SandboxResult,
    get_executor,
)
from cohezion.sandbox.hooks import (
    ExecutionContext,
    Hook,
    HookAction,
    HookDiscovery,
    HookExecutor,
    HookIntegration,
    HookMetadata,
    HookRegistry,
    HookResult,
    HookStage,
    get_hook_integration,
)
from cohezion.sandbox.safety import (
    POLICIES,
    ConstraintEnforcer,
    Monitor,
    PreFlightChecker,
    RiskAssessor,
    RiskLevel,
    SafetyCheckResult,
    SafetyHarness,
    SafetyPolicy,
    Violation,
    ViolationSeverity,
)


__all__ = [
    # Executor (implemented)
    "SandboxExecutor",
    "SandboxRequest",
    "SandboxResult",
    "ResourceLimits",
    "ResourceMetrics",
    "get_executor",
    # Safety (implemented)
    "SafetyHarness",
    "SafetyPolicy",
    "SafetyCheckResult",
    "Violation",
    "ViolationSeverity",
    "RiskLevel",
    "Monitor",
    "PreFlightChecker",
    "RiskAssessor",
    "ConstraintEnforcer",
    "POLICIES",
    # Hooks (implemented)
    "HookIntegration",
    "HookStage",
    "HookAction",
    "HookMetadata",
    "Hook",
    "HookResult",
    "ExecutionContext",
    "HookDiscovery",
    "HookExecutor",
    "HookRegistry",
    "get_hook_integration",
]
