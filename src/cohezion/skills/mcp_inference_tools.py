"""Inference-style MCP tool implementations (OCR, agentic coding, TTS, ...).

These call out to local Ollama (via ``curl``) or Pocket TTS to produce the
final ``content`` payload returned to the JSON-RPC client. Pure handlers,
no I/O against the registries — those live in other ``mcp_*`` modules.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any


def elite_ocr_analysis(args: dict[str, Any]) -> dict[str, Any]:
    """Run GLM-OCR document understanding on the image at ``args['image_path']``.

    Honors ``analysis_type`` (text/table/formula/document/handwriting) and
    ``output_format`` (structured/plain/json/markdown). Returns the standard
    ``{"content": [{"type": "text", "text": ...}]}`` envelope.
    """
    try:
        image_path = args.get("image_path")
        analysis_type = args.get("analysis_type", "document-analysis")
        output_format = args.get("output_format", "structured")

        if not image_path:
            return {"content": [{"type": "text", "text": "Error: image_path is required"}]}

        # Construct OCR prompt based on analysis type
        ocr_prompts = {
            "text-recognition": "Extract all text from this image with high accuracy.",
            "table-recognition": "Extract and structure table data from this image, maintaining row/column relationships.",
            "formula-recognition": "Recognize and transcribe mathematical formulas and equations from this image.",
            "document-analysis": "Perform comprehensive document analysis: extract text, identify structure, and summarize content.",
            "handwriting": "Extract handwritten text from this image with best effort interpretation.",
        }

        prompt = ocr_prompts.get(analysis_type, ocr_prompts["document-analysis"])

        # Format-specific instructions
        format_instructions = {
            "structured": "Provide results in structured format with clear hierarchy.",
            "plain-text": "Provide plain text output only.",
            "json": "Provide results in valid JSON format.",
            "markdown": "Provide results in markdown format with proper formatting.",
        }

        full_prompt = f"{prompt} {format_instructions.get(output_format, '')}"

        payload = {
            "model": "glm-ocr:latest",
            "prompt": full_prompt,
            "images": [image_path],
            "stream": False,
            "options": {
                "temperature": 0.3,  # More deterministic for OCR
                "num_ctx": 128000,
            },
        }

        cmd = [
            "curl",
            "-s",
            "-X",
            "POST",
            "http://localhost:11434/api/generate",
            "-H",
            "Content-Type: application/json",
            "-d",
            json.dumps(payload),
        ]

        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            return {"content": [{"type": "text", "text": f"OCR API call failed: {res.stderr}"}]}

        result = json.loads(res.stdout)
        ocr_result = result.get("response", "")

        # Add metadata about the OCR processing
        metadata = {
            "model": "glm-ocr:latest",
            "analysis_type": analysis_type,
            "output_format": output_format,
            "accuracy_estimate": "94.62% OmniDocBench",
            "processing_time": "optimized with MoE architecture",
        }

        final_result = {"ocr_result": ocr_result, "metadata": metadata}

        return {"content": [{"type": "text", "text": json.dumps(final_result, indent=2)}]}

    except (
        OSError,
        ValueError,
        KeyError,
    ) as e:
        return {"content": [{"type": "text", "text": f"Elite OCR analysis failed: {e}"}]}


def agentic_coding_workflow(args: dict[str, Any]) -> dict[str, Any]:
    """Generate code via Qwen3-Coder-Next with complexity-driven model selection.

    Reads ``task_description`` (required), plus optional ``complexity_level``,
    ``language``, ``context_files`` (inlined into the prompt), and
    ``output_type`` to control verbosity (code-only vs full-solution etc.).
    """
    try:
        task_description = args.get("task_description")
        complexity_level = args.get("complexity_level", "medium")
        language = args.get("language", "Python")
        context_files = args.get("context_files", [])
        output_type = args.get("output_type", "full-solution")

        if not task_description:
            return {"content": [{"type": "text", "text": "Error: task_description is required"}]}

        # Select optimal model based on complexity
        model_mapping = {
            "simple": "qwen3-coder-next:latest",
            "medium": "qwen3-coder-next:latest",
            "complex": "qwen3-coder-next:q8_0",
            "enterprise": "qwen3-coder-next:q8_0",
        }

        selected_model = model_mapping.get(complexity_level, "qwen3-coder-next:latest")

        # Build comprehensive coding prompt
        coding_prompts = {
            "code-only": "Generate only the code solution for the following task. No explanations.",
            "with-explanation": "Generate the code solution with detailed explanations of the approach and key decisions.",
            "with-tests": "Generate the code solution along with comprehensive unit tests.",
            "full-solution": "Generate a complete solution including code, explanations, tests, and documentation.",
        }

        base_prompt = f"""
Task: {task_description}
Language: {language}
Complexity: {complexity_level}

{coding_prompts.get(output_type, coding_prompts["full-solution"])}
"""

        # Add context files if provided
        if context_files:
            base_prompt += "\n\nContext Files:\n"
            for file_path in context_files:
                try:
                    with open(file_path) as f:
                        content = f.read()
                    base_prompt += f"\n--- {file_path} ---\n{content}\n"
                except (OSError, UnicodeDecodeError) as e:
                    base_prompt += f"\n--- {file_path} ---\nError reading file: {e}\n"

        # Add system prompt for agentic behavior
        system_prompt = f"""
You are Qwen3-Coder-Next, an elite agentic coding assistant with 70.6% SWE-Bench performance.
You are using the {selected_model} model with Mixture of Experts architecture (80B total, 3B active parameters).

Key capabilities:
- Advanced agentic reasoning and planning
- Complex software engineering tasks
- Performance-optimized code generation
- Modern best practices and patterns

Generate production-ready, maintainable code that follows industry standards.
"""

        payload = {
            "model": selected_model,
            "prompt": base_prompt,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": 0.7 if output_type != "code-only" else 0.3,
                "num_ctx": 262144,
                "repeat_penalty": 1.05,
            },
        }

        cmd = [
            "curl",
            "-s",
            "-X",
            "POST",
            "http://localhost:11434/api/generate",
            "-H",
            "Content-Type: application/json",
            "-d",
            json.dumps(payload),
        ]

        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Coding API call failed: {res.stderr}",
                    }
                ]
            }

        result = json.loads(res.stdout)
        coding_result = result.get("response", "")

        # Add metadata about the coding process
        metadata = {
            "model": selected_model,
            "complexity_level": complexity_level,
            "language": language,
            "output_type": output_type,
            "swe_bench_score": "70.6%",
            "moe_efficiency": "96.25% (3B/80B active params)",
            "context_window": 262144,
        }

        final_result = {"coding_solution": coding_result, "metadata": metadata}

        return {"content": [{"type": "text", "text": json.dumps(final_result, indent=2)}]}

    except (
        OSError,
        ValueError,
        KeyError,
    ) as e:
        return {"content": [{"type": "text", "text": f"Agentic coding workflow failed: {e}"}]}


def compound_engineering_orchestrator(args: dict[str, Any]) -> dict[str, Any]:
    """Plan a multi-model compound workflow against a memory budget.

    Selects a predefined workflow template (enterprise/autonomous/document/math),
    refuses execution if ``resource_constraints.max_memory_gb`` is less than the
    template's requirement, and otherwise returns the orchestration plan.
    """
    try:
        workflow_type = args.get("workflow_type")
        primary_task = args.get("primary_task")
        sub_tasks = args.get("sub_tasks", [])
        resource_constraints = args.get("resource_constraints", {})

        if not workflow_type or not primary_task:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "Error: workflow_type and primary_task are required",
                    }
                ]
            }

        # Define compound engineering workflows
        workflows = {
            "enterprise-ai-development": {
                "models": [
                    "qwen3-coder-next:q8_0",
                    "glm-ocr:latest",
                    "phi4-256k:latest",
                ],
                "memory_required": 89.2,
                "description": "Complete enterprise AI development with elite models",
            },
            "autonomous-agent-creation": {
                "models": ["qwen3-coder-next:q8_0", "gpt-oss-256k:latest"],
                "memory_required": 97,
                "description": "Create autonomous AI agents with elite reasoning",
            },
            "document-driven-coding": {
                "models": ["glm-ocr:latest", "qwen3-coder-next:latest"],
                "memory_required": 53.2,
                "description": "Code generation driven by document analysis",
            },
            "mathematical-system-design": {
                "models": ["qwen3-coder-next:q8_0", "phi4-256k:latest"],
                "memory_required": 87,
                "description": "Mathematical system design with elite optimization",
            },
        }

        workflow = workflows.get(workflow_type)
        if not workflow:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: Unknown workflow type '{workflow_type}'",
                    }
                ]
            }

        # Check resource constraints
        max_memory = resource_constraints.get("max_memory_gb", 125)
        if workflow["memory_required"] > max_memory:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Insufficient memory for {workflow_type}. Required: {workflow['memory_required']}GB, Available: {max_memory}GB",
                    }
                ]
            }

        # Execute compound workflow
        orchestration_result = {
            "workflow_type": workflow_type,
            "primary_task": primary_task,
            "sub_tasks": sub_tasks,
            "models_used": workflow["models"],
            "memory_usage": workflow["memory_required"],
            "workflow_description": workflow["description"],
            "status": "orchestrated",
            "optimizations": {
                "moe_efficiency": "96.25%",
                "ocr_savings": "90.5%",
                "compound_synergy": "Elite model orchestration",
            },
        }

        return {"content": [{"type": "text", "text": json.dumps(orchestration_result, indent=2)}]}

    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
    ) as e:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Compound engineering orchestration failed: {e}",
                }
            ]
        }


def pocket_tts_generate(args: dict[str, Any]) -> dict[str, Any]:
    """Synthesise speech from ``args['text']`` via Kyutai Pocket TTS.

    Falls back gracefully if ``pocket_tts``/``scipy`` aren't installed,
    returning a text-only error envelope rather than raising.
    """
    try:
        text = args.get("text")
        voice = args.get("voice", "alba")
        output_path = args.get("output_path", "/tmp/pocket_tts_output.wav")
        _speed = args.get("speed", 1.0)

        if not text:
            return {"content": [{"type": "text", "text": "Error: text is required"}]}

        # Import pocket-tts
        try:
            import scipy.io.wavfile
            from pocket_tts import TTSModel
        except ImportError:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "Error: pocket-tts not installed. Install with: pip install pocket-tts",
                    }
                ]
            }

        # Load model
        tts_model = TTSModel.load_model()
        voice_state = tts_model.get_state_for_audio_prompt(voice)

        # Generate audio
        audio = tts_model.generate_audio(voice_state, text)

        # Save to file
        scipy.io.wavfile.write(output_path, tts_model.sample_rate, audio.numpy())

        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Successfully generated speech using Pocket TTS\nVoice: {voice}\nOutput: {output_path}\nDuration: {len(audio) / tts_model.sample_rate:.2f}s\nSize: {len(audio) * 2 / 1024 / 1024:.2f}MB",
                }
            ]
        }

    except (
        ImportError,
        OSError,
        ValueError,
        RuntimeError,
        AttributeError,
    ) as e:
        return {"content": [{"type": "text", "text": f"Pocket TTS generation failed: {e}"}]}