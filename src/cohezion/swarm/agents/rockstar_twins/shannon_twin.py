"""Digital Twin: Dr. Claude Shannon (Interface & Channel Architect)."""

from __future__ import annotations

from pathlib import Path

from cohezion.microservices.spec import BoundedContext, MicroserviceContract
from cohezion.swarm.agents.rockstar_twins.base_twin import (
    RefactoringProposal,
    RockstarScientistTwin,
)


class ClaudeShannonTwin(RockstarScientistTwin):
    """Digital Twin of Dr. Claude Shannon.

    Specializes in Information Theory, noise-free channels, Pydantic v2 event envelopes,
    and unifying fragmented API gateways.
    """

    def __init__(self) -> None:
        super().__init__(
            name="Dr. Claude Shannon",
            title="Chief Interface & Channel Architect",
            domain="Information Theory & Event Channel Optimization",
            core_maxim="The fundamental problem of communication is that of reproducing at one point either exactly or approximately a message selected at another point.",
            target_microservice="cz-gateway",
            target_modules=[
                "api",
                "cz_gateway.py",
                "gateway",
                "protocols",
                "wiring",
                "mcp",
                "contracts.py",
            ],
            hardware_target="Host CPU / Async Event Loop",
        )

    def synthesize_bounded_context(self) -> BoundedContext:
        return BoundedContext(
            name=self.target_microservice,
            lead_scientist=self.name,
            scientific_domain=self.domain,
            description="Unified ingress, protocol negotiation, and noise-free Shannon event distribution across all microservices.",
            consolidated_modules=self.target_modules,
            invariants=[
                "Zero loss of event envelopes during transit (lossless channel invariant)",
                "Strict Pydantic v2 schema validation at boundary with zero implicit coercion",
                "Entropy calculation and bit-compacted JSON serialization for all IPC messages",
            ],
        )

    def synthesize_contract(self) -> MicroserviceContract:
        return MicroserviceContract(
            context=self.synthesize_bounded_context(),
            port=13300,
            published_events=[
                "gateway.request.received",
                "gateway.route.dispatched",
                "gateway.error.quarantined",
            ],
            subscribed_events=["*"],
            max_latency_ms=15.0,
            zero_copy_ipc=True,
        )

    def develop_refactoring_proposal(self, base_dir: Path) -> RefactoringProposal:
        loc = self.count_target_loc(base_dir)
        return RefactoringProposal(
            scientist_name=self.name,
            microservice_name=self.target_microservice,
            bounded_context=self.synthesize_bounded_context(),
            analyzed_modules=self.target_modules,
            total_loc=loc,
            estimated_entropy_reduction_pct=42.5,
            refactored_interfaces=[
                "POST /v1/gateway/dispatch",
                "WS /v1/gateway/stream",
                "GET /v1/gateway/routes",
                "GET /healthz",
            ],
            subscribed_events=["*"],
            published_events=[
                "gateway.request.received",
                "gateway.route.dispatched",
            ],
            theoretical_rationale="Collapsing the sprawling api, cz_gateway.py, and wiring modules into a single Shannon-bounded gateway reduces communication entropy and eliminates circular import overhead.",
            hardware_target=self.hardware_target,
        )
