"""Static MCP tool descriptors exposed by the Cohezion bridge.

``BASE_TOOLS`` is the canonical JSON-schema list returned by ``tools/list``
for the built-in (non skill-derived) tools. Skill-derived tools are appended
dynamically by :func:`build_tool_list`.

Keeping the descriptors in one data-only module lets the dispatch layer
(``cohezion_mcp.py``) stay focused on routing instead of schema authoring.
"""

from __future__ import annotations

from typing import Any


BASE_TOOLS: list[dict[str, Any]] = [
    {
        "name": "elite_ocr_analysis",
        "description": (
            "State-of-the-art OCR with GLM-OCR (94.62% OmniDocBench accuracy) "
            "for complex document understanding"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "Path to image file for OCR processing",
                },
                "analysis_type": {
                    "type": "string",
                    "enum": [
                        "text-recognition",
                        "table-recognition",
                        "formula-recognition",
                        "document-analysis",
                        "handwriting",
                    ],
                    "description": "Type of OCR analysis to perform",
                    "default": "document-analysis",
                },
                "output_format": {
                    "type": "string",
                    "enum": ["structured", "plain-text", "json", "markdown"],
                    "description": "Output format for OCR results",
                    "default": "structured",
                },
            },
            "required": ["image_path"],
        },
    },
    {
        "name": "agentic_coding_workflow",
        "description": (
            "Elite coding workflow with Qwen3-Coder-Next (70.6% SWE-Bench) "
            "for complex software engineering tasks"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_description": {
                    "type": "string",
                    "description": "Detailed description of coding task",
                },
                "complexity_level": {
                    "type": "string",
                    "enum": ["simple", "medium", "complex", "enterprise"],
                    "description": "Complexity level for optimal model selection",
                    "default": "medium",
                },
                "language": {
                    "type": "string",
                    "description": "Programming language/framework",
                },
                "context_files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Relevant source code files for context",
                },
                "output_type": {
                    "type": "string",
                    "enum": [
                        "code-only",
                        "with-explanation",
                        "with-tests",
                        "full-solution",
                    ],
                    "description": "Type of output to generate",
                    "default": "full-solution",
                },
            },
            "required": ["task_description"],
        },
    },
    {
        "name": "compound_engineering_orchestrator",
        "description": (
            "Orchestrate compound engineering workflows using elite models "
            "with optimal resource allocation"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "workflow_type": {
                    "type": "string",
                    "enum": [
                        "enterprise-ai-development",
                        "autonomous-agent-creation",
                        "document-driven-coding",
                        "mathematical-system-design",
                    ],
                    "description": "Predefined compound engineering workflow template",
                },
                "primary_task": {
                    "type": "string",
                    "description": "Main task to accomplish",
                },
                "sub_tasks": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Sub-tasks for compound workflow",
                },
                "resource_constraints": {
                    "type": "object",
                    "properties": {
                        "max_memory_gb": {"type": "number"},
                        "time_limit_minutes": {"type": "number"},
                        "priority_level": {
                            "type": "string",
                            "enum": ["low", "medium", "high", "critical"],
                        },
                    },
                },
            },
            "required": ["workflow_type", "primary_task"],
        },
    },
    {
        "name": "get_compound_config",
        "description": (
            "Get unified compound engineering settings, model registry, and system vitals"
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "elite_model_selection",
        "description": (
            "Select optimal elite model with MoE awareness and memory optimization for v0.15.5-rc2"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_type": {
                    "type": "string",
                    "enum": [
                        "elite-coding",
                        "agentic-coding",
                        "ocr-vision",
                        "coding",
                        "vision",
                        "reasoning",
                        "general",
                    ],
                    "description": "Type of task requiring model selection",
                },
                "memory_available": {
                    "type": "number",
                    "description": "Available system memory in GB",
                },
                "context_needs": {
                    "type": "number",
                    "description": "Required context window size",
                },
                "performance_priority": {
                    "type": "string",
                    "enum": [
                        "speed",
                        "accuracy",
                        "memory-efficiency",
                        "balanced",
                    ],
                    "description": "Performance optimization priority",
                    "default": "balanced",
                },
            },
            "required": ["task_type"],
        },
    },
    {
        "name": "performance_benchmark",
        "description": "Benchmark elite models and generate performance reports for optimization",
        "inputSchema": {
            "type": "object",
            "properties": {
                "models": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Models to benchmark (default: all elite models)",
                },
                "benchmark_types": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "inference-speed",
                            "memory-usage",
                            "accuracy",
                            "token-efficiency",
                        ],
                    },
                    "description": "Types of benchmarks to run",
                    "default": ["inference-speed", "memory-usage"],
                },
                "iterations": {
                    "type": "number",
                    "description": "Number of test iterations",
                    "default": 3,
                },
            },
        },
    },
    {
        "name": "resolve_claims",
        "description": "Verify text claims against ground truth and known hallucinations",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text containing claims to verify",
                }
            },
            "required": ["text"],
        },
    },
    {
        "name": "get_truth_anchors",
        "description": "Get concise verified system facts for context grounding",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "offload_task",
        "description": "Offload a menial/support task to a local SLM with a context harness",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The task query to offload",
                },
                "system_prompt": {
                    "type": "string",
                    "description": "Optional system instructions",
                },
                "model": {
                    "type": "string",
                    "description": "Target model for offload task",
                    "enum": [
                        "qwen3-coder-next:latest",
                        "qwen3-coder-next:q8_0",
                        "glm-ocr:latest",
                        "phi4-256k:latest",
                        "pocket-tts:latest",
                    ],
                },
            },
            "required": ["query"],
        },
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
                            "context": {"type": "string"},
                        },
                        "required": ["id", "query"],
                    },
                },
                "model": {
                    "type": "string",
                    "description": "Target local model",
                    "enum": [
                        "qwen3-coder-next:latest",
                        "qwen3-coder-next:q8_0",
                        "glm-ocr:latest",
                        "phi4-256k:latest",
                        "pocket-tts:latest",
                    ],
                },
            },
            "required": ["tasks"],
        },
    },
    {
        "name": "inspect_cache",
        "description": "Get semantic cache statistics and hit rates",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "elite_ocr_analysis",
        "description": "State-of-the-art OCR with 94.62% OmniDocBench accuracy using GLM-OCR",
        "inputSchema": {
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "Path to image file for OCR analysis",
                },
                "extract_format": {
                    "type": "string",
                    "enum": ["text", "structured", "table", "formula"],
                    "description": "Output format for extracted content",
                },
                "language": {
                    "type": "string",
                    "description": "Language for OCR (default: auto-detect)",
                },
            },
            "required": ["image_path"],
        },
    },
    {
        "name": "agentic_coding_workflow",
        "description": (
            "Elite coding workflow using Qwen3-Coder-Next with 70.6% SWE-Bench performance"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_description": {
                    "type": "string",
                    "description": "Detailed description of coding task",
                },
                "context_files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of context file paths",
                },
                "output_format": {
                    "type": "string",
                    "enum": ["code", "plan", "analysis", "full_solution"],
                    "description": "Desired output format",
                },
                "complexity_level": {
                    "type": "string",
                    "enum": ["simple", "medium", "complex", "enterprise"],
                    "description": "Task complexity for model selection",
                },
            },
            "required": ["task_description"],
        },
    },
    {
        "name": "compound_engineering_orchestrator",
        "description": (
            "Orchestrate multiple elite models for compound engineering workflows "
            "with 96% token efficiency"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "workflow_type": {
                    "type": "string",
                    "enum": [
                        "enterprise_ai_development",
                        "autonomous_agent_creation",
                        "document_driven_coding",
                        "voice_enabled_development",
                    ],
                    "description": "Type of compound workflow to execute",
                },
                "primary_task": {
                    "type": "string",
                    "description": "Primary task description",
                },
                "context_data": {
                    "type": "object",
                    "description": "Additional context data for the workflow",
                },
                "resource_constraints": {
                    "type": "object",
                    "properties": {
                        "max_memory_gb": {"type": "number"},
                        "max_execution_time_min": {"type": "number"},
                        "preferred_models": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
            },
            "required": ["workflow_type", "primary_task"],
        },
    },
    {
        "name": "elite_model_selection",
        "description": (
            "Intelligent model selection based on task requirements and available system resources"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_type": {
                    "type": "string",
                    "enum": [
                        "coding",
                        "vision",
                        "math",
                        "tts",
                        "analysis",
                        "compound",
                        "autonomous",
                    ],
                    "description": "Primary task type",
                },
                "complexity": {
                    "type": "string",
                    "enum": [
                        "simple",
                        "medium",
                        "complex",
                        "enterprise",
                        "frontier",
                    ],
                    "description": "Task complexity level",
                },
                "performance_priority": {
                    "type": "string",
                    "enum": [
                        "speed",
                        "accuracy",
                        "memory_efficiency",
                        "cost",
                        "balanced",
                    ],
                    "description": "Performance optimization priority",
                },
                "available_memory_gb": {
                    "type": "number",
                    "description": "Available system memory in GB",
                },
                "special_requirements": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Special requirements like voice, vision, etc.",
                },
            },
            "required": ["task_type", "complexity"],
        },
    },
    {
        "name": "pocket_tts_generate",
        "description": (
            "Generate speech from text using Kyutai Pocket TTS (100M parameters, CPU-only)"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text to convert to speech",
                },
                "voice": {
                    "type": "string",
                    "description": (
                        "Voice model (alba, marius, javert, jean, fantine, "
                        "cosette, eponine, azelma, or custom path)"
                    ),
                },
                "output_path": {
                    "type": "string",
                    "description": "Output file path for generated audio",
                },
                "speed": {
                    "type": "number",
                    "minimum": 0.5,
                    "maximum": 2.0,
                    "description": "Speech speed factor (0.5-2.0)",
                },
            },
            "required": ["text"],
        },
    },
    {
        "name": "get_truth_anchors",
        "description": "Get concise verified system hardware facts for context grounding",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "remember_fact",
        "description": "Store a fact in long-term semantic memory for future reference",
        "inputSchema": {
            "type": "object",
            "properties": {
                "fact": {
                    "type": "string",
                    "description": "The fact or information to remember",
                },
                "category": {
                    "type": "string",
                    "description": "Optional category for the fact",
                },
            },
            "required": ["fact"],
        },
    },
    {
        "name": "recall_context",
        "description": "Recall semantically relevant context from long-term memory",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for memory recall",
                },
                "limit": {
                    "type": "number",
                    "description": "Max number of memories to recall",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "daily_scout_research",
        "description": (
            "Trigger the Daily Scout agent to research SOTA SLMs and propose registry updates"
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def build_tool_list(skills: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the full ``tools/list`` payload (built-ins + skill-derived tools).

    Each registered skill is exposed as ``skill_<lowered_id>`` with a generic
    ``inputs`` object schema so callers can pass arbitrary skill arguments.
    """
    tools = list(BASE_TOOLS)
    for skill_id, skill_info in skills.items():
        tools.append(
            {
                "name": f"skill_{skill_id.lower()}",
                "description": f"Execute skill: {skill_info.get('description', skill_id)}",
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
    return tools
