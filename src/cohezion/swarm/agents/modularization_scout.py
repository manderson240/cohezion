"""
Modularization Scout Agent: Analyzes codebase for modularization boundaries and unused code.
"""

import logging
import ast
import re
from typing import Any, Dict, List, Set
from pathlib import Path

from cohezion.agents.base import BaseAgent
from cohezion.swarm.swarm_types import SwarmConfig
from cohezion.healing.deep_audit import CodeIssue

logger = logging.getLogger(__name__)

class ModularizationScoutAgent(BaseAgent):
    """
    An agent that scouts for modularization opportunities and unused code.
    Identifies high-coupling points and dead weight.
    """

    def __init__(self, config: SwarmConfig | None = None):
        # Using phi3:mini for efficient cross-file analysis in verification mode
        super().__init__(model_name="phi3:mini", config=config)

    async def analysis_dependencies(self, directory: str) -> Dict[str, Any]:
        """
        Maps dependencies across a directory to identify service boundaries.
        """
        logger.info(f"🗺️ [SCOUT] Mapping dependencies in {directory}")
        
        # 1. Start Journey
        journey = await self._universe.start_journey(
            agent_name=self.__class__.__name__,
            intent=f"Map service boundaries in {directory}"
        )

        # 2. Extract Imports (Manual AST)
        dep_map = {}
        for py_file in Path(directory).rglob("*.py"):
            try:
                content = py_file.read_text()
                tree = ast.parse(content)
                imports = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        imports.append(f"{node.module}.{node.names[0].name}" if node.module else node.names[0].name)
                
                rel_path = str(py_file.relative_to(directory))
                dep_map[rel_path] = imports
            except Exception as e:
                logger.error(f"Failed to parse {py_file}: {e}")

        # 3. Analyze with LLM
        prompt = f"""
I have mapped the following dependencies for the directory '{directory}':
{json.dumps(dep_map, indent=2)}

TASK:
1. Identify natural clusters of files that should be grouped into discrete services.
2. Highlight circular dependencies or "God objects" that prevent modularization.
3. Propose a service-oriented structure (e.g., 'agents', 'core', 'universe').

Output your analysis in JSON format:
{{
  "clusters": [
    {{ "service_name": "...", "files": ["...", "..."], "justification": "..." }}
  ],
  "bottlenecks": [
    {{ "file": "...", "issue": "...", "impact": "..." }}
  ],
  "proposed_structure": {{ ... }}
}}
"""
        response = await self._call_ollama(
            prompt=prompt,
            system_prompt="You are a senior system architect in the Cohezion swarm. Focus on decoupling and scalability.",
            task_type="light-reasoning"
        )

        # 4. Evolve and Precipitate
        await self._universe.evolve_trajectory(journey, "dependency_mapped", str(response))
        precipitation = await self._universe.precipitate_reality(
            journey,
            outputs={"dependency_map": dep_map, "architect_review": str(response)},
            phi_score=response.phi_score
        )
        
        return precipitation

    async def find_unused_methods(self, file_path: str) -> Dict[str, Any]:
        """
        Identifies potentially unused methods in a file.
        """
        logger.info(f"🧹 [SCOUT] Hunting for dead code in {file_path}")
        
        content = Path(file_path).read_text()
        tree = ast.parse(content)
        
        # Find all local definitions
        def_nodes = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        methods = {node.name: node.lineno for node in def_nodes}
        
        # Heuristic: Grep repo for usages of these method names
        # (This is a rough check, meant for LLM to confirm)
        prompt = f"""
FILE CONTENT of '{file_path}':
{content}

LOCALLY DEFINED METHODS:
{list(methods.keys())}

TASK:
1. Analyze the file content.
2. Based on your knowledge of the Cohezion codebase and common patterns, identify which of these methods are likely UNUSED or REDUNDANT (e.g., helpers that are never called).
3. Specifically check for methods like 'quantize_q4_k' or stubs.

Output JSON:
{{
  "unused_methods": [
    {{ "name": "...", "line": ..., "reason": "..." }}
  ],
  "confidence": 0.0-1.0
}}
"""
        response = await self._call_ollama(
            prompt=prompt,
            system_prompt="You are a code cleanup specialist. Identify dead weight to be pruned.",
            task_type="light-reasoning"
        )

        return {"analysis": str(response), "file": file_path}
