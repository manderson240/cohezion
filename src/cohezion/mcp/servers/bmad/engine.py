"""BMAD Engine - v6.3.0 catalog-driven workflow and agent management.

Reads skill/agent manifests and the bmad-help.csv catalog produced by
``npx bmad-method install`` to provide structured BMAD access via MCP.
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)

# IDE skill directories to search (in priority order)
_SKILL_DIRS = (".pi/skills", ".claude/skills", ".gemini/skills", ".opencode/skills")


class BMADEngine:
    """Engine for loading and executing BMAD workflows — catalog-driven."""

    def __init__(self, data_path: Path | str):
        self.data_path = Path(data_path)
        self.project_root = self._find_project_root()
        self._modules: dict[str, dict] = {}
        self._skills: dict[str, dict] = {}      # skill name → metadata + resolved paths
        self._agents: dict[str, dict] = {}
        self._catalog: list[dict[str, Any]] = []  # raw rows from bmad-help.csv
        self._load_index()

    # ------------------------------------------------------------------
    # Index loading
    # ------------------------------------------------------------------

    def _find_project_root(self) -> Path:
        """Walk upward from data_path to find project root (contains _bmad/)."""
        candidate = self.data_path
        for _ in range(5):
            if (candidate / "_bmad").exists() or (candidate / ".git").exists():
                return candidate
            candidate = candidate.parent
        return self.data_path.parent

    def _load_index(self) -> None:
        """Build index from manifests, catalog, and skill directories."""
        if not self.data_path.exists():
            logger.warning(f"BMAD data path not found: {self.data_path}")
            return

        self._load_manifests()
        self._load_catalog()
        self._resolve_skill_paths()

        logger.info(
            f"BMAD engine loaded: {len(self._modules)} modules, "
            f"{len(self._skills)} skills, {len(self._agents)} agents, "
            f"{len(self._catalog)} catalog entries"
        )

    def _load_manifests(self) -> None:
        """Load skill-manifest.csv and agent-manifest.csv from _config/."""
        config_dir = self.data_path / "_config"

        # --- Skill manifest ---
        skill_csv = config_dir / "skill-manifest.csv"
        if skill_csv.exists():
            try:
                with open(skill_csv, newline="", encoding="utf-8") as f:
                    for row in csv.DictReader(f):
                        skill_name = row.get("canonicalId", "").strip()
                        if not skill_name:
                            continue
                        self._skills[skill_name] = {
                            "name": skill_name,
                            "description": row.get("description", "").strip(),
                            "module": row.get("module", "").strip(),
                            "manifest_path": row.get("path", "").strip(),
                            "resolved_path": None,
                        }
            except Exception as exc:
                logger.warning(f"Failed to load skill manifest: {exc}")

        # --- Agent manifest ---
        agent_csv = config_dir / "agent-manifest.csv"
        if agent_csv.exists():
            try:
                with open(agent_csv, newline="", encoding="utf-8") as f:
                    for row in csv.DictReader(f):
                        agent_name = row.get("name", "").strip()
                        if not agent_name:
                            continue
                        self._agents[agent_name] = {
                            "name": agent_name,
                            "displayName": row.get("displayName", "").strip(),
                            "title": row.get("title", "").strip(),
                            "icon": row.get("icon", "").strip(),
                            "capabilities": row.get("capabilities", "").strip(),
                            "role": row.get("role", "").strip(),
                            "module": row.get("module", "").strip(),
                            "manifest_path": row.get("path", "").strip(),
                        }
            except Exception as exc:
                logger.warning(f"Failed to load agent manifest: {exc}")

        # --- Module discovery from directory structure ---
        for module_dir in self.data_path.iterdir():
            if module_dir.is_dir() and not module_dir.name.startswith("_"):
                name = module_dir.name
                self._modules.setdefault(name, {
                    "name": name,
                    "path": str(module_dir),
                    "skills": [],
                    "agents": [],
                })

        # --- Module help CSVs ---
        for mod_name, mod_info in self._modules.items():
            help_csv = self.data_path / mod_name / "module-help.csv"
            if help_csv.exists():
                try:
                    with open(help_csv, newline="", encoding="utf-8") as f:
                        for row in csv.DictReader(f):
                            skill_name = row.get("skill", row.get("canonicalId", "")).strip()
                            if skill_name and skill_name in self._skills:
                                mod_info["skills"].append(skill_name)
                except Exception:
                    pass

        # Assign skills/agents to modules based on manifest data
        for skill_name, skill_info in self._skills.items():
            mod = skill_info.get("module", "")
            if mod and mod in self._modules:
                if skill_name not in self._modules[mod]["skills"]:
                    self._modules[mod]["skills"].append(skill_name)
                    skill_info["module"] = mod

        for agent_name, agent_info in self._agents.items():
            mod = agent_info.get("module", "")
            if mod and mod in self._modules:
                if agent_name not in self._modules[mod]["agents"]:
                    self._modules[mod]["agents"].append(agent_name)

    def _load_catalog(self) -> None:
        """Load bmad-help.csv catalog for structured help and routing."""
        catalog_path = self.data_path / "_config" / "bmad-help.csv"
        if not catalog_path.exists():
            logger.warning(f"BMAD help catalog not found: {catalog_path}")
            return
        try:
            with open(catalog_path, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    self._catalog.append(row)
        except Exception as exc:
            logger.warning(f"Failed to load help catalog: {exc}")

    def _resolve_skill_paths(self) -> None:
        """Map manifest skill paths to actual files in IDE skill directories."""
        for skill_name, skill_info in self._skills.items():
            # Check each IDE skill directory
            for skill_dir_name in _SKILL_DIRS:
                candidate = self.project_root / skill_dir_name / skill_name
                skill_md = candidate / "SKILL.md"
                if skill_md.exists():
                    skill_info["resolved_path"] = str(candidate)
                    skill_info["skill_md"] = str(skill_md)
                    # Also load workflow.md if present
                    workflow_md = candidate / "workflow.md"
                    if workflow_md.exists():
                        skill_info["workflow_md"] = str(workflow_md)
                    break

            if not skill_info.get("resolved_path"):
                # Try the manifest path directly
                manifest_path = self.project_root / skill_info["manifest_path"]
                if manifest_path.exists():
                    skill_info["resolved_path"] = str(manifest_path.parent)
                    skill_info["skill_md"] = str(manifest_path)

    # ------------------------------------------------------------------
    # Skill / workflow loading
    # ------------------------------------------------------------------

    def load_skill(self, skill_name: str) -> dict[str, Any]:
        """Load a skill's SKILL.md and workflow content.

        Args:
            skill_name: Skill identifier (e.g., 'bmad-create-prd', 'bmad-help')

        Returns:
            Skill content and metadata
        """
        # Direct match
        if skill_name in self._skills:
            info = self._skills[skill_name]
            return self._read_skill_content(info)

        # Partial match
        for name, info in self._skills.items():
            if skill_name.lower() in name.lower():
                return self._read_skill_content(info)

        # Try as a skill directory that exists but isn't in the manifest
        for skill_dir_name in _SKILL_DIRS:
            candidate = self.project_root / skill_dir_name / skill_name / "SKILL.md"
            if candidate.exists():
                return {
                    "name": skill_name,
                    "skill_md": str(candidate),
                    "content": candidate.read_text(),
                }

        return {"error": f"Skill not found: {skill_name}"}

    def _read_skill_content(self, info: dict) -> dict[str, Any]:
        """Read skill content from resolved paths."""
        result = {k: v for k, v in info.items() if v}

        # Read SKILL.md
        skill_md = info.get("skill_md") or info.get("resolved_path")
        if skill_md and Path(skill_md).is_file():
            result["content"] = Path(skill_md).read_text()
        elif skill_md and Path(skill_md).is_dir():
            md_path = Path(skill_md) / "SKILL.md"
            if md_path.exists():
                result["content"] = md_path.read_text()

        # Read workflow.md
        workflow_md = info.get("workflow_md")
        if workflow_md and Path(workflow_md).exists():
            result["workflow_content"] = Path(workflow_md).read_text()

        # Read steps if available
        resolved = info.get("resolved_path")
        if resolved and Path(resolved).is_dir():
            steps = []
            for steps_dir in Path(resolved).glob("steps-*"):
                for step_file in sorted(steps_dir.glob("*.md")):
                    steps.append({
                        "name": step_file.stem,
                        "path": str(step_file),
                        "content": step_file.read_text(),
                    })
            if steps:
                result["steps"] = steps

        return result

    def load_workflow(self, module: str, path: str) -> dict[str, Any]:
        """Load workflow content by module and path.

        In v6.3.0, workflows live inside skills. This method tries to find
        the relevant skill and return its workflow.md content.
        """
        # Try to find a skill whose workflow matches the given path
        path_lower = path.lower()
        for skill_name, info in self._skills.items():
            resolved = info.get("resolved_path", "")
            if path_lower in skill_name.lower() or path_lower in resolved.lower():
                content = self._read_skill_content(info)
                if "workflow_content" in content:
                    return {
                        "id": f"{module}/{path}",
                        "module": module,
                        "path": resolved,
                        "content": content["workflow_content"],
                        "skill_name": skill_name,
                    }
                if "content" in content:
                    return {
                        "id": f"{module}/{path}",
                        "module": module,
                        "path": resolved,
                        "content": content["content"],
                        "skill_name": skill_name,
                    }

        # Fallback: try direct filesystem path
        from cohezion.mcp.servers.safe_input import sanitize_path

        try:
            candidates = [
                sanitize_path(self.data_path / module / f"{path}.md", base_dir=self.data_path),
                sanitize_path(self.data_path / module / path, base_dir=self.data_path),
            ]
        except ValueError:
            return {"error": f"Invalid workflow path: {module}/{path}"}

        for candidate in candidates:
            if candidate.exists():
                content = candidate.read_text() if candidate.is_file() else "directory"
                return {
                    "id": f"{module}/{path}",
                    "module": module,
                    "path": str(candidate),
                    "content": content,
                }

        return {"error": f"Workflow not found: {module}/{path}"}

    # ------------------------------------------------------------------
    # Agent loading
    # ------------------------------------------------------------------

    def load_agent(self, agent_id: str) -> dict[str, Any]:
        """Load agent persona by identifier."""
        # Direct match
        if agent_id in self._agents:
            return self._agents[agent_id]

        # Search by partial name
        for aid, info in self._agents.items():
            if agent_id.lower() in aid.lower():
                return info

        # Search in skill dirs (agents can also be skills)
        for skill_dir_name in _SKILL_DIRS:
            candidate = self.project_root / skill_dir_name / agent_id
            skill_md = candidate / "SKILL.md"
            if skill_md.exists():
                content = skill_md.read_text()
                return {
                    "id": agent_id,
                    "name": agent_id,
                    "content": content,
                }

        return {"error": f"Agent not found: {agent_id}"}

    def load_agent_prompt(self, agent_id: str) -> str:
        """Load agent as a prompt string."""
        agent = self.load_agent(agent_id)
        if "error" in agent:
            return f"# Error loading agent\n{agent['error']}"
        return agent.get("content", agent.get("role", ""))

    # ------------------------------------------------------------------
    # Listing
    # ------------------------------------------------------------------

    def list_modules(self) -> list[dict[str, Any]]:
        """List all available modules with counts."""
        return [
            {
                "name": name,
                "skills": len(info.get("skills", [])),
                "agents": len(info.get("agents", [])),
            }
            for name, info in self._modules.items()
        ]

    def list_skills(self, module: str | None = None) -> list[dict[str, Any]]:
        """List available skills, optionally filtered by module."""
        results = []
        for name, info in self._skills.items():
            if module and info.get("module") != module:
                continue
            results.append({
                "name": name,
                "description": info.get("description", ""),
                "module": info.get("module", ""),
                "resolved": bool(info.get("resolved_path")),
            })
        return results

    def list_workflows(
        self, module: str | None = None, phase: str | None = None
    ) -> list[dict[str, Any]]:
        """List available workflows from the catalog."""
        if not self._catalog:
            # Fallback to skills that have workflow.md
            results = []
            for name, info in self._skills.items():
                if module and info.get("module") != module:
                    continue
                if info.get("workflow_md"):
                    results.append({
                        "id": name,
                        "module": info.get("module", ""),
                        "name": name,
                    })
            return results

        results = []
        for entry in self._catalog:
            entry_module = entry.get("module", "")
            entry_phase = entry.get("phase", "")
            entry_skill = entry.get("skill", entry.get("name", ""))

            # Skip meta rows
            if entry_phase == "_meta" or entry_skill == "_meta":
                continue

            if module and entry_module.lower() != module.lower():
                continue
            if phase and entry_phase.lower() != phase.lower():
                continue

            results.append({
                "id": entry_skill or entry.get("name", ""),
                "module": entry_module,
                "name": entry.get("name", entry_skill),
                "phase": entry_phase,
                "code": entry.get("code", ""),
                "required": entry.get("required", "false").lower() == "true",
                "description": entry.get("description", ""),
            })
        return results

    def list_agents(self, module: str | None = None) -> list[dict[str, Any]]:
        """List available agents."""
        results = []
        for aid, info in self._agents.items():
            if module and info.get("module") != module:
                continue
            results.append({
                "id": aid,
                "module": info.get("module", ""),
                "name": info.get("displayName", aid),
                "title": info.get("title", ""),
                "icon": info.get("icon", ""),
                "role": info.get("role", ""),
            })
        return results

    # ------------------------------------------------------------------
    # Help & recommendations (catalog-driven)
    # ------------------------------------------------------------------

    def analyze_context(self, context: str, session: dict | None) -> dict[str, Any]:
        """Analyze user context to provide recommendations."""
        analysis: dict[str, Any] = {
            "context_length": len(context),
            "has_session": session is not None,
            "keywords": [],
            "suggested_modules": [],
            "suggested_phases": [],
        }

        context_lower = context.lower()

        # Keywords
        keywords = [
            "product", "prd", "brief", "story", "sprint", "architecture",
            "game", "test", "testing", "brainstorm", "create", "design",
            "research", "market", "domain", "technical", "code review",
            "ux", "epic", "implementation", "dev", "retrospective", "help",
        ]
        for kw in keywords:
            if kw in context_lower:
                analysis["keywords"].append(kw)

        # Module suggestions
        module_keywords = {
            "bmm": ["product", "prd", "story", "sprint", "architecture", "brief", "epic", "implementation"],
            "gds": ["game", "gdd", "playtest"],
            "cis": ["brainstorm", "creative", "innovation", "storytelling", "problem"],
            "tea": ["test", "testing", "qa", "automation", "tdd"],
            "core": ["review", "distill", "shard", "editorial", "help"],
        }
        for mod, mod_kws in module_keywords.items():
            if any(kw in context_lower for kw in mod_kws):
                analysis["suggested_modules"].append(mod)

        # Phase suggestions
        phase_keywords = {
            "1-analysis": ["research", "brainstorm", "discover", "analyze", "market", "brief"],
            "2-planning": ["prd", "plan", "ux", "design", "requirements"],
            "3-solutioning": ["architecture", "epic", "structure", "technical"],
            "4-implementation": ["sprint", "story", "dev", "code", "implement", "review"],
        }
        for phase, phase_kws in phase_keywords.items():
            if any(kw in context_lower for kw in phase_kws):
                analysis["suggested_phases"].append(phase)

        return analysis

    def get_next_steps(self, query: str, analysis: dict, session: dict | None) -> dict:
        """Get catalog-driven recommended next steps."""
        recommendations: dict[str, Any] = {
            "suggested_commands": [],
            "suggested_skills": [],
            "reasoning": "",
            "phases": {},
        }

        query_lower = query.lower()

        # Build recommendations from catalog
        for entry in self._catalog:
            phase = entry.get("phase", "")
            skill = entry.get("skill", entry.get("name", ""))
            name = entry.get("name", "")
            is_required = entry.get("required", "false").lower() == "true"
            desc = entry.get("description", "")

            if phase == "_meta" or skill == "_meta":
                continue

            # Match against query keywords
            match_terms = f"{name} {skill} {desc}".lower()
            if any(kw in match_terms for kw in query_lower.split() if len(kw) > 2):
                recommendations["suggested_skills"].append({
                    "skill": skill,
                    "name": name,
                    "phase": phase,
                    "required": is_required,
                    "description": desc[:80],
                })

        # General help pattern
        if any(kw in query_lower for kw in ["what should i do", "next", "help", "start", "begin"]):
            # Return the first required skill from each phase
            for entry in self._catalog:
                phase = entry.get("phase", "")
                skill = entry.get("skill", entry.get("name", ""))
                name = entry.get("name", "")
                is_required = entry.get("required", "false").lower() == "true"
                desc = entry.get("description", "")

                if phase == "_meta" or skill == "_meta":
                    continue

                if phase not in recommendations["phases"]:
                    recommendations["phases"][phase] = []
                recommendations["phases"][phase].append({
                    "skill": skill,
                    "name": name,
                    "code": entry.get("code", ""),
                    "required": is_required,
                    "description": desc[:80],
                })

            recommendations["reasoning"] = (
                "Here's the BMad Method workflow. Follow the phases in order, "
                "starting with analysis. Required items must complete before moving on."
            )
            recommendations["suggested_commands"] = [
                "bmad_help",
                "bmad_list_workflows",
                "bmad_list_agents",
            ]

        # Fallback
        if not recommendations["suggested_skills"] and not recommendations["phases"]:
            # Default first steps
            first_steps = [e for e in self._catalog
                          if e.get("phase", "").startswith("1-") or e.get("phase") == "anytime"]
            for entry in first_steps[:5]:
                skill = entry.get("skill", entry.get("name", ""))
                name = entry.get("name", "")
                recommendations["suggested_skills"].append({
                    "skill": skill,
                    "name": name,
                    "phase": entry.get("phase", ""),
                    "description": entry.get("description", "")[:80],
                })
            recommendations["reasoning"] = "Start with analysis-phase or anytime skills."
            recommendations["suggested_commands"] = ["bmad_help", "bmad_list_workflows"]

        return recommendations

    # ------------------------------------------------------------------
    # Workflow execution (placeholder)
    # ------------------------------------------------------------------

    async def execute_workflow(
        self, workflow: dict[str, Any], params: dict[str, Any], session_id: str | None
    ) -> dict[str, Any]:
        """Execute a workflow with given parameters.

        This returns the workflow content and steps for the agent to follow.
        Actual execution happens through the AI agent interpreting the steps.
        """
        workflow_id = workflow.get("id", "unknown")
        parts = workflow_id.split("/")
        workflow_name = parts[-1] if len(parts) > 1 else workflow_id

        result: dict[str, Any] = {
            "workflow": workflow_id,
            "params": params,
            "session_id": session_id,
            "status": "loaded",
            "output": f"Workflow '{workflow_name}' loaded — follow the steps to execute.",
        }

        # If the workflow has content, include it
        if "content" in workflow:
            result["workflow_content"] = workflow["content"]

        # Add specific guidance based on workflow type
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

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

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
