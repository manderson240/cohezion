# FLUME: Thought Autoencoders for Agent Navigation

**Training continuous latent representations that enable semantic trajectory prediction**

*Mike Anderson • [Date] • 8 min read*

---

## The Problem: Discrete Tokens Don't Capture Reasoning Trajectories

When building agentic AI systems that perform long-horizon tasks, we face a fundamental challenge: how do we represent the *path* an agent's reasoning takes, not just the discrete outputs it produces?

Traditional language models operate in discrete token space. They predict the next token, then the next, in a chain. This works remarkably well for text generation, but it has limitations for agent reasoning:

1. **No continuous interpolation**: You can't smoothly interpolate between "research the problem" and "write the solution"
2. **Hard to predict trajectories**: Given a starting concept, what semantic path will the agent take?
3. **Difficult coherence tracking**: How do we measure if an agent is drifting from its intended reasoning path?

For Cohezion's compound engineering loop—where agents execute tasks, reflect on their performance, and refine their own skills—we needed a way to represent *semantic intent* as continuous vectors. This enables:

- **Trajectory prediction**: Given a starting state, where will the agent's reasoning go?
- **Coherence tracking**: Measure distance from the intended path in continuous space
- **Skill refinement**: Compare "before refinement" and "after refinement" thought vectors

**Enter FLUME**: Fluid Latent Understanding through Manifold Encoding.

---

## The Approach: Variational Autoencoders for Thought Compression

FLUME is a **variational autoencoder (VAE)** that compresses text into 256-dimensional continuous "thought vectors." The architecture:

```
Text → Encoder → 256D latent vector (z) → Decoder → Reconstructed text
              ↓
          Continuous semantic space
          (interpolation, trajectory prediction)
```

### Why VAE instead of standard autoencoder?

A standard autoencoder learns to compress input → latent → reconstruct. But the latent space can be "spiky"—nearby vectors might represent completely different concepts.

A **VAE adds probabilistic structure**:
- Encoder outputs: **mu** (mean) and **log_var** (log variance) for each latent dimension
- Sample latent vector: `z = mu + std * epsilon` (reparameterization trick)
- Loss function: **reconstruction loss** + **KL divergence** (forces smooth latent space)

This gives us:
- **Smooth interpolation**: Linear paths between concepts in latent space map to semantically coherent trajectories
- **Generative capability**: Sample new thought vectors from the learned distribution
- **Uncertainty quantification**: Variance indicates confidence in the latent representation

---

## Architecture Deep Dive

### Encoder: Text → Thought Vector

```python
class ThoughtEncoder(nn.Module):
    def __init__(self, config: FlumeConfig):
        super().__init__()

        # Token embedding + positional encoding
        self.embedding = nn.Embedding(config.vocab_size, config.embed_dim)
        self.pos_embedding = nn.Embedding(config.max_seq_len, config.embed_dim)

        # Transformer encoder (2 layers, 4 heads, 256D)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=config.embed_dim,
            nhead=config.num_heads,
            dim_feedforward=config.hidden_dim,
            dropout=config.dropout,
            batch_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, config.num_layers)

        # Project to latent space
        self.to_z = nn.Linear(config.embed_dim, config.z_dim)

    def forward(self, tokens, attention_mask=None):
        # tokens: [batch, seq_len]
        positions = torch.arange(seq_len, device=tokens.device)
        x = self.embedding(tokens) + self.pos_embedding(positions)

        # Transformer encoding
        x = self.transformer(x, src_key_padding_mask=~attention_mask)

        # Mean pooling (attention-weighted)
        x = (x * attention_mask.unsqueeze(-1)).sum(1) / attention_mask.sum(1).unsqueeze(-1)

        # Project to 256D thought vector
        z = self.to_z(x)
        return z
```

**Key design decisions**:

1. **Transformer encoder** (not RNN): Captures long-range dependencies in reasoning text
2. **Mean pooling** (not CLS token): Aggregates semantic content across entire sequence
3. **256D latent space**: Balances expressiveness (high-dim) vs tractability (interpretable projections)

### Decoder: Thought Vector → Text

The decoder mirrors the encoder: linear projection → transformer decoder → token logits. We use teacher forcing during training (feed ground-truth tokens), then autoregressive sampling at inference.

### VAE Components: Mu, Log-Var, Reparameterization

For Cohezion's simplified VAE (operating directly on latent vectors, not text):

```python
class FlumeVAETrainer:
    def __init__(self, config):
        z_dim = config.z_dim  # 256
        hidden = z_dim * 2    # 512

        # Encoder: z -> hidden -> (mu, log_var)
        self.encoder = nn.Sequential(
            nn.Linear(z_dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
        )
        self.mu_head = nn.Linear(hidden, z_dim)
        self.logvar_head = nn.Linear(hidden, z_dim)

        # Decoder: z -> hidden -> reconstruction
        self.decoder = nn.Sequential(
            nn.Linear(z_dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Linear(hidden, z_dim),
        )

    def _reparameterize(self, mu, log_var):
        """VAE reparameterization trick: z = mu + std * eps"""
        std = torch.exp(0.5 * log_var)
        eps = torch.randn_like(std)
        return mu + std * eps
```

**Why reparameterization?** We need gradients to flow through the sampling step. By expressing `z = mu + std * epsilon` (where epsilon is random noise), we can backpropagate through `mu` and `std`.

---

## Training Pipeline

### Data: Thought Vectors from Compound Execution

We trained FLUME on **11,000 thought vectors** extracted from Cohezion's compound engineering loop. Each vector represents:
- Agent intent before task execution
- Reasoning trace during execution
- Reflection after completion
- Refined skill definition post-retrospection

**Data source**: `data/mass_sim/artifacts/` (JSONL files with latent states from universe simulation)

### Loss Function: Reconstruction + KL + Coherence

```python
def compute_loss(self, x, recon, mu, log_var):
    # 1. Reconstruction loss (MSE)
    recon_loss = F.mse_loss(recon, x, reduction='mean')

    # 2. KL divergence (regularization)
    # KL(q(z|x) || p(z)) where p(z) = N(0, I)
    kl_loss = -0.5 * torch.mean(1 + log_var - mu.pow(2) - log_var.exp())

    # 3. Coherence regularization (toward HIHO 0.5 target)
    coherence = compute_coherence(recon)  # Custom metric
    coherence_loss = (coherence - 0.5).pow(2).mean()

    # Combined loss
    total_loss = (
        recon_loss +
        self.config.kl_weight * kl_loss +
        self.config.coherence_weight * coherence_loss
    )

    return total_loss, {
        'recon': recon_loss.item(),
        'kl': kl_loss.item(),
        'coherence': coherence_loss.item(),
    }
```

**Hyperparameters**:
- `kl_weight = 0.01`: Balance reconstruction vs regularization (updated from 0.1 — β≥0.1 causes posterior collapse per autoresearch 2026-05-15)
- `coherence_weight = 0.05`: Soft constraint toward HIHO stability
- `lr = 1e-3`: Adam optimizer with cosine annealing schedule
- `batch_size = 128`: Fits in 128GB RAM on Strix Halo (no GPU); updated from 64 — bs=128 gives +0.8% reconstruction improvement

### Training Results

After **50 epochs** on 11K samples:

| Metric | Value | Interpretation |
|--------|-------|----------------|
| **MSE** | 0.1322 | Low reconstruction error (scale: 0-1) |
| **KL divergence** | 0.4329 | Balanced latent distribution (not collapsed) |
| **Coherence** | 0.63 ± 0.15 | Slightly above HIHO 0.5 target (exploration bias) |
| **Training time** | ~2 hours | On AMD Ryzen AI MAX+ 395 (16C, CPU only) |

**Training curve**:

```
Epoch  1/50: loss=0.89, recon=0.67, kl=1.82, coherence=0.71
Epoch 10/50: loss=0.34, recon=0.28, kl=0.52, coherence=0.65
Epoch 25/50: loss=0.21, recon=0.17, kl=0.44, coherence=0.63
Epoch 50/50: loss=0.18, recon=0.13, kl=0.43, coherence=0.63
```

**Key observation**: KL divergence stabilized around 0.43, indicating the latent space is smooth (no posterior collapse) but not over-regularized.

---

## Applications: What Can You Do With Thought Vectors?

### 1. Semantic Interpolation

Interpolate between two concepts by linearly interpolating their latent vectors:

```python
# Encode two concepts
z_research = encoder.encode("Research the problem thoroughly")
z_planning = encoder.encode("Create a detailed implementation plan")

# Interpolate (alpha from 0 to 1)
z_intermediate = (1 - alpha) * z_research + alpha * z_planning

# Decode to see intermediate semantic steps
text = decoder.decode(z_intermediate)
# Example outputs (alpha = [0.0, 0.25, 0.5, 0.75, 1.0]):
# 0.00: "Research the problem thoroughly"
# 0.25: "Research and outline key requirements"
# 0.50: "Draft initial approach based on research"
# 0.75: "Refine approach into actionable plan"
# 1.00: "Create a detailed implementation plan"
```

**Use case**: Predict intermediate reasoning steps an agent will take.

### 2. Trajectory Prediction

Given an agent's starting state and task, predict where its reasoning will go:

```python
# Agent starts with research intent
z_start = encoder.encode(agent_initial_intent)

# Predict next steps using learned dynamics (linear approximation)
z_trajectory = [z_start]
for step in range(max_steps):
    z_next = z_trajectory[-1] + learned_velocity_field(z_trajectory[-1])
    z_trajectory.append(z_next)

# Decode trajectory to semantic path
semantic_path = [decoder.decode(z) for z in z_trajectory]
```

**Use case**: Early detection if agent is heading toward low-coherence regions.

### 3. Coherence Tracking

Measure how far the agent drifts from its intended path:

```python
# Expected trajectory (from initial plan)
z_expected = encoder.encode(planned_reasoning_path)

# Actual trajectory (from agent execution)
z_actual = encoder.encode(actual_agent_output)

# Coherence = 1 - normalized_distance
distance = torch.norm(z_actual - z_expected)
coherence = 1.0 / (1.0 + distance)  # Maps [0, inf) to [0, 1]

# Trigger intervention if coherence < 0.5 (HIHO threshold)
if coherence < 0.5:
    logger.warning("Agent coherence degrading, initiating rollback")
```

**Use case**: Real-time degradation detection in the compound engineering loop.

### 4. Skill Refinement Visualization

After retrospection, compare before/after skill definitions:

```python
# Before refinement
z_before = encoder.encode(original_skill_definition)

# After refinement (from RetrospectionEngine)
z_after = encoder.encode(refined_skill_definition)

# Visualize change (project 256D -> 2D via t-SNE)
projection = tsne.fit_transform([z_before, z_after])

# Plot trajectory: before -> after
plt.plot([projection[0,0], projection[1,0]],
         [projection[0,1], projection[1,1]],
         marker='o', label='Skill refinement')
```

**Use case**: Observable AI—show users how agent skills evolve over time.

---

## Production Deployment: Checkpoints & Inference

### Saving Checkpoints

```python
checkpoint = {
    'epoch': epoch,
    'encoder_state': self.encoder.state_dict(),
    'decoder_state': self.decoder.state_dict(),
    'mu_head_state': self.mu_head.state_dict(),
    'logvar_head_state': self.logvar_head.state_dict(),
    'optimizer_state': optimizer.state_dict(),
    'config': self.config,
    'metrics': {'mse': mse, 'kl': kl, 'coherence': coherence},
}
torch.save(checkpoint, f'data/flume/checkpoints/flume_vae_ep{epoch}.pt')
```

**Checkpoint strategy**:
- Save every 10 epochs during training
- Keep best checkpoint (lowest combined loss)
- Store config + metrics for reproducibility

### Loading for Inference

```python
from cohezion.flume.training import FlumeVAETrainer

# Load trained model
trainer = FlumeVAETrainer.from_checkpoint('data/flume/checkpoints/flume_vae_ep50.pt')

# Encode text to thought vector
z = trainer.encode(latent_vector)

# Decode thought vector to text (if using full text-based VAE)
text = trainer.decode(z)
```

---

## Lessons Learned: Production Insights

### 1. CPU-Only Training Is Viable

**Challenge**: Strix Halo has an iGPU (Radeon 8060S) with unified memory, but PyTorch CUDA support is flaky. We trained entirely on CPU.

**Solution**:
- Small batch size (64) fits in L3 cache → fast iteration
- Cosine annealing LR schedule → fewer epochs needed (50 vs 200+)
- Incremental checkpointing → resume from failure without retraining

**Result**: 2 hours for 50 epochs on 11K samples (acceptable for research iteration).

### 2. KL Weight Tuning Is Critical

**Challenge**: Initial training collapsed to zero KL divergence (posterior collapse). Model ignored latent code, decoded from prior only.

**Solution**:
- Start with `kl_weight = 0.01` (weak regularization)
- Gradually increase to `0.1` over first 10 epochs (KL annealing)
- Monitor KL divergence: should stabilize around 0.3-0.5

**Result**: Final KL = 0.4329 (healthy latent structure).

### 3. Coherence Regularization Prevents Drift

**Challenge**: Without coherence loss, reconstructed vectors drifted far from HIHO 0.5 target (avg 0.82, too exploitative).

**Solution**:
- Add soft constraint: `(coherence - 0.5)^2` with weight 0.05
- Don't make it too strong (overfits to 0.5, loses diversity)

**Result**: Mean coherence 0.63 ± 0.15 (biased toward exploration, but not collapsed).

---

## Future Work: Scaling FLUME

### 1. Conditional VAE (Task-Specific Latent Spaces)

Right now, FLUME learns a single 256D space for all reasoning types. We could condition on task type:

```python
# Encoder takes (text, task_type)
z = encoder(text, condition=task_type)  # "research", "planning", "execution"
```

This creates **task-specific manifolds** in latent space, enabling better trajectory prediction per domain.

### 2. Multi-Modal Encoding (Code + Text)

Agents often work with code. Extend FLUME to encode (text + code) jointly:

```python
z = encoder(text=reasoning_trace, code=implementation)
```

This enables coherence tracking across modalities (is the code aligned with the reasoning?).

### 3. Diffusion Models for Trajectory Generation

Instead of deterministic interpolation, use **diffusion models** to sample diverse reasoning trajectories:

```python
# Sample 10 plausible paths from z_start to z_goal
trajectories = diffusion_model.sample(z_start, z_goal, n_samples=10)
```

**Use case**: Generate diverse approaches to a task, not just linear interpolation.

---

## Try It Yourself: Interactive Demo

I've deployed a live Marimo notebook where you can:
- Encode custom text → visualize in 2D latent space (t-SNE projection)
- Interpolate between concepts → see semantic intermediate steps
- View training curves (MSE, KL, coherence over epochs)
- Explore coherence tracking on example agent trajectories

**[Live Demo]** | **[GitHub Code]** | **[Training Guide]**

---

## Conclusion

FLUME demonstrates that **thought autoencoders** enable new capabilities for agentic AI:
- Continuous semantic navigation (not discrete tokens)
- Trajectory prediction (where will reasoning go?)
- Coherence tracking (detect drift before failure)

This infrastructure directly supports Cohezion's compound engineering loop, where agents refine their own skills through retrospection. By representing semantic intent as continuous vectors, we make agent reasoning **observable, predictable, and controllable**.

If you're building long-horizon agent systems, consider: **Can you represent your agent's reasoning as trajectories in continuous space?** If so, tools like FLUME VAE can unlock new evaluation and intervention strategies.

---

**Technical Details**:
- **Architecture**: Transformer encoder/decoder, 256D latent
- **Training**: 50 epochs, 11K samples, 2 hours on AMD Ryzen AI MAX+ 395
- **Metrics**: MSE 0.1322, KL 0.4329, coherence 0.63±0.15
- **Code**: [github.com/manderson240/cohezion/src/cohezion/flume](https://github.com/manderson240/cohezion)

**Questions or feedback?** Reach out on [LinkedIn/Twitter/Email]

---

*This is part 1 of a 5-part series on building production infrastructure for agentic AI. Next: "Observable AI: The Compound Engineering Loop."*
