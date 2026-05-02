#!/usr/bin/env python3
"""
ollama_task_router.py - Task Router for Ollama Gemma4 + kimi-k2.5:cloud

Offloads appropriate tasks to Gemma4 (local/free) while reserving
kimik2.5:cloud for complex tasks. Extends cloud availability.
"""

import json
import subprocess
import sys


# Task classification
def classify_task(prompt: str) -> str:
    """Classify task complexity to determine model."""

    # Simple tasks -> Gemma4
    simple_patterns = [
        "format",
        "lint",
        "style",
        "syntax check",
        "variable name",
        "comment",
        "docstring",
        "refactor",
        "rename",
        "reorder",
        "simple function",
        "utility",
        "helper",
        "test case",
        "assert",
        "verify",
        "count",
        "list",
        "enumerate",
    ]

    # Complex tasks -> kimi-k2.5:cloud
    complex_patterns = [
        "optimize kernel",
        "gpu",
        "hip",
        "mfma",
        "performance",
        "benchmark",
        "profile",
        "algorithm",
        "data structure",
        "complex",
        "architecture",
        "design",
        "strategy",
        "research",
        "analyze",
        "investigate",
        "breakthrough",
        "novel",
        "innovation",
    ]

    prompt_lower = prompt.lower()

    # Check for complex patterns first
    for pattern in complex_patterns:
        if pattern in prompt_lower:
            return "kimik2.5-cloud"

    # Check for simple patterns
    for pattern in simple_patterns:
        if pattern in prompt_lower:
            return "gemma4"

    # Default based on length - short tasks to Gemma4
    if len(prompt) < 500:
        return "gemma4"

    return "kimik2.5-cloud"


def query_ollama(prompt: str, model: str = "gemma4") -> str:
    """Query Ollama with Gemma4."""
    try:
        result = subprocess.run(
            ["ollama", "run", model], input=prompt, capture_output=True, text=True, timeout=120
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        return "[TIMEOUT]"
    except Exception as e:
        return f"[ERROR: {e}]"


def query_kimik(prompt: str) -> str:
    """Placeholder for kimi-k2.5:cloud query via popcorn/aiter system."""
    # This would integrate with your existing kimi-k2.5:cloud interface
    return f"[CLOUD TASK] {prompt[:50]}..."


def route_task(prompt: str, force_model: str | None = None) -> dict:
    """Route task to appropriate model."""

    model = force_model or classify_task(prompt)

    result = {"model": model, "prompt": prompt, "response": "", "cached": False}

    if model == "gemma4":
        result["response"] = query_ollama(prompt, "gemma4")
    elif model == "gemma4-9b":
        result["response"] = query_ollama(prompt, "gemma4:9b")
    else:
        result["response"] = query_kimik(prompt)

    return result


# Task types for Luma speedrun
TASK_TYPES = {
    "code_format": "gemma4",
    "syntax_check": "gemma4",
    "docstring_write": "gemma4",
    "simple_refactor": "gemma4",
    "test_generation": "gemma4",
    "parameter_tweak": "gemma4",
    "kernel_optimization": "kimik2.5-cloud",
    "performance_analysis": "kimik2.5-cloud",
    "breakthrough_research": "kimik2.5-cloud",
    " architectural_design": "kimik2.5-cloud",
}


def offload_to_gemma(task_type: str, task_input: str, context: str = "") -> str:
    """
    Offload a task to Gemma4 when appropriate.

    Args:
        task_type: Type of task (see TASK_TYPES)
        task_input: The actual task content
        context: Additional context

    Returns:
        Result from appropriate model
    """

    prompt = f"""Task: {task_type}
Context: {context}

{task_input}

Provide concise, correct output."""

    model = TASK_TYPES.get(task_type, "gemma4")
    result = route_task(prompt, model)

    return result["response"]


# Specific offloaders for Luma speedrun


def offload_kernel_commentary(kernel_code: str) -> str:
    """Add comments to kernel code - Gemma4."""
    prompt = f"Add detailed comments explaining this GPU kernel:\n\n{kernel_code}"
    return query_ollama(prompt, "gemma4")


def offload_code_review(code: str) -> str:
    """Quick code review - Gemma4."""
    prompt = f"Review this code for obvious bugs and style issues:\n```python\n{code}\n```"
    return query_ollama(prompt, "gemma4")


def offload_variant_generation(base_code: str, parameter: str, values: list) -> list:
    """Generate parameter variants - Gemma4."""
    variants = []
    for value in values:
        prompt = f"Modify this code to set {parameter}={value}:\n{base_code}"
        variant = query_ollama(prompt, "gemma4")
        variants.append(variant)
    return variants


def offload_log_analysis(log_content: str) -> str:
    """Analyze submission logs - Gemma4."""
    prompt = (
        f"Analyze these submission logs. Summarize errors and suggest fixes:\n{log_content[:2000]}"
    )
    return query_ollama(prompt, "gemma4")


def offload_submission_summary(submissions: list) -> str:
    """Summarize submission status - Gemma4."""
    data = json.dumps(submissions, indent=2)
    prompt = f"Summarize these submission results. Highlight successes and failures:\n{data}"
    return query_ollama(prompt, "gemma4")


def offload_rate_limit_calculation(last_submissions: dict) -> dict:
    """Calculate when next submissions are allowed - Gemma4."""
    data = json.dumps(last_submissions, indent=2)
    prompt = f"Given these last submission times, calculate when next submission allowed (1/hour):\n{data}"
    response = query_ollama(prompt, "gemma4")
    # Parse response to extract times
    return {"gemma_response": response}  # Would parse properly in production


# Main execution
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: ollama_task_router.py <task_type> [<input_file>]")
        print(f"Task types: {', '.join(TASK_TYPES.keys())}")
        sys.exit(1)

    task_type = sys.argv[1]

    if len(sys.argv) > 2:
        with open(sys.argv[2]) as f:
            task_input = f.read()
    else:
        task_input = sys.stdin.read()

    result = offload_to_gemma(task_type, task_input)
    print(result)
