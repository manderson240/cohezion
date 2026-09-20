"""Rockstar Scientist Digital Twin Council Coordinator."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from cohezion.microservices.bus import ShannonEvent, ShannonMicroserviceBus
from cohezion.microservices.spec import MicroserviceContract
from cohezion.swarm.agents.rockstar_twins.base_twin import (
    RefactoringProposal,
    RockstarScientistTwin,
)
from cohezion.swarm.agents.rockstar_twins.feynman_twin import RichardFeynmanTwin
from cohezion.swarm.agents.rockstar_twins.lamport_twin import LeslieLamportTwin
from cohezion.swarm.agents.rockstar_twins.mcclintock_twin import BarbaraMcClintockTwin
from cohezion.swarm.agents.rockstar_twins.prigogine_twin import IlyaPrigogineTwin
from cohezion.swarm.agents.rockstar_twins.shannon_twin import ClaudeShannonTwin
from cohezion.swarm.agents.rockstar_twins.von_neumann_twin import JohnVonNeumannTwin


@dataclass
class CouncilDeliberationResult:
    """Master deliberation output from the Council of Rockstar Scientist Digital Twins."""

    session_id: str
    twins: list[str]
    proposals: list[RefactoringProposal]
    total_monolith_loc_analyzed: int
    mean_entropy_reduction_pct: float
    contracts: list[MicroserviceContract]
    timestamp: float = field(default_factory=time.time)

    def to_markdown(self) -> str:
        """Render a comprehensive markdown blueprint of the microservice refactoring."""
        date_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(self.timestamp))
        lines = [
            "# 🏛 Council of Rockstar Scientist Digital Twins: Microservice Blueprint",
            "",
            f"**Session ID**: `{self.session_id}`  ",
            f"**Convened At**: `{date_str}`  ",
            f"**Council Members**: `{len(self.twins)}`  ",
            f"**Total Monolith LOC Analyzed**: `{self.total_monolith_loc_analyzed:,}`  ",
            f"**Projected System Entropy Reduction**: `~{self.mean_entropy_reduction_pct:.1f}%`  ",
            "",
            "## 1. Executive Allocation of Autonomous Microservices",
            "",
            "| Microservice | Rockstar Architect | Bounded Domain | Target Port | Invariants & Guarantees |",
            "|---|---|---|---|---|",
        ]
        for p in self.proposals:
            inv_str = "<br>".join(f"• {inv}" for inv in p.bounded_context.invariants)
            lines.append(
                f"| **`{p.microservice_name}`** | **{p.scientist_name}** | {p.bounded_context.scientific_domain} | `:{13300 + self.proposals.index(p)}` | {inv_str} |"
            )

        lines.extend(
            [
                "",
                "## 2. Monolithic Module Consolidation Matrix",
                "",
                "| Microservice | Monolithic Source Directories Consolidated | Analyzed LOC | Planned REST / WS Interfaces |",
                "|---|---|---|---|",
            ]
        )
        for p in self.proposals:
            mods_str = ", ".join(f"`{m}`" for m in p.analyzed_modules)
            ifaces_str = "<br>".join(f"`{i}`" for i in p.refactored_interfaces)
            lines.append(
                f"| **`{p.microservice_name}`** | {mods_str} | {p.total_loc:,} | {ifaces_str} |"
            )

        lines.extend(
            [
                "",
                "## 3. Asynchronous Event Choreography (Shannon Bus)",
                "",
                "```mermaid",
                "graph LR",
                '    Gateway["cz-gateway<br>(Shannon :13300)"] -->|"gateway.request.received"| Swarm["cz-swarm<br>(Von Neumann :13304)"]',
                '    Swarm -->|"swarm.task.scheduled"| Inference["cz-inference<br>(Feynman :13302)"]',
                '    Swarm -->|"swarm.task.scheduled"| Consensus["cz-consensus<br>(Lamport :13301)"]',
                '    Inference -->|"inference.completed"| Swarm',
                '    Inference -->|"inference.memory.pressure"| Autopoiesis["cz-autopoiesis<br>(McClintock :13303)"]',
                '    Consensus -->|"consensus.state.replicated"| Persistence["cz-persistence<br>(Prigogine :13305)"]',
                '    Autopoiesis -->|"autopoiesis.healing.completed"| Persistence',
                "```",
                "",
                "## 4. Scientist Maxim Declarations",
                "",
            ]
        )
        for p in self.proposals:
            lines.append(f"> **{p.scientist_name}** (`{p.microservice_name}`):")
            lines.append(f'> *"{p.theoretical_rationale}"*\n')

        return "\n".join(lines)


class RockstarCouncil:
    """Master orchestrator for the Council of Rockstar Scientist Digital Twins."""

    def __init__(self, bus: ShannonMicroserviceBus | None = None) -> None:
        self.bus = bus or ShannonMicroserviceBus()
        self.twins: list[RockstarScientistTwin] = [
            ClaudeShannonTwin(),
            LeslieLamportTwin(),
            RichardFeynmanTwin(),
            BarbaraMcClintockTwin(),
            JohnVonNeumannTwin(),
            IlyaPrigogineTwin(),
        ]
        # Register all contracts with the bus
        for twin in self.twins:
            self.bus.register_service_contract(twin.synthesize_contract())

    async def convene(self, codebase_dir: Path) -> CouncilDeliberationResult:
        """Convene the Council to analyze the monolith and synthesize the refactoring blueprint."""
        session_id = f"council-session-{int(time.time())}"
        proposals: list[RefactoringProposal] = []
        contracts: list[MicroserviceContract] = []

        for twin in self.twins:
            prop = twin.develop_refactoring_proposal(codebase_dir)
            contract = twin.synthesize_contract()
            proposals.append(prop)
            contracts.append(contract)

            # Publish proposal announcement event
            event = ShannonEvent(
                topic="council.proposal.submitted",
                source_service=twin.name,
                target_service="council-orchestrator",
                payload=prop.to_dict(),
            )
            await self.bus.publish(event)

        total_loc = sum(p.total_loc for p in proposals)
        mean_reduction = sum(p.estimated_entropy_reduction_pct for p in proposals) / len(proposals)

        return CouncilDeliberationResult(
            session_id=session_id,
            twins=[t.name for t in self.twins],
            proposals=proposals,
            total_monolith_loc_analyzed=total_loc,
            mean_entropy_reduction_pct=mean_reduction,
            contracts=contracts,
        )
