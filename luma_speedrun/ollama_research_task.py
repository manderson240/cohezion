"""Autonomous kernel optimization research via Ollama (gemma4:31b).

This script runs independently of Claude, using local Ollama models to:
1. Research FP4 MFMA 32x32 register layouts by analyzing AMD ISA docs
2. Generate candidate kernel code for testing
3. Write results to files for next Claude session to pick up

Usage: python3 luma_speedrun/ollama_research_task.py
"""
import json, time, os
from urllib.request import Request, urlopen
from pathlib import Path

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "gemma4:31b"
OUTPUT_DIR = Path("luma_speedrun/ollama_research")
OUTPUT_DIR.mkdir(exist_ok=True)

def ask_ollama(prompt, max_tokens=4096):
    payload = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "stream": True,
        "options": {"num_predict": max_tokens, "temperature": 0.3},
    }).encode()
    req = Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"})
    chunks = []
    try:
        with urlopen(req, timeout=300) as resp:
            for line in resp:
                if not line.strip(): continue
                data = json.loads(line)
                chunks.append(data.get("response", ""))
                if data.get("done"): break
    except Exception as e:
        return f"ERROR: {e}"
    return "".join(chunks)

# Task 1: Research FP4 MFMA 32x32 register layout
print(f"[{time.strftime('%H:%M:%S')}] Task 1: Researching FP4 MFMA register layout...")
q1 = """You are an AMD GPU kernel optimization expert. 

I have verified that the BF16 MFMA 16x16x16 instruction (__builtin_amdgcn_mfma_f32_16x16x16bf16_1k) on AMD gfx950 (MI355X) has this output mapping:
- c_reg[j] maps to output C[(tid/16)*4 + j][tid % 16]  
- That is: 4 consecutive ROWS at a single COLUMN per thread

Now I need the output mapping for the FP4 MFMA 32x32x64 instruction:
__builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4

The AMD blog shows this write pattern for the 32x32 output:
C[threadIdx.x % 32 + (threadIdx.x / 32) * 4 * 32 + i * 32 * 8]

But this DOES NOT produce correct results when I use it.

Given that the 16x16 BF16 MFMA uses column-major output (rows vary, column fixed per thread), what are ALL possible output mappings for the 32x32 FP4 MFMA? The instruction produces 16 f32 values per thread across 64 threads = 1024 values = 32x32 output.

Please list the most likely register-to-output mappings, considering:
1. The blog pattern writes to row = (tid/32)*4 + j + i*8 and col = tid%32
2. An alternative column-major pattern where col = (tid/32)*something and row depends on tid%32
3. Any other patterns consistent with CDNA4 wavefront architecture

For each pattern, show the exact C++ code for the epilogue (write-back from c_reg to output matrix C).
"""
r1 = ask_ollama(q1)
(OUTPUT_DIR / "task1_mfma_register_layout.md").write_text(f"# FP4 MFMA Register Layout Research\n\nModel: {MODEL}\nTimestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n{r1}")
print(f"[{time.strftime('%H:%M:%S')}] Task 1 done, saved to ollama_research/task1_mfma_register_layout.md")

# Task 2: Research per_1x32_f4_quant_hip usage
print(f"[{time.strftime('%H:%M:%S')}] Task 2: Researching per_1x32_f4_quant_hip...")
q2 = """I discovered that the AMD aiter library on MI355X has a function called per_1x32_f4_quant_hip.
This is a HIP-native FP4 quantization function that might be faster than the Triton-based dynamic_mxfp4_quant.

The current GEMM pipeline is:
1. A = bf16 input [M, K]
2. A_fp4, A_scale = dynamic_mxfp4_quant(A)  # Triton kernel, ~5us
3. A_scale_sh = e8m0_shuffle(A_scale)
4. result = gemm_a4w4(A_fp4, B_shuffle, A_scale_sh, B_scale_sh)

How would I use per_1x32_f4_quant_hip to replace step 2? 
What is the likely function signature based on the name pattern?
Could this save the ~5us Triton dispatch overhead?

Also: aiter has gemm_a4w4_asm(A, B, A_scale, B_scale, out, kernelName, bias, alpha, beta, bpreshuffle, log2_k_split).
What values of log2_k_split should I try for shapes like M=8 K=7168 N=2112?
"""
r2 = ask_ollama(q2)
(OUTPUT_DIR / "task2_hip_quant_and_ksplit.md").write_text(f"# HIP Quant + K-Split Research\n\nModel: {MODEL}\nTimestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n{r2}")
print(f"[{time.strftime('%H:%M:%S')}] Task 2 done")

# Task 3: Research ck_moe_stage1/stage2 direct dispatch
print(f"[{time.strftime('%H:%M:%S')}] Task 3: Researching CK MoE direct dispatch...")
q3 = """I'm optimizing an MoE (Mixture of Experts) kernel on AMD MI355X for a competition.
Current best is 154us using aiter.fused_moe(). The leader is at 107us.

I discovered these direct CK dispatch functions on the runner:
- aiter.ck_moe_stage1()
- aiter.ck_moe_stage1_fwd()
- aiter.ck_moe_stage2()
- aiter.ck_moe_stage2_fwd()
- aiter.moe_sorting_fwd()
- aiter.moe_sorting_opus_fwd()

The fused_moe Python wrapper does: sorting -> stage1 GEMM -> SiLU activation -> stage2 GEMM.
If I call ck_moe_stage1 and ck_moe_stage2 directly (bypassing fused_moe), I might save Python overhead.

What are the likely function signatures for ck_moe_stage1 and ck_moe_stage2?
What tensors do I need to prepare (sorted_token_ids, expert_ids, etc.)?
How does the sorting work with moe_sorting_fwd?

The data format is MXFP4 (per_1x32 quantized, shuffled weights).
"""
r3 = ask_ollama(q3)
(OUTPUT_DIR / "task3_ck_moe_dispatch.md").write_text(f"# CK MoE Direct Dispatch Research\n\nModel: {MODEL}\nTimestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n{r3}")
print(f"[{time.strftime('%H:%M:%S')}] Task 3 done")

print(f"\n[{time.strftime('%H:%M:%S')}] All research tasks complete. Results in luma_speedrun/ollama_research/")
