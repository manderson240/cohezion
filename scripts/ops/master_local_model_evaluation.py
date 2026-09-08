r"""Master Local Model Roster Evaluation & Dispatch Matrix
======================================================
Evaluates the complete local model roster across AMD Strix Halo NPU, iGPU, and CPU:

Models Evaluated:
  1. `deepseek-r1-0528-8b-FLM` (NPU): Deep Reasoning & Unthrottled CoT
  2. `Qwen3-Coder-30B` (iGPU): Multi-File Code Generation & AST Harnesses
  3. `qwen3.6-moe-35b-a3b-FLM` (NPU MoE): High-Throughput Research Synthesis
  4. `qwen3vl-it-4b-FLM` (NPU Vision): Multimodal UI/UX & Diagram-to-Code
  5. `llama3.2-1b-FLM` (NPU Fast Lane): Intent Routing & Fast Q&A (<20ms)
  6. `embed-gemma-300m-FLM` (NPU Embeddings): 768D Vector Search & HNSW Indexing
  7. `Muse-Glimmer-30B-GGUF` (iGPU): Ultra-Detailed Creative Reasoning
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

from cohezion.inference.load_safety import check_load_safe
from cohezion.inference.unified_hybrid_router import TaskClass, UnifiedHybridRouter
from cohezion.reliability.oom_guard import OOMGuard


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ModelRosterProfile:
    model_id: str
    hardware_lane: str
    reported_size_gb: float
    inflated_size_gb: float
    primary_task_class: TaskClass
    when_to_use: str
    why_to_use: str
    card_defaults: dict[str, float]


ROSTER: tuple[ModelRosterProfile, ...] = (
    ModelRosterProfile(
        model_id="deepseek-r1-0528-8b-FLM",
        hardware_lane="NPU Lane (port 13305)",
        reported_size_gb=5.2,
        inflated_size_gb=8.84,
        primary_task_class=TaskClass.REASONING,
        when_to_use="Complex reasoning, root-cause debugging, mathematical logic, deep planning.",
        why_to_use="SOTA reasoning per parameter; unthrottled CoT thinking trace on NPU.",
        card_defaults={"temperature": 0.6, "top_p": 0.95},
    ),
    ModelRosterProfile(
        model_id="Qwen3-Coder-30B",
        hardware_lane="iGPU Vulkan/ROCm Lane (port 13305)",
        reported_size_gb=18.2,
        inflated_size_gb=30.94,
        primary_task_class=TaskClass.CODING,
        when_to_use="Writing code, multi-file refactoring, AutoHarness AST verifiers, unit test generation.",
        why_to_use="Top open-source coding model, 32k context, native tool use.",
        card_defaults={"temperature": 0.6, "top_p": 0.95, "top_k": 20},
    ),
    ModelRosterProfile(
        model_id="qwen3.6-moe-35b-a3b-FLM",
        hardware_lane="NPU MoE Sparse Lane (port 13305)",
        reported_size_gb=12.0,
        inflated_size_gb=20.40,
        primary_task_class=TaskClass.RESEARCH,
        when_to_use="High-throughput literature synthesis, multi-doc research summarization, swarm task allocation.",
        why_to_use="3B active parameter token generation speed (~100+ tok/s) with 35B dense capacity.",
        card_defaults={"temperature": 0.7, "top_p": 0.80, "top_k": 20},
    ),
    ModelRosterProfile(
        model_id="qwen3vl-it-4b-FLM",
        hardware_lane="NPU Vision Lane (port 13305)",
        reported_size_gb=3.8,
        inflated_size_gb=6.46,
        primary_task_class=TaskClass.VISION,
        when_to_use="Inspecting UI mockups, architectural diagrams, visual debugging.",
        why_to_use="94%+ vision accuracy on edge hardware, native multimodal attention.",
        card_defaults={"temperature": 0.6, "top_p": 0.95},
    ),
    ModelRosterProfile(
        model_id="llama3.2-1b-FLM",
        hardware_lane="NPU Fast Lane (port 13305)",
        reported_size_gb=1.1,
        inflated_size_gb=1.87,
        primary_task_class=TaskClass.FAST_QA,
        when_to_use="Intent classification, fast Q&A, prompt routing, semantic cache lookup.",
        why_to_use="Ultra-low TTFT (<20ms), pre-warmed on NPU, zero-overhead memory footprint.",
        card_defaults={"temperature": 0.3},
    ),
    ModelRosterProfile(
        model_id="embed-gemma-300m-FLM",
        hardware_lane="NPU Embeddings Lane (port 13305)",
        reported_size_gb=0.4,
        inflated_size_gb=0.68,
        primary_task_class=TaskClass.EMBEDDINGS,
        when_to_use="Embedding source code, 768D Poincaré vector search, SurrealDB HNSW indexing.",
        why_to_use="Fast local embedding model, 8192 context window, zero token cost.",
        card_defaults={},
    ),
    ModelRosterProfile(
        model_id="Muse-Glimmer-30B-GGUF-UD-Q5_K_L",
        hardware_lane="iGPU Vulkan/ROCm Lane (port 13305)",
        reported_size_gb=20.5,
        inflated_size_gb=34.85,
        primary_task_class=TaskClass.GENERAL,
        when_to_use="Ultra-detailed uncensored synthesis, open-ended problem solving, creative exploration.",
        why_to_use="Ultra-detailed fine-tuning with custom sampling sweet-spot (temp=0.7, min_p=0.05).",
        card_defaults={"temperature": 0.7, "top_p": 0.90, "top_k": 40, "min_p": 0.05},
    ),
)


async def evaluate_full_roster() -> None:
    logger.info("🚀 Starting Master Local Model Roster Evaluation...")
    t0 = time.perf_counter()

    mem = OOMGuard.get_memory_state()
    logger.info("📡 Live Memory Headroom: %.2f GiB available", mem.available_gb)

    router = UnifiedHybridRouter()

    print("\n" + "=" * 105)
    print("                    MASTER LOCAL MODEL ROSTER EVALUATION & DISPATCH MATRIX")
    print("=" * 105)

    for p in ROSTER:
        meta = {"size": p.reported_size_gb, "recipe": "flm" if "FLM" in p.model_id else "gguf"}
        safe, reason = check_load_safe(meta, available_gb=mem.available_gb)
        status_str = "✅ SAFE TO LOAD" if safe else f"⚠️ QUEUED ({reason})"

        print(f"\n🔹 MODEL: {p.model_id}")
        print(f"   • Hardware Lane: {p.hardware_lane}")
        print(f"   • Primary Task Class: {p.primary_task_class.value.upper()}")
        print(
            f"   • Catalog Size: {p.reported_size_gb:.2f} GB | Inflated Footprint (1.7x): {p.inflated_size_gb:.2f} GB"
        )
        print(f"   • Load Safety Status: {status_str}")
        print(f"   • Sampling Defaults: {p.card_defaults}")
        print(f"   • WHEN TO RUN: {p.when_to_use}")
        print(f"   • WHY TO RUN:  {p.why_to_use}")

    dt_total = time.perf_counter() - t0
    print("\n" + "=" * 105)
    print(f"🎉 Master Local Model Roster Evaluation Complete in {dt_total:.3f} s!")


def main() -> None:
    asyncio.run(evaluate_full_roster())


if __name__ == "__main__":
    main()
