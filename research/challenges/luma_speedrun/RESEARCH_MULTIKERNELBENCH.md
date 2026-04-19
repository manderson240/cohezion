# MultiKernelBench Research Report

**Research Date:** April 2026  
**Paper:** MultiKernelBench: A Multi-Platform Benchmark for Kernel Generation (arXiv:2507.17773)  
**GitHub:** https://github.com/wzzll123/MultiKernelBench

---

## 1. What is MultiKernelBench?

MultiKernelBench is the **first comprehensive, multi-platform benchmark for LLM-based deep learning kernel generation**. It was developed by researchers at Nanjing University and released in July 2025.

### Key Specifications:

- **285 kernel tasks** across **14 well-defined functional categories**
- **3 major hardware platforms** supported:
  - **Nvidia GPUs** (CUDA, Triton)
  - **Huawei NPUs** (AscendC, TileLang)
  - **Google TPUs** (Pallas)
  - **Intel GPUs** (SYCL) - added Oct 2025
  - **Added Oct 2025:** Attention tasks including MQA and GQA

### Task Categories:

| Category | #Tasks | Representative Tasks |
|----------|--------|---------------------|
| Activation | 15 | relu, gelu |
| Broadcast | 10 | bias_add |
| Convolution | 34 | conv2d |
| Full Architecture | 50 | resnet18 |
| Fusion | 100 | fused_matmul_bias |
| Loss | 7 | cross_entropy, mse |
| Math | 6 | multiply |
| Matrix Multiply | 17 | sgemm, bmm |
| Normalization | 8 | batchnorm, layernorm |
| Optimizer | 5 | adam_update, sgd_momentum |
| Pooling | 6 | maxpool2d, avgpool2d |
| Index | 12 | gather, scatter_update |
| Resize | 10 | bilinear_resize |
| Reduce | 5 | reduce_sum, reduce_max |

---

## 2. Key Findings About Cross-Platform Kernel Generation

### Finding 1: Performance Varies Dramatically by Platform

The research reveals **severe platform-dependent performance degradation**:

| Platform | Best Pass@1 | Notes |
|----------|-------------|-------|
| **CUDA** | 52.6% (DeepSeek-R1) | Well-documented, extensive training data |
| **AscendC** | 2.5% (DeepSeek-V3) | Severe lack of training exposure |
| **Pallas** | 8.4% (Claude-Sonnet-4) | Python-based, but API understanding limited |

**Key Insight:** Model effectiveness correlates directly with training corpus coverage. Platforms with less representation in pretraining data show dramatically lower performance.

### Finding 2: Task Difficulty Varies by Category

**Easiest Categories** (CUDA Pass@1):
- **Activation**: ~88.9% average (relu, gelu)
- **Reduction**: ~86.7% average (reduce_sum, reduce_max)
- **Normalization**: ~75.0% average (batchnorm, layernorm)

**Hardest Categories** (CUDA Pass@1):
- **Convolution**: ~13.7% average (conv2d)
- **Full Architecture**: ~21.3% average (resnet18)
- **Fusion**: ~52.7% average (fused_matmul_bias)

### Finding 3: Category-Aware One-Shot Prompting Works

The paper introduces a **"category-aware one-shot"** prompting strategy that:
- Selects exemplar kernels from the **same category** as the target task
- Provides domain-specific patterns and optimization strategies
- Significantly improves performance on platforms with limited training exposure

**Result:** Category-aware prompting outperforms generic one-shot examples, especially for less-documented platforms.

### Finding 4: Reasoning Models Excel at CUDA

**Top Performers on CUDA:**
1. **DeepSeek-R1** (reasoning): 52.6% Pass@1, 26.0% SpeedUp@1
2. **Claude-Sonnet-4**: 47.0% Pass@1, 20.4% SpeedUp@1
3. **Qwen3-235B (think)**: 44.2% Pass@1, 19.3% SpeedUp@1

However, reasoning models show **worse performance on AscendC/Pallas** due to limited exposure in training data.

### Finding 5: Failure Mode Analysis

**CUDA Failures:**
- Output mismatch: 53.0%
- Output shape mismatch: 16.1%
- CUDA runtime errors: 15.9%

**AscendC Failures:**
- 74.8% of compilation failures contain "no member named" (API unfamiliarity)
- LLMs hallucinate non-existent functions (e.g., `AscendC::Softmax`)
- Limited understanding of SIMD, data transfer, memory management

**Pallas Failures:**
- "Unexpected Keyword Argument": 22.4%
- Block rank limitations (no scalar support)
- Python-based but API hallucinations common

---

## 3. Patterns That Transfer Between NVIDIA and AMD

### Hardware Architecture Comparison:

| Feature | Nvidia GPU (CUDA) | AMD GPU (ROCm) | Huawei NPU (Ascend) |
|---------|-------------------|----------------|---------------------|
| **Compute Units** | Thousands of ALUs | Similar to NV | Scalar/Vector/Cube units |
| **Matrix Cores** | Tensor Cores | MFMA units | Cube Units |
| **Memory** | HBM with hierarchy | HBM | HBM |
| **Programming** | CUDA C/C++ | HIP/CUDA-compatible | AscendC (C++) |

### Transferable Optimization Patterns:

1. **Memory Hierarchy Exploitation**
   - Shared/local memory usage patterns transfer
   - Register pressure management concepts
   - Coalesced memory access patterns

2. **Tiling and Blocking**
   - Matrix multiply tiling strategies
   - Convolution windowing approaches
   - Data reuse optimization

3. **Vectorization**
   - SIMD/SIMT concepts
   - Warp/Wavefront-level operations
   - Vector unit utilization

4. **Kernel Fusion**
   - Element-wise fusion (activation + element-wise)
   - Reduction fusion patterns
   - Memory bandwidth optimization

### Key Differences (AMD MI355X Specific):

- **MFMA instructions** vs NVIDIA's Tensor Cores
- **XCD-aware scheduling** (MI355X has 8 XCDs)
- **ROCm-specific optimizations** (different from CUDA)
- **CDNA4 architecture** features (gfx950)

---

## 4. Applicability to MI355X Competition

### Relevant Findings:

1. **Fusion Kernels** are the largest category (100 tasks) - directly relevant to our MoE/GEMM/MLA kernels

2. **Matrix Multiply** is a core category - GEMM optimization patterns apply

3. **Attention** tasks (MQA, GQA) were added in Oct 2025 - directly relevant to MLA

4. **Category-aware prompting** can improve kernel generation for AMD-specific optimizations

### Platform Gap Analysis:

The MultiKernelBench results show that **AMD/ROCm is underrepresented** in LLM training data:

- CUDA has extensive documentation and code examples
- AscendC/NPUs have proprietary ecosystems
- ROCm/AMD has less public training data than CUDA

**Implication:** For MI355X (gfx950), we need to:
- Use ROCm/HIP documentation as reference
- Study AMD-specific optimizations
- Consider CDNA4-specific MFMA patterns

---

## 5. Recommendations for Our Kernels

### 5.1 Prompting Strategy

**Adopt Category-Aware One-Shot Prompting:**
```
# Instead of generic one-shot example:
# Provide category-specific exemplars

# For MoE: Use existing MoE kernel as example
# For GEMM: Use existing GEMM kernel as example
# For MLA: Use attention kernel examples
```

**Rationale:** MultiKernelBench shows this approach improves correctness by providing domain-specific patterns.

### 5.2 Focus on Transferable Patterns

From MultiKernelBench findings, prioritize:

1. **Memory Access Patterns**
   - Coalesced loads/stores
   - Shared memory tiling
   - Register reuse

2. **Tiling Strategies**
   - BLOCK_M, BLOCK_N, BLOCK_K configuration
   - Data reuse optimization
   - Bank conflict avoidance

3. **Kernel Fusion**
   - Element-wise operations fused with compute
   - Reduction fusion
   - Memory bandwidth reduction

### 5.3 Platform-Specific Considerations

**For AMD MI355X (CDNA4/gfx950):**

1. **MFMA utilization** (vs Tensor Cores on NVIDIA)
2. **XCD-aware scheduling** (8 XCDs on MI355X)
3. **ROCm-specific APIs** (different from CUDA)
4. **FP4/BF16 support** (cdna4 features)

### 5.4 Testing Strategy

From MultiKernelBench evaluation approach:

1. **Randomized Testing** (N=5 recommended)
2. **Tolerance**: atol=1e-2, rtol=1e-2
3. **Correctness + Performance** both measured
4. **Compilation success** tracked separately

### 5.5 Difficulty Expectations

Based on MultiKernelBench category analysis:

- **GEMM**: Medium difficulty (expect ~70%+ Pass@1 with good prompting)
- **MoE**: High difficulty (expect ~50% Pass@1, requires expert patterns)
- **MLA/Attention**: Medium-High difficulty (MQA/GQA specific challenges)

---

## 6. Summary

MultiKernelBench provides critical insights for our MI355X optimization:

1. **Cross-platform kernel generation is HARD** - expect lower success rates on AMD vs CUDA
2. **Category-aware prompting helps** - use domain-specific examples
3. **Fusion is the largest task category** - directly relevant to our workloads
4. **Memory and tiling patterns transfer** - focus on architecture-agnostic optimizations
5. **Platform-specific knowledge gaps exist** - ROCm/AMD has less training data exposure

### Key Takeaway:

The benchmark shows that even state-of-the-art LLMs struggle with kernel generation, especially on less-documented platforms. For MI355X, we should:
- Provide extensive ROCm/HIP documentation in prompts
- Use category-aware examples
- Expect iterative refinement (don't expect first-pass correctness)
- Focus on transferable optimization patterns

---

## References

- Paper: https://arxiv.org/abs/2507.17773
- GitHub: https://github.com/wzzll123/MultiKernelBench
- Related: KernelBench (Ouyang et al., 2025), TritonBench (Li et al., 2025)
