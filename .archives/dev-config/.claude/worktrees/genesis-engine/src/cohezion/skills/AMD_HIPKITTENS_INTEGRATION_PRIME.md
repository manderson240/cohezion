---
name: amd-hipkittens-integration
description: HipKittens integration for AMD GPU kernel development. Microbenchmarking and profiling tools for HIP kernels on CDNA3/CDNA4 architectures. Use for low-level GPU performance analysis and kernel optimization on MI300X/MI355X.
metadata:
  version: "1.0"
  legacy-name: AMD_HIPKITTENS_INTEGRATION
  category: amd_optimization
  source_session: "Session 77-79"
---

# SKILL: AMD_HIPKITTENS_INTEGRATION

## DOMAIN EXPERTISE
You are a specialist in **HipKittens** microbenchmarking and profiling for AMD GPUs. You understand how to use HipKittens to analyze kernel performance, memory bandwidth, and instruction throughput on CDNA3/CDNA4 architectures.

## KEY FINDINGS

### HipKittens Overview
- **Microbenchmarking suite** for AMD GPU kernels
- Provides **detailed instruction-level profiling**
- Measures memory bandwidth, cache utilization, and compute throughput
- Essential for identifying performance bottlenecks in HIP kernels

### CDNA3/CDNA4 Specific Features
- **CDNA3 (MI300X)**: Full support for matrix core profiling
- **CDNA4 (MI355X)**: Extended support for FP4/FP6 instructions
- Supports both wave-level and workgroup-level analysis

### Key Metrics Provided
- **Instruction mix**: ALU vs MEM vs barrier instructions
- **Memory bandwidth**: HBM, L2, L1 cache hit rates
- **Occupancy**: Active waves vs hardware limits
- **Latency hiding**: Memory vs compute overlap effectiveness

## USAGE

### Installing HipKittens
```bash
# Clone HipKittens repository
git clone https://github.com/ROCm/hipkittens.git
cd hipkittens

# Build for current ROCm version
mkdir build && cd build
cmake .. -DROCM_PATH=/opt/rocm
make -j$(nproc)

# Install Python bindings (optional)
pip install -e python/
```

### Basic Kernel Profiling
```python
import hipkittens as hk
import torch

# Initialize profiler for target GPU
profiler = hk.Profiler(device="cuda:0")

# Define kernel to profile
kernel_code = """
__global__ void saxpy(float* y, float* x, float alpha, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) {
        y[i] = alpha * x[i] + y[i];
    }
}
"""

# Compile and profile
module = profiler.compile(kernel_code)
results = profiler.profile(
    module.saxpy,
    grid=(256,),
    block=(256,),
    args=[y, x, 2.0, n]
)

# Print results
print(f"Duration: {results.duration_ms:.3f} ms")
print(f"ALU utilization: {results.alu_utilization:.1f}%")
print(f"Memory bandwidth: {results.memory_bw_gb_s:.1f} GB/s")
```

### Advanced Metrics Collection
```python
# Collect detailed instruction counts
metrics = profiler.collect_metrics(
    kernel=module.saxpy,
    counters=[
        "SQ_INSTS_VALU_ADD_F32",
        "SQ_INSTS_VALU_MUL_F32",
        "SQ_INSTS_VALU_FMA_F32",
        "SQ_INSTS_VALU_MFMA_M32_F16",
        "TA_FLAT_READ_WAVEFRONTS",
        "TA_FLAT_WRITE_WAVEFRONTS",
        "TCP_L1_TLB_MISS_RATE",
        "TCP_L2_CACHE_HIT_RATE"
    ]
)

# Analyze instruction mix
total_valu = metrics["SQ_INSTS_VALU_ADD_F32"] + metrics["SQ_INSTS_VALU_MUL_F32"]
print(f"VALU instructions: {total_valu}")
print(f"MFMA instructions: {metrics['SQ_INSTS_VALU_MFMA_M32_F16']}")
print(f"L2 hit rate: {metrics['TCP_L2_CACHE_HIT_RATE']:.1%}")
```

### Roofline Analysis
```python
# Generate roofline plot for kernel
roofline = hk.RooflineAnalysis(profiler)

# Profile multiple problem sizes
for size in [1024, 4096, 16384, 65536]:
    x = torch.randn(size, device="cuda")
    y = torch.randn(size, device="cuda")
    roofline.profile_point(
        kernel=module.saxpy,
        args=[y, x, 2.0, size],
        arithmetic_intensity=size / (2 * size * 4),  # FLOPs/Bytes
        performance=2 * size / results.duration_ms / 1e9  # GFLOP/s
    )

# Generate roofline plot
roofline.plot(save_path="roofline_analysis.png")
```

## BEST PRACTICES

### Profiling Checklist
- [ ] Profile with warm-up iterations (first run may include compilation)
- [ ] Test multiple grid configurations to find optimal occupancy
- [ ] Measure both compute-bound and memory-bound scenarios
- [ ] Compare against theoretical peak (calculated from specs)

### Common Pitfalls
- **Cold start overhead**: First kernel launch includes JIT compilation
- **Clock throttling**: Long-running kernels may trigger thermal throttling
- **Occupancy limits**: Not all theoretical waves can be active simultaneously

## REFERENCES

- HipKittens GitHub: https://github.com/ROCm/hipkittens
- ROCm Profiler documentation
- Source: Session 77-79 AMD Speedrun Research
- Related: `CK_TILE_FUSED_MOE_PRIME`, `ROCM_GFX950_SUPPORT_PRIME`

## VERSION

v1.0 (Extracted from unified registry)
