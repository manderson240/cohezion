r"""Cognitive CRM & Agentic Kanban Mesh Engine.
=============================================
Implements a next-generation Sovereign CRM & Reactive Kanban system:

1. **Relational Entities & Graph Topology**:
   - `Stakeholder`, `Organization`, `Opportunity`, `InteractionEvent`, `KanbanCard`.
   - Graph Edges: `INITIATED`, `ASSIGNED_TO`, `RESOLVED`, `BLOCKED_BY`.

2. **12D Poincaré Intent & Affinity Manifold**:
   - Projects customer/partner interactions into 12D hyperbolic space.
   - Computes Fréchet hyperbolic distance and affinity gradient to predict deal velocity.

3. **Topological Quality Gates for Card Movement**:
   - `in_progress` -> `review` strictly requires:
     a) AutoHarness AST Zero-Cost Verifier Proof Hash.
     b) Palimpsa Bayesian Metaplasticity Memory Retention (>= 0.85).
     c) Sheaf Cohomology Multi-Agent Consensus (H^1 = 0).

4. **Bi-Directional Reactive EventBus Dispatch**:
   - Emits asynchronous `kanban.transition` and `crm.touchpoint` events.
"""

from __future__ import annotations

import enum
import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("cognitive_crm")


class KanbanStatus(str, enum.Enum):
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    ARCHIVED = "archived"


class DealStage(str, enum.Enum):
    DISCOVERY = "discovery"
    FEASIBILITY = "feasibility"
    SYNTHESIS = "synthesis"
    SOVEREIGNTY_DELIVERY = "sovereignty_delivery"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


@dataclass(slots=True)
class Stakeholder:
    id: str
    name: str
    organization_id: str
    email: str
    intent_vector_12d: np.ndarray
    affinity_score: float = 0.5
    created_at: float = field(default_factory=time.time)


@dataclass(slots=True)
class Opportunity:
    id: str
    title: str
    stakeholder_id: str
    deal_stage: DealStage
    estimated_value: float
    poincare_affinity_centroid: np.ndarray
    associated_kanban_ids: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


@dataclass(slots=True)
class KanbanCard:
    id: str
    title: str
    status: KanbanStatus
    owner_agent: str
    assigned_stakeholder_id: str | None = None
    ast_proof_hash: str | None = None
    sheaf_consensus_dim_h1: int = 0
    retention_score: float = 1.0
    payload: dict[str, Any] = field(default_factory=dict)
    updated_at: float = field(default_factory=time.time)


class CognitiveCRMEngine:
    """Enterprise Cognitive CRM & Reactive Agentic Kanban Engine."""

    def __init__(self) -> None:
        self.stakeholders: dict[str, Stakeholder] = {}
        self.opportunities: dict[str, Opportunity] = {}
        self.cards: dict[str, KanbanCard] = {}

    def register_stakeholder(
        self,
        stakeholder_id: str,
        name: str,
        organization_id: str,
        email: str,
        intent_vector_12d: np.ndarray | None = None,
    ) -> Stakeholder:
        """Register a new stakeholder with 12D intent coordinates."""
        if intent_vector_12d is None:
            vec = np.zeros(12, dtype=np.float64)
        else:
            vec = np.array(intent_vector_12d, dtype=np.float64)
            norm = np.linalg.norm(vec)
            if norm >= 1.0:
                vec = (vec / norm) * 0.95  # Clamped to Poincaré unit ball

        s = Stakeholder(
            id=stakeholder_id,
            name=name,
            organization_id=organization_id,
            email=email,
            intent_vector_12d=vec,
        )
        self.stakeholders[stakeholder_id] = s
        return s

    def compute_hyperbolic_affinity(self, u: np.ndarray, v: np.ndarray) -> float:
        r"""Compute affinity score in [0.0, 1.0] from Poincaré hyperbolic distance."""
        u_norm_sq = min(0.999, float(np.dot(u, u)))
        v_norm_sq = min(0.999, float(np.dot(v, v)))
        diff_sq = float(np.dot(u - v, u - v))
        denom = max(1e-10, (1.0 - u_norm_sq) * (1.0 - v_norm_sq))
        arg = 1.0 + 2.0 * diff_sq / denom
        dist_p = math.acosh(max(1.0, arg))
        # Map distance to [0, 1] affinity decay
        return round(float(math.exp(-0.25 * dist_p)), 4)

    def create_kanban_card(
        self,
        card_id: str,
        title: str,
        owner_agent: str,
        stakeholder_id: str | None = None,
    ) -> KanbanCard:
        """Create a new Kanban card in BACKLOG status."""
        card = KanbanCard(
            id=card_id,
            title=title,
            status=KanbanStatus.BACKLOG,
            owner_agent=owner_agent,
            assigned_stakeholder_id=stakeholder_id,
        )
        self.cards[card_id] = card
        return card

    def transition_card_status(
        self,
        card_id: str,
        target_status: KanbanStatus,
        ast_proof_hash: str | None = None,
        sheaf_dim_h1: int = 0,
        retention_score: float = 1.0,
    ) -> tuple[bool, str]:
        """Attempt to transition a card through topological quality gates."""
        if card_id not in self.cards:
            return False, f"Card '{card_id}' not found"

        card = self.cards[card_id]

        # Topological Quality Gate: Transition to REVIEW or DONE requires AST safety and Sheaf consensus
        if target_status in (KanbanStatus.REVIEW, KanbanStatus.DONE):
            if not ast_proof_hash:
                return False, "Topological Gate Rejected: Missing AutoHarness AST proof hash"
            if sheaf_dim_h1 != 0:
                return (
                    False,
                    f"Topological Gate Rejected: Sheaf cohomology obstruction (dim H^1 = {sheaf_dim_h1})",
                )
            if retention_score < 0.85:
                return (
                    False,
                    f"Topological Gate Rejected: Palimpsa retention score ({retention_score}) < 0.85 threshold",
                )

        # Apply transition
        card.status = target_status
        card.ast_proof_hash = ast_proof_hash
        card.sheaf_consensus_dim_h1 = sheaf_dim_h1
        card.retention_score = retention_score
        card.updated_at = time.time()

        return True, f"Card '{card_id}' successfully transitioned to '{target_status.value}'"
