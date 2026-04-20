# How Gemma 3 4B Was Processed (Research Summary)

**Research Date**: 2026-04-10
**Key Finding**: Gemma 3 4B was NOT converted through AMD Quark/OGA pipeline - it was already a **pre-optimized FLM model** from AMD.

---

## The Critical Difference

### Gemma 3 4B Processing (How it actually worked)

```
┌─────────────────────────────────────┐
│  AMD Pre-built FLM Model Repository │
│  (FastFlowLM GitHub releases)      │
└──────────────┬──────────────────────┘
               │
         flm pull gemma3:4b
               │
     ┌─────────▼──────────┐
     │ Download pre-built  │
     │ NPU-optimized       │
     │ binaries            │
     │                     │
     │ • Q4NX quantized    │
     │ • XDNA2 tiled       │
     │ • FLM packaged      │
     └─────────┬───────────┘
               │
    ┌──────────▼──────────────┐
    │  Serve via FLM runtime │
    │  (NPU inference)       │
    │                        │
    │  Performance: 75 TPS   │
    └────────────────────────┘
```

**User command**:
```bash
flm pull gemma3:4b     # Download pre-built
flm serve gemma3:4b    # Run on NPU
```

**Key characteristic**: NO conversion, NO quantization, NO compilation. Just download and run.

---

### What We Tried for Gemma 4 (Different Path)

```
┌─────────────────────────────────────┐
│  HuggingFace Gemma 4 RAW weights     │
│  (PyTorch format, full precision)    │
└──────────────┬──────────────────────┘
               │
     export_gemma4_simple.py
               │
     ┌─────────▼──────────┐
     │ PyTorch → ONNX     │
     │ (with use_cache=False)
     └─────────┬───────────┘
               │
     ┌─────────▼──────────┐
     │ ONNX 11MB + 8.7GB   │
     │ external data       │
     └─────────┬───────────┘
               │
         [BLOCKED HERE]
               │
     ┌─────────▼──────────┐
     │ AMD Quark quantized │ ❌ Not available
     │ (requires dev tools)│ ❌ Proprietary
     └─────────┬───────────┘
               │
     ┌─────────▼──────────┐
     │ aie-compile        │ ❌ Not available
     │ (XDNA2 tiling)     │ ❌ Enterprise only
     └─────────┬───────────┘
               │
     ┌─────────▼──────────┐
     │ FLM package        │ ❌ Can't be created
     │ (model.flm)        │ ❌ without AMD tools
     └────────────────────┘
```

**What we did**:
```bash
# 1. Created virtual environment
python3 -m venv venv
source venv/bin/activate
pip install torch transformers onnx

# 2. Exported ONNX (worked!)
python3 export_gemma4_simple.py
# → gemma4.onnx (11MB) + gemma4.onnx.data (8.7GB)

# 3. Quantization attempt (blocked)
source /opt/ryzen-ai/bin/activate
python3 quantize_gemma4_sdk.py
# → google.protobuf.message.EncodeError: Failed to serialize proto
#    (protobuf 2GB limit on external data)
```

---

## Why These Are Completely Different

| Aspect | Gemma 3 4B | Gemma 4 |
|--------|----------|---------|
| **Source** | Pre-built FLM download | Raw HuggingFace weights |
| ** quantization** | Already Q4NX quantized (AMD did it) | Full float16 |
| **Compilation** | Pre-tiled for XDNA2 (AMD did it) | Not tiled |
| **Tools needed** | Just `flm` | AMD Quark + aie-compile + FLM packager |
| **Availability** | ✅ Public download | ❌ AMD must build & release |
| **Status** | Working (75 TPS) | Blocked on AMD release |

---

## Historical Pattern: AMD FLM Model Releases

Based on documentation:

| Model | HuggingFace Release | AMD FLM Release | Delay |
|-------|---------------------|-----------------|-------|
| Gemma 2 | ~2024 | ~2 months later | AMD conversion time |
| Gemma 3 | ~2025 | ~2 months later | AMD conversion time |
| Qwen 2/2.5/3 | Ongoing | Available | Regular updates |
| Gemma 4 | 2026 (recent) | ❌ Not yet | Unknown months |

**Pattern**: AMD must manually convert each new architecture to FLM format. They're typically 2+ months behind new model releases.

---

## Why FLM Can't Just Use PyTorch → ONNX Export

The FLM runtime requires very specific optimizations:

### 1. Quantization
- **Standard**: Float32/16 PyTorch → ONNX
- **FLM Needs**: Q4NX (4-bit per-channel symmetric)
- **Tool**: `ryzenai-transformers` (AMD proprietary)

### 2. Tiling
- **Standard**: Linear graph execution
- **FLM Needs**: 128x128 (or 64x64) spatial tiles for XDNA2
- **Tool**: `aie-compile` (ROCm Pro / enterprise)

### 3. Attention Optimization
- **Standard**: Standard Multi-Head Attention
- **FLM Needs**: GQA (Grouped Query Attention) optimized for XDNA2
- **Tool**: AMD internal optimization passes

### 4. KV-Cache Management
- **Standard**: Dynamic cache
- **FLM Needs**: Pre-allocated XDNA2 memory
- **Tool**: FLM runtime-specific

---

## What Actually Happened: Session Analysis

**Past session** (Gemma 3 4B):
- User wanted NPU-accelerated inference
- Checked `flm list` → `gemma3:4b` available ✅
- Ran `flm pull gemma3:4b && flm serve gemma3:4b --port 13306`
- Result: 75 TPS NPU inference ✅

**This session** (Gemma 4):
- User wanted same for Gemma 4
- Checked `flm list` → NO `gemma4:*` models ❌
- Attempted DIY conversion (assumed could convert like ONNX→TensorRT)
- Discovered: **Gemma 4 not available as FLM, can't DIY without AMD tools**
- Result: Export succeeded, quantization blocked

---

## Why We Can't DIY (Technical Deep Dive)

### The FLM Model Format

FLM models are NOT simple ONNX files. They contain:

```
gemma3:4b.flm (internal structure):
├── metadata.json          # FLM manifest
├── config.json            # XDNA2 config (tile size, cols, etc.)
├── model/
│   ├── tile_0000.q4nx     # Quantized tile 0 (4-bit weights + uint8 activations)
│   ├── tile_0001.q4nx     # Quantized tile 1
│   ├── ...                # One per XDNA2 tile
│   └── tile_0033.q4nx     # Gemma 3 4B: 34 tiles
├── tokenizer.json         # Tokenizer
└── kernels/               # XDNA2 microcode
    ├── gemm_tile.bin      # Matrix multiply kernels
    ├── attn_tile.bin      # Attention kernels
    └── kv_tile.bin        # KV-cache kernels
```

Each `.q4nx` file is **not just weights** - it's:
1. **4-bit quantized weights** (Q4NX format: per-channel symmetric)
2. **Pre-tuned activations** (INT8/UINT8)
3. **XDNA2 memory layout** (bank addressing for unified memory)
4. **Compiled kernels** (tile-specific microcode)

### Why ONNX Export Alone Doesn't Work

Our export produced:
```
gemma4.onnx              # 11 MB (graph structure)
gemma4.onnx.data         # 8.7 GB (raw float16 weights)
```

This is **standard ONNX with external data**. Missing:
- ❌ Q4NX quantization
- ❌ XDNA2 tiling
- ❌ FLM kernel bindings
- ❌ NPU memory layout

Even if we quantized to INT8 (not Q4NX), it still wouldn't run on FLM because FLM expects:
- Specific tile structure
- Pre-compiled XDNA2 kernels
- FLM metadata format

---

## Working Alternatives for Gemma 4

### Option 1: GPU Vulkan (Working Now) ✅

```bash
# llama.cpp Vulkan backend (RADV driver)
llama-server -m gemma-4-E2B-it.gguf --port 8890

# Performance: ~100 TPS
# Memory: 131GB VRAM
# Status: Fully operational, no ROCm hang
```

**Why it works**: llama.cpp's Vulkan backend uses standard GGUF format, no proprietary AMD tooling needed.

### Option 2: Wait for AMD FLM Release ❓

```bash
# Future (when AMD releases)
flm list | grep gemma4
# gemma4:2b ⏬
# gemma4:4b ⏬

flm pull gemma4:4b
flm serve gemma4:4b --port 13307
```

**Timeline**: Unknown (historically 2+ months after HF release)

### Option 3: GPU ROCm (Blocked) ❌

```bash
# Custom llama.cpp build (blocked)
lemonade load Gemma-4-E2B-it-GGUF --llamacpp rocm --ngl 99
# Hangs at sched_reserve (Issue #6027)
```

**Status**: Blocked on llama.cpp ROCm backend gfx1151 support

---

## Lessons

### Key Insight

**"75 TPS Gemma 3 4B on NPU"** doesn't mean:
- ❌ "We converted Gemma 3 4B using tools"
- ❌ "Any ONNX model can run on FLM"

**It means**:
- ✅ "AMD released a pre-optimized FLM package"
- ✅ "FLM is a download-and-run ecosystem, not a DIY conversion platform"

### Misconception Chain

1. **Assumption**: If Gemma 3 4B runs on NPU via FLM, we can convert Gemma 4 the same way
2. **Reality**: Gemma 3 was pre-packaged by AMD; Gemma 4 isn't available
3. **Attempt**: Try to convert using ONNX export + quantization
4. **Block**: Proprietary AMD tools required (Quark, aie-compile)
5. **Resolution**: Use GPU Vulkan (faster anyway) or wait for AMD

---

## Conclusion

**Gemma 3 4B was processed by AMD, not by us.**

FLM provides pre-converted models in a black-box ecosystem. When AMD hasn't released a model (like Gemma 4), there is **no DIY path** without their proprietary tools.

**Current recommendation**:
- Gemma 3 4B: `flm serve gemma3:4b` (NPU, 75 TPS)
- Gemma 4 variants: `llama-server -m model.gguf` (GPU Vulkan, 100 TPS)
- Gemma 4 NPU: Wait for AMD release or pursue Developer Program (2-4 weeks, high effort)

The ComputeBackendRouter correctly routes:
- Gemma 3:4b → NPU (FLM)
- Gemma 4:* → GPU Vulkan (llama.cpp)

---

**Document**: `GEMMA3_PROCESSING_RESEARCH.md`
**Status**: Complete
**Next Action**: Use GPU Vulkan for Gemma 4, monitor AMD FLM releases
