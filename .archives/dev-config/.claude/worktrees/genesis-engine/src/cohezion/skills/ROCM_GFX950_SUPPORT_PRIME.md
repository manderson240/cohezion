---
name: rocm-gfx950-support
description: ROCm 7.2.0 gfx950 CDNA4 architecture support for MI355X GPUs. Includes hipBLASLt 1.2.1 FP4/FP6/BF6 native support, CK Tile async pipelines, MIOpen 3.5.1 3D heuristics, and rocMLIR MXFP kernel generation. Use when targeting MI355X or CDNA4-specific optimizations.
metadata:
  version: "1.0"
  legacy-name: ROCM_GFX950_SUPPORT
  category: kernel_research
  source_worktree: research_specialist
  source_session: "Session 77-79"
---

# SKILL: ROCM_GFX950_SUPPORT

## DOMAIN EXPERTISE
You are a specialist in **ROCm 7.2.0 gfx950 CDNA4 architecture** features and optimizations. You understand the unique capabilities of MI355X GPUs that are NOT available on MI300X, including native FP4/FP6/BF6 support, async pipelines, and specialized 3D heuristics.

## KEY FINDINGS

### hipBLASLt 1.2.1 (gfx950 Exclusive)
- **Native FP4/FP6/BF6 support** - Hardware-accelerated on CDNA4 only
- Not available on MI300X (gfx942) - exclusive MI355X feature
- Significant performance gains for quantized inference

### CK Tile Async Pipeline (gfx950)
- **Async pipeline + weight preshuffle** - Overlap computation with memory
- Reduces memory latency impact on GEMM operations
- Critical for achieving peak TFLOPS on CDNA4

### MIOpen 3.5.1 (gfx950 Specific)
- **3D heuristics optimized for CDNA4** - Better convolution performance
- Takes advantage of new matrix core layouts
- Improved fusion patterns for common CNN architectures

### rocMLIR Kernel Generation
- **MXFP8 and MXFP4 kernel generation** - MLIR-based compilation
- Generates optimized kernels for mixed-precision training/inference
- Integrates with PyTorch Inductor for seamless usage

## COMPETITIVE ADVANTAGE

These features are **exclusive to MI355X vs MI300X**:

| Feature | MI300X (gfx942) | MI355X (gfx950) |
|---------|----------------|-----------------|
| FP4 native | Emulated | Hardware-accelerated |
| FP6/BF6 | Not supported | Native support |
| Async pipeline | Limited | Full support |
| Weight preshuffle | Manual | Automatic |
| 3D heuristics | Generic | CDNA4-optimized |

## USAGE

### hipBLASLt FP4 GEMM (gfx950 only)
```cpp
#include <hipblaslt/hipblaslt.h>

// Initialize hipBLASLt handle
hipblasLtHandle_t handle;
hipblasLtCreate(&handle);

// Configure for FP4 (gfx950 only)
hipblasLtMatmulDesc_t operationDesc;
hipblasLtMatmulDescCreate(&operationDesc, HIPBLAS_COMPUTE_32F, HIP_R_32F);

// Set to FP4 format (HIPBLAS_R_4F_E2M1 or similar)
hipblasLtMatmulDescSetAttribute(
    operationDesc,
    HIPBLASLT_MATMUL_EPILOGUE_AUXILIARY_DATA_TYPE,
    &HIP_R_4F_E2M1,
    sizeof(hipDataType)
);

// Execute GEMM with automatic scaling
hipblasLtMatmul(
    handle,
    operationDesc,
    &alpha,
    A, Adesc,
    B, Bdesc,
    &beta,
    C, Cdesc,
    D, Ddesc,
    &algo,
    workspace,
    workspaceSize,
    stream
);
```

### rocMLIR MXFP Kernel Generation
```python
import torch

# Enable rocMLIR backend in PyTorch Inductor
import torch._inductor.config as inductor_config
inductor_config.rocm.use_mlir = True

# Compile model with MXFP4/FP8 support
model = MyModel().cuda()
compiled_model = torch.compile(
    model,
    backend="inductor",
    options={"max_autotune": True, "fallback_random": True}
)

# Forward pass uses rocMLIR-generated MXFP kernels on gfx950
output = compiled_model(input_tensor)
```

### Feature Detection
```python
def is_gfx950():
    """Check if running on MI355X (gfx950)"""
    import torch
    if not torch.cuda.is_available():
        return False
    props = torch.cuda.get_device_properties(0)
    return "gfx950" in str(props.gcnArchName).lower()

def get_optimal_config():
    """Return architecture-specific optimizations"""
    if is_gfx950():
        return {
            "use_native_fp4": True,
            "use_async_pipeline": True,
            "use_weight_preshuffle": True,
            "hipblaslt_version": "1.2.1+",
            "miopen_version": "3.5.1+"
        }
    else:
        return {
            "use_native_fp4": False,  # Emulated on gfx942
            "use_async_pipeline": False,
            "use_weight_preshuffle": False
        }
```

## REFERENCES

- hipBLASLt 1.2.1 documentation
- MIOpen 3.5.1 release notes
- rocMLIR MXFP kernel documentation
- Source: Session 77-79 AMD Speedrun Research

## VERSION

v1.0 (Extracted from unified registry)
