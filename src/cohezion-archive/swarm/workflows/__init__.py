# Swarm Workflows Package
"""
Workflow implementations for coordinating swarm agents.

- DebateWorkflow: Hierarchical voting with parallel analysts
"""

from cohezion.swarm.workflows.debate_protocol import DebateWorkflow


__all__ = ["DebateWorkflow"]
