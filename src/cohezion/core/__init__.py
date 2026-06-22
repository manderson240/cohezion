"""Cohezion core infrastructure."""

import contextlib

from cohezion.core.config import CohezionConfig
from cohezion.core.context_engineering import ContextEngineeringInfrastructure
from cohezion.core.mcp_client import (
    MCPAuthenticationError,
    MCPClient,
    MCPClientError,
    MCPConfig,
    MCPConnectionError,
    MCPToolError,
    create_mcp_client,
)
from cohezion.core.vault_subscription import VaultEvent as VaultChangeEvent
from cohezion.core.vault_subscription import VaultSubscriptionClient

# Wiring-sweep 2026-06-22: core/ orphan modules round-4
with contextlib.suppress(Exception):
    from cohezion.core.plan_executor import (
        TokenClient as TokenClient,
    )
with contextlib.suppress(Exception):
    from cohezion.core.plan_executor import (
        StepResult as StepResult,
    )
with contextlib.suppress(Exception):
    from cohezion.core.plan_executor import (
        ExecutionResult as ExecutionResult,
    )

with contextlib.suppress(Exception):
    from cohezion.core.heterogeneous_sharding import (
        NodeStatus as NodeStatus,
    )
with contextlib.suppress(Exception):
    from cohezion.core.heterogeneous_sharding import (
        ComputeNode as ComputeNode,
    )
with contextlib.suppress(Exception):
    from cohezion.core.heterogeneous_sharding import (
        Shard as Shard,
    )

with contextlib.suppress(Exception):
    from cohezion.core.zero_copy_validator import (
        TypeMismatchError as TypeMismatchError,
    )
with contextlib.suppress(Exception):
    from cohezion.core.zero_copy_validator import (
        ChecksumValidationError as ChecksumValidationError,
    )
with contextlib.suppress(Exception):
    from cohezion.core.zero_copy_validator import (
        SHMBuffer as SHMBuffer,
    )

with contextlib.suppress(Exception):
    from cohezion.core.instruction_expander import (
        PlanStep as PlanStep,
    )
with contextlib.suppress(Exception):
    from cohezion.core.instruction_expander import (
        ExecutablePlan as ExecutablePlan,
    )
with contextlib.suppress(Exception):
    from cohezion.core.instruction_expander import (
        InstructionExpander as InstructionExpander,
    )

with contextlib.suppress(Exception):
    from cohezion.core.substrate_loom import (
        LoomMode as LoomMode,
    )
with contextlib.suppress(Exception):
    from cohezion.core.substrate_loom import (
        SHMSnapshot as SHMSnapshot,
    )
with contextlib.suppress(Exception):
    from cohezion.core.substrate_loom import (
        SubstrateLoom as SubstrateLoom,
    )

with contextlib.suppress(Exception):
    from cohezion.core.substrate_governor import (
        PressureLevel as PressureLevel,
    )
with contextlib.suppress(Exception):
    from cohezion.core.substrate_governor import (
        DilationState as DilationState,
    )
with contextlib.suppress(Exception):
    from cohezion.core.substrate_governor import (
        GovernorEvent as GovernorEvent,
    )

with contextlib.suppress(Exception):
    from cohezion.core.connection_pool import (
        SurrealClientProtocol as SurrealClientProtocol,
    )
with contextlib.suppress(Exception):
    from cohezion.core.connection_pool import (
        PoolConfig as PoolConfig,
    )
with contextlib.suppress(Exception):
    from cohezion.core.connection_pool import (
        PooledConnection as PooledConnection,
    )

with contextlib.suppress(Exception):
    from cohezion.core.task_manager import (
        TaskStatus as TaskStatus,
    )
with contextlib.suppress(Exception):
    from cohezion.core.task_manager import (
        TaskInfo as TaskInfo,
    )
with contextlib.suppress(Exception):
    from cohezion.core.task_manager import (
        TaskManager as TaskManager,
    )

with contextlib.suppress(Exception):
    from cohezion.core.manifold_sharding import (
        PulseMode as PulseMode,
    )
with contextlib.suppress(Exception):
    from cohezion.core.manifold_sharding import (
        ManifoldShard as ManifoldShard,
    )
with contextlib.suppress(Exception):
    from cohezion.core.manifold_sharding import (
        HolographicCoherenceReport as HolographicCoherenceReport,
    )

with contextlib.suppress(Exception):
    from cohezion.core.event_bus import (
        EventType as EventType,
    )
with contextlib.suppress(Exception):
    from cohezion.core.event_bus import (
        Event as Event,
    )
with contextlib.suppress(Exception):
    from cohezion.core.event_bus import (
        EventBus as EventBus,
    )


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
