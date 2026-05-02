"""Tests for Agentic Mitosis & Apoptosis (Story 5.6, NFR-1)."""

from __future__ import annotations

from cohezion.swarm.mitosis_apoptosis import AgentState, SwarmGovernor


class TestMitosis:
    def test_no_mitosis_below_threshold(self):
        """Agent below context threshold doesn't split."""
        gov = SwarmGovernor(mitosis_threshold=0.8)
        agent = AgentState("a1", coherence=0.5, context_usage=0.5)
        assert gov.check_mitosis(agent) is None

    def test_mitosis_above_threshold(self):
        """Agent above context threshold splits into two children."""
        gov = SwarmGovernor(mitosis_threshold=0.8)
        agent = AgentState(
            "a1",
            coherence=0.5,
            context_usage=0.9,
            task_queue=["t1", "t2", "t3", "t4"],
        )
        event = gov.check_mitosis(agent)
        assert event is not None
        assert len(event.child_ids) == 2
        assert event.tasks_redistributed == 4

    def test_parent_terminated_after_mitosis(self):
        """Parent agent is terminated after splitting."""
        gov = SwarmGovernor(mitosis_threshold=0.8)
        agent = AgentState("a1", coherence=0.5, context_usage=0.9, task_queue=["t1"])
        gov.check_mitosis(agent)
        assert agent.is_alive is False

    def test_mitosis_events_tracked(self):
        """Mitosis events are accumulated."""
        gov = SwarmGovernor(mitosis_threshold=0.8)
        agent = AgentState("a1", coherence=0.5, context_usage=0.9, task_queue=["t1"])
        gov.check_mitosis(agent)
        assert len(gov.mitosis_events) == 1


class TestApoptosis:
    def test_no_apoptosis_above_threshold(self):
        """Agent with good coherence doesn't die."""
        gov = SwarmGovernor(apoptosis_threshold=0.3, apoptosis_patience=3)
        agent = AgentState("a1", coherence=0.5, context_usage=0.3)
        assert gov.check_apoptosis(agent, []) is None

    def test_apoptosis_after_streak(self):
        """Agent with low coherence for 3 cycles dies."""
        gov = SwarmGovernor(apoptosis_threshold=0.3, apoptosis_patience=3)
        agent = AgentState("a1", coherence=0.2, context_usage=0.3, task_queue=["t1"])
        recipient = AgentState("a2", coherence=0.8, context_usage=0.3)

        # Cycle 1 & 2: no death yet
        gov.check_apoptosis(agent, [recipient])
        gov.check_apoptosis(agent, [recipient])
        assert agent.is_alive

        # Cycle 3: death
        event = gov.check_apoptosis(agent, [recipient])
        assert event is not None
        assert agent.is_alive is False

    def test_tasks_redistributed_to_highest_coherence(self):
        """Dying agent's tasks go to highest-coherence agent."""
        gov = SwarmGovernor(apoptosis_threshold=0.3, apoptosis_patience=1)
        dying = AgentState("d1", coherence=0.1, context_usage=0.3, task_queue=["t1", "t2"])
        low = AgentState("l1", coherence=0.4, context_usage=0.3)
        high = AgentState("h1", coherence=0.9, context_usage=0.3)

        event = gov.check_apoptosis(dying, [low, high])
        assert event is not None
        assert event.recipient_id == "h1"
        assert "t1" in high.task_queue

    def test_streak_resets_on_recovery(self):
        """Coherence recovery resets the low-coherence streak."""
        gov = SwarmGovernor(apoptosis_threshold=0.3, apoptosis_patience=3)
        agent = AgentState("a1", coherence=0.2, context_usage=0.3)
        recipient = AgentState("a2", coherence=0.8, context_usage=0.3)

        gov.check_apoptosis(agent, [recipient])  # streak=1
        gov.check_apoptosis(agent, [recipient])  # streak=2

        agent.coherence = 0.5  # Recovery
        gov.check_apoptosis(agent, [recipient])  # streak reset

        agent.coherence = 0.2  # Low again
        result = gov.check_apoptosis(agent, [recipient])  # streak=1
        assert result is None  # Not dead yet

    def test_no_candidates_no_apoptosis(self):
        """Apoptosis requires at least one live candidate."""
        gov = SwarmGovernor(apoptosis_threshold=0.3, apoptosis_patience=1)
        agent = AgentState("a1", coherence=0.1, context_usage=0.3, task_queue=["t1"])
        assert gov.check_apoptosis(agent, []) is None

    def test_apoptosis_events_tracked(self):
        """Apoptosis events are accumulated."""
        gov = SwarmGovernor(apoptosis_threshold=0.3, apoptosis_patience=1)
        agent = AgentState("a1", coherence=0.1, context_usage=0.3, task_queue=["t1"])
        recipient = AgentState("a2", coherence=0.8, context_usage=0.3)
        gov.check_apoptosis(agent, [recipient])
        assert len(gov.apoptosis_events) == 1
