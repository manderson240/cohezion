from __future__ import annotations

import contextlib

from cohezion.agent.unified_harness import ExecutionTrace, ToolRegistry, UnifiedAgent


__all__ = [UnifiedAgent, ToolRegistry, ExecutionTrace]

# Wiring-sweep 2026-06-22: skill_adaptor was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.agent.skill_adaptor import AcceptanceCheck as AcceptanceCheck
    from cohezion.agent.skill_adaptor import FaultAttribution as FaultAttribution
    from cohezion.agent.skill_adaptor import SkillUpdate as SkillUpdate
    from cohezion.agent.skill_adaptor import adapt_skill as adapt_skill
    from cohezion.agent.skill_adaptor import attribute_fault as attribute_fault
    from cohezion.agent.skill_adaptor import mask_volatile as mask_volatile

# Wiring-sweep 2026-06-22: error_loop was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.agent.error_loop import ErrorClass as ErrorClass
    from cohezion.agent.error_loop import ErrorClassifier as ErrorClassifier
    from cohezion.agent.error_loop import ReDispatchLedger as ReDispatchLedger
    from cohezion.agent.error_loop import error_signature as error_signature
    from cohezion.agent.error_loop import reflect as reflect

# Wiring-sweep 2026-06-22: reflective_orchestrator was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.agent.reflective_orchestrator import (
        run_with_reflection as run_with_reflection,
    )

# Wiring-sweep 2026-06-22: reflective_driver was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.agent.reflective_driver import ReflectiveDriver as ReflectiveDriver
