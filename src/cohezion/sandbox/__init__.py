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
    "POLICIES",
    "ConstraintEnforcer",
    "ExecutionContext",
    "Hook",
    "HookAction",
    "HookDiscovery",
    "HookExecutor",
    # Hooks (implemented)
    "HookIntegration",
    "HookMetadata",
    "HookRegistry",
    "HookResult",
    "HookStage",
    "Monitor",
    "PreFlightChecker",
    "ResourceLimits",
    "ResourceMetrics",
    "RiskAssessor",
    "RiskLevel",
    "SafetyCheckResult",
    # Safety (implemented)
    "SafetyHarness",
    "SafetyPolicy",
    # Executor (implemented)
    "SandboxExecutor",
    "SandboxRequest",
    "SandboxResult",
    "Violation",
    "ViolationSeverity",
    "get_executor",
    "get_hook_integration",
]

import contextlib

# Wiring-sweep 2026-06-22: isolation, rollback, shadow_worktree were genuine orphans.
with contextlib.suppress(Exception):
    from cohezion.sandbox.isolation import IsolationMode as IsolationMode
    from cohezion.sandbox.isolation import IsolationStatus as IsolationStatus

with contextlib.suppress(Exception):
    from cohezion.sandbox.rollback import AuditEventType as AuditEventType
    from cohezion.sandbox.rollback import (
        SnapshotBackendType as SnapshotBackendType,
    )

with contextlib.suppress(Exception):
    from cohezion.sandbox.shadow_worktree import (
        ShadowWorktree as ShadowWorktree,
    )
