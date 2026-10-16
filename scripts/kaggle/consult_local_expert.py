"""
Consult local silicon model on Lemonade (Qwen3.6-35B-A3B-MTP-GGUF) with ample tokens (4096)
and full reasoning time ('leave plenty of time for the fat to render') to evaluate the optimal
next steps across our active Kaggle competitions.
"""

import json
import sys
import httpx

LEMONADE_URL = "http://localhost:13305/v1/chat/completions"
MODEL_NAME = "llama3.2-1b-FLM"

SYSTEM_PROMPT = """You are the Senior Kaggle Grandmaster and Autoresearch Strategist for Cohezion.
Your job is to evaluate active Kaggle competitions, analyze why previous submissions succeeded or plateaued,
and recommend the highest-leverage actions to maximize leaderboard rank and prize ascent.

Context on our active competitions (as of October 2, 2026):
1. RSNA Knee Abnormality Detection ($77,000, deadline Oct 22, 20 days left):
   - Current rank: 426 / 4,877 (Top 8.7%). Best score: 0.943 (Top 10 cutoff ~0.957).
   - In v20, score regressed from 0.943 to 0.939 when slice count was increased from 16 to 32 (introducing stride decimation on pretrained Raptor/CoAtNet weights) and probability clipping flattened ROC-AUC rank statistics.
   - We patched v21: restored native 16-slice fidelity (`TARGET_CACHE_SLICES = 16`), pure intra-class quantile rank normalization (`.rank(method='average', pct=True)`), and Kolmogorov monotonicity projection P(Abnormal) >= max_k P_k.
   - Hardware: NvidiaL4 GPU on Kaggle.

2. ARC Prize 2026: ARC-AGI-2 ($700,000, deadline Nov 2, 31 days left):
   - Current rank: 223 / 2,337 (Top 9.5%). Best score: 31.81% (Top 10 cutoff 33.89%, gap is +2.08%, approx 2-3 puzzle tasks).
   - Qwen3-4B LoRA SFT139 + Unsloth Test-Time Training (TTT) on 4x NVIDIA L4 GPUs.
   - Zero-False-Prune AutoHarness Rule ensures only mathematically impossible candidate grids are pruned (dimensions outside 1..30, non-rectangular, illegal color IDs).
   - Recent run 56653596 dipped to 29.31% due to overly strict pruning.

3. ARC Prize 2026: ARC-AGI-3 Interactive Agent ($850,000, deadline Nov 2, 31 days left):
   - Current rank: 2,075 / 3,590. Best score: 0.26 (v15 Directed Affordance Rarity SearchAgent).
   - Later versions (v22-v25) drifted down to 0.07-0.08 due to over-constraining the step budget and cycle evasion deadlocks.
   - Kaggle provides UNLIMITED CPU compute hours (up to 10 concurrent CPU sessions, 0 GPU quota used).

4. Enveda CASMI26 Molecule ID from Mass Spectra ($50,000, deadline Dec 14, 73 days left):
   - Current rank: 930 / 2,142. Best score: 0.328 MRR (Top 10 is 0.383, gap +0.055).
   - 4-Channel Mass-Shifted Analog Propagation + FPNet Neural Reranking.

Important constraints:
- Biohub and Kaggriculture are CLOSED. Pokémon TCG is explicitly EXCLUDED.
- We have 0 submissions sent between Sept 28 and Oct 2; 5/5 daily submission quota is completely unused for today!
- Quality over speed: reason deeply through trade-offs, edge cases, and execution sequence.
"""

USER_PROMPT = """Analyze the active competition portfolio and provide a comprehensive, unhurried strategic roadmap:
1. RSNA Knee Abnormality Detection:
   - Critically evaluate why 16-slice vs 32-slice input changes representation quality for 2D/3D hybrid backbones.
   - Explain why ROC-AUC requires rank normalization over probability calibration.
   - Verify if v21 is ready to push and submit immediately.

2. ARC-AGI-2:
   - How to bridge the +2.08% gap into the Top 10 (33.89%).
   - What specific beam search and AutoHarness invariant scoring rules should be active?

3. ARC-AGI-3:
   - How to exploit Kaggle's unlimited CPU compute quota without touching GPU quota.
   - How to restore the v15 0.26 score and push beyond 0.30+ using Go-Explore and Zobrist state hashing.

4. Execution Order & Daily Quota Dispatch:
   - What is the optimal sequence to push and submit today across all 4 competitions?
"""

def main():
    print(f"Connecting to Lemonade server at {LEMONADE_URL}...")
    print(f"Consulting resident expert model: {MODEL_NAME}")
    print("Allocating up to 4096 tokens with 300s timeout for deep reasoning...")

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT}
        ],
        "temperature": 0.6,
        "max_tokens": 4096,
        "stream": False
    }

    try:
        with httpx.Client(timeout=httpx.Timeout(connect=15.0, read=300.0, write=30.0, pool=10.0)) as client:
            response = client.post(LEMONADE_URL, json=payload)
            response.raise_for_status()
            data = response.json()
            
            content = data["choices"][0]["message"]["content"]
            print("\n=== LOCAL GRANDMASTER CONSULTATION RESPONSE ===\n")
            print(content)
            print("\n=== END CONSULTATION ===\n")
            
            # Save consultation to disk
            out_file = "scripts/kaggle/local_expert_consultation_20261002.md"
            with open(out_file, "w") as f:
                f.write(f"# Local Grandmaster Consultation ({MODEL_NAME})\n\n")
                f.write(f"**Date**: 2026-10-02\n**Tokens allocated**: 4096\n\n")
                f.write(content)
            print(f"Saved consultation transcript to {out_file}")

    except Exception as e:
        print(f"Error querying Lemonade: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
