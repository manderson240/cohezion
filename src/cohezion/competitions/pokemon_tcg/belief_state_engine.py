"""Pokémon TCG Public Belief State (PBS) & Policy Inference Engine."""

from __future__ import annotations

from typing import Any

import numpy as np


class PublicBeliefStateEngine:
    """Constructs probability vectors over unobserved opponent hands & prize cards."""

    def __init__(self, full_deck_list: list[int]):
        self.full_deck = full_deck_list.copy()

    def compute_belief_vector(
        self,
        visible_hand: list[int],
        visible_board: list[int],
        discard_pile: list[int],
        prizes_remaining: int,
    ) -> dict[str, np.ndarray]:
        # Track remaining unrevealed cards
        revealed = visible_hand + visible_board + discard_pile
        remaining_deck = self.full_deck.copy()
        for c in revealed:
            if c in remaining_deck:
                remaining_deck.remove(c)

        total_unrevealed = len(remaining_deck)
        if total_unrevealed == 0:
            probs = np.zeros(len(set(self.full_deck)), dtype=np.float32)
        else:
            counts = {}
            for c in remaining_deck:
                counts[c] = counts.get(c, 0) + 1
            unique_cards = sorted(list(set(self.full_deck)))
            probs = np.array(
                [counts.get(c, 0) / float(total_unrevealed) for c in unique_cards], dtype=np.float32
            )

        # Prize slot probability vector (6 slots)
        prize_dist = np.full((6,), prizes_remaining / 6.0, dtype=np.float32)

        return {
            "unrevealed_card_distribution": probs,
            "prize_distribution": prize_dist,
            "unrevealed_count": total_unrevealed,
        }

    def construct_state_tensor(
        self, active_hp: float, active_energy: int, belief_dict: dict[str, Any]
    ) -> np.ndarray:
        """Fuses visible scalars with probabilistic belief state into flat input vector."""
        visible_scalars = np.array([active_hp / 300.0, active_energy / 10.0], dtype=np.float32)
        return np.concatenate(
            [
                visible_scalars,
                belief_dict["unrevealed_card_distribution"],
                belief_dict["prize_distribution"],
            ]
        )
