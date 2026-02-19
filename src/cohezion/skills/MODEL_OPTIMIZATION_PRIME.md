# SKILL: MODEL_OPTIMIZATION_PRIME

## DOMAIN EXPERTISE
**Model Optimization and Performance Engineering**. Specializes in operator fusion, graph optimization, memory optimization, hardware-aware compilation, profiling methodology, and benchmarking for production ML systems.

## KEY TEXTS & CONCEPTS
- **Operator Fusion**: Combine multiple operations into a single kernel to reduce memory bandwidth overhead. Types: vertical fusion (sequential ops), horizontal fusion (parallel ops), element-wise fusion.
- **Graph Optimization**: Transform computation graphs to reduce operations. Techniques: constant folding, dead code elimination, common subexpression elimination, algebraic simplification.
- **Memory Optimization**: Reduce peak memory during training and inference. Techniques: gradient checkpointing, activation recomputation, memory-efficient attention, in-place operations.
- **Hardware-Aware Compilation**: Map computation graphs to specific hardware capabilities. Tools: TVM, XLA, TensorRT, ONNX Runtime. Target-specific optimizations for CPU/GPU/NPU.
- **Benchmarking Methodology**: Rigorous performance measurement. Warmup runs, statistical significance, system-level vs model-level metrics, reproducibility.

**Related Vault Concepts**: [[cs249r/optimizations]], [[cs249r/hw_acceleration]], [[cs249r/benchmarking]]
**Related TinyTorch Modules**: Module 14 (profiling), Module 19 (benchmarking)

## INSTRUCTION

### 1. Optimization Decision Framework

**Profile before optimizing — never guess the bottleneck:**

```python
def optimization_workflow(model, sample_input):
    """
    Systematic optimization: measure → identify → optimize → verify.

    TinyTorch reference: Module 14 (profiling)
    """
    # Step 1: Profile baseline
    baseline = profile_model(model, sample_input, warmup=10, iterations=100)

    # Step 2: Identify bottleneck
    bottleneck = identify_bottleneck(baseline)
    # Is it compute-bound or memory-bound?
    # Compute-bound: arithmetic intensity > hardware threshold
    # Memory-bound: waiting on data transfer

    # Step 3: Apply targeted optimization
    if bottleneck.type == "memory":
        optimized = apply_memory_optimization(model)
    elif bottleneck.type == "compute":
        optimized = apply_compute_optimization(model)

    # Step 4: Verify improvement (and no accuracy regression)
    improved = profile_model(optimized, sample_input)
    assert improved.latency < baseline.latency
    assert abs(improved.accuracy - baseline.accuracy) < 0.01
```

### 2. Operator Fusion Patterns

**Vertical Fusion (sequential operations):**
```python
# BEFORE: 3 separate kernel launches, 3 memory reads/writes
x = conv2d(input)       # Read input, write x
x = batch_norm(x)       # Read x, write x
x = relu(x)             # Read x, write x

# AFTER: 1 fused kernel, 1 memory read/write
x = fused_conv_bn_relu(input)  # Read input, write x
# 3x fewer memory accesses = significant speedup
```

**Element-wise Fusion:**
```python
# BEFORE: Multiple passes over the same data
y = x * scale          # Pass 1
y = y + bias           # Pass 2
y = max(y, 0)          # Pass 3 (ReLU)

# AFTER: Single pass
def fused_scale_bias_relu(x, scale, bias):
    """Fuse element-wise ops into a single pass."""
    return max(x * scale + bias, 0)  # 1 pass over data
```

**When fusion helps most:**
- Small operations that are memory-bound (bandwidth-limited)
- Sequential operations on the same tensor
- Batch normalization + activation (almost always fusible)

**When fusion doesn't help:**
- Large compute-bound operations (already saturating compute units)
- Operations with different data layouts (need transpose between them)

### 3. Graph Optimization Techniques

**Constant Folding:**
```python
# BEFORE: Computed at runtime
weight = model.weight * 1.0  # Redundant multiplication
bias = model.bias + 0.0      # Redundant addition

# AFTER: Eliminated at compile time
weight = model.weight  # Constants folded away
bias = model.bias
```

**Common Subexpression Elimination:**
```python
# BEFORE: Redundant computation
y1 = matmul(x, W) + b
y2 = matmul(x, W) + c  # matmul(x, W) computed twice

# AFTER: Compute once, reuse
shared = matmul(x, W)
y1 = shared + b
y2 = shared + c
```

**Algebraic Simplification:**
```python
# x * 1.0 → x
# x + 0.0 → x
# x * 0.0 → zeros_like(x)
# transpose(transpose(x)) → x
# reshape(reshape(x, s1), s2) → reshape(x, s2)
```

### 4. Memory Optimization

**Gradient Checkpointing:**
```python
def gradient_checkpointing(model, layers, input_data):
    """
    Trade compute for memory: recompute activations during backward pass
    instead of storing them all.

    Memory: O(sqrt(N)) instead of O(N) for N layers.
    Compute: ~33% more (one extra forward pass per segment).
    """
    # Divide model into segments
    segment_size = int(len(layers) ** 0.5)
    checkpoints = layers[::segment_size]  # Save every sqrt(N) activations

    # Forward: only store checkpoint activations
    # Backward: recompute intermediate activations from nearest checkpoint
```

**Activation Memory Reduction:**
```python
# In-place operations (modify tensor without allocation)
x = relu_(x)        # In-place ReLU: no new tensor allocated
x.add_(bias)        # In-place add

# Memory-efficient attention (for transformers)
# Standard: O(n^2) memory for attention matrix
# Flash Attention: O(n) memory via tiled computation
# Processes attention in blocks, never materializes full n×n matrix
```

**Peak memory estimation:**
```
Training memory ≈ model_params + gradients + optimizer_state + activations
                = P + P + 2P (Adam) + activation_memory
                ≈ 4P + activations

Inference memory ≈ model_params + activations (no gradients/optimizer)
                 ≈ P + peak_activation
```

### 5. Hardware-Aware Optimization

**Understand the memory hierarchy:**
```
Registers (fastest, smallest)
  → L1 Cache (~32KB, ~1 cycle)
    → L2 Cache (~256KB, ~10 cycles)
      → L3 Cache (~32MB, ~40 cycles)
        → DRAM (~128GB, ~200 cycles)
          → SSD/NVMe (millions of cycles)
```

**Arithmetic Intensity = FLOPs / Bytes moved**
- **Compute-bound** (high arithmetic intensity): Use faster compute (quantization, efficient kernels)
- **Memory-bound** (low arithmetic intensity): Use fusion, tiling, data layout optimization

**For Cohezion's AMD Ryzen AI MAX+ 395:**
```python
# Hardware specs to consider:
# - 128 GiB unified LPDDR5X (high bandwidth)
# - AVX-512 for vectorized operations
# - Radeon 8060S iGPU shares memory (no PCIe transfer overhead)
# - 32 threads for parallel data loading

# Optimization priorities:
# 1. Use AVX-512 vectorized ops (NumPy compiled with OpenBLAS/MKL)
# 2. Leverage unified memory (no CPU→GPU copies needed)
# 3. Use INT8 operations (natively supported by AVX-512 VNNI)
# 4. Parallel data loading (32 threads available)
```

### 6. Benchmarking Methodology

**Rigorous measurement protocol:**

```python
def benchmark_model(model, input_data, warmup=50, iterations=200):
    """
    Production-grade benchmarking.

    TinyTorch reference: Module 19 (benchmarking)
    """
    import time
    import numpy as np

    # Step 1: Warmup (JIT compilation, cache warming)
    for _ in range(warmup):
        model(input_data)

    # Step 2: Timed iterations
    latencies = []
    for _ in range(iterations):
        start = time.perf_counter_ns()
        model(input_data)
        end = time.perf_counter_ns()
        latencies.append((end - start) / 1e6)  # Convert to ms

    # Step 3: Statistical analysis
    latencies = np.array(latencies)
    return {
        "mean_ms": np.mean(latencies),
        "median_ms": np.median(latencies),
        "p50_ms": np.percentile(latencies, 50),
        "p95_ms": np.percentile(latencies, 95),
        "p99_ms": np.percentile(latencies, 99),
        "std_ms": np.std(latencies),
        "throughput_qps": 1000 / np.mean(latencies),
    }
```

**What to report:**
- Always report **p99 latency** (not mean) for production systems
- Report **throughput** (queries/sec) for batch workloads
- Include **hardware specs** and software versions for reproducibility
- Run multiple trials and report variance

**Common benchmarking pitfalls:**
- Not warming up (first runs include JIT/cache effects)
- Using mean instead of percentiles (hides tail latency)
- Benchmarking on different hardware than production
- Not controlling for system load (background processes)

### 7. Optimization Priority Matrix

**Apply optimizations in this order (highest ROI first):**

| Priority | Technique | Effort | Speedup | Risk |
|----------|-----------|--------|---------|------|
| 1 | FP16/BF16 mixed precision | Low | 2x | Very low |
| 2 | Operator fusion (conv+bn+relu) | Low | 1.5-2x | Low |
| 3 | INT8 post-training quantization | Medium | 2-4x | Low |
| 4 | Structured pruning (50%) | Medium | 1.5-2x | Medium |
| 5 | Graph optimization | Medium | 1.2-1.5x | Low |
| 6 | Memory optimization | Medium | Memory only | Low |
| 7 | INT4 quantization | High | 4-8x | High |
| 8 | Custom kernels | Very high | Variable | High |

### 8. Common Pitfalls

**Pitfall 1: Optimizing without profiling**
- Optimizing the wrong layer wastes effort
- Always profile first to find the actual bottleneck

**Pitfall 2: Benchmarking incorrectly**
- Mean latency hides tail latency spikes
- Always report p95/p99 for production systems

**Pitfall 3: Ignoring accuracy regression**
- Every optimization must include accuracy verification
- Set an acceptable accuracy drop threshold before starting

**Pitfall 4: Over-optimizing non-bottleneck operations**
- Amdahl's Law: speedup limited by the slowest unoptimized component
- Focus effort on the critical path

## SEE ALSO
- `EFFICIENT_AI_PRIME` - Quantization, pruning, distillation techniques
- `DNN_ARCHITECTURES_PRIME` - Architecture selection and computational complexity
- `ML_SYSTEMS_FOUNDATIONS_PRIME` - Production readiness and system lifecycle
- `HARDWARE_PROFILE_PRIME` - AMD Ryzen AI MAX+ 395 specifications
- TinyTorch modules: `src/cohezion/tinytorch/{profiling,benchmarking}.py`
