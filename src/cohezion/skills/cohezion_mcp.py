#!/usr/bin/env python3
"""Cohezion MCP Server (skills + workflows over JSON-RPC stdio).

The class ``CohezionMCP`` is a thin façade over four focused tool modules:

* :mod:`cohezion.skills.mcp_inference_tools` (OCR, coding, compound, TTS)
* :mod:`cohezion.skills.mcp_model_tools` (model selection, benchmarks, vitals)
* :mod:`cohezion.skills.mcp_reliability_tools` (claim resolution, offload)
* :mod:`cohezion.skills.mcp_skill_tools` (skill exec, memory, scout)

Tool descriptors live in :mod:`cohezion.skills.mcp_tool_definitions`; path
resolution lives in :mod:`cohezion.skills.mcp_paths`.

Public API (``list_tools``, ``call_tool``, every individual tool method,
``run``) is preserved verbatim — this is a structure-only refactor.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any


# Add project root to path to allow importing cohezion modules
project_root = os.environ.get("COHEZION_ROOT", "/home/mike-anderson/dev/cohezion") + "/src"
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from cohezion.skills import (
    mcp_inference_tools,
    mcp_model_tools,
    mcp_reliability_tools,
    mcp_skill_tools,
)
from cohezion.skills.mcp_paths import (
    compound_config_path,
    knowledge_graph_path,
    load_json,
    model_registry_path,
    skill_registry_path,
    workflow_registry_path,
)
from cohezion.skills.mcp_tool_definitions import build_tool_list


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


class CohezionMCP:
    """Stdio JSON-RPC server exposing Cohezion skills, workflows, and tools.

    Holds the parsed registries (skills/workflows/models/compound config) and
    the optional reliability singletons (monitor/resolver/offloader). Each
    tool method delegates to a function in the per-responsibility modules.
    """

    def __init__(self):
        """Load all registries and instantiate available reliability helpers."""
        self.skill_registry_path = skill_registry_path()
        self.workflow_registry_path = workflow_registry_path()
        self.knowledge_graph_path = knowledge_graph_path()
        self.model_registry_path = model_registry_path()
        self.compound_config_path = compound_config_path()

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
        """Generic JSON loader with comment stripping (delegates to ``mcp_paths``)."""
        return load_json(path)

    # ------------------------------------------------------------------ tools

    def list_tools(self) -> list[dict[str, Any]]:
        """Return the full ``tools/list`` payload (built-ins + skills)."""
        return build_tool_list(self.skills)

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Dispatch a single ``tools/call`` request to the right handler.

        Skill-derived tools are matched via the ``skill_<id>`` prefix and
        looked up case-insensitively in the registry.
        """
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
            return self.offload_task(arguments.get("query", ""), arguments.get("system_prompt"))
        elif name.startswith("skill_"):
            skill_id = name.replace("skill_", "").upper()
            # Try to find the exact case match in self.skills
            match = next((s for s in self.skills if s.lower() == skill_id.lower()), None)
            if match:
                inputs = arguments.get("inputs", {})
                return self.execute_skill(match, inputs)

        raise ValueError(f"Unknown tool: {name}")

    # ---------------------------------------------------- inference delegates

    def elite_ocr_analysis(self, args: dict[str, Any]) -> dict[str, Any]:
        """Elite OCR analysis using GLM-OCR with advanced document understanding."""
        return mcp_inference_tools.elite_ocr_analysis(args)

    def agentic_coding_workflow(self, args: dict[str, Any]) -> dict[str, Any]:
        """Agentic coding workflow using Qwen3-Coder-Next with elite performance."""
        return mcp_inference_tools.agentic_coding_workflow(args)

    def compound_engineering_orchestrator(self, args: dict[str, Any]) -> dict[str, Any]:
        """Orchestrate compound engineering workflows with elite models."""
        return mcp_inference_tools.compound_engineering_orchestrator(args)

    def pocket_tts_generate(self, args: dict[str, Any]) -> dict[str, Any]:
        """Generate speech using Kyutai Pocket TTS."""
        return mcp_inference_tools.pocket_tts_generate(args)

    # -------------------------------------------------------- model delegates

    def elite_model_selection(self, args: dict[str, Any]) -> dict[str, Any]:
        """Elite model selection with MoE awareness and memory optimization."""
        return mcp_model_tools.elite_model_selection(args, self.model_registry)

    def performance_benchmark(self, args: dict[str, Any]) -> dict[str, Any]:
        """Benchmark elite models and generate performance reports."""
        return mcp_model_tools.performance_benchmark(args)

    def get_compound_config(self) -> dict[str, Any]:
        """Return compound config + model registry + live system vitals."""
        return mcp_model_tools.get_compound_config(
            self.compound_config, self.model_registry, self.monitor
        )

    def select_model(self, task_type: str, complexity: int, context_needs: int) -> dict[str, Any]:
        """Pick a registry model that matches ``task_type`` and is installed."""
        return mcp_model_tools.select_model(
            task_type, complexity, context_needs, self.model_registry
        )

    # -------------------------------------------------- reliability delegates

    def resolve_claims(self, text: str) -> dict[str, Any]:
        """Verify claims in ``text`` against the hallucination resolver."""
        return mcp_reliability_tools.resolve_claims(text, self.resolver)

    def offload_task(self, query: str, system_prompt: str | None = None) -> dict[str, Any]:
        """Offload ``query`` to a local SLM via the harness/offloader pair."""
        return mcp_reliability_tools.offload_task(
            query, system_prompt, self.offloader, ContextHarness
        )

    def batch_offload(
        self, tasks: list[dict[str, Any]], model: str | None = None
    ) -> dict[str, Any]:
        """Bundle several SLM tasks into a single Ollama call."""
        return mcp_reliability_tools.batch_offload(tasks, model)

    def inspect_cache(self) -> dict[str, Any]:
        """Return semantic cache hit-rate and population statistics."""
        return mcp_reliability_tools.inspect_cache()

    # -------------------------------------------------------- skill delegates

    def execute_skill(self, skill_name: str, inputs: dict[str, Any]) -> dict[str, Any]:
        """Read a registered skill file by ID and return its source contents."""
        return mcp_skill_tools.execute_skill(skill_name, inputs, self.skills)

    def get_truth_anchors(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Return the verified hardware/system context block for grounding."""
        return mcp_skill_tools.get_truth_anchors(arguments)

    def remember_fact(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Persist a fact into long-term semantic memory."""
        return mcp_skill_tools.remember_fact(arguments)

    def recall_context(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Search semantic memory for relevant context."""
        return mcp_skill_tools.recall_context(arguments)

    def daily_scout_research(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Trigger the Daily Scout agent and return filtered SLM proposals."""
        return mcp_skill_tools.daily_scout_research(arguments)

    # ----------------------------------------------------------- JSON-RPC run

    def run(self):
        """Standard MCP JSON-RPC loop over stdin/stdout (blocking)."""
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
                        # MCP tool dispatch must report back any error as JSON-RPC error code,
                        # otherwise the client sees a hung connection. SystemExit/KeyboardInterrupt
                        # still propagate (they don't inherit Exception).
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
                # Top-level JSON-RPC loop must survive malformed input or downstream errors;
                # log to stderr and keep reading the next request. SystemExit propagates.
                sys.stderr.write(f"Error in JSON-RPC loop: {e}\n")


if __name__ == "__main__":
    mcp = CohezionMCP()
    mcp.run()
