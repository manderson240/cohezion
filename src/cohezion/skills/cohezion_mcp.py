#!/usr/bin/env python3
"""
Cohezion MCP Server for Skills and Workflows Integration
Implements standard MCP JSON-RPC protocol over stdio.
"""

import json
import os
import sys
from typing import Any

from cohezion.skills.mcp_tool_handlers import ToolHandlersMixin
from cohezion.skills.mcp_tool_schemas import BASE_TOOL_SCHEMAS


project_root = (
    os.environ.get("COHEZION_ROOT", "/home/mike-anderson/dev/cohezion") + "/src"
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from cohezion.reliability.monitor import ResourceMonitor
except ImportError:
    ResourceMonitor = None

try:
    from cohezion.reliability.resolver import HallucinationResolver
except ImportError:
    HallucinationResolver = None

try:
    from cohezion.reliability.context_harness import ContextHarness
    from cohezion.reliability.offload_manager import OffloadManager
except ImportError:
    OffloadManager = None
    ContextHarness = None


class CohezionMCP(ToolHandlersMixin):
    def __init__(self):
        self.skill_registry_path = (
            os.environ.get("COHEZION_ROOT", "/home/mike-anderson/dev/cohezion")
            + "/src/cohezion/registry/skill_registry.json"
        )
        self.workflow_registry_path = (
            os.environ.get("COHEZION_ROOT", "/home/mike-anderson/dev/cohezion")
            + "/src/cohezion/registry/workflow_registry.json"
        )
        _root = os.environ.get("COHEZION_ROOT", "/home/mike-anderson/dev/cohezion")
        self.knowledge_graph_path = _root + "/src/cohezion/knowledge_graph"
        self.model_registry_path = _root + "/model_registry.json"
        self.compound_config_path = os.path.join(
            os.path.expanduser("~"),
            ".config/opencode/compound_engineering.json",
        )

        self.skills = self._load_json(self.skill_registry_path)
        self.workflows = self._load_json(self.workflow_registry_path)
        self.model_registry = self._load_json(self.model_registry_path)
        self.compound_config = self._load_json(self.compound_config_path)

        if ResourceMonitor:
            self.monitor = ResourceMonitor()
        else:
            self.monitor = None

        if HallucinationResolver:
            self.resolver = HallucinationResolver()
        else:
            self.resolver = None

        if OffloadManager:
            self.offloader = OffloadManager()
        else:
            self.offloader = None

    def _load_json(self, path: str) -> dict[str, Any]:
        """Generic JSON loader with comment stripping"""
        try:
            if not os.path.exists(path):
                return {}
            with open(path) as f:
                content = f.read()
                lines = content.splitlines()
                clean_lines = [
                    line for line in lines if not line.strip().startswith(("#", "//"))
                ]
                return json.loads("\n".join(clean_lines))
        except Exception as e:
            sys.stderr.write(f"Error loading {path}: {e}\n")
            return {}

    def list_tools(self) -> list[dict[str, Any]]:
        base_tools = BASE_TOOL_SCHEMAS.copy()

        for skill_id, skill_info in self.skills.items():
            base_tools.append(
                {
                    "name": f"skill_{skill_id.lower()}",
                    "description": (
                        f"Execute skill: {skill_info.get('description', skill_id)}"
                    ),
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "inputs": {
                                "type": "object",
                                "description": "Optional inputs for the skill",
                            }
                        },
                    },
                }
            )

        return base_tools

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "elite_ocr_analysis":
            return self.elite_ocr_analysis(arguments)
        elif name == "agentic_coding_workflow":
            return self.agentic_coding_workflow(arguments)
        elif name == "compound_engineering_orchestrator":
            return self.compound_engineering_orchestrator(arguments)
        elif name == "get_compound_config":
            return self.get_compound_config()
        elif name == "elite_model_selection":
            return self.elite_model_selection(arguments)
        elif name == "performance_benchmark":
            return self.performance_benchmark(arguments)
        elif name == "resolve_claims":
            text = arguments.get("text", "")
            return self.resolve_claims(text)
        elif name == "get_truth_anchors":
            return self.get_truth_anchors(arguments)
        elif name == "remember_fact":
            return self.remember_fact(arguments)
        elif name == "recall_context":
            return self.recall_context(arguments)
        elif name == "daily_scout_research":
            return self.daily_scout_research(arguments)
        elif name == "offload_task":
            return self.offload_task(
                arguments.get("query", ""), arguments.get("system_prompt")
            )
        elif name.startswith("skill_"):
            skill_id = name.replace("skill_", "").upper()
            match = next(
                (s for s in self.skills if s.lower() == skill_id.lower()), None
            )
            if match:
                inputs = arguments.get("inputs", {})
                return self.execute_skill(match, inputs)

        raise ValueError(f"Unknown tool: {name}")

    def run(self):
        """Standard MCP JSON-RPC loop"""
        for line in sys.stdin:
            try:
                request = json.loads(line)
                if request.get("method") == "initialize":
                    print(
                        json.dumps(
                            {
                                "jsonrpc": "2.0",
                                "id": request.get("id"),
                                "result": {
                                    "capabilities": {"tools": {}},
                                    "serverInfo": {
                                        "name": "cohezion-bridge",
                                        "version": "1.0.0",
                                    },
                                },
                            }
                        )
                    )
                elif request.get("method") == "tools/list":
                    print(
                        json.dumps(
                            {
                                "jsonrpc": "2.0",
                                "id": request.get("id"),
                                "result": {"tools": self.list_tools()},
                            }
                        )
                    )
                elif request.get("method") == "tools/call":
                    params = request.get("params", {})
                    name = params.get("name")
                    args = params.get("arguments", {})
                    try:
                        result = self.call_tool(name, args)
                        print(
                            json.dumps(
                                {
                                    "jsonrpc": "2.0",
                                    "id": request.get("id"),
                                    "result": result,
                                }
                            )
                        )
                    except Exception as e:
                        print(
                            json.dumps(
                                {
                                    "jsonrpc": "2.0",
                                    "id": request.get("id"),
                                    "error": {"code": -32000, "message": str(e)},
                                }
                            )
                        )
                sys.stdout.flush()
            except Exception as e:
                sys.stderr.write(f"Error in JSON-RPC loop: {e}\n")


if __name__ == "__main__":
    mcp = CohezionMCP()
    mcp.run()
