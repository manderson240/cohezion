#!/usr/bin/env python3
"""Model-Specific Quality Optimization with Context Harnesses

Optimizes per-model based on model cards and strengths:
- Gemma-4-26B-A4B: MoE reasoning, 256K context, thinking mode
- Qwen3-8B: Coding specialist, Q4_1 quantization
- DeepSeek: Reasoning chains, 
Uses Gaia SDK patterns and context harnesses for quality over raw speed.
"""

import asyncio
import time
from dataclasses import dataclass

import aiohttp


@dataclass
class ModelProfile:
    """Model-specific optimization profile."""
    name: str
    strengths: list[str]
    weaknesses: list[str]
    optimal_system: str
    temperature: float
    top_p: float
    max_tokens: int
    thinking_mode: bool = False
    context_size: int = 4096


# Model-specific profiles based on architecture
MODEL_PROFILES = {
    "DeepSeek-Qwen3-8B-GGUF": ModelProfile(
        name="DeepSeek-Qwen3-8B",
        strengths=["reasoning","instruction_following","multilingual"],
        weaknesses=["long_context","creative_writing"],
        optimal_system="You are a precise reasoning assistant. Use step-by-step logic. Be concise and factual.",
        temperature=0.3,  # Lower for reasoning
        top_p=0.9,
        max_tokens=150,
        thinking_mode=False,
        context_size=4096,
    ),
    "gemma-4-26B": ModelProfile(
        name="Gemma-4-26B-A4B",
        strengths=["complex_reasoning","moE_architecture"," vision"],
        weaknesses=["memory_intensive","slow_prefill"],
        optimal_system="You are an expert analyst. Provide structured, thorough responses with clear reasoning.",
        temperature=0.7,
        top_p=0.95,
        max_tokens=200,
        thinking_mode=True,  # Enable for MoE
        context_size=256000,
    ),
    "Qwen3-0.6B": ModelProfile(
        name="Qwen3-0.6B",
        strengths=["speed","low_latency","simple_tasks"],
        weaknesses=["reasoning","nuance","complex_instructions"],
        optimal_system="You are a fast, efficient assistant. Give direct, short answers.",
        temperature=0.5,
        top_p=0.9,
        max_tokens=50,
        thinking_mode=False,
        context_size=2048,
    ),
}


class ContextHarness:
    """Optimize context for specific model capabilities."""

    def __init__(self, profile: ModelProfile):
        self.profile = profile

    def craft_prompt(self, task: str, complexity: str = "medium") -> dict[str, str]:
        """Craft optimized prompt based on task complexity and model strengths."""

        # Task routing based on model strengths
        if complexity == "high" and "reasoning" in self.profile.strengths:
            # Complex task + reasoning model = enable thinking
            system = f"{self.profile.optimal_system}\n\nThink step-by-step. Show your work."
        elif complexity == "low" and "speed" in self.profile.strengths:
            # Simple task + fast model = minimal overhead
            system = f"{self.profile.optimal_system}\n\nRespond in 1-2 sentences only."
        else:
            system = self.profile.optimal_system

        # Add harness directives
        harnessed = self._apply_harness_directives(task)

        return {
            "system": system,
            "prompt": harnessed,
            "temperature": self.profile.temperature,
            "top_p": self.profile.top_p,
            "max_tokens": self.profile.max_tokens,
        }

    def _apply_harness_directives(self, prompt: str) -> str:
        """Add structural directives based on model weaknesses."""

        # If model struggles with long context, add summary directive
        if "long_context" in self.profile.weaknesses:
            return f"[SUMMARIZE IF NEEDED] {prompt}"

        # If model needs structure, add formatting
        if "nuance" in self.profile.weaknesses:
            return f"Answer clearly:\n1. Main point\n2. Supporting detail\n\n{prompt}"

        return prompt


class QualityBenchmark:
    """Benchmark quality per model with optimized settings."""

    def __init__(self, base_url: str = "http://localhost:8002"):
        self.base_url = base_url
        self.models = {
            "DeepSeek-Qwen3-8B-GGUF": "deepseek-optimized",
        }

    async def benchmark_model_quality(
        self,
        model_id: str,
        profile: ModelProfile,
        test_tasks: list[str],
    ) -> dict:
        """Benchmark quality with model-specific optimization."""

        harness = ContextHarness(profile)

        async with aiohttp.ClientSession() as session:
            results = []

            for task in test_tasks:
                # Craft optimized prompt
                crafted = harness.craft_prompt(task, complexity="high")

                # Time and execute
                start = time.time()
                try:
                    async with session.post(
                        f"{self.base_url}/v1/chat/completions",
                        json={
                            "model": model_id,
                            "messages": [
                                {"role": "system", "content": crafted["system"]},
                                {"role": "user", "content": crafted["prompt"]},
                            ],
                            "temperature": crafted["temperature"],
                            "top_p": crafted["top_p"],
                            "max_tokens": crafted["max_tokens"],
                        },
                        timeout=aiohttp.ClientTimeout(total=60),
                    ) as resp:
                        data = await resp.json()
                        elapsed = (time.time() - start) * 1000

                        text = data["choices"][0]["message"]["content"]
                        tokens = data.get("usage", {}).get("completion_tokens", 0)

                        # Quality heuristics
                        quality_score = self._assess_quality(text)

                        results.append({
                            "task": task,
                            "tokens": tokens,
                            "latency_ms": elapsed,
                            "tps": tokens / (elapsed / 1000) if elapsed > 0 else 0,
                            "quality": quality_score,
                            "length": len(text.split()),
                        })
                except Exception as e:
                    results.append({"task": task, "error": str(e)})

            # Aggregate
            valid = [r for r in results if "error" not in r]
            if valid:
                avg_quality = sum(r["quality"] for r in valid) / len(valid)
                avg_latency = sum(r["latency_ms"] for r in valid) / len(valid)
                avg_tps = sum(r["tps"] for r in valid) / len(valid)
            else:
                avg_quality = avg_latency = avg_tps = 0

            return {
                "model": profile.name,
                "profile": "optimized",
                "avg_quality": avg_quality,
                "avg_latency_ms": avg_latency,
                "avg_tps": avg_tps,
                "tasks": len(valid),
                "results": results,
            }

    def _assess_quality(self, text: str) -> float:
        """Simple quality scoring."""
        score = 0.0

        # Structure indicators
        words = text.split()
        if len(words) > 20:  # Has substance
            score += 1.0
        if text.count('.') > 2:  # Multiple sentences
            score += 1.0
        if any(c.isupper() for c in text[:5]):  # Starts properly
            score += 0.5

        # Reasoning indicators
        if any(w in text.lower() for w in ['because', 'therefore', 'step', 'first', 'second']):
            score += 1.5  # Has reasoning markers
        if any(w in text.lower() for w in ['however', 'although', 'but', 'instead']):
            score += 0.5  # Shows nuance

        return score


async def main():
    print("=" * 70)
    print("MODEL-SPECIFIC QUALITY OPTIMIZATION")
    print("Using context harnesses and model profiles")
    print("=" * 70)

    benchmark = QualityBenchmark()

    test_tasks = [
        "Explain why the sky is blue.",
        "Write a haiku about technology.",
        "What makes a good software engineer?",
        "Describe the water cycle.",
    ]

    print("\nTest tasks:")
    for i, task in enumerate(test_tasks, 1):
        print(f"  {i}. {task}")

    # Test with DeepSeek (reasoning optimized)
    model_id = "DeepSeek-Qwen3-8B-GGUF"
    profile = MODEL_PROFILES.get(model_id, MODEL_PROFILES["DeepSeek-Qwen3-8B-GGUF"])

    print(f"\n{'='*70}")
    print(f"Testing: {profile.name}")
    print(f"Profile: temp={profile.temperature}, top_p={profile.top_p}")
    print(f"Strengths: {', '.join(profile.strengths)}")
    print(f"{'='*70}\n")

    result = await benchmark.benchmark_model_quality(model_id, profile, test_tasks)

    print("\nResults:")
    print(f"  Average Quality Score: {result['avg_quality']:.2f}/4.0")
    print(f"  Average Latency: {result['avg_latency_ms']:.1f}ms")
    print(f"  Average TPS: {result['avg_tps']:.1f}")
    print(f"  Tasks completed: {result['tasks']}")

    # Show sample outputs
    print(f"\n{'='*70}")
    print("SAMPLE OUTPUTS")
    print(f"{'='*70}")

    for r in result['results'][:2]:
        if 'error' not in r:
            print(f"\nTask: {r['task']}")
            print(f"Quality: {r['quality']:.1f} | Tokens: {r['tokens']} | Latency: {r['latency_ms']:.1f}ms")

    # Quality vs Baseline comparison
    print(f"\n{'='*70}")
    print("COMPARISON: Quality-Optimized vs Baseline")
    print(f"{'='*70}")
    print("Optimized Settings:")
    print(f"  - System: {profile.optimal_system[:60]}...")
    print(f"  - Temperature: {profile.temperature} (vs 0.7 default)")
    print(f"  - Max tokens: {profile.max_tokens} (targeted)")
    print(f"  - Quality Score: {result['avg_quality']:.2f}")

    print(f"\nMETRIC quality_score={result['avg_quality']:.2f}")
    print(f"METRIC avg_latency_ms={result['avg_latency_ms']:.1f}")
    print(f"METRIC tokens_per_sec={result['avg_tps']:.1f}")


if __name__ == "__main__":
    asyncio.run(main())
