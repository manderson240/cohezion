# SKILL: EFFICIENT_AI_PRIME

## DOMAIN EXPERTISE
**Efficient AI and Model Compression**. Specializes in knowledge distillation, pruning, quantization (int8/int4), neural architecture search (NAS), and efficient inference on resource-constrained devices.

## KEY TEXTS & CONCEPTS
- **Knowledge Distillation**: Train a small "student" model to mimic a large "teacher" model. Types: response-based (soft targets), feature-based (intermediate representations), attention transfer.
- **Pruning**: Remove redundant weights or structures. Types: unstructured (individual weights), structured (entire channels/filters), gradual magnitude pruning. Lottery Ticket Hypothesis: sparse subnetworks can match full network performance.
- **Quantization**: Reduce numerical precision of weights and activations. Levels: FP32 → FP16 → INT8 → INT4 → binary. Post-training quantization (PTQ) vs quantization-aware training (QAT).
- **Neural Architecture Search (NAS)**: Automated discovery of efficient architectures. Approaches: reinforcement learning, evolutionary, differentiable (DARTS). One-shot NAS with weight sharing for efficiency.
- **Scaling Laws**: Chinchilla scaling — optimal model size depends on compute budget and data budget. Compute-optimal training balances parameters and tokens.

**Related Vault Concepts**: [[cs249r/efficient_ai]], [[cs249r/optimizations]], [[cs249r/hw_acceleration]]
**Related TinyTorch Modules**: Module 15 (quantization), Module 16 (compression), Module 17 (acceleration)

## INSTRUCTION

### 1. Compression Strategy Selection

**Choose the right technique for your constraints:**

```
Deployment Target?
├─ Edge/Mobile (< 50 MB model)
│   ├─ Accuracy critical → Quantization-Aware Training (QAT)
│   ├─ Latency critical → Structured Pruning + INT8
│   └─ Both → Distillation + Pruning + Quantization (compound)
│
├─ Server (latency-sensitive)
│   ├─ Batch inference → INT8 Quantization (fastest ROI)
│   ├─ Real-time → FP16 Mixed Precision
│   └─ Cost reduction → Distillation to smaller model
│
└─ Extreme constraint (< 1 MB, MCU)
    ├─ Binary/Ternary quantization
    ├─ Aggressive pruning (90%+ sparsity)
    └─ Custom NAS for target hardware
```

### 2. Quantization Patterns

**Post-Training Quantization (PTQ):**
```python
def quantize_tensor(tensor, num_bits=8):
    """
    Quantize floating-point tensor to fixed-point.

    TinyTorch reference: Module 15 (quantization)
    """
    qmin = -(2 ** (num_bits - 1))
    qmax = 2 ** (num_bits - 1) - 1

    # Compute scale and zero point
    min_val, max_val = tensor.min(), tensor.max()
    scale = (max_val - min_val) / (qmax - qmin)
    zero_point = qmin - min_val / scale

    # Quantize
    q_tensor = (tensor / scale + zero_point).round().clip(qmin, qmax)

    return q_tensor.astype(int), scale, zero_point

def dequantize_tensor(q_tensor, scale, zero_point):
    """Recover approximate floating-point values."""
    return (q_tensor.astype(float) - zero_point) * scale
```

**Quantization-Aware Training (QAT):**
```python
class FakeQuantize:
    """Simulate quantization during training (straight-through estimator)."""

    def __init__(self, num_bits=8):
        self.num_bits = num_bits

    def forward(self, x):
        # Forward: quantize then dequantize
        q, scale, zp = quantize_tensor(x, self.num_bits)
        x_hat = dequantize_tensor(q, scale, zp)
        return x_hat

    def backward(self, grad_output):
        # Straight-through: pass gradient unchanged
        return grad_output
```

**Precision trade-offs:**

| Precision | Size Reduction | Accuracy Drop | Hardware Support |
|-----------|---------------|---------------|-----------------|
| FP32 → FP16 | 2x | ~0% | GPUs, modern CPUs |
| FP32 → INT8 | 4x | 0.1-1% | Most hardware |
| FP32 → INT4 | 8x | 1-5% | Specialized HW |
| FP32 → Binary | 32x | 5-15% | Custom accelerators |

### 3. Pruning Patterns

**Magnitude-Based Pruning:**
```python
def prune_by_magnitude(weights, sparsity=0.5):
    """
    Remove weights with smallest absolute values.

    TinyTorch reference: Module 16 (compression)
    """
    threshold = np.percentile(np.abs(weights), sparsity * 100)
    mask = np.abs(weights) > threshold
    return weights * mask, mask

def gradual_pruning_schedule(initial_sparsity, final_sparsity, total_steps):
    """
    Cubic sparsity schedule (from Zhu & Gupta 2017).
    Gradually increases sparsity during training.
    """
    def sparsity_at_step(step):
        progress = step / total_steps
        return final_sparsity + (initial_sparsity - final_sparsity) * (1 - progress) ** 3
    return sparsity_at_step
```

**Structured vs Unstructured:**
```python
# Unstructured: prune individual weights (high sparsity, needs sparse HW)
mask = np.abs(weights) > threshold  # Irregular sparsity pattern

# Structured: prune entire channels/filters (lower sparsity, runs on any HW)
channel_importance = np.linalg.norm(conv_weights, axis=(1, 2, 3))  # L2 norm per channel
channels_to_keep = np.argsort(channel_importance)[-num_keep:]  # Keep most important
pruned_weights = conv_weights[channels_to_keep]
```

**Key insight:** Structured pruning gives smaller speedups but works on standard hardware. Unstructured pruning achieves higher compression but requires sparse matrix support.

### 4. Knowledge Distillation Patterns

**Response-Based Distillation:**
```python
def distillation_loss(student_logits, teacher_logits, labels, temperature=4.0, alpha=0.7):
    """
    Combine soft targets (from teacher) with hard targets (labels).

    - Higher temperature → softer probability distribution → more knowledge transfer
    - Alpha balances teacher knowledge vs ground truth
    """
    # Soft targets: teacher's dark knowledge
    soft_loss = kl_divergence(
        softmax(student_logits / temperature),
        softmax(teacher_logits / temperature)
    ) * (temperature ** 2)  # Scale by T^2 to match gradient magnitude

    # Hard targets: standard cross-entropy
    hard_loss = cross_entropy(student_logits, labels)

    return alpha * soft_loss + (1 - alpha) * hard_loss
```

**Distillation best practices:**
- Teacher should be well-trained (overfit slightly is OK)
- Temperature 2-20 (higher = more knowledge transfer, lower = more focus on top predictions)
- Student architecture should be similar to teacher but smaller (same depth, fewer channels)
- Train student longer than teacher (small models need more steps)

### 5. Neural Architecture Search

**NAS approaches by compute budget:**

| Approach | Compute | Best For |
|----------|---------|----------|
| Reinforcement Learning NAS | Very high (1000+ GPU-hours) | Research, large budgets |
| Evolutionary NAS | High (100+ GPU-hours) | Custom constraints |
| Differentiable NAS (DARTS) | Medium (10+ GPU-hours) | Practical deployment |
| One-Shot NAS | Low (1+ GPU-hours) | Rapid prototyping |

**Efficient NAS pattern:**
```python
class SearchSpace:
    """Define the architecture search space."""
    OPERATIONS = [
        'conv_3x3', 'conv_5x5',    # Standard convolutions
        'sep_conv_3x3',             # Depthwise separable (efficient)
        'dil_conv_3x3',             # Dilated (larger receptive field)
        'max_pool_3x3',             # Pooling (no parameters)
        'skip_connect',             # Identity (residual)
        'none',                     # Zero (prune this edge)
    ]

    def sample_architecture(self):
        """Random architecture from search space."""
        return [random.choice(self.OPERATIONS) for _ in range(self.num_edges)]
```

### 6. Compound Compression Pipeline

**Maximum compression: combine techniques sequentially:**

```
Step 1: Distillation (teacher → student)
  └─ 3-5x parameter reduction
Step 2: Structured Pruning (remove channels)
  └─ Additional 2-3x reduction
Step 3: Quantization (FP32 → INT8)
  └─ Additional 4x reduction
Step 4: Operator Fusion (combine layers)
  └─ Latency improvement

Total: 24-60x compression with <2% accuracy drop
```

**Order matters:** Distill first (creates a good small model), prune second (removes redundancy), quantize last (reduces precision of what remains).

### 7. Hardware-Aware Optimization

**For Cohezion's AMD Ryzen AI MAX+ 395:**
- Use XNNPACK or OneDNN for CPU inference optimization
- AVX-512 enables fast INT8 operations natively
- Unified memory architecture means no CPU-GPU transfer overhead
- Profile with TinyTorch Module 14 (profiling) before optimizing

**Measurement-first approach:**
```python
# Always profile before optimizing
from cohezion.tinytorch.profiling import profile_model

results = profile_model(model, sample_input)
# Results show: time per layer, memory per layer, FLOPs per layer

# Optimize the bottleneck, not everything
slowest_layer = max(results, key=lambda r: r.time_ms)
# Apply technique to THIS layer first
```

### 8. Common Pitfalls

**Pitfall 1: Quantizing without calibration**
- INT8 needs representative calibration data to set scale/zero-point
- Use 100-1000 samples from training distribution

**Pitfall 2: Pruning too aggressively at once**
- Gradual pruning (cubic schedule) outperforms one-shot pruning
- Allow fine-tuning between pruning steps

**Pitfall 3: Wrong compression order**
- Quantize AFTER pruning (not before)
- Distill BEFORE pruning

**Pitfall 4: Ignoring hardware**
- Unstructured sparsity is useless without sparse matrix hardware support
- INT4 is only faster on hardware with INT4 compute units

## SEE ALSO
- `MODEL_OPTIMIZATION_PRIME` - Operator fusion, graph optimization, benchmarking
- `DNN_ARCHITECTURES_PRIME` - Architecture selection and design
- `EDGE_INTELLIGENCE_PRIME` - Edge deployment and distributed inference
- `HARDWARE_PROFILE_PRIME` - Cohezion's AMD hardware specifications
- TinyTorch modules: `src/cohezion/tinytorch/{quantization,compression,acceleration}.py`
