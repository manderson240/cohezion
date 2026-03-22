"""BMAD Engine - Workflow and agent management."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


class BMADEngine:
    """Engine for loading and executing BMAD workflows."""

    def __init__(self, data_path: Path | str):
        self.data_path = Path(data_path)
        self._modules: dict[str, dict] = {}
        self._workflows: dict[str, dict] = {}
        self._agents: dict[str, dict] = {}
        self._load_index()

    def _load_index(self) -> None:
        """Build index of available modules, workflows, and agents."""
        if not self.data_path.exists():
            logger.warning(f"BMAD data path not found: {self.data_path}")
            return

        # Load modules
        for module_dir in self.data_path.iterdir():
            if module_dir.is_dir() and not module_dir.name.startswith("_"):
                module_name = module_dir.name
                self._modules[module_name] = {
                    "name": module_name,
                    "path": str(module_dir),
                    "workflows": [],
                    "agents": [],
                }

                # Index workflows
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
                        self._modules[module_name]["workflows"].append(workflow_id)

                # Index agents
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
                        self._modules[module_name]["agents"].append(agent_id)

        logger.info(
            f"BMAD engine loaded: {len(self._modules)} modules, "
            f"{len(self._workflows)} workflows, {len(self._agents)} agents"
        )

    def load_workflow(self, module: str, path: str) -> dict[str, Any]:
        """Load workflow content.

        Args:
            module: Module name (e.g., 'bmm', 'gds')
            path: Workflow path within module

        Returns:
            Workflow content and metadata
        """
        from cohezion.mcp.servers.safe_input import sanitize_path

        # Try different path formats
        try:
            workflow_paths = [
                sanitize_path(self.data_path / module / f"{path}.md", base_dir=self.data_path),
                sanitize_path(
                    self.data_path / module / path / f"{path.split('/')[-1]}.md",
                    base_dir=self.data_path,
                ),
                sanitize_path(
                    self.data_path / module / "workflows" / f"{path}.md", base_dir=self.data_path
                ),
            ]
        except ValueError:
            return {"error": f"Invalid workflow path: {module}/{path}"}

        for workflow_path in workflow_paths:
            if workflow_path.exists():
                content = workflow_path.read_text()
                return {
                    "id": f"{module}/{path}",
                    "module": module,
                    "path": str(workflow_path),
                    "content": content,
                }

        return {"error": f"Workflow not found: {module}/{path}"}

    def load_agent(self, agent_id: str) -> dict[str, Any]:
        """Load agent persona.

        Args:
            agent_id: Agent identifier (e.g., 'bmm-pm', 'gds-game-designer')

        Returns:
            Agent content and metadata
        """
        if agent_id in self._agents:
            agent = self._agents[agent_id]
            content = Path(agent["path"]).read_text()
            return {
                "id": agent_id,
                "module": agent["module"],
                "name": agent["name"],
                "content": content,
            }

        # Try to find by partial match
        for aid, agent in self._agents.items():
            if agent_id.lower() in aid.lower():
                content = Path(agent["path"]).read_text()
                return {
                    "id": aid,
                    "module": agent["module"],
                    "name": agent["name"],
                    "content": content,
                }

        return {"error": f"Agent not found: {agent_id}"}

    def load_agent_prompt(self, agent_id: str) -> str:
        """Load agent as a prompt string.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent content as string
        """
        agent = self.load_agent(agent_id)
        if "error" in agent:
            return f"# Error loading agent\n{agent['error']}"
        return agent.get("content", "")

    def list_modules(self) -> list[dict[str, Any]]:
        """List all available modules."""
        return [
            {
                "name": name,
                "workflows": len(info["workflows"]),
                "agents": len(info["agents"]),
            }
            for name, info in self._modules.items()
        ]

    def list_workflows(
        self, module: str | None = None, phase: str | None = None
    ) -> list[dict[str, Any]]:
        """List available workflows.

        Args:
            module: Filter by module
            phase: Filter by phase (not yet implemented)

        Returns:
            List of workflow summaries
        """
        workflows = []
        for wid, info in self._workflows.items():
            if module and info["module"] != module:
                continue
            workflows.append(
                {
                    "id": wid,
                    "module": info["module"],
                    "name": info["name"],
                }
            )
        return workflows

    def list_agents(self, module: str | None = None) -> list[dict[str, Any]]:
        """List available agents.

        Args:
            module: Filter by module

        Returns:
            List of agent summaries
        """
        agents = []
        for aid, info in self._agents.items():
            if module and info["module"] != module:
                continue
            agents.append(
                {
                    "id": aid,
                    "module": info["module"],
                    "name": info["name"],
                }
            )
        return agents

    def analyze_context(self, context: str, session: dict | None) -> dict[str, Any]:
        """Analyze user context to provide recommendations."""
        # Simple analysis - can be enhanced with AI
        analysis = {
            "context_length": len(context),
            "has_session": session is not None,
            "keywords": [],
            "suggested_modules": [],
        }

        # Extract keywords
        keywords = [
            "product",
            "prd",
            "story",
            "sprint",
            "game",
            "test",
            "brainstorm",
            "create",
            "design",
        ]
        context_lower = context.lower()
        for kw in keywords:
            if kw in context_lower:
                analysis["keywords"].append(kw)

        # Suggest modules
        if any(kw in context_lower for kw in ["product", "prd", "story", "sprint"]):
            analysis["suggested_modules"].append("bmm")
        if any(kw in context_lower for kw in ["game", "gdd", "playtest"]):
            analysis["suggested_modules"].append("gds")
        if any(kw in context_lower for kw in ["brainstorm", "creative", "innovation"]):
            analysis["suggested_modules"].append("cis")
        if any(kw in context_lower for kw in ["test", "testing", "qa"]):
            analysis["suggested_modules"].append("tea")

        return analysis

    def get_next_steps(self, query: str, analysis: dict, session: dict | None) -> dict:
        """Get recommended next steps based on context."""
        recommendations = {
            "suggested_commands": [],
            "reasoning": "",
        }

        query_lower = query.lower()

        # Pattern matching for recommendations
        if any(kw in query_lower for kw in ["what should i do", "next", "help"]):
            recommendations["suggested_commands"] = [
                "bmad_list_workflows",
                "bmad_list_agents",
                "bmad_help",
            ]
            recommendations["reasoning"] = (
                "You can explore available workflows, agents, or get general help."
            )

        if "prd" in query_lower or "product" in query_lower:
            recommendations["suggested_commands"].append("bmad_bmm_create_prd")

        if "story" in query_lower:
            recommendations["suggested_commands"].append("bmad_bmm_create_story")

        if "sprint" in query_lower:
            recommendations["suggested_commands"].append("bmad_bmm_sprint_planning")

        if "game" in query_lower:
            recommendations["suggested_commands"].append("bmad_gds_create_game_brief")

        if not recommendations["suggested_commands"]:
            recommendations["suggested_commands"] = [
                "bmad_help",
                "bmad_list_workflows",
            ]

        return recommendations

    async def execute_workflow(
        self, workflow: dict[str, Any], params: dict[str, Any], session_id: str | None
    ) -> dict[str, Any]:
        """Execute a workflow with given parameters.

        This is a placeholder - actual execution would involve AI model calls.
        For now, returns structured data based on workflow type.
        """
        workflow_id = workflow.get("id", "unknown")

        # Extract workflow name from ID
        parts = workflow_id.split("/")
        workflow_name = parts[-1] if len(parts) > 1 else workflow_id

        # Generate response based on workflow type
        result = {
            "workflow": workflow_id,
            "params": params,
            "session_id": session_id,
            "status": "completed",
            "output": f"Workflow '{workflow_name}' executed with {len(params)} parameters",
        }

        # Add specific output based on workflow type
        if "create-prd" in workflow_name:
            result["prd_sections"] = [
                "Executive Summary",
                "Product Overview",
                "User Stories",
                "Acceptance Criteria",
                "Technical Requirements",
                "Timeline",
            ]
        elif "create-story" in workflow_name:
            result["story_template"] = {
                "title": params.get("title", "User Story"),
                "as_a": "user",
                "i_want": "feature",
                "so_that": "benefit",
                "acceptance_criteria": params.get("acceptance_criteria", []),
            }

        return result

    def generate_session_id(self) -> str:
        """Generate a new session ID."""
        import uuid

        return str(uuid.uuid4())

    async def index_project(self, project_path: str, include_patterns: list[str]) -> dict[str, Any]:
        """Index a project for searchability."""
        import os

        from cohezion.mcp.servers.safe_input import sanitize_path

        try:
            base_path = sanitize_path(project_path, base_dir=Path.cwd())
        except ValueError:
            return {"error": f"Path escapes allowed directory: {project_path}"}

        if not base_path.exists():
            return {"error": f"Project path not found: {project_path}"}

        files_indexed = 0
        indexed_files = []

        for root, _, files in os.walk(base_path):
            for file in files:
                file_path = Path(root) / file
                rel_path = file_path.relative_to(base_path)

                # Check against include patterns
                for pattern in include_patterns:
                    if file.endswith(pattern.replace("*", "")):
                        files_indexed += 1
                        indexed_files.append(str(rel_path))
                        break

        return {
            "project_path": project_path,
            "files_indexed": files_indexed,
            "patterns": include_patterns,
            "sample_files": indexed_files[:10],
        }
