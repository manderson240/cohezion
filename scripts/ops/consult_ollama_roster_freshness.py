#!/usr/bin/env python3
"""Consult Ollama Cloud models on the exact 2026-08-21 local model roster alignment for AMD Strix Halo & https://github.com/amd/skills standards."""

import json
import time
import urllib.request


prompt = """
You are a Principal AI Hardware & Systems Architect reviewing an AMD Strix Halo deployment as of August 21, 2026.
System specs: AMD Ryzen AI MAX+ 395 w/ Radeon 8060S, 128GB Unified Memory, XDNA2 NPU (50 TOPS), RDNA 3.5 iGPU (40 CUs), Zen 5 CPU.
Integration: Official AMD Skills repository (https://github.com/amd/skills) + Lemonade Server (:13305).

Review our active local model roster as of August 21, 2026:
1. Fast Conversational Chat (NPU): `qwen3.6-moe-35b-a3b-FLM` (35B total, 3B active, 256k ctx) + `waslmedia-qwen3-4b-Q4_K_M`
2. Coding & Agentic Tool Execution (iGPU): `Qwen3-Coder-30B-A3B-Instruct-GGUF` (Vulkan/ROCm)
3. Deep Diagnostic Reasoning (Reasoning): `deepseek-r1-0528-8b-FLM`
4. Speech & Voice (Lemonade native): `Whisper-Large-v3-Turbo` (STT) + `kokoro-v1` (TTS) (Aligned with official AMD local-ai-use skill)
5. Image Diffusion: `SD-Turbo` / `TRELLIS-3D` (Aligned with official AMD local-ai-use skill)
6. Embeddings: `lfm25-embed-350m` (1024D, 128k ctx) + `embed-gemma-300m-FLM` (NPU)

Questions to evaluate:
A. Are these the exact right, high-performing open-weights models for this AMD hardware configuration as of August 21, 2026?
B. How cleanly does this setup align with the official AMD skills repository guidelines (https://github.com/amd/skills)?
C. Are there any immediate model drop-in replacements that provide strictly superior throughput or accuracy on AMD Strix Halo today?
"""

def query_model(model_name: str):
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False
    }
    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload).encode("utf-8")
    )
    print(f"Querying {model_name} on port 11434...")
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            dt = time.perf_counter() - t0
            data = json.loads(resp.read().decode("utf-8"))
            res_text = data.get("response", "")
            print(f"✓ Received response from {model_name} in {dt:.2f}s ({len(res_text)} chars)")
            return res_text
    except Exception as e:
        print(f"✗ Error querying {model_name}: {e}")
        return f"Error: {e}"

res_glm = query_model("glm-5.2:cloud")

with open("/home/mike-anderson/dev/cohezion/docs/research/amd_skills_model_roster_audit_20260821.md", "w", encoding="utf-8") as f:
    f.write("# AMD Skills & 2026-08-21 Local Model Roster Audit\n\n")
    f.write("**Audit Date**: 2026-08-21\n")
    f.write("**Target System**: AMD Ryzen AI MAX+ 395 w/ Radeon 8060S (128GB Unified Memory)\n")
    f.write("**Official Repository**: `https://github.com/amd/skills` (`src/cohezion/skills/amd/skills-repo/`)\n\n---\n\n")
    f.write(res_glm)

print("✓ Saved audit report to docs/research/amd_skills_model_roster_audit_20260821.md")
