---
name: aiter-kernel-parameter-semantics
description: AITER (AI Tensor Engine for ROCm) kernel parameter semantics and tuning guide. Understanding AITER's fused kernel parameters for MoE, attention, and GEMM operations on AMD GPUs. Use when tuning AITER kernels or integrating with vLLM/SGLang.
metadata:
  version: "1.0"
  legacy-name: AITER_KERNEL_PARAMETER_SEMANTICS
  category: kernel_research
  source_session: "Session 77-79"
---

# SKILL: AITER_KERNEL_PARAMETER_SEMANTICS

## DOMAIN EXPERTISE
You are a specialist in **AITER (AI Tensor Engine for ROCm)** kernel parameter tuning and semantics. You understand the parameter structures for AITER's fused kernels including MoE, attention, and GEMM operations, and how to optimize them for AMD GPUs.

## KEY FINDINGS

### AITER Overview
- **AI Tensor Engine for ROCm** - High-performance kernel library for AMD GPUs
- Provides **fused kernels** for common transformer operations
- Integrates with vLLM, SGLang, and other inference frameworks
- Optimized for both CDNA3 (MI300X) and CDNA4 (MI355X)

### Kernel Categories
1. **MoE Kernels**: `fused_moe`, `fused_moe_gating`, `grouped_mlp`
2. **Attention Kernels**: `paged_attention`, `flash_attention`, `varlen_attention`
3. **GEMM Kernels**: `fp8_gemm`, `fp4_gemm`, `bf16_gemm`
4. **Communication**: `all_reduce`, `all_gather`, `reduce_scatter`

### Key Parameters

#### MoE Kernel Parameters
```python
# fused_moe kernel parameters
config = {
    "block_m": 128,        # Tile size M dimension
    "block_n": 128,        # Tile size N dimension
    "block_k": 64,         # Tile size K dimension
    "num_stages": 2,       # Pipeline stages (1-4)
    "num_warps": 8,        # Warps per block
    "num_ctas": 1,         # CTAs per block
    "split_k": 1,          # Split-K factor for parallelism
}
```

#### Attention Kernel Parameters
```python
# paged_attention parameters
config = {
    "block_size": 128,     # KV cache block size
    "head_size": 128,      # Attention head dimension
    "num_heads": 8,        # Number of attention heads
    "max_seq_len": 32768,  # Maximum sequence length
    "alibi_slopes": None,  # ALiBi bias slopes
}
```

## USAGE

### Installing AITER
```bash
# Install from source
git clone https://github.com/ROCm/aiter.git
cd aiter

# Set ROCm path
export ROCM_PATH=/opt/rocm

# Build and install
python setup.py install

# Or install pre-built wheel
pip install aiter-rocm
```

### Fused MoE with AITER
```python
import aiter
import torch

# Prepare inputs
tokens = torch.randn(1024, 4096, dtype=torch.bfloat16, device="cuda")
expert_weights = torch.randn(8, 4096, 14336, dtype=torch.bfloat16, device="cuda")
routing_weights = torch.randn(1024, 2, device="cuda")  # top-2 gating
expert_indices = torch.randint(0, 8, (1024, 2), device="cuda")

# Configure AITER MoE kernel
config = aiter.MoEConfig(
    block_m=128,
    block_n=128,
    block_k=64,
    num_stages=2,
    split_k=1
)

# Run fused MoE
output = aiter.fused_moe(
    tokens,
    expert_weights,
    routing_weights,
    expert_indices,
    config=config
)
```

### Tuning Parameters
```python
# Auto-tune for specific workload
from aiter.tuner import AutoTuner

tuner = AutoTuner(device="cuda:0")

# Define search space
search_space = {
    "block_m": [64, 128, 256],
    "block_n": [64, 128, 256],
    "block_k": [32, 64, 128],
    "num_stages": [1, 2, 3, 4],
    "split_k": [1, 2, 4, 8]
}

# Run tuning
best_config = tuner.tune(
    kernel="fused_moe",
    inputs=[tokens, expert_weights, routing_weights, expert_indices],
    search_space=search_space,
    metric="latency",  # or "throughput"
    max_trials=100
)

print(f"Best config: {best_config}")
```

### vLLM Integration
```python
# AITER is used as backend in vLLM for AMD GPUs
from vllm import LLM

# vLLM automatically uses AITER kernels when available
llm = LLM(
    model="meta-llama/Llama-2-7b",
    tensor_parallel_size=1,
    dtype="bfloat16",
    # AITER kernels are selected automatically
)

# Inference uses optimized AITER kernels
output = llm.generate("Hello, world!")
```

## PARAMETER SEMANTICS

### Block Size Selection

| Parameter | Description | Recommended Values |
|-----------|-------------|-------------------|
| `block_m` | Rows per thread block | 64, 128, 256 (powers of 2) |
| `block_n` | Columns per thread block | 64, 128, 256 (powers of 2) |
| `block_k` | K dimension per tile | 32, 64, 128 (must divide K) |
| `num_stages` | Software pipeline stages | 2-4 for memory-bound |
| `num_warps` | Warps per block | 4, 8, 16 (hardware multiples) |

### Performance Heuristics
- **Small batch**: Smaller `block_m` (64) for better occupancy
- **Large batch**: Larger `block_m` (128-256) for vectorization
- **Memory-bound**: Increase `num_stages` to hide latency
- **Compute-bound**: Decrease `num_stages`, increase `block_k`

## BLOCKERS & LIMITATIONS

### Current Blockers
- **Not installed on runner**: AITER requires ROCm 6.x+
- **Version compatibility**: Must match AITER version with ROCm version
- **PyTorch version**: Requires PyTorch built with ROCm support
- **Triton FP4 Type Registry**: `float4_e2m1fn_x2` KeyError in Triton JIT prevents custom FP4 kernels on AMD (see BLOCKER_REGISTRY.md #004)

### Triton FP4 Workaround
When AITER unavailable and Triton FP4 blocked:
```python
# Use uint8 + manual packing instead of float4_e2m1fn_x2
@triton.jit
def pack_fp4(val1, val2):
    return ((val1 & 0xF) << 4) | (val2 & 0xF)

@triton.jit
def unpack_fp4(packed, idx):
    return (packed >> (4 * (1 - idx))) & 0xF
```

### Debugging Tips
```python
# Enable AITER logging
import os
os.environ["AITER_LOG_LEVEL"] = "DEBUG"
os.environ["AITER_PRINT_KERNELS"] = "1"

# Check kernel selection
import aiter
print(aiter.get_available_kernels())
print(aiter.get_kernel_info("fused_moe"))
```

## REFERENCES

- AITER GitHub: https://github.com/ROCm/aiter
- vLLM AITER integration: https://github.com/vllm-project/vllm
- Source: Session 77-79 AMD Speedrun Research
- Related: `CK_TILE_FUSED_MOE_PRIME`, `AMD_HIPKITTENS_INTEGRATION_PRIME`

## VERSION

v1.0 (Extracted from unified registry)
