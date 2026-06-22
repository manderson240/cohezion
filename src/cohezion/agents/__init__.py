# Swarm Agents Package
"""
Agent implementations for the SLM Swarm.

- BaseAgent: Core agent functionality
"""

from __future__ import annotations

import contextlib

from cohezion.agents.base import BaseAgent


__all__ = [
    "BaseAgent",
]

# Wiring-sweep 2026-06-22: analyst was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.agents.analyst import AnalystAgent as AnalystAgent

# Wiring-sweep 2026-06-22: architect_agent was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.agents.architect_agent import ArchitectAgent as ArchitectAgent

# Wiring-sweep 2026-06-22: critic was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.agents.critic import CriticAgent as CriticAgent

# Wiring-sweep 2026-06-22: factory was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.agents.factory import AgentFactory as AgentFactory

# Wiring-sweep 2026-06-22: lab_agent was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.agents.lab_agent import LabAgent as LabAgent

# Wiring-sweep 2026-06-22: prompt_injection_guard was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.agents.prompt_injection_guard import wrap_untrusted as wrap_untrusted

# Wiring-sweep 2026-06-22: security_guard_agent was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.agents.security_guard_agent import SecurityGuardAgent as SecurityGuardAgent

# Wiring-sweep 2026-06-22: synthesizer was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.agents.synthesizer import SynthesizerAgent as SynthesizerAgent

# Wiring-sweep 2026-06-22: template_pipeline was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.agents.template_pipeline import GenerationResult as GenerationResult
    from cohezion.agents.template_pipeline import StaleAgent as StaleAgent
    from cohezion.agents.template_pipeline import SyncResult as SyncResult
    from cohezion.agents.template_pipeline import TemplatePipeline as TemplatePipeline

# Wiring-sweep 2026-06-22: version_tracker was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.agents.version_tracker import VersionTracker as VersionTracker
