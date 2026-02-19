# SKILL: DNN_ARCHITECTURES_PRIME

## DOMAIN EXPERTISE
**Deep Neural Network Architectures**. Specializes in CNNs, RNNs, Transformers, attention mechanisms, architecture selection criteria, and computational complexity analysis for different DNN types.

## KEY TEXTS & CONCEPTS
- **CNNs (Convolutional Neural Networks)**: Spatial feature extraction via convolution layers. Best for images, spatial data. Key components: conv layers, pooling, spatial hierarchy.
- **RNNs (Recurrent Neural Networks)**: Sequential data processing with hidden state. Variants: LSTM (long short-term memory), GRU (gated recurrent units). Best for time series, sequences.
- **Transformers**: Attention-based architecture without recurrence. Parallelizable, scales to massive datasets. Foundation for GPT, BERT, vision transformers.
- **Attention Mechanisms**: Learn what to focus on in input. Types: self-attention (within sequence), cross-attention (between sequences), multi-head attention (parallel attention).
- **Architecture Selection**: Choose based on data type (images→CNN, sequences→Transformer, time series→RNN/Transformer), compute budget, and latency requirements.

**Related Vault Concepts**: [[cs249r/dnn_architectures]], [[cs249r/dl_primer]], [[cs249r/efficient_ai]]
**Related TinyTorch Modules**: Module 09 (convolutions), Module 12 (attention), Module 13 (transformers)

## INSTRUCTION

### 1. Architecture Selection Decision Tree

```
Input Data Type?
├─ Images/Spatial Data → CNN
│   ├─ Small dataset → ResNet-18, EfficientNet-B0
│   ├─ Large dataset → ResNet-50, EfficientNet-B3
│   └─ Strict latency → MobileNetV3, EfficientNet-Lite
│
├─ Sequential/Text Data → Transformer (preferred) or RNN
│   ├─ Long sequences → Transformer (better parallelization)
│   ├─ Real-time streaming → RNN/LSTM (processes sequentially)
│   └─ Limited compute → Distilled BERT, TinyBERT
│
├─ Time Series → Transformer or RNN
│   ├─ Irregular sampling → Transformer (positional encoding handles gaps)
│   ├─ Very long history → Sparse Transformer, Longformer
│   └─ Real-time prediction → LSTM, GRU
│
└─ Multimodal (Image + Text) → Hybrid
    ├─ CNN for images + Transformer for text → fusion layer
    └─ Vision Transformer (ViT) for unified processing
```

### 2. CNN Architecture Patterns

**Convolutional layers for spatial feature extraction:**

```python
import numpy as np

def apply_convolution(input_image, kernel):
    """
    Core CNN operation: sliding window feature extraction.

    TinyTorch reference: Module 09 (convolutions)
    """
    # Convolution = dot product of kernel with image patches
    # Output size = (input_size - kernel_size + 2*padding) / stride + 1
    pass

# Standard CNN architecture
class CNN:
    def __init__(self):
        self.conv1 = Conv2d(in_channels=3, out_channels=64, kernel_size=3)
        self.pool = MaxPool2d(kernel_size=2)
        self.conv2 = Conv2d(64, 128, 3)
        self.fc = Linear(128 * 7 * 7, num_classes)

    def forward(self, x):
        x = relu(self.conv1(x))  # Spatial features
        x = self.pool(x)          # Downsample
        x = relu(self.conv2(x))  # Higher-level features
        x = self.pool(x)
        x = x.flatten()
        return self.fc(x)
```

**Key CNN design choices:**
- **Kernel size**: 3x3 most common (efficient), 1x1 for channel mixing, 5x5+ for larger receptive fields
- **Pooling**: Max pooling (preserves features), Average pooling (smooths), Stride convolutions (learnable downsampling)
- **Depth vs Width**: Deeper (more layers) = more abstract features, Wider (more channels) = more capacity

### 3. Transformer Architecture Patterns

**Attention-based sequence processing:**

```python
class MultiHeadAttention:
    """
    Core transformer operation: learn what to attend to.

    TinyTorch reference: Module 12 (attention), Module 13 (transformers)
    """
    def __init__(self, d_model, num_heads):
        self.d_model = d_model
        self.num_heads = num_heads
        self.head_dim = d_model // num_heads

        # Q, K, V projections
        self.q_proj = Linear(d_model, d_model)
        self.k_proj = Linear(d_model, d_model)
        self.v_proj = Linear(d_model, d_model)
        self.out_proj = Linear(d_model, d_model)

    def forward(self, x):
        # 1. Project to Q, K, V
        Q = self.q_proj(x)  # Queries: what I'm looking for
        K = self.k_proj(x)  # Keys: what each position offers
        V = self.v_proj(x)  # Values: actual content

        # 2. Scaled dot-product attention
        # attention_weights = softmax(Q @ K^T / sqrt(d_k))
        # output = attention_weights @ V

        # 3. Multi-head: parallel attention on different subspaces
        return self.out_proj(output)
```

**Transformer advantages:**
- Parallelizable (unlike RNNs) → faster training on GPUs
- Long-range dependencies via attention
- State-of-the-art for NLP, increasingly for vision

**Transformer costs:**
- O(n²) complexity in sequence length (attention over all pairs)
- Memory intensive (KV cache for generation)
- Requires large datasets to train effectively

### 4. Computational Complexity Analysis

**Model selection based on compute constraints:**

| Architecture | Time Complexity | Space Complexity | Best For |
|------|------|------|------|
| CNN (single conv) | O(C_out × C_in × k² × H × W) | O(C_out × k²) | Images, spatial data |
| RNN (single step) | O(d × h + h × h) | O(h) | Streaming sequences |
| Transformer (single layer) | O(n² × d) | O(n × d) | Parallel sequence processing |

**Where:**
- C = channels, k = kernel size, H/W = height/width (CNN)
- d = embedding dimension, h = hidden size (RNN)
- n = sequence length, d = model dimension (Transformer)

**Practical implications:**
- **Long sequences** → Transformer O(n²) becomes prohibitive. Use sparse attention, hierarchical models, or RNNs.
- **Real-time** → CNN or RNN preferred (no need to process full sequence at once)
- **Batch processing** → Transformer preferred (parallelizable)

### 5. Architecture Optimization Patterns

**Pattern 1: Depth vs Width Trade-off**
```python
# Deeper network (more layers, fewer parameters per layer)
deep_model = [
    Conv(64, 64, 3) for _ in range(10)  # 10 layers, 64 channels
]  # Good for learning hierarchical features

# Wider network (fewer layers, more parameters per layer)
wide_model = [
    Conv(256, 256, 3) for _ in range(3)  # 3 layers, 256 channels
]  # Good for learning diverse features in parallel
```

**Pattern 2: Residual Connections (Skip Connections)**
```python
def residual_block(x):
    """ResNet-style skip connection."""
    identity = x
    x = conv(x)
    x = relu(x)
    x = conv(x)
    return relu(x + identity)  # Add input to output

# Why it works: Allows gradients to flow directly through network
# Enables training very deep networks (100+ layers)
```

**Pattern 3: Efficient Attention (for long sequences)**
```python
# Standard attention: O(n²)
attention = softmax(Q @ K.T / sqrt(d)) @ V

# Sparse attention: O(n * sqrt(n))
# Only attend to nearby positions + few global positions

# Linear attention: O(n)
# Approximate attention with kernel methods
```

### 6. Model Selection Criteria

**Decision matrix for production deployment:**

| Criterion | CNN | RNN/LSTM | Transformer |
|------|------|------|------|
| **Latency** | Low | Medium | Medium-High |
| **Throughput** | High | Low (sequential) | High (parallel) |
| **Memory** | Low | Medium | High |
| **Long sequences** | N/A | Good | Excellent (but costly) |
| **Training speed** | Fast | Slow | Fast (with GPUs) |
| **Data efficiency** | Medium | High | Low (needs big data) |

**Recommended choices:**
- **Mobile/Edge**: MobileNet (CNN), DistilBERT (Transformer), quantized models
- **Cloud/Server**: ResNet-50 (CNN), GPT-style Transformer (text), ViT (vision)
- **Real-time**: EfficientNet-Lite (CNN), LSTM (sequences)

### 7. Integration with TinyTorch Modules

**TinyTorch provides from-scratch implementations:**

```python
# Module 09: Convolutions
from cohezion.tinytorch.convolutions import Conv2d, MaxPool2d

# Module 12: Attention
from cohezion.tinytorch.attention import MultiHeadAttention

# Module 13: Transformers
from cohezion.tinytorch.transformers import TransformerEncoder

# Build a complete vision model
model = Sequential([
    Conv2d(3, 64, kernel_size=3),  # TinyTorch conv
    ReLU(),
    MaxPool2d(2),
    # ... more layers
])
```

**Educational value:** TinyTorch implements these from NumPy only, showing the mathematics behind each architecture without framework abstractions.

### 8. Common Pitfalls

**Pitfall 1: Wrong architecture for data type**
- ❌ Using RNN for images (loses spatial structure)
- ✅ CNN for spatial data, Transformer for sequences

**Pitfall 2: Not considering deployment constraints**
- ❌ Using Transformer with 1B parameters for mobile app
- ✅ Check latency/memory budget before architecture selection

**Pitfall 3: Ignoring inductive biases**
- CNNs have spatial locality bias (good for images)
- RNNs have temporal locality bias (good for sequences)
- Transformers have no built-in bias (need more data but more flexible)

**Pitfall 4: Optimizing for wrong metric**
- ❌ Maximizing accuracy without checking latency
- ✅ Balance accuracy with inference speed and resource usage

## SEE ALSO
- `EFFICIENT_AI_PRIME` - Model quantization, pruning, distillation for deployment
- `MODEL_OPTIMIZATION_PRIME` - Operator fusion, graph optimization
- `ML_SYSTEMS_FOUNDATIONS_PRIME` - ML system lifecycle and production readiness
- TinyTorch modules: `src/cohezion/tinytorch/{convolutions,attention,transformers}.py`
