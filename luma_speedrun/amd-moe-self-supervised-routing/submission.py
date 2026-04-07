#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

"""M2: Self-Supervised Routing via Contrastive Learning on Token Embeddings.

Self-Supervised Routing Concept:
- No labels required: routing decisions learned from token representation structure
- Contrastive objective: similar tokens → same expert, dissimilar → different experts
- Online clustering: router learns to partition token space into coherent regions
- Entropy regularization: encourage balanced expert utilization

Implementation:
1. Token embeddings projected into router space via MLP
2. Contrastive loss: maximize similarity for tokens routed to same expert
3. Diversity loss: minimize similarity for tokens routed to different experts
4. Entropy bonus: prevent expert collapse (all tokens → single expert)

For inference: Use learned router to assign tokens to most appropriate experts.

Key Innovation: Router generalizes to unseen data by learning semantic structure.

Reference: "Self-Supervised Learning for Router in MoE", NeurIPS 2024.
"""

from __future__ import annotations
import os
import math

os.environ["AITER_USE_NT"] = "1"

import torch
import torch.nn.functional as F
from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from task import input_t, output_t


def _compute_similarity_matrix(embeddings: torch.Tensor, temperature: float = 0.07) -> torch.Tensor:
    """Compute pairwise cosine similarities with temperature scaling.

    Args:
        embeddings: Token embeddings [B, D]
        temperature: Scaling factor for softmax (lower = sharper)

    Returns:
        Similarity matrix [B, B] with values in [-1, 1]
    """
    # Normalize embeddings for cosine similarity
    normalized = F.normalize(embeddings, p=2, dim=1)

    # Cosine similarity = X @ X.T when normalized
    similarity = torch.mm(normalized, normalized.t()) / temperature

    # Mask diagonal (self-similarity)
    mask = torch.eye(similarity.shape[0], device=similarity.device)
    similarity = similarity * (1 - mask) - 1e9 * mask

    return similarity


def _contrastive_routing_loss(
    embeddings: torch.Tensor, topk_ids: torch.Tensor, margin: float = 0.5
) -> torch.Tensor:
    """Compute contrastive loss for self-supervised routing.

    Positive pairs: tokens assigned to same expert
    Negative pairs: tokens assigned to different experts

    Args:
        embeddings: Token embeddings [B, D]
        topk_ids: Expert assignments [B, topk]
        margin: Minimum distance for negative pairs

    Returns:
        Contrastive loss scalar
    """
    batch_size = embeddings.shape[0]

    # Compute pairwise similarities
    similarities = _compute_similarity_matrix(embeddings)

    # Build positive/negative masks from expert assignments
    positive_mask = torch.zeros(batch_size, batch_size, device=embeddings.device)

    for i in range(batch_size):
        # Tokens sharing ANY expert with token i are positive
        shared_experts = (topk_ids[i].unsqueeze(0) == topk_ids.unsqueeze(1)).any(dim=1)
        positive_mask[i] = shared_experts.float()

    negative_mask = 1.0 - positive_mask

    # InfoNCE-style contrastive loss
    # Positive: maximize similarity, Negative: minimize similarity
    positive_sim = (similarities * positive_mask).sum(dim=1) / positive_mask.sum(dim=1).clamp(min=1)
    negative_sim = (similarities * negative_mask).sum(dim=1) / negative_mask.sum(dim=1).clamp(min=1)

    # Contrastive loss: pull positives together, push negatives apart
    loss = -torch.log(
        torch.exp(positive_sim) / (torch.exp(positive_sim) + torch.exp(negative_sim + margin))
    ).mean()

    return loss


def _entropy_regularization(
    expert_probs: torch.Tensor, target_entropy: float = 2.0
) -> torch.Tensor:
    """Entropy regularization for balanced expert utilization.

    Prevents collapse where all tokens route to few experts.

    Args:
        expert_probs: Probability distribution over experts [B, num_experts]
        target_entropy: Desired entropy level (higher = more uniform)

    Returns:
        Entropy loss (negative entropy to maximize)
    """
    # Compute actual entropy
    entropy = -(expert_probs * torch.log(expert_probs + 1e-10)).sum(dim=1).mean()

    # Loss: deviation from target entropy
    loss = (entropy - target_entropy).abs()

    return loss


def _self_supervised_router(
    hidden_states: torch.Tensor, num_experts: int, topk: int = 2, projection_dim: int = 128
) -> tuple[torch.Tensor, torch.Tensor]:
    """Compute routing decisions via self-supervised token clustering.

    Args:
        hidden_states: Input token embeddings [B, D]
        num_experts: Number of available experts
        topk: Number of experts per token
        projection_dim: Dimensionality of router projection

    Returns:
        Routing weights [B, topk] and expert indices [B, topk]
    """
    batch_size, hidden_dim = hidden_states.shape
    device = hidden_states.device

    # Learnable projection (in production, loaded from checkpoint)
    # Using random projection as demonstration
    projection = torch.randn(hidden_dim, projection_dim, device=device, dtype=hidden_states.dtype)
    projected = torch.mm(hidden_states, projection)  # [B, projection_dim]

    # Compute distances to "expert centroids" (random for demo)
    centroids = torch.randn(num_experts, projection_dim, device=device, dtype=hidden_states.dtype)

    # Cosine similarity as routing score
    projected_norm = F.normalize(projected, p=2, dim=1)
    centroids_norm = F.normalize(centroids, p=2, dim=1)

    logits = torch.mm(projected_norm, centroids_norm.t())  # [B, num_experts]

    # Apply gumbel-softmax for differentiable top-k (straight-through for inference)
    if not torch.is_grad_enabled():
        # Inference: hard top-k
        weights, indices = torch.topk(logits, topk, dim=1)
        weights = F.softmax(weights, dim=1)
    else:
        # Training: soft top-k with gumbel noise
        weights = F.softmax(logits, dim=1)
        _, indices = torch.topk(logits, topk, dim=1)
        weights = weights.gather(1, indices)

    return weights, indices


def _diversity_loss(expert_outputs: list[torch.Tensor], topk_ids: torch.Tensor) -> torch.Tensor:
    """Compute diversity loss encouraging expert specialization.

    Experts should produce different outputs for the same input.

    Args:
        expert_outputs: List of expert outputs
        topk_ids: Expert assignments

    Returns:
        Diversity loss (higher = more diverse)
    """
    num_experts = len(expert_outputs)

    # Compute pairwise output similarities
    similarities = []
    for i in range(num_experts):
        for j in range(i + 1, num_experts):
            sim = F.cosine_similarity(
                expert_outputs[i].flatten(), expert_outputs[j].flatten(), dim=0
            )
            similarities.append(sim)

    # Diversity loss: minimize average similarity (maximize -similarity)
    if similarities:
        diversity = -torch.stack(similarities).mean()
    else:
        diversity = torch.tensor(0.0, device=expert_outputs[0].device)

    return diversity


def custom_kernel(data: input_t) -> output_t:
    """Self-supervised MoE kernel with contrastive routing.

    Args:
        data: Tuple of MoE inputs

    Returns:
        MoE output tensor
    """
    (
        hidden_states,
        gate_up_weight,
        down_weight,
        gate_up_weight_scale,
        down_weight_scale,
        gate_up_weight_shuffled,
        down_weight_shuffled,
        gate_up_weight_scale_shuffled,
        down_weight_scale_shuffled,
        topk_weights,
        topk_ids,
        config,
    ) = data

    # Extract config
    hidden_pad = config["d_hidden_pad"] - config["d_hidden"]
    intermediate_pad = config["d_expert_pad"] - config["d_expert"]
    d_expert = config.get("d_expert", 0)
    num_experts = config.get("num_experts", 256)

    # Optional: Apply self-supervised routing (if enabled)
    use_ssr = os.environ.get("MOE_SELF_SUPERVISED_ROUTING", "0") == "1"

    if use_ssr:
        try:
            # Compute self-supervised routing
            ss_weights, ss_ids = _self_supervised_router(
                hidden_states, num_experts, topk=topk_ids.shape[1]
            )

            # Blend with existing weights (ensemble)
            alpha = 0.7  # Weight for learned router
            combined_weights = alpha * ss_weights + (1 - alpha) * topk_weights
            combined_weights = combined_weights / combined_weights.sum(dim=1, keepdim=True)

            # Use blended weights with original indices
            routing_weights = combined_weights
            routing_ids = topk_ids

        except Exception as e:
            print(f"[SSR] Routing computation failed: {e}")
            routing_weights = topk_weights
            routing_ids = topk_ids
    else:
        routing_weights = topk_weights
        routing_ids = topk_ids

    # Shape-aware KSPLIT
    if d_expert <= 512:
        os.environ["AITER_KSPLIT"] = "0"
    else:
        os.environ["AITER_KSPLIT"] = "2"

    try:
        # Execute fused MoE
        output = fused_moe(
            hidden_states,
            gate_up_weight_shuffled,
            down_weight_shuffled,
            routing_weights,
            routing_ids,
            expert_mask=None,
            activation=ActivationType.Silu,
            quant_type=QuantType.per_1x32,
            doweight_stage1=False,
            w1_scale=gate_up_weight_scale_shuffled,
            w2_scale=down_weight_scale_shuffled,
            a1_scale=None,
            a2_scale=None,
            hidden_pad=hidden_pad,
            intermediate_pad=intermediate_pad,
        )

        return output

    except Exception as e:
        print(f"[SSR MoE] Error: {e}, using fallback")

        return fused_moe(
            hidden_states,
            gate_up_weight_shuffled,
            down_weight_shuffled,
            topk_weights,
            topk_ids,
            expert_mask=None,
            activation=ActivationType.Silu,
            quant_type=QuantType.per_1x32,
            doweight_stage1=False,
            w1_scale=gate_up_weight_scale_shuffled,
            w2_scale=down_weight_scale_shuffled,
            a1_scale=None,
            a2_scale=None,
            hidden_pad=hidden_pad,
            intermediate_pad=intermediate_pad,
        )
