"""Unit tests for the Council of Rockstar Scientist Digital Twins and Microservices Framework."""

from __future__ import annotations

from pathlib import Path

import pytest

from cohezion.microservices.bus import ShannonEvent, ShannonMicroserviceBus
from cohezion.swarm.agents.rockstar_twins.feynman_twin import RichardFeynmanTwin
from cohezion.swarm.agents.rockstar_twins.lamport_twin import LeslieLamportTwin
from cohezion.swarm.agents.rockstar_twins.mcclintock_twin import BarbaraMcClintockTwin
from cohezion.swarm.agents.rockstar_twins.prigogine_twin import IlyaPrigogineTwin
from cohezion.swarm.agents.rockstar_twins.shannon_twin import ClaudeShannonTwin
from cohezion.swarm.agents.rockstar_twins.twin_council import RockstarCouncil
from cohezion.swarm.agents.rockstar_twins.von_neumann_twin import JohnVonNeumannTwin


class TestRockstarScientistTwins:
    def test_shannon_twin_contract(self) -> None:
        twin = ClaudeShannonTwin()
        assert twin.name == "Dr. Claude Shannon"
        assert twin.target_microservice == "cz-gateway"
        contract = twin.synthesize_contract()
        assert contract.port == 13300
        assert "gateway.request.received" in contract.published_events

    def test_lamport_twin_invariants(self) -> None:
        twin = LeslieLamportTwin()
        assert twin.name == "Dr. Leslie Lamport"
        assert twin.target_microservice == "cz-consensus"
        context = twin.synthesize_bounded_context()
        assert len(context.invariants) >= 3

    def test_feynman_twin_silicon_acceleration(self) -> None:
        twin = RichardFeynmanTwin()
        assert twin.name == "Dr. Richard Feynman"
        assert twin.target_microservice == "cz-inference"
        assert "AMD Strix Halo APU" in twin.hardware_target

    def test_mcclintock_twin_autopoiesis(self) -> None:
        twin = BarbaraMcClintockTwin()
        assert twin.name == "Dr. Barbara McClintock"
        assert twin.target_microservice == "cz-autopoiesis"
        contract = twin.synthesize_contract()
        assert contract.port == 13303

    def test_von_neumann_twin_swarm_automata(self) -> None:
        twin = JohnVonNeumannTwin()
        assert twin.name == "Dr. John von Neumann"
        assert twin.target_microservice == "cz-swarm"
        contract = twin.synthesize_contract()
        assert contract.port == 13304

    def test_prigogine_twin_dissipative_memory(self) -> None:
        twin = IlyaPrigogineTwin()
        assert twin.name == "Dr. Ilya Prigogine"
        assert twin.target_microservice == "cz-persistence"
        contract = twin.synthesize_contract()
        assert contract.port == 13305


class TestShannonMicroserviceBus:
    @pytest.mark.asyncio
    async def test_event_publishing_and_entropy(self) -> None:
        bus = ShannonMicroserviceBus()
        received_events: list[ShannonEvent] = []

        async def handler(event: ShannonEvent) -> None:
            received_events.append(event)

        bus.subscribe("test.topic", handler)

        event = ShannonEvent(
            topic="test.topic",
            source_service="cz-gateway",
            target_service="cz-swarm",
            payload={"action": "dispatch_agent", "priority": "high", "cluster_id": 42},
        )
        count = await bus.publish(event)

        assert count == 1
        assert len(received_events) == 1
        assert received_events[0].lamport_clock == 1
        assert received_events[0].entropy_bits > 0.0
        assert bus.total_messages == 1


class TestRockstarCouncil:
    @pytest.mark.asyncio
    async def test_council_deliberation(self, tmp_path: Path) -> None:
        # Create a mock miniature monolithic layout
        (tmp_path / "api").mkdir()
        (tmp_path / "api" / "routes.py").write_text("def route(): pass\n")
        (tmp_path / "governance").mkdir()
        (tmp_path / "governance" / "rules.py").write_text("class Rule: pass\n")

        council = RockstarCouncil()
        deliberation = await council.convene(tmp_path)

        assert len(deliberation.twins) == 6
        assert len(deliberation.proposals) == 6
        assert deliberation.total_monolith_loc_analyzed >= 2
        assert deliberation.mean_entropy_reduction_pct > 30.0

        md = deliberation.to_markdown()
        assert "# 🏛 Council of Rockstar Scientist Digital Twins" in md
        assert "cz-gateway" in md
        assert "cz-consensus" in md
        assert "cz-inference" in md
        assert "cz-autopoiesis" in md
        assert "cz-swarm" in md
        assert "cz-persistence" in md
