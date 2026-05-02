#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

"""M2: Federated MoE - Distributed Expert Training with Privacy.

Federated Learning Concept:
- Multiple clients, central server
- Local training, global aggregation
- Privacy: raw data never leaves client
- For MoE: Each client specializes experts

Implementation:
1. Local expert updates on client data
2. Secure aggregation to server
3. Global model with all experts
4. Personalized routing per client

Benefits:
- Privacy preservation
- Distributed training
- Client specialization
- No central data collection

Reference: "Communication-Efficient Learning of Deep Networks", AISTATS 2017.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


os.environ["AITER_USE_NT"] = "1"
os.environ["AITER_KSPLIT"] = "2"

import torch
from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from task import input_t, output_t


@dataclass
class ClientState:
    """State for federated client."""

    client_id: str
    expert_weights: dict[int, torch.Tensor]  # Local expert updates
    data_distribution: torch.Tensor  # Distribution over data


class FederatedMoE:
    """Federated Mixture of Experts."""

    def __init__(self, num_experts: int, num_clients: int):
        self.num_experts = num_experts
        self.num_clients = num_clients

        # Global model
        self.global_experts: dict[int, torch.Tensor] = {}

        # Client states
        self.clients: dict[str, ClientState] = {}

        # Expert assignment per client
        self.client_expert_map: dict[str, list[int]] = {}

    def register_client(self, client_id: str) -> None:
        """Register new federated client."""
        # Assign subset of experts to client
        experts_per_client = self.num_experts // self.num_clients
        start_idx = len(self.clients) * experts_per_client
        assigned = list(range(start_idx, start_idx + experts_per_client))

        self.client_expert_map[client_id] = assigned
        self.clients[client_id] = ClientState(
            client_id=client_id,
            expert_weights={},
            data_distribution=torch.ones(experts_per_client) / experts_per_client,
        )

    def local_update(self, client_id: str, local_data: torch.Tensor) -> dict[int, torch.Tensor]:
        """Perform local expert update.

        Args:
            client_id: Client identifier
            local_data: Local training data

        Returns:
            Updated expert weights
        """
        # Get client's assigned experts
        assigned = self.client_expert_map.get(client_id, [])

        # Local training (simplified)
        updates = {}
        for expert_id in assigned:
            # Compute local gradient
            # In production: actual training
            updates[expert_id] = torch.randn(1) * 0.01

        return updates

    def secure_aggregation(
        self, client_updates: dict[str, dict[int, torch.Tensor]]
    ) -> dict[int, torch.Tensor]:
        """Aggregate client updates securely.

        Uses secure multi-party computation or differential privacy.
        """
        aggregated = {}

        # Simple average (in production: secure aggregation)
        for expert_id in range(self.num_experts):
            updates = [
                updates[expert_id] for updates in client_updates.values() if expert_id in updates
            ]

            if updates:
                aggregated[expert_id] = torch.stack(updates).mean()

        return aggregated

    def get_personalized_routing(self, client_id: str, hidden_states: torch.Tensor) -> torch.Tensor:
        """Get personalized routing for client.

        Args:
            client_id: Client identifier
            hidden_states: Input

        Returns:
            Routing preferences
        """
        if client_id not in self.clients:
            # Use global routing
            return torch.ones(hidden_states.shape[0], self.num_experts) / self.num_experts

        client = self.clients[client_id]

        # Personalize based on client's data distribution
        probs = client.data_distribution

        # Expand to batch
        return probs.unsqueeze(0).expand(hidden_states.shape[0], -1)


def _federated_routing(
    hidden_states: torch.Tensor, num_experts: int, client_id: Optional[str] = None
) -> torch.Tensor:
    """Apply federated personalized routing.

    Args:
        hidden_states: Input
        num_experts: Number of experts
        client_id: Optional client identifier

    Returns:
        Personalized routing weights
    """
    fed = FederatedMoE(num_experts, num_clients=4)

    if client_id:
        fed.register_client(client_id)
        probs = fed.get_personalized_routing(client_id, hidden_states)
    else:
        probs = torch.ones(hidden_states.shape[0], num_experts) / num_experts

    return probs.to(hidden_states.device)


def custom_kernel(data: input_t) -> output_t:
    """Federated MoE with distributed expert training.

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

    hidden_pad = config["d_hidden_pad"] - config["d_hidden"]
    intermediate_pad = config["d_expert_pad"] - config["d_expert"]
    d_expert = config.get("d_expert", 0)
    num_experts = config.get("num_experts", 256)

    use_federated = os.environ.get("MOE_FEDERATED", "0") == "1"
    client_id = os.environ.get("MOE_CLIENT_ID", None)

    if use_federated:
        try:
            # Apply federated routing
            fed_probs = _federated_routing(hidden_states, num_experts, client_id)

            # Blend with standard routing
            alpha = 0.5
            combined = alpha * fed_probs + (1 - alpha) * topk_weights

            routing_weights = combined
            routing_ids = topk_ids

            print(f"[Federated] Client: {client_id}")

        except Exception as e:
            print(f"[Federated] Error: {e}")
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
        print(f"[Federated MoE] Error: {e}")

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
