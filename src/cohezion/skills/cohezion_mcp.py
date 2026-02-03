#!/usr/bin/env python3
"""
Cohezion MCP Server for Skills and Workflows Integration
Implements standard MCP JSON-RPC protocol over stdio.
"""

import json
import os
import sys
from typing import Dict, Any, List, Optional
from pathlib import Path

# Add project root to path to allow importing cohezion modules
project_root = os.environ.get("COHEZION_ROOT", "/home/mike-anderson/dev/cohezion") + "/src"
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
    from cohezion.reliability.offload_manager import OffloadManager
    from cohezion.reliability.context_harness import ContextHarness
except ImportError:
    OffloadManager = None
    ContextHarness = None


class CohezionMCP:
    def __init__(self):
        self.skill_registry_path = (
            os.environ.get("COHEZION_ROOT", "/home/mike-anderson/dev/cohezion") + "/src/cohezion/registry/skill_registry.json"
        )
        self.workflow_registry_path = os.environ.get("COHEZION_ROOT", "/home/mike-anderson/dev/cohezion") + "/src/cohezion/registry/workflow_registry.json"
        self.knowledge_graph_path = (
            "/home/mike-anderson/dev/cohezion/src/cohezion/knowledge_graph"
        )
        self.model_registry_path = os.environ.get("COHEZION_ROOT", "/home/mike-anderson/dev/cohezion") + "/model_registry.json"
        self.compound_config_path = "/home/mike-anderson/.config/opencode/compound_engineering.json"

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

    def _load_json(self, path: str) -> Dict[str, Any]:
        """Generic JSON loader with comment stripping"""
        try:
            if not os.path.exists(path):
                return {}
            with open(path, "r") as f:
                content = f.read()
                # Simple comment stripping
                lines = content.splitlines()
                clean_lines = [l for l in lines if not l.strip().startswith(("#", "//"))]
                return json.loads("\n".join(clean_lines))
        except Exception as e:
            sys.stderr.write(f"Error loading {path}: {e}\n")
            return {}

    def list_tools(self) -> List[Dict[str, Any]]:
        base_tools = [
            {
                "name": "get_compound_config",
                "description": "Get unified compound engineering settings, model registry, and system vitals",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "model_selection",
                "description": "Select optimal model based on task requirements",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_type": {"type": "string"},
                        "complexity": {"type": "number"},
                        "context_needs": {"type": "number"}
                    },
                    "required": ["task_type"]
                }
            },
            {
                "name": "resolve_claims",
                "description": "Verify text claims against ground truth and known hallucinations",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "The text containing claims to verify"}
                    },
                    "required": ["text"]
                }
            },
            {
                "name": "get_truth_anchors",
                "description": "Get concise verified system facts for context grounding",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "offload_task",
                "description": "Offload a menial/support task to a local SLM with a context harness",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The task query to offload"},
                        "system_prompt": {"type": "string", "description": "Optional system instructions"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "batch_offload",
                "description": "Consolidate and execute multiple menial tasks in a single local SLM call",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "tasks": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "query": {"type": "string"},
                                    "context": {"type": "string"}
                                },
                                "required": ["id", "query"]
                            }
                        },
                        "model": {"type": "string", "description": "Target local model"}
                    },
                    "required": ["tasks"]
                }
            },
            {
                "name": "inspect_cache",
                "description": "Get semantic cache statistics and hit rates",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]
        
        # Dynamically add skills as tools
        for skill_id, skill_info in self.skills.items():
            base_tools.append({
                "name": f"skill_{skill_id.lower()}",
                "description": f"Execute skill: {skill_info.get('description', skill_id)}",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "inputs": {"type": "object", "description": "Optional inputs for the skill"}
                    }
                }
            })
            
        return base_tools

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if name == "get_compound_config":
            return self.get_compound_config()
        elif name == "model_selection":
            task_type = arguments.get("task_type", "coding")
            complexity = arguments.get("complexity", 5)
            context_needs = arguments.get("context_needs", 10000)
            return self.select_model(task_type, complexity, context_needs)
        elif name == "resolve_claims":
            text = arguments.get("text", "")
            return self.resolve_claims(text)
        elif name == "get_truth_anchors":
            return self.get_truth_anchors()
        elif name == "offload_task":
            query = arguments.get("query", "")
            system_prompt = arguments.get("system_prompt")
            return self.offload_task(query, system_prompt)
        elif name == "batch_offload":
            tasks = arguments.get("tasks", [])
            model = arguments.get("model")
            return self.batch_offload(tasks, model)
        elif name == "inspect_cache":
            return self.inspect_cache()
        elif name.startswith("skill_"):
            skill_id = name.replace("skill_", "").upper()
            # Try to find the exact case match in self.skills
            match = next((s for s in self.skills if s.lower() == skill_id.lower()), None)
            if match:
                inputs = arguments.get("inputs", {})
                return self.execute_skill(match, inputs)
            
        raise ValueError(f"Unknown tool: {name}")

    def resolve_claims(self, text: str) -> Dict[str, Any]:
        if not self.resolver:
            return {"content": [{"type": "text", "text": "Error: HallucinationResolver not available"}]}
        res = self.resolver.resolve_claims(text)
        return {"content": [{"type": "text", "text": json.dumps(res, indent=2)}]}

    def get_truth_anchors(self) -> Dict[str, Any]:
        if not self.resolver:
            return {"content": [{"type": "text", "text": "Error: HallucinationResolver not available"}]}
        anchors = self.resolver.get_truth_anchors()
        return {"content": [{"type": "text", "text": anchors}]}

    def offload_task(self, query: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        if not self.offloader:
            return {"content": [{"type": "text", "text": "Error: OffloadManager not available"}]}
            
        recommendation = self.offloader.get_offload_recommendation(query)
        if not recommendation["offload"]:
             return {"content": [{"type": "text", "text": "Task unsuitable for local offload (too complex or critical)."}]}
             
        target_model = recommendation["target"]
        harness = ContextHarness(target_model=target_model)
        payload = harness.harness_prompt(query, system_prompt)
        
        # Execute via Ollama API using curl for robustness
        try:
            import subprocess
            payload_json = json.dumps({
                "model": target_model,
                "prompt": payload["prompt"],
                "system": payload["system"],
                "stream": False
            })
            cmd = ["curl", "-s", "-X", "POST", "http://localhost:11434/api/generate", "-d", payload_json]
            
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                
                return {"content": [{"type": "text", "text": f"Curl failed: {res.stderr}"}]}
            
            
            res_text = res_json.get("response", "")
            return {"content": [{"type": "text", "text": res_text}]}
        except Exception as e:
            return {"content": [{"type": "text", "text": f"Offload execution failed: {e}"}]}

    def batch_offload(self, tasks: List[Dict[str, Any]], model: Optional[str] = None) -> Dict[str, Any]:
        from cohezion.reliability.batch_manager import BatchManager
        from cohezion.reliability.context_harness import ContextHarness
        
        target_model = model or "phi4"
        batch_mgr = BatchManager()
        for t in tasks:
            batch_mgr.enqueue(t["id"], t["query"], t.get("context"))
            
        batch = batch_mgr.get_batch()
        if not batch:
             return {"content": [{"type": "text", "text": "No tasks to batch."}]}
             
        harness = ContextHarness(target_model=target_model)
        payload = harness.harness_prompt(batch["prompt"])
        
        try:
            import subprocess
            payload_json = json.dumps({
                "model": target_model,
                "prompt": payload["prompt"],
                "system": payload["system"],
                "stream": False
            })
            cmd = ["curl", "-s", "-X", "POST", "http://localhost:11434/api/generate", "-d", payload_json]
            res = subprocess.run(cmd, capture_output=True, text=True)
            res_json = json.loads(res.stdout)
            res_text = res_json.get("response", "")
            
            results = batch_mgr.parse_batch_response(res_text)
            return {"content": [{"type": "text", "text": json.dumps(results, indent=2)}]}
        except Exception as e:
            return {"content": [{"type": "text", "text": f"Batch offload failed: {e}"}]}

    def inspect_cache(self) -> Dict[str, Any]:
        from cohezion.reliability.semantic_cache import SemanticCache
        # Using a default instance for inspection
        cache = SemanticCache()
        stats = cache.get_stats()
        return {"content": [{"type": "text", "text": json.dumps(stats, indent=2)}]}

    def execute_skill(self, skill_name: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        if skill_name not in self.skills:
            return {"content": [{"type": "text", "text": f"Error: Skill '{skill_name}' not found"}]}
        skill = self.skills[skill_name]
        skill_path_rel = skill.get("path")
        if not skill_path_rel:
             return {"content": [{"type": "text", "text": f"Error: Skill path missing for '{skill_name}'"}]}
             
        skill_path = os.path.join(os.environ.get("COHEZION_ROOT", "/home/mike-anderson/dev/cohezion"), skill_path_rel)
        if not os.path.exists(skill_path):
            return {"content": [{"type": "text", "text": f"Error: Skill file not found: {skill_path}"}]}
        try:
            with open(skill_path, "r") as f:
                return {"content": [{"type": "text", "text": f.read()}]}
        except Exception as e:
            return {"content": [{"type": "text", "text": f"Error executing skill: {e}"}]}

    def get_compound_config(self) -> Dict[str, Any]:
        vitals = self.monitor.get_vitals() if self.monitor else {"status": "monitor_not_available"}
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "config": self.compound_config,
                        "models": self.model_registry.get("models", {}),
                        "vitals": vitals
                    }, indent=2)
                }
            ]
        }

    def select_model(self, task_type: str, complexity: int, context_needs: int) -> Dict[str, Any]:
        models = self.model_registry.get("models", {})
        
        # Pre-flight check: which models are actually in Ollama?
        installed_models = set()
        try:
            import subprocess
            res = subprocess.run(["ollama", "list"], capture_output=True, text=True)
            for line in res.stdout.splitlines()[1:]:  # Skip header
                if line.strip():
                    installed_models.add(line.split()[0].split(":")[0])  # Base name
        except Exception as e:
            sys.stderr.write(f"Failed to check installed models: {e}\n")

        # Filter candidates by specialization AND installation status
        candidates = []
        for m_id, m_info in models.items():
            if m_info.get("specialization") == task_type:
                if m_id in installed_models:
                    candidates.append((m_id, m_info))
                else:
                    sys.stderr.write(f"Warning: Specialist model {m_id} not installed in Ollama.\n")

        if candidates:
            candidates.sort(key=lambda x: x[1].get("priority", 99))
            recommended = candidates[0][0]
        else:
            # Fallback to the most capable installed model
            fallback_order = ["qwen3-coder-256k", "gpt-oss-256k", "phi4-256k", "phi4-mini"]
            recommended = next((m for m in fallback_order if m in installed_models), "phi4-mini")
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "recommended_model": f"{recommended}:latest",
                        "all_models": [f"{m}:latest" for m in models.keys()],
                        "installed_only": list(installed_models)
                    }, indent=2)
                }
            ]
        }

    def run(self):
        """Standard MCP JSON-RPC loop"""
        for line in sys.stdin:
            try:
                request = json.loads(line)
                if request.get("method") == "initialize":
                    print(json.dumps({
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "result": {
                            "capabilities": {"tools": {}},
                            "serverInfo": {"name": "cohezion-bridge", "version": "1.0.0"}
                        }
                    }))
                elif request.get("method") == "tools/list":
                    print(json.dumps({
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "result": {"tools": self.list_tools()}
                    }))
                elif request.get("method") == "tools/call":
                    params = request.get("params", {})
                    name = params.get("name")
                    args = params.get("arguments", {})
                    try:
                        result = self.call_tool(name, args)
                        print(json.dumps({
                            "jsonrpc": "2.0",
                            "id": request.get("id"),
                            "result": result
                        }))
                    except Exception as e:
                        print(json.dumps({
                            "jsonrpc": "2.0",
                            "id": request.get("id"),
                            "error": {"code": -32000, "message": str(e)}
                        }))
                sys.stdout.flush()
            except Exception as e:
                sys.stderr.write(f"Error in JSON-RPC loop: {e}\n")


if __name__ == "__main__":
    mcp = CohezionMCP()
    mcp.run()
