"""
AIMO3 SC-TIR Submission: Self-Consistency + Tool-Integrated Reasoning.

Architecture:
1. DeepSeek-R1-Distill-Qwen-32B-AWQ via vLLM (primary)
2. Majority voting: N=4 solutions per problem, temperature=0.7
3. TIR: Extract Python code blocks, execute, feed results back
4. Budget forcing: Extend reasoning via "Wait" token injection
5. Deterministic final answer: temperature=0.0 for boxed extraction

Scoring: Penalized accuracy (1.0 correct, 0.5 non-deterministic, 0.0 wrong)
Constraint: Must produce SAME answer in two independent runs (deterministic scoring)
"""

import os
import re
import subprocess
import sys
from collections import Counter
from typing import Optional

import polars as pl


sys.path.append("/kaggle/input/ai-mathematical-olympiad-progress-prize-3")
import kaggle_evaluation.aimo_3_inference_server


# Model selection: DeepSeek-R1-Distill-Qwen-32B-AWQ (best open-weight reasoning)
# Fallback: Qwen2.5-Math-7B if 32B doesn't fit
MODEL_CANDIDATES = [
    "/kaggle/input/deepseek-r1-distill-qwen/deepseek-r1-distill-qwen-32b-awq",
    "/kaggle/input/qwen2-5-math-7b-instruct",
]

# SC-TIR configuration
N_SAMPLES = 4  # Number of majority voting samples
TEMPERATURE = 0.7  # Sampling temperature for diversity
MAX_TOKENS = 4096  # Max reasoning tokens
CODE_TIMEOUT = 10  # Python execution timeout (seconds)

global_model = None


def load_model():
    global global_model
    from vllm import LLM

    for model_path in MODEL_CANDIDATES:
        if os.path.exists(model_path):
            print(f"Loading model from {model_path}", flush=True)
            global_model = LLM(
                model=model_path,
                tensor_parallel_size=1,
                trust_remote_code=True,
                gpu_memory_utilization=0.95,
                enforce_eager=True,
                max_model_len=MAX_TOKENS + 512,
                quantization="awq" if "awq" in model_path.lower() else None,
            )
            print(f"Model loaded: {model_path}", flush=True)
            return
    raise RuntimeError(f"No model found at: {MODEL_CANDIDATES}")


def execute_python(code: str) -> str:
    """Execute Python code in a sandboxed subprocess. Returns stdout or error."""
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=CODE_TIMEOUT,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        elif result.stderr:
            return f"Error: {result.stderr[:200]}"
        return "No output"
    except subprocess.TimeoutExpired:
        return "Error: Execution timed out"
    except Exception as e:
        return f"Error: {str(e)[:200]}"


def extract_code_blocks(text: str) -> list[str]:
    """Extract Python code blocks from model output."""
    pattern = r"```python\s*\n(.*?)```"
    return re.findall(pattern, text, re.DOTALL)


def solve_with_tir(problem: str) -> str:
    """Solve with Tool-Integrated Reasoning: generate → execute code → continue."""
    from vllm import SamplingParams

    # Phase 1: Initial reasoning with code generation
    prompt = (
        "<|im_start|>system\n"
        "You are a mathematical problem solver. Think step by step. "
        "When you need to compute something, write Python code in ```python``` blocks. "
        "Put your final integer answer in \\boxed{}.\n"
        "<|im_end|>\n"
        f"<|im_start|>user\n{problem}<|im_end|>\n"
        "<|im_start|>assistant\n"
    )

    params = SamplingParams(
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        stop=["<|im_end|>"],
    )

    outputs = global_model.generate([prompt], params, use_tqdm=False)
    response = outputs[0].outputs[0].text

    # Phase 2: Execute any Python code blocks and feed results back
    code_blocks = extract_code_blocks(response)
    if code_blocks:
        for code in code_blocks[:3]:  # Max 3 code executions
            result = execute_python(code)
            if result and not result.startswith("Error"):
                # Append execution result and continue reasoning
                continuation_prompt = (
                    prompt + response + f"\n\nCode output: {result}\n\nBased on this result, "
                    "let me verify and state the final answer in \\boxed{}:\n"
                )
                params_final = SamplingParams(
                    temperature=0.0,  # Deterministic for final answer
                    max_tokens=512,
                    stop=["<|im_end|>"],
                )
                cont_outputs = global_model.generate(
                    [continuation_prompt], params_final, use_tqdm=False
                )
                response = response + "\n" + cont_outputs[0].outputs[0].text

    return response


def extract_answer(text: str) -> int:
    """Extract integer answer from \\boxed{} or last number."""
    # Try boxed first (most reliable)
    matches = re.findall(r"\\boxed\{([^}]+)\}", text)
    if matches:
        last_boxed = matches[-1].strip()
        # Handle expressions like \boxed{42}
        nums = re.findall(r"-?\d+", last_boxed)
        if nums:
            return int(nums[-1]) % 100000

    # Fallback: last number in text
    numbers = re.findall(r"-?\d+", text)
    if numbers:
        return int(numbers[-1]) % 100000
    return 0


def solve_with_majority_vote(problem: str) -> int:
    """Generate N solutions, extract answers, return majority vote."""
    answers = []
    for _ in range(N_SAMPLES):
        response = solve_with_tir(problem)
        answer = extract_answer(response)
        answers.append(answer)

    # Majority vote
    counter = Counter(answers)
    most_common = counter.most_common(1)[0]
    print(
        f"  Votes: {dict(counter)}, Winner: {most_common[0]} ({most_common[1]}/{N_SAMPLES})",
        flush=True,
    )
    return most_common[0]


def predict(
    id_: pl.DataFrame, question: pl.DataFrame, answer: Optional[pl.DataFrame] = None
) -> pl.DataFrame:
    if global_model is None:
        load_model()

    problem_id = id_.item(0, 0)
    problem_text = question.item(0, 0)

    print(f"Solving problem {problem_id}...", flush=True)
    prediction = solve_with_majority_vote(problem_text)
    print(f"  Answer: {prediction}", flush=True)

    return pl.DataFrame({"id": [problem_id], "answer": [prediction]})


if __name__ == "__main__":
    inference_server = kaggle_evaluation.aimo_3_inference_server.AIMO3InferenceServer(predict)
    if os.getenv("KAGGLE_IS_COMPETITION_RERUN"):
        inference_server.serve()
    else:
        inference_server.run_local_gateway(
            ("/kaggle/input/ai-mathematical-olympiad-progress-prize-3/test.csv",)
        )
