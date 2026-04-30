"""BMAD MCP Server - Shared config, engine, and route definitions."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

from aiohttp import web


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

MCP_PORT = int(os.getenv("MCP_PORT", "8361"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
BMAD_DATA_PATH = Path(os.getenv("BMAD_DATA_PATH", "_bmad"))

routes = web.RouteTableDef()


class BMADEngine:
    """Simple BMAD engine for workflow and agent management."""

    def __init__(self, data_path: Path):
        self.data_path = data_path
        self._modules: dict[str, Any] = {}
        self._workflows: dict[str, Any] = {}
        self._agents: dict[str, Any] = {}
        self._load_index()

    def _load_index(self) -> None:
        """Build index of modules, workflows, and agents."""
        if not self.data_path.exists():
            logger.warning(f"BMAD data path not found: {self.data_path}")
            return

        for module_dir in self.data_path.iterdir():
            if module_dir.is_dir() and not module_dir.name.startswith("_"):
                module_name = module_dir.name
                self._modules[module_name] = {"name": module_name}

                workflows_dir = module_dir / "workflows"
                if workflows_dir.exists():
                    for workflow_file in workflows_dir.rglob("*.md"):
                        rel_path = workflow_file.relative_to(workflows_dir)
                        workflow_id = f"{module_name}/{rel_path.with_suffix('')}"
                        self._workflows[workflow_id] = {
                            "id": workflow_id,
                            "module": module_name,
                            "path": str(workflow_file),
                            "name": workflow_file.stem,
                        }

                agents_dir = module_dir / "agents"
                if agents_dir.exists():
                    for agent_file in agents_dir.glob("*.md"):
                        agent_id = f"{module_name}-{agent_file.stem}"
                        self._agents[agent_id] = {
                            "id": agent_id,
                            "module": module_name,
                            "path": str(agent_file),
                            "name": agent_file.stem,
                        }

        logger.info(
            (
                f"BMAD: {len(self._modules)} modules, {len(self._workflows)} workflows, "
                f"{len(self._agents)} agents"
            )
        )

    def list_modules(self) -> list[dict]:
        """List all modules."""
        return [{"name": name} for name in self._modules]

    def list_workflows(self, module: str | None = None) -> list[dict]:
        """List workflows."""
        workflows = []
        for wid, info in self._workflows.items():
            if module and info["module"] != module:
                continue
            workflows.append({"id": wid, "module": info["module"], "name": info["name"]})
        return workflows

    def list_agents(self, module: str | None = None) -> list[dict]:
        """List agents."""
        agents = []
        for aid, info in self._agents.items():
            if module and info["module"] != module:
                continue
            agents.append({"id": aid, "module": info["module"], "name": info["name"]})
        return agents

    def get_workflow(self, workflow_id: str) -> dict:
        """Get workflow content."""
        if workflow_id not in self._workflows:
            for wid, _ in self._workflows.items():
                if workflow_id.lower() in wid.lower():
                    workflow_id = wid
                    break

        if workflow_id in self._workflows:
            info = self._workflows[workflow_id]
            try:
                content = Path(info["path"]).read_text()
                return {"id": workflow_id, "content": content}
            except Exception as e:
                return {"error": f"Failed to read workflow: {e}"}

        return {"error": f"Workflow not found: {workflow_id}"}

    def get_agent(self, agent_id: str) -> dict:
        """Get agent content."""
        if agent_id not in self._agents:
            for aid, _ in self._agents.items():
                if agent_id.lower() in aid.lower():
                    agent_id = aid
                    break

        if agent_id in self._agents:
            info = self._agents[agent_id]
            try:
                content = Path(info["path"]).read_text()
                return {"id": agent_id, "content": content}
            except Exception as e:
                return {"error": f"Failed to read agent: {e}"}

        return {"error": f"Agent not found: {agent_id}"}

    def get_next_steps(self, query: str) -> list[dict]:
        """Get recommended next steps."""
        query_lower = query.lower()
        suggestions = []

        keyword_map = {
            ("prd", "product"): ("bmad_bmm_create_prd", "Create a Product Requirements Document"),
            ("story", "user story"): ("bmad_bmm_create_story", "Create a user story"),
            ("sprint", "planning"): ("bmad_bmm_sprint_planning", "Plan a sprint"),
            ("game", "gdd"): ("bmad_gds_create_game_brief", "Create a game design brief"),
            ("brainstorm", "creative"): (
                "bmad_cis_brainstorming",
                "Facilitate brainstorming session",
            ),
            ("test", "testing"): ("bmad_tea_test_design", "Design tests"),
            ("agent", "create agent"): ("bmad_bmb_create_agent", "Create a custom BMAD agent"),
        }

        for keywords, (command, description) in keyword_map.items():
            if any(kw in query_lower for kw in keywords):
                suggestions.append({"command": command, "description": description})

        if not suggestions:
            suggestions = [
                {"command": "bmad_help", "description": "Get help with BMAD"},
                {"command": "bmad_list_workflows", "description": "List available workflows"},
                {"command": "bmad_list_agents", "description": "List available agents"},
            ]

        return suggestions


_engine: BMADEngine | None = None


def get_engine() -> BMADEngine:
    """Get or create BMAD engine."""
    global _engine
    if _engine is None:
        _engine = BMADEngine(BMAD_DATA_PATH)
    return _engine
