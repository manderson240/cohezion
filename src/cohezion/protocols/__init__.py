"""Protocols — A2A server and UCP capability handler."""

import contextlib


with contextlib.suppress(Exception):
    from cohezion.protocols.a2a_server import A2AMessage as A2AMessage
    from cohezion.protocols.a2a_server import A2ATask as A2ATask
    from cohezion.protocols.a2a_server import AgentCard as AgentCard
    from cohezion.protocols.a2a_server import TaskState as TaskState

with contextlib.suppress(Exception):
    from cohezion.protocols.ucp_capability_handler import UCPCapability as UCPCapability
    from cohezion.protocols.ucp_capability_handler import (
        UCPCapabilityHandler as UCPCapabilityHandler,
    )
    from cohezion.protocols.ucp_capability_handler import UCPInvocationResult as UCPInvocationResult
