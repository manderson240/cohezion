"""Registry package initializer.

Exports the primary registry APIs so that callers can simply:

    from cohezion.registry import load_registry, register_skill, search_skills
    from cohezion.registry import CapabilityRegistry
"""

import contextlib

from .capability_registry import Capability, CapabilityRegistry
from .skill_registry import auto_sync, load_registry, register_skill, search_skills


# Wiring-sweep 2026-06-22: autonomous_registration.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.registry.autonomous_registration import (
        AutonomousSkillRegistry as AutonomousSkillRegistry,
    )
    from cohezion.registry.autonomous_registration import (
        RegisteredSkill as RegisteredSkill,
    )
    from cohezion.registry.autonomous_registration import (
        RegistrationConflict as RegistrationConflict,
    )

# Wiring-sweep 2026-06-22: compound_version_registry.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.registry.compound_version_registry import (
        CompoundVersionRegistry as CompoundVersionRegistry,
    )
    from cohezion.registry.compound_version_registry import (
        VersionEntry as VersionEntry,
    )

# Wiring-sweep 2026-06-22: dependency_scanner.py was a genuine import-graph orphan.
# Note: DeprecationWarning omitted — shadows the Python builtin.
with contextlib.suppress(Exception):
    from cohezion.registry.dependency_scanner import (
        CVEAlert as CVEAlert,
    )
    from cohezion.registry.dependency_scanner import (
        DependencySecurityScanner as DependencySecurityScanner,
    )
    from cohezion.registry.dependency_scanner import (
        ScanReport as ScanReport,
    )
    from cohezion.registry.dependency_scanner import (
        Severity as Severity,
    )

# Wiring-sweep 2026-06-22: hooks.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.registry.hooks import (
        HookManager as HookManager,
    )
    from cohezion.registry.hooks import (
        RegistryEvent as RegistryEvent,
    )
    from cohezion.registry.hooks import (
        RegistryHook as RegistryHook,
    )
    from cohezion.registry.hooks import (
        get_hook_manager as get_hook_manager,
    )

# Wiring-sweep 2026-06-22: ouroboros_version_healer.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.registry.ouroboros_version_healer import (
        HealingEvent as HealingEvent,
    )
    from cohezion.registry.ouroboros_version_healer import (
        HealingOutcome as HealingOutcome,
    )
    from cohezion.registry.ouroboros_version_healer import (
        OuroborosVersionHealer as OuroborosVersionHealer,
    )

# Wiring-sweep 2026-06-22: version_telemetry.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.registry.version_telemetry import (
        DriftStatus as DriftStatus,
    )
    from cohezion.registry.version_telemetry import (
        VersionTelemetry as VersionTelemetry,
    )

# Wiring-sweep 2026-06-22: version_traceability_gate.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.registry.version_traceability_gate import (
        EpicCompletionGate as EpicCompletionGate,
    )
    from cohezion.registry.version_traceability_gate import (
        VersionTraceabilityGate as VersionTraceabilityGate,
    )


__all__ = [
    "AutonomousSkillRegistry",
    "CVEAlert",
    "Capability",
    "CapabilityRegistry",
    "CompoundVersionRegistry",
    "DependencySecurityScanner",
    "DriftStatus",
    "EpicCompletionGate",
    "HealingEvent",
    "HealingOutcome",
    "HookManager",
    "OuroborosVersionHealer",
    "RegisteredSkill",
    "RegistrationConflict",
    "RegistryEvent",
    "RegistryHook",
    "ScanReport",
    "Severity",
    "VersionEntry",
    "VersionTelemetry",
    "VersionTraceabilityGate",
    "auto_sync",
    "get_hook_manager",
    "load_registry",
    "register_skill",
    "search_skills",
]
