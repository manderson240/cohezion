# Swarm Workflows Package
"""
Workflow implementations for coordinating swarm agents.

- DebateWorkflow: Hierarchical voting with parallel analysts
"""

import contextlib

with contextlib.suppress(Exception):
    from cohezion.swarm.workflows.debate_protocol import DebateWorkflow as DebateWorkflow


__all__ = ["DebateWorkflow"]
