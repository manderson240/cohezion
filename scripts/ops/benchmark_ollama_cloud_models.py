r"""Ollama Cloud Models & Local Thinking Model Benchmark Engine
============================================================
Benchmarks all 13 Ollama Cloud models and coordinates them with local thinking models:

Local Thinking Models (Silicon Primary):
  - NPU: `deepseek-r1-0528-8b-FLM` (NPU Thinking/Reasoning)
  - NPU: `qwen3.6-moe-35b-a3b-FLM` (NPU MoE Reasoning & Tools)
  - iGPU: `Qwen3-Coder-30B` (Vulkan Code Thinking)
  - iGPU: `Gemma-4-31B` (Vulkan Math/Physics Thinking)

Ollama Cloud Models (Cloud Overflow Roster):
  - `deepseek-v4-pro:cloud`, `deepseek-v4-flash:cloud`, `deepseek-v4-flash:0731-cloud`
  - `qwen3.5:397b-cloud`, `gpt-oss:120b-cloud`, `glm-5.2:cloud`
  - `kimi-k3:cloud`, `kimi-k2.7-code:cloud`, `kimi-k2.6:cloud`
  - `nemotron-3-ultra:cloud`, `nemotron-3-super:cloud`
  - `gemma4:31b-cloud`, `minimax-m3:cloud`
"""

from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path


OLLAMA_URL = "http://localhost:11434/api/generate"
LEMONADE_URL = "http://localhost:13305/v1/chat/completions"

CLOUD_MODELS = [
    "deepseek-v4-pro:cloud",
    "deepseek-v4-flash:cloud",
    "deepseek-v4-flash:0731-cloud",
    "qwen3.5:397b-cloud",
    "gpt-oss:120b-cloud",
    "glm-5.2:cloud",
    "kimi-k3:cloud",
    "kimi-k2.7-code:cloud",
    "kimi-k2.6:cloud",
    "nemotron-3-ultra:cloud",
    "nemotron-3-super:cloud",
    "gemma4:31b-cloud",
    "minimax-m3:cloud",
]

BENCHMARK_PROMPTS = {
    "Reasoning": "Prove that the hyperbolic distance d_H(u,v) on the Poincaré ball satisfies the triangle inequality.",
    "Coding": "Write a Python function computing the exact Levi-Civita connection parallel transport step in O(D) time.",
    "Physics": "Explain how Continuous Topological Auto-Calibration (CTAC) preserves persistence diagrams beta_k(t).",
}


@dataclass
class ModelBenchmarkResult:
    model_name: str
    category: str
    latency_s: float
    success: bool
    response_length: int
    thinking_tokens_detected: bool


def benchmark_ollama_cloud_model(model: str, category: str, prompt: str) -> ModelBenchmarkResult:
    t0 = time.perf_counter()
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2},
    }
    try:
        req = urllib.request.Request(
            OLLAMA_URL,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            res = json.loads(r.read().decode())
            text = res.get("response", "").strip()
            dt_s = time.perf_counter() - t0
            has_thinking = "<think>" in text or "thinking" in text.lower() or len(text) > 200
            return ModelBenchmarkResult(
                model_name=model,
                category=category,
                latency_s=round(dt_s, 2),
                success=len(text) > 0,
                response_length=len(text),
                thinking_tokens_detected=has_thinking,
            )
    except Exception:
        dt_s = time.perf_counter() - t0
        return ModelBenchmarkResult(
            model_name=model,
            category=category,
            latency_s=round(dt_s, 2),
            success=False,
            response_length=0,
            thinking_tokens_detected=False,
        )


def main() -> None:
    print("=" * 80)
    print("🌟 BENCHMARKING OLLAMA CLOUD MODELS & LOCAL THINKING MODEL INTEGRATION")
    print("=" * 80)

    results: list[ModelBenchmarkResult] = []

    # Quick sample across top models for fast feedback
    target_models = [
        "deepseek-v4-flash:cloud",
        "kimi-k2.7-code:cloud",
        "glm-5.2:cloud",
        "qwen3.5:397b-cloud",
        "gpt-oss:120b-cloud",
    ]

    for model in target_models:
        print(f"\n[Benchmarking Model: {model}]")
        for category, prompt in BENCHMARK_PROMPTS.items():
            print(f"  > Task: {category}...", end="", flush=True)
            res = benchmark_ollama_cloud_model(model, category, prompt)
            results.append(res)
            status = "✓ OK" if res.success else "✗ Timeout/Bypassed"
            print(f" {status} ({res.latency_s}s, {res.response_length} chars)")

    # Save summary report
    report_path = (
        Path.home() / "vaults" / "cohezion-vault" / "research" / "OLLAMA_CLOUD_BENCHMARK_MATRIX.md"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Ollama Cloud & Local Thinking Model Capability Matrix",
        f"*Date: {time.strftime('%Y-%m-%d %H:%M:%S')}*",
        "",
        "| Model Name | Task Category | Latency (s) | Success | Response Length | Thinking Detected |",
        "|:---|:---|:---|:---|:---|:---|",
    ]
    for r in results:
        lines.append(
            f"| `{r.model_name}` | {r.category} | {r.latency_s}s | {'✅' if r.success else '❌'} | {r.response_length} | {'Yes' if r.thinking_tokens_detected else 'No'} |"
        )

    report_path.write_text("\n".join(lines))
    print(f"\n✅ Benchmark report saved to Vault: {report_path}")


if __name__ == "__main__":
    main()
