# SKILL: EDGE_INTELLIGENCE_PRIME

## DOMAIN EXPERTISE
**Edge Intelligence and Distributed ML**. Specializes in federated learning, split computing, communication-efficient training, fault-tolerant distributed systems, on-device inference, and edge-cloud collaboration for resource-constrained environments.

## KEY TEXTS & CONCEPTS
- **Federated Learning**: Train models collaboratively across devices without sharing raw data. Server aggregates model updates (FedAvg, FedProx). Privacy by design — data never leaves the device.
- **Split Computing**: Partition a model between edge device and cloud. Early layers run on-device (feature extraction), later layers in cloud (classification). Reduces latency and bandwidth.
- **Communication-Efficient Training**: Minimize data transferred during distributed training. Techniques: gradient compression, quantized gradients, sparse updates, local SGD (multiple local steps before sync).
- **Edge-Cloud Collaboration**: Dynamic workload splitting between edge and cloud based on network conditions, device capabilities, and latency requirements. Adaptive inference routing.
- **TinyML**: ML inference on microcontrollers (MCUs) with kilobytes of memory. Requires extreme model compression, fixed-point arithmetic, and hardware-aware design.

**Related Vault Concepts**: [[cs249r/ondevice_learning]], [[cs249r/privacy_security]], [[cs249r/hw_acceleration]]

## INSTRUCTION

### 1. Edge Deployment Decision Framework

**Choose the right edge strategy:**

```
Where does inference run?
├─ Fully On-Device
│   ├─ Privacy critical (medical, personal data) → Federated Learning
│   ├─ No network available → Standalone edge model
│   └─ Ultra-low latency (<10ms) → Quantized on-device model
│
├─ Split Computing (Edge + Cloud)
│   ├─ Large model, good network → Early exit on-device, full model in cloud
│   ├─ Variable network → Adaptive splitting based on bandwidth
│   └─ Bandwidth limited → Feature extraction on-device, cloud classification
│
└─ Cloud with Edge Cache
    ├─ Latency tolerant → Cloud inference with edge caching
    └─ Personalization needed → Cloud base model + edge fine-tuning
```

### 2. Federated Learning Patterns

**Federated Averaging (FedAvg):**
```python
class FederatedServer:
    """Coordinate federated learning across edge devices."""

    def __init__(self, global_model, min_clients=10):
        self.global_model = global_model
        self.min_clients = min_clients
        self.round_number = 0

    def run_round(self, available_clients):
        """Execute one round of federated averaging."""
        # 1. Select subset of clients (don't require all devices)
        selected = self.select_clients(available_clients)
        if len(selected) < self.min_clients:
            return None  # Not enough clients

        # 2. Send global model weights to selected clients
        global_weights = self.global_model.get_weights()

        # 3. Clients train locally and send back updates
        client_updates = []
        for client in selected:
            update = client.train_local(
                global_weights,
                local_epochs=5,     # Multiple local epochs (efficiency)
                learning_rate=0.01
            )
            client_updates.append(update)

        # 4. Aggregate using weighted average
        self.aggregate_updates(client_updates)
        self.round_number += 1

    def aggregate_updates(self, updates):
        """FedAvg: weighted average by number of samples."""
        total_samples = sum(u.num_samples for u in updates)
        new_weights = {}

        for key in self.global_model.get_weights():
            new_weights[key] = sum(
                u.weights[key] * (u.num_samples / total_samples)
                for u in updates
            )

        self.global_model.set_weights(new_weights)

    def select_clients(self, available, fraction=0.1):
        """Select random subset of available clients."""
        n_select = max(self.min_clients, int(len(available) * fraction))
        return random.sample(available, min(n_select, len(available)))
```

**FedProx (handles heterogeneous devices):**
```python
def fedprox_local_loss(local_model, global_weights, mu=0.01):
    """
    Add proximal term to prevent client drift.
    Handles non-IID data better than FedAvg.

    Loss = task_loss + (mu/2) * ||local_weights - global_weights||^2
    """
    task_loss = compute_task_loss(local_model)
    proximal_term = sum(
        np.sum((local - global_) ** 2)
        for local, global_ in zip(local_model.get_weights().values(),
                                   global_weights.values())
    )
    return task_loss + (mu / 2) * proximal_term
```

### 3. Communication-Efficient Training

**Gradient Compression:**
```python
def top_k_sparsification(gradients, k_ratio=0.01):
    """
    Send only top-k% of gradient values.
    Reduces communication by 100x with minimal accuracy loss.
    """
    flat = gradients.flatten()
    k = max(1, int(len(flat) * k_ratio))
    top_k_indices = np.argpartition(np.abs(flat), -k)[-k:]
    top_k_values = flat[top_k_indices]

    # Accumulate residual (error feedback) for next round
    residual = gradients.copy()
    sparse_grad = np.zeros_like(flat)
    sparse_grad[top_k_indices] = top_k_values
    residual -= sparse_grad.reshape(gradients.shape)

    return top_k_indices, top_k_values, residual

def quantize_gradients(gradients, num_bits=2):
    """
    Quantize gradients to low-bit representation.
    2-bit: send only sign + magnitude bucket.
    """
    # Sign quantization (1-bit: positive or negative)
    signs = np.sign(gradients)

    # Magnitude quantization
    abs_grad = np.abs(gradients)
    threshold = np.mean(abs_grad)

    # 2-bit: {0, +threshold, -threshold, +2*threshold}
    quantized = signs * np.where(abs_grad > threshold, threshold, 0)

    return quantized
```

**Communication budget comparison:**

| Technique | Compression Ratio | Accuracy Impact |
|-----------|------------------|-----------------|
| No compression | 1x | Baseline |
| FP16 gradients | 2x | ~0% |
| Top-1% sparsification | 100x | <0.5% |
| 2-bit quantization | 16x | <1% |
| Local SGD (H=10 steps) | 10x | <0.5% |
| Combined (sparse + quantized) | 1000x+ | 1-3% |

### 4. Split Computing Architecture

**Dynamic model splitting:**
```python
class SplitComputeManager:
    """
    Split model execution between edge and cloud.
    Adapt split point based on network conditions.
    """

    def __init__(self, model, split_points):
        self.model = model
        self.split_points = split_points  # Candidate layer indices

    def choose_split_point(self, network_bandwidth_mbps, device_compute_gflops):
        """
        Optimal split minimizes total latency:
        Total = edge_compute + transfer + cloud_compute
        """
        best_split = None
        best_latency = float('inf')

        for split_idx in self.split_points:
            # Edge computation time
            edge_flops = self.model.flops_before(split_idx)
            edge_time = edge_flops / (device_compute_gflops * 1e9)

            # Transfer time
            intermediate_size = self.model.output_size_at(split_idx)
            transfer_time = intermediate_size / (network_bandwidth_mbps * 1e6 / 8)

            # Cloud computation time
            cloud_flops = self.model.flops_after(split_idx)
            cloud_time = cloud_flops / (100 * 1e9)  # Assume 100 GFLOPS cloud

            total = edge_time + transfer_time + cloud_time

            if total < best_latency:
                best_latency = total
                best_split = split_idx

        return best_split

    def infer(self, input_data, split_point):
        """Execute split inference."""
        # Run early layers on edge
        intermediate = self.model.forward_to(input_data, split_point)

        # Transfer intermediate representation
        compressed = self.compress_intermediate(intermediate)

        # Run remaining layers on cloud
        result = self.model.forward_from(compressed, split_point)

        return result
```

### 5. TinyML Patterns

**Microcontroller deployment constraints:**

| Resource | Typical MCU | What It Means |
|----------|------------|---------------|
| RAM | 256 KB | Model + activations must fit |
| Flash | 1 MB | Model weights storage |
| Clock | 100 MHz | Limited compute throughput |
| Power | 1-10 mW | Battery/energy harvesting |

**Fixed-point inference for MCU:**
```python
def fixed_point_inference(weights_int8, input_int8, scale_w, scale_x, scale_y):
    """
    INT8 inference without floating point hardware.
    Output = (Input * Weights) * (scale_x * scale_w / scale_y)
    """
    # Integer matrix multiply (no FPU needed)
    accumulator_int32 = np.dot(input_int8.astype(np.int32),
                                weights_int8.astype(np.int32))

    # Rescale to output range
    multiplier = (scale_x * scale_w) / scale_y
    # Approximate multiplier as fixed-point: M * 2^(-shift)
    shift = 15
    fixed_multiplier = int(multiplier * (1 << shift))

    output_int8 = (accumulator_int32 * fixed_multiplier) >> shift
    return output_int8.clip(-128, 127).astype(np.int8)
```

### 6. Fault Tolerance in Distributed Training

**Handle device failures gracefully:**
```python
class FaultTolerantTrainer:
    """Distributed training with fault tolerance."""

    def __init__(self, model, num_workers):
        self.model = model
        self.num_workers = num_workers
        self.checkpoints = {}

    def train_step_with_recovery(self, data_shards):
        """Training step that tolerates worker failures."""
        gradients = []
        failed_workers = []

        for worker_id, shard in enumerate(data_shards):
            try:
                grad = self.compute_gradient(worker_id, shard, timeout=30)
                gradients.append(grad)
            except (TimeoutError, ConnectionError) as e:
                failed_workers.append(worker_id)
                # Use stale gradient from checkpoint if available
                if worker_id in self.checkpoints:
                    gradients.append(self.checkpoints[worker_id])

        if len(gradients) < self.num_workers * 0.5:
            raise TrainingError("Too many worker failures (>50%)")

        # Average available gradients (robust to missing workers)
        avg_gradient = np.mean(gradients, axis=0)
        self.model.update(avg_gradient)

        # Checkpoint successful gradients
        for worker_id, grad in zip(range(len(gradients)), gradients):
            if worker_id not in failed_workers:
                self.checkpoints[worker_id] = grad
```

### 7. Integration with Cohezion's Local-First Architecture

**Cohezion runs on AMD Ryzen AI MAX+ 395 with local Ollama models:**

```python
# Cohezion's local-first approach aligns with edge intelligence:
# - Ollama models run locally (no cloud dependency)
# - 128 GiB unified memory enables large local models
# - SemanticCache provides inference caching (95%+ hit rate)
# - Cost savings from local inference vs API calls

# Edge intelligence patterns applicable to Cohezion:
# 1. Model selection based on query complexity
#    (small model for simple queries, large for complex)
# 2. Caching as a form of edge intelligence
#    (semantic cache = learned index of common queries)
# 3. Federated knowledge aggregation
#    (multiple Cohezion instances could share learned skills)
```

### 8. Common Pitfalls

**Pitfall 1: Assuming IID data in federated learning**
- Real-world devices have non-IID data distributions
- Use FedProx or FedBN to handle heterogeneity

**Pitfall 2: Ignoring communication costs**
- Network transfers dominate training time in distributed settings
- Always compress gradients and minimize sync frequency

**Pitfall 3: Not testing on actual edge hardware**
- Emulators miss real-world constraints (thermal throttling, memory fragmentation)
- Profile on target hardware before deployment

**Pitfall 4: Synchronous training with heterogeneous devices**
- Slow devices bottleneck synchronous training
- Use asynchronous SGD or tolerate stragglers

## SEE ALSO
- `EFFICIENT_AI_PRIME` - Model compression for edge deployment
- `MLOPS_DEPLOYMENT_PRIME` - Production deployment and on-device learning
- `MODEL_OPTIMIZATION_PRIME` - Hardware-aware optimization techniques
- `HARDWARE_PROFILE_PRIME` - Cohezion's AMD hardware specifications
- [[cs249r/ondevice_learning]] - On-device learning chapter concepts
