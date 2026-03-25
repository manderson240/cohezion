# AMD GPU MODE Competition Quick Reference
## LLMs for Kernel Optimization - Secret Sauce Techniques

## Competition Targets (from official page)
1. **MXFP4 MoE** - Mixture-of-Experts with MXFP4 quantization
2. **MLA Decode** - Multi-head Latent Attention decode  
3. **MXFP4 GEMM** - Matrix multiplication with MXFP4 precision

## Key Discovery: AITER Environment Already Contains
- Lean Attention (arXiv:2405.10480) - State-of-the-art efficient attention
- Paged Attention (arXiv:2309.06180) - Memory-efficient KV caching
- FP8/BF16/MXFP4 quantization support
- CDNA3-specific optimizations in gluon/pa_decode_gluon.py
- Triton-based kernels ready for optimization

## LLM-Based Optimization Strategies

### Strategy 1: LLM-Guided Search Space Exploration
**Instead of**: Random or grid search over optimization parameters
**Use**: LLMs to predict promising regions of optimization space

**Example**: 
- Input: "MXFP4 MoE kernel struggling with memory bandwidth on MI355X"
- LLM Output: Suggest specific tile sizes, memory access patterns, instruction schedules
- Result: 3-5x fewer evaluations needed to find optimum

### Strategy 2: Natural Language to Kernel Generation
**Prompt Template**:
```
Generate optimized Triton kernel for [KERNEL_TYPE] on AMD MI355X:
- Focus: [PERFORMANCE_GOAL]
- Constraints: [NUMERICAL_ACCURACY, MEMORY_LIMIT]
- Architecture: [CDNA3_SPECIFICS]
```

**Example for MLA Decode**:
```
Generate optimized Triton kernel for Multi-head Latent Attention decode:
- Focus: Minimize memory bandwidth for latent representations
- Constraints: RTOL <= 2e-2, support variable batch sizes
- Architecture: Use CDNA3 MFMA, optimize for gfx942 wavefronts
```

### Strategy 3: Learned Performance Modeling
**Process**:
1. Collect performance data from kernel variants
2. Train lightweight predictor (can be LLM-based)
3. Use predictor to guide optimization decisions
4. Continuously update with new measurements

### Strategy 4: Hybrid Approach (Recommended)
```
LLM Suggestions → Traditional Autotuning → Validation → LLM Analysis → Repeat
```

## Immediate Action Items

### Day 1: Baseline Establishment
```bash
# Check what's available
ls /tmp/aiter/op_tests/op_benchmarks/triton/

# Run reference implementations to get baselines
cd /tmp/aiter
python op_tests/op_benchmarks/triton/bench_mla_decode.py --help
python op_tests/op_benchmarks/triton/bench_fav3_sage_mxfp4.py --help
```

### Day 2: LLM Setup
```bash
# Deploy local LLM for code generation
# Options: CodeLlama, StarCoder, or similar
# Quantized versions for efficient local inference
```

### Day 3: First Optimization Cycle
```bash
# 1. Generate LLM-suggested variant
# 2. Measure performance
# 3. Analyze with LLM 
# 4. Generate improved variant
# Repeat until convergence
```

## Specific Optimization Opportunities Found

### MXFP4 MoE Opportunities:
- Expert computation parallelism strategies
- MXFP4 packing/unpacking optimization overhead reduction
- Memory routing optimization for sparse expert access

### MLA Decode Opportunities:
- Latent attention computation optimization
- KV cache access pattern improvements for paged attention
- Grouped query processing efficiency

### MXFP4 GEMM Opportunities:
- MXFP4-specific packing strategies
- Accumulation precision optimization (when to use FP16 vs FP32)
- MFMA instruction scheduling for CDNA3 matrix cores

## Validation Requirements (from competition docs)
- Numerical tolerance: RTOL ≤ 2e-2, ATOL ≤ 2e-2 (for moe-mxfp4)
- Must match reference functionality exactly
- Performance measured on standardized benchmarks

## Resources Already Available
- Reference implementations in `/tmp/aiter/op_tests/op_benchmarks/triton/`
- Academic papers: Lean Attention, Paged Attention, Flash Attention
- AMD CDNA3 optimization examples in gluon/pa_decode_gluon.py
- ROCm optimization guide references

## Winning Approach
**Don't** try to invent completely new algorithms
**Do** apply LLM-assisted optimization to already-excellent foundations:
1. Start with Lean Attention + Paged Attention (SOTA)
2. Add MXFP4 quantization support (already present)
3. Use LLMs to find optimal combinations and parameters
4. Validate rigorously against numerical requirements
5. Iterate quickly with measured feedback

The winning edge comes from **speed of exploration**, not novel algorithms.
LLMs enable 10x faster exploration of optimization space.
```

## Final Tips

### Performance Measurement
- Focus on end-to-end inference time, not just kernel time
- Account for data transfer overhead
- Test across realistic batch sizes and sequence lengths

### Numerical Validation
- Always compare against reference implementation
- Use the specified tolerances religiously
- Test edge cases (very small, very large inputs)

### Development Workflow
1. Measure baseline
2. Generate LLM-suggested improvement
3. Implement and measure
4. If better, keep; if worse, analyze why and try again
5. Never sacrifice correctness for speed

**Remember**: The fastest wrong answer is still wrong. Correctness first, then speed.