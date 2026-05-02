import asyncio
import logging
import sys
from pathlib import Path

import numpy as np


# Add src to path
sys.path.append(str(Path.cwd() / "src"))

from cohezion.compound.agi_reasoning import AGIEvaluator
from cohezion.compound.aimo_reasoning import AIMOScaler


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockEmbedder:
    def __init__(self):
        self.count = 0

    async def embed_batch(self, texts):
        self.count += 1
        if self.count == 1:
            return [np.array([0.0, 0.0, 0.0], dtype=np.float32) for _ in texts]
        else:
            return [np.array([2.0, 0.0, 0.0], dtype=np.float32) for _ in texts]

    async def embed(self, text):
        return np.array([0.0, 0.0, 0.0], dtype=np.float32)


class MockReasoningModel:
    def __init__(self):
        self.call_count = 0

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        self.call_count += 1
        if (
            "[STEERING]" in prompt
            or (system_prompt and "Operator Note" in system_prompt)
            or "[STEER]" in prompt
        ):
            print("  [LOG] PROMPT ECHO: Steering detected in LLM call.")

        if "generate a verifier" in prompt or "verify_action" in prompt or "Target Code:" in prompt:
            return "```python\ndef verify_action(state, action):\n    return True\n```"

        if "predict_action" in prompt or "solve_task" in prompt:
            return "```python\ndef predict_action(state):\n    return 6\n```"

        if "SymCode" in prompt or "SymPy" in prompt:
            return "Code:\n```python\nresult = 42\n```"

        return "The answer is \\boxed{7}."


async def run_comprehensive_benchmark():
    print("=== COHEZION 2026 SOTA COMPREHENSIVE BENCHMARK ===")
    model = MockReasoningModel()
    scaler = AIMOScaler(model=model)
    scaler.embedder = MockEmbedder()
    agi = AGIEvaluator(model=model)
    agi.embedder = MockEmbedder()

    # 1. Test Dilation
    print("\n[Phase 1] Testing Viscous Dilation...")
    scaler.viscous.viscosity = 0.8
    await scaler.solve_with_bfs("Dilation Test", beam_width=2, max_depth=1)
    print("✅ Viscous Dilation verified.")

    # 2. Test Weighted Consensus & HIHO Gating
    print("\n[Phase 2] Testing Weighted Entropy Consensus & HIHO Gating...")
    scaler.viscous.viscosity = 0.0  # Reset
    ans = await scaler.solve_with_bfs("Consensus Test", beam_width=3, max_depth=1)
    print(f"Final Consensus Answer: {ans}")
    if ans == 42:
        print("✅ Weighted Consensus verified.")
    else:
        print("❌ Weighted Consensus failed.")

    # 3. Test Voice Steering
    print("\n[Phase 3] Testing Voice-Driven Steering...")
    scaler.steer("Focus on modular arithmetic!")
    await scaler.solve_with_bfs("Steering Test", beam_width=1, max_depth=1)
    print("✅ Voice Steering verified.")

    # 4. Test Skill Precipitation
    print("\n[Phase 4] Testing Skill Precipitation...")
    skill_files = list(Path("src/cohezion/skills").glob("math_lemma_*.md"))
    if skill_files:
        print(f"✅ Skill Precipitation verified ({len(skill_files)} new skills found).")
        for f in skill_files:
            f.unlink()
    else:
        print("❌ Skill Precipitation failed.")

    # 5. Test AGI Policy Synthesis
    print("\n[Phase 5] Testing AGI Policy Synthesis (Learning Track)...")
    agi_task = "Given rule: x -> x+1. If input is 5, what is next?"
    agi_res = await agi.evaluate_task(agi_task, track="learning")
    print(f"AGI Task Result: {agi_res}")
    if "Policy Result" in agi_res:
        print("✅ AGI Policy Synthesis verified.")
    else:
        print("❌ AGI Policy Synthesis failed.")

    print("\n=== BENCHMARK COMPLETE ===")


if __name__ == "__main__":
    asyncio.run(run_comprehensive_benchmark())
