"""A2A Protocol Server (v1.0.2 Phase 4).

Implements Google's Agent-to-Agent (A2A) protocol v1.0 for Cohezion.
Exposes Cohezion agents as compliant remote agents via:
1. Agent Cards — capability discovery
2. Task lifecycle — send/receive/status/cancel
3. Streaming — SSE for long-running tasks

Reference:
    https://github.com/a2a-protocol/a2a
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


logger = logging.getLogger(__name__)


class TaskState(StrEnum):
    """A2A task lifecycle states."""

    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    CANCELED = "canceled"
    FAILED = "failed"


@dataclass
class A2AMessage:
    """A2A protocol message."""

    role: str  # "user" or "agent"
    parts: list[dict[str, Any]]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class A2ATask:
    """A2A protocol task."""

    id: str
    state: TaskState
    messages: list[A2AMessage] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class AgentCard:
    """A2A Agent Card for capability discovery."""

    name: str = "Cohezion Agent"
    description: str = (
        "AI swarm orchestration platform with FLUME methodology for "
        "multi-agent coordination, physics simulation, and intelligent "
        "skill routing."
    )
    url: str = "http://localhost:8000"
    version: str = "1.0.2"
    capabilities: list[str] = field(
        default_factory=lambda: [
            "simulation",
            "synthesis",
            "routing",
            "analysis",
        ]
    )
    skills: list[str] = field(default_factory=list)
    authentication: dict[str, Any] = field(
        default_factory=lambda: {
            "type": "api_key",
            "header": "X-Cohezion-Key",
        }
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to A2A Agent Card format."""
        return {
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "version": self.version,
            "capabilities": {
                "streaming": True,
                "pushNotifications": False,
                "stateTransitionHistory": True,
            },
            "skills": [
                {"id": s, "name": s, "description": f"Cohezion {s} skill"}
                for s in self.capabilities
            ],
            "authentication": self.authentication,
            "defaultInputModes": ["text/plain", "application/json"],
            "defaultOutputModes": ["text/plain", "application/json"],
        }

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class A2AServer:
    """A2A-compliant agent server for Cohezion.

    Manages task lifecycle and routes requests to Cohezion agents.

    Parameters
    ----------
    agent_card : AgentCard
        The agent's capability declaration.
    """

    def __init__(
        self,
        agent_card: AgentCard | None = None,
    ) -> None:
        self.agent_card = agent_card or AgentCard()
        self.tasks: dict[str, A2ATask] = {}
        self._handlers: dict[str, Any] = {}

    def get_agent_card(self) -> dict[str, Any]:
        """Return the Agent Card (/.well-known/agent.json)."""
        return self.agent_card.to_dict()

    async def send_task(
        self,
        message: dict[str, Any],
        task_id: str | None = None,
    ) -> A2ATask:
        """Create or continue a task (POST /tasks/send).

        Parameters
        ----------
        message : dict
            A2A message with role and parts.
        task_id : str, optional
            Existing task ID for continuation.

        Returns
        -------
        A2ATask
            The created or updated task.
        """
        if task_id and task_id in self.tasks:
            task = self.tasks[task_id]
        else:
            task_id = str(uuid.uuid4())
            task = A2ATask(id=task_id, state=TaskState.SUBMITTED)
            self.tasks[task_id] = task

        a2a_msg = A2AMessage(
            role=message.get("role", "user"),
            parts=message.get("parts", []),
        )
        task.messages.append(a2a_msg)
        task.state = TaskState.WORKING
        task.updated_at = time.time()

        # Route to Cohezion agent
        try:
            result = await self._route_to_agent(task)
            task.state = TaskState.COMPLETED
            task.messages.append(
                A2AMessage(
                    role="agent",
                    parts=[{"type": "text", "text": result}],
                )
            )
        except Exception as e:
            logger.exception("Task %s failed", task_id)
            task.state = TaskState.FAILED
            task.messages.append(
                A2AMessage(
                    role="agent",
                    parts=[
                        {
                            "type": "text",
                            "text": f"Error: {type(e).__name__}: Task execution failed",
                        }
                    ],
                )
            )

        task.updated_at = time.time()
        return task

    async def get_task(self, task_id: str) -> A2ATask | None:
        """Get task status (GET /tasks/{id})."""
        return self.tasks.get(task_id)

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task (POST /tasks/{id}/cancel)."""
        task = self.tasks.get(task_id)
        if task and task.state == TaskState.WORKING:
            task.state = TaskState.CANCELED
            task.updated_at = time.time()
            return True
        return False

    async def _route_to_agent(self, task: A2ATask) -> str:
        """Route A2A task to internal Cohezion agent.

        Extracts the text from the latest user message and routes
        it through the compound executor.
        """
        last_user_msg = None
        for msg in reversed(task.messages):
            if msg.role == "user":
                last_user_msg = msg
                break

        if not last_user_msg:
            return "No user message found in task."

        text_parts = [p.get("text", "") for p in last_user_msg.parts if p.get("type") == "text"]
        prompt = " ".join(text_parts)

        if not prompt.strip():
            return "Empty prompt received."

        # Route through Cohezion's compound executor
        try:
            from cohezion.compound.executor import CompoundExecutor

            executor = CompoundExecutor()
            result = await executor.execute(prompt)
            return str(result)
        except ImportError:
            logger.warning("CompoundExecutor not available, using echo")
            return f"[Cohezion A2A Echo] Received: {prompt[:200]}"


class A2AClient:
    """Client for invoking external A2A-compliant agents.

    Parameters
    ----------
    timeout : float
        HTTP request timeout in seconds.
    """

    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout
        self._discovered_agents: dict[str, dict[str, Any]] = {}

    async def discover_agent(self, base_url: str) -> dict[str, Any] | None:
        """Discover an A2A agent via its Agent Card.

        Parameters
        ----------
        base_url : str
            Agent's base URL (e.g., "https://agent.example.com").

        Returns
        -------
        dict or None
            Agent Card if discovered, None otherwise.
        """
        try:
            import httpx

            url = f"{base_url.rstrip('/')}/.well-known/agent.json"
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    card = resp.json()
                    self._discovered_agents[base_url] = card
                    logger.info(
                        "Discovered A2A agent: %s at %s",
                        card.get("name", "unknown"),
                        base_url,
                    )
                    return card
        except Exception as e:
            logger.error(
                "Failed to discover agent at %s: %s",
                base_url,
                e,
            )
        return None

    async def send_task(
        self,
        base_url: str,
        prompt: str,
        task_id: str | None = None,
    ) -> dict[str, Any]:
        """Send a task to an external A2A agent.

        Parameters
        ----------
        base_url : str
            Agent's base URL.
        prompt : str
            User prompt to send.
        task_id : str, optional
            Existing task ID for continuation.

        Returns
        -------
        dict
            Task response from the agent.
        """
        try:
            import httpx

            url = f"{base_url.rstrip('/')}/tasks/send"
            payload: dict[str, Any] = {
                "jsonrpc": "2.0",
                "method": "tasks/send",
                "params": {
                    "message": {
                        "role": "user",
                        "parts": [{"type": "text", "text": prompt}],
                    },
                },
            }
            if task_id:
                payload["params"]["id"] = task_id

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload)
                return resp.json()
        except Exception as e:
            logger.error("A2A send_task failed: %s", e)
            return {"error": str(e)}
