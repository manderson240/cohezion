# AMD ROCm FastFlowLM (FLM v1.0.4) on XDNA2 NPU Architecture

## 1. Executive Summary

AMD ROCm FastFlowLM (`FLM`) is an official, purpose-built NPU runtime engineered specifically for AMD Ryzen AI XDNA2 neural processing units (Strix Point, Strix Halo, Kraken Point, Gorgon Point).

On the **AMD Strix Halo** platform (128GB unified DDR5 memory, Ryzen 9 7945HX, Radeon 8060S iGPU, XDNA2 NPU), FastFlowLM provides an isolated, ultra-efficient inference tier operating with **<2W power consumption**, **0 UMA RAM contention**, and **0 CPU/iGPU resource consumption**.

Repository: `https://github.com/ROCm/FastFlowLM`

---

## 2. Hardware Topology & System Specs

Hardware telemetry validated on the active system:

| Metric | Measured Value | Operational Role |
|---|---|---|
| **NPU Device** | `/dev/accel/accel0` | Dedicated hardware device node |
| **Compute Columns** | 8 Columns | Parallel spatial execution lanes |
| **Firmware Version** | `1.1.2.65` | NPU microcode / scheduler |
| **Driver Stack** | `amdxdna v0.7` | Kernel acceleration driver |
| **Memlock Limit** | `infinity` | Zero-copy locked memory pool |
| **Power Profile** | `<2.0 W` | Continual 24/7 background operation |
| **Host Port (Default)**| `52625` (FLM) / `13305` (Lemonade) | API service endpoints |

---

## 3. Installed Model Catalog

FLM stores models in `~/.config/flm/` (override with `FLM_MODEL_PATH`).
Installed models on this Strix Halo node:

| Model ID | Architecture | Context | Primary Deployment Role |
|---|---|---|---|
| `llama3.2:1b` | LLaMA 3.2 1B | 4,096 | Fast reflexive routing, classification (~24ms TTFT) |
| `deepseek-r1-0528:8b` | DeepSeek R1 8B Distill | 40,960 | High-depth mathematical & algorithmic reasoning |
| `qwen3.5:4b` | Qwen 3.5 4B Dense | 32,768 | General code synthesis & tool calling |
| `qwen3.6-moe:35b-a3b` | Qwen 3.6 MoE 35B (3B active) | 16,384 | Flagship MoE architecture & multi-agent synthesis |
| `gemma3:4b` | Gemma 3 4B VLM | 65,536 | Vision-language and multimodal reasoning |

---

## 4. Operational Commands & Flags

```bash
# Validate hardware stack
flm validate

# Interactive CLI execution
flm run llama3.2:1b

# Serve model on HTTP
flm serve llama3.2:1b --pmode balanced --ctx-len 8192 --port 52625

# Run concurrent embeddings alongside model
flm serve llama3.2:1b --embed 1

# List installed models
flm list --filter installed
```

---

## 5. Structured Decoding: The BAML + AutoHarness Solution

### The Sampler Invariant
- GBNF grammar constraints are a **llama.cpp** sampler feature.
- FastFlowLM is an independent from-scratch C++ NPU runtime. It accepts and silently discards unknown parameters such as `grammar`.
- Direct `json.loads()` on raw FLM output will fail whenever the model emits Markdown code fences or plain-text key-value summaries.

### The Solution
1. **Instruction Schema Conditioning**: Prompts explicitly format requested keys.
2. **BAML Resilient Schema Parsing** (`src/cohezion/baml/baml_bridge.py`):
   - Strips `<think>` tokens.
   - Cleans Markdown fences (` ```json `).
   - Heals unclosed braces and balances syntax.
   - Performs heuristic field extraction against YAML/Markdown key-value outputs (`Node: GPU\nConfidence: 0.85`).
3. **AutoHarness Bytecode Verification** (`src/cohezion/agi/autoharness_policy.py`):
   - Verifies required schema keys and types deterministically in **<1 ms**.
4. **Adaptive Fallback Cascade**:
   - If strict token-level grammar forcing is mandated (`strict_sampler=True`), requests route automatically to resident `llamacpp` models (`Bonsai-8B-gguf`, `Qwen3-Coder-30B-A3B-Instruct-GGUF`).
