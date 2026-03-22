"""Sequential Thinking MCP Server - Multi-step reasoning with revision.

Port: 8367
Features:
- Dynamic thought sequences
- Branching logic (if/then reasoning)
- Thought revision capability
- Hypothesis generation
- Reasoning persistence

Based on MCP Reference Sequential Thinking Server.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from aiohttp import web


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

MCP_PORT = int(os.getenv("MCP_PORT", "8367"))


@dataclass
class Thought:
    """Single thought in sequence."""

    id: str
    content: str
    thought_number: int
    total_thoughts: int
    next_thought_needed: bool = True
    is_revision: bool = False
    revises_thought: int | None = None
    branch_from_thought: int | None = None
    branch_id: str | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "thoughtNumber": self.thought_number,
            "totalThoughts": self.total_thoughts,
            "nextThoughtNeeded": self.next_thought_needed,
            "isRevision": self.is_revision,
            "revisesThought": self.revises_thought,
            "branchFromThought": self.branch_from_thought,
            "branchId": self.branch_id,
            "createdAt": self.created_at,
        }


class ThinkingSession:
    """Session for multi-step reasoning."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.thoughts: list[Thought] = []
        self.branches: dict[str, list[Thought]] = {}
        self.created_at = datetime.utcnow().isoformat()

    def add_thought(
        self,
        content: str,
        next_thought_needed: bool = True,
        is_revision: bool = False,
        revises_thought: int | None = None,
        branch_from_thought: int | None = None,
        branch_id: str | None = None,
    ) -> Thought:
        """Add thought to sequence."""
        # Calculate thought number
        if branch_id and branch_id in self.branches:
            thought_number = len(self.branches[branch_id]) + 1
            total_thoughts = thought_number if not next_thought_needed else thought_number + 1
        else:
            thought_number = len(self.thoughts) + 1
            total_thoughts = thought_number if not next_thought_needed else thought_number + 1

        thought = Thought(
            id=str(uuid.uuid4())[:8],
            content=content,
            thought_number=thought_number,
            total_thoughts=total_thoughts,
            next_thought_needed=next_thought_needed,
            is_revision=is_revision,
            revises_thought=revises_thought,
            branch_from_thought=branch_from_thought,
            branch_id=branch_id,
        )

        if branch_id:
            if branch_id not in self.branches:
                self.branches[branch_id] = []
            self.branches[branch_id].append(thought)
        else:
            self.thoughts.append(thought)

        return thought

    def get_thought(self, thought_number: int, branch_id: str | None = None) -> Thought | None:
        """Get specific thought."""
        thoughts = self.branches.get(branch_id, self.thoughts)
        for t in thoughts:
            if t.thought_number == thought_number:
                return t
        return None

    def get_sequence(self, branch_id: str | None = None) -> list[Thought]:
        """Get thought sequence."""
        return self.branches.get(branch_id, self.thoughts)

    def to_dict(self) -> dict:
        return {
            "sessionId": self.session_id,
            "createdAt": self.created_at,
            "mainSequence": [t.to_dict() for t in self.thoughts],
            "branches": {
                bid: [t.to_dict() for t in thoughts] for bid, thoughts in self.branches.items()
            },
        }


# Global sessions
_sessions: dict[str, ThinkingSession] = {}


def get_session(session_id: str) -> ThinkingSession:
    """Get or create thinking session."""
    if session_id not in _sessions:
        _sessions[session_id] = ThinkingSession(session_id)
    return _sessions[session_id]


routes = web.RouteTableDef()


@routes.get("/health")
async def health(request: web.Request) -> web.Response:
    """Health check."""
    return web.json_response(
        {
            "status": "healthy",
            "server": "sequential-thinking",
            "port": MCP_PORT,
        }
    )


@routes.get("/")
async def index(request: web.Request) -> web.Response:
    """Server info."""
    return web.json_response(
        {
            "name": "Sequential Thinking MCP Server",
            "version": "1.0.0",
            "port": MCP_PORT,
            "sessions": len(_sessions),
            "tools": [
                "thinking_think",
                "thinking_revise",
                "thinking_branch",
                "thinking_get_sequence",
                "thinking_get_session",
            ],
        }
    )


@routes.post("/tools/thinking_think")
async def tool_think(request: web.Request) -> web.Response:
    """Add thought to sequence."""
    try:
        data = await request.json()
        session_id = data.get("sessionId", str(uuid.uuid4()))
        thought = data.get("thought", "")
        next_thought_needed = data.get("nextThoughtNeeded", True)

        if not thought:
            return web.json_response({"error": "thought is required"}, status=400)

        session = get_session(session_id)
        result = session.add_thought(thought, next_thought_needed)

        return web.json_response(
            {
                "tool": "thinking_think",
                "sessionId": session_id,
                "thought": result.to_dict(),
            }
        )
    except Exception as e:
        logger.exception("Think failed")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/thinking_revise")
async def tool_revise(request: web.Request) -> web.Response:
    """Revise existing thought."""
    try:
        data = await request.json()
        session_id = data.get("sessionId", "")
        thought_number = data.get("thoughtNumber", 0)
        new_content = data.get("newThought", "")

        if not session_id or not thought_number or not new_content:
            return web.json_response(
                {"error": "sessionId, thoughtNumber, and newThought are required"}, status=400
            )

        session = get_session(session_id)

        # Add as revision
        result = session.add_thought(
            content=new_content,
            is_revision=True,
            revises_thought=thought_number,
        )

        return web.json_response(
            {
                "tool": "thinking_revise",
                "sessionId": session_id,
                "revisedThoughtNumber": thought_number,
                "revision": result.to_dict(),
            }
        )
    except Exception as e:
        logger.exception("Revise failed")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/thinking_branch")
async def tool_branch(request: web.Request) -> web.Response:
    """Create branch from thought."""
    try:
        data = await request.json()
        session_id = data.get("sessionId", "")
        branch_from = data.get("branchFrom", 0)
        branch_id = data.get("branchId") or str(uuid.uuid4())[:8]
        first_thought = data.get("firstThought", "")

        if not session_id or not branch_from or not first_thought:
            return web.json_response(
                {"error": "sessionId, branchFrom, and firstThought are required"}, status=400
            )

        session = get_session(session_id)

        # Add first thought to branch
        result = session.add_thought(
            content=first_thought,
            branch_from_thought=branch_from,
            branch_id=branch_id,
        )

        return web.json_response(
            {
                "tool": "thinking_branch",
                "sessionId": session_id,
                "branchId": branch_id,
                "branchedFrom": branch_from,
                "firstThought": result.to_dict(),
            }
        )
    except Exception as e:
        logger.exception("Branch failed")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/thinking_get_sequence")
async def tool_get_sequence(request: web.Request) -> web.Response:
    """Get thought sequence."""
    try:
        data = await request.json()
        session_id = data.get("sessionId", "")
        branch_id = data.get("branchId")  # Optional

        if not session_id:
            return web.json_response({"error": "sessionId is required"}, status=400)

        session = get_session(session_id)
        thoughts = session.get_sequence(branch_id)

        return web.json_response(
            {
                "tool": "thinking_get_sequence",
                "sessionId": session_id,
                "branchId": branch_id,
                "thoughtCount": len(thoughts),
                "thoughts": [t.to_dict() for t in thoughts],
            }
        )
    except Exception as e:
        logger.exception("Get sequence failed")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/thinking_get_session")
async def tool_get_session(request: web.Request) -> web.Response:
    """Get full session details."""
    try:
        data = await request.json()
        session_id = data.get("sessionId", "")

        if not session_id:
            return web.json_response({"error": "sessionId is required"}, status=400)

        session = get_session(session_id)

        return web.json_response(
            {
                "tool": "thinking_get_session",
                "session": session.to_dict(),
            }
        )
    except Exception as e:
        logger.exception("Get session failed")
        return web.json_response({"error": str(e)}, status=500)


def create_app() -> web.Application:
    """Create the web application."""
    from cohezion.mcp.shared.auth import api_key_middleware

    app = web.Application(middlewares=[api_key_middleware])
    app.add_routes(routes)
    return app


# Global app instance for import
app = create_app()


async def main():
    """Run the Sequential Thinking MCP Server."""
    logger.info(f"Starting Sequential Thinking MCP Server on port {MCP_PORT}")
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", MCP_PORT)
    await site.start()

    logger.info(f"✅ Sequential Thinking Server running on http://localhost:{MCP_PORT}")

    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Sequential Thinking Server stopped")
