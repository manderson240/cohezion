"""Tests for the DemocraticDebate orchestrator (cohezion.swarm.democratic_debate)."""

from __future__ import annotations

import pytest

from cohezion.swarm.democratic_debate import (
    AGENT_PERSONAS,
    AgentRole,
    AgentVote,
    DebateRound,
    DebateSession,
    DemocraticDebate,
    VoteValue,
)


class TestAgentRole:
    def test_all_roles_defined(self):
        assert len(AgentRole) == 7
        assert AgentRole.ARCHITECT.value == "architect"
        assert AgentRole.RED_TEAM.value == "red_team"
        assert AgentRole.BLUE_TEAM.value == "blue_team"


class TestAgentPersona:
    def test_persona_system_prompt(self):
        persona = AGENT_PERSONAS[AgentRole.ARCHITECT]
        prompt = persona.system_prompt()
        assert "Aurora" in prompt
        assert "architect" in prompt
        assert "system coherence" in prompt

    def test_all_personas_have_required_fields(self):
        for role, persona in AGENT_PERSONAS.items():
            assert persona.role == role
            assert persona.name
            assert persona.model
            assert persona.style
            assert len(persona.priorities) > 0


class TestVoteValue:
    def test_vote_values(self):
        assert VoteValue.STRONGLY_AGREE.value == 2
        assert VoteValue.NEUTRAL.value == 0
        assert VoteValue.STRONGLY_DISAGREE.value == -2


class TestDebateRound:
    def test_no_votes_no_consensus(self):
        dr = DebateRound(round_number=1, topic="test", proposals={})
        consensus, score = dr.calculate_consensus()
        assert consensus is False
        assert score == 0.0

    def test_all_strongly_agree(self):
        votes = [
            AgentVote(
                role=AgentRole.ARCHITECT,
                vote=VoteValue.STRONGLY_AGREE,
                reasoning="good",
            ),
            AgentVote(role=AgentRole.BUILDER, vote=VoteValue.STRONGLY_AGREE, reasoning="great"),
        ]
        dr = DebateRound(round_number=1, topic="test", proposals={}, votes=votes)
        consensus, score = dr.calculate_consensus()
        assert consensus is True
        assert score == 1.0

    def test_all_strongly_disagree(self):
        votes = [
            AgentVote(
                role=AgentRole.ARCHITECT,
                vote=VoteValue.STRONGLY_DISAGREE,
                reasoning="bad",
            ),
            AgentVote(
                role=AgentRole.BUILDER,
                vote=VoteValue.STRONGLY_DISAGREE,
                reasoning="awful",
            ),
        ]
        dr = DebateRound(round_number=1, topic="test", proposals={}, votes=votes)
        consensus, score = dr.calculate_consensus()
        assert consensus is False
        assert score == 0.0

    def test_mixed_votes_below_threshold(self):
        votes = [
            AgentVote(role=AgentRole.ARCHITECT, vote=VoteValue.AGREE, reasoning="ok"),
            AgentVote(role=AgentRole.BUILDER, vote=VoteValue.DISAGREE, reasoning="nah"),
            AgentVote(role=AgentRole.GUARDIAN, vote=VoteValue.NEUTRAL, reasoning="meh"),
        ]
        dr = DebateRound(round_number=1, topic="test", proposals={}, votes=votes)
        consensus, score = dr.calculate_consensus()
        # total = 1 + (-1) + 0 = 0, max_possible = 6, score = (0+6)/12 = 0.5
        assert score == 0.5
        assert consensus is False

    def test_consensus_threshold_at_70(self):
        votes = [
            AgentVote(role=AgentRole.ARCHITECT, vote=VoteValue.AGREE, reasoning=""),
            AgentVote(role=AgentRole.BUILDER, vote=VoteValue.AGREE, reasoning=""),
            AgentVote(role=AgentRole.GUARDIAN, vote=VoteValue.AGREE, reasoning=""),
        ]
        dr = DebateRound(round_number=1, topic="test", proposals={}, votes=votes)
        _, score = dr.calculate_consensus()
        # total = 3, max = 6, score = (3+6)/12 = 0.75
        assert score == 0.75
        assert score >= 0.7


class TestDebateSession:
    def test_to_dict(self):
        session = DebateSession(session_id="test_123", topic="improve X")
        d = session.to_dict()
        assert d["session_id"] == "test_123"
        assert d["topic"] == "improve X"
        assert d["rounds"] == []
        assert d["final_consensus"] is None
        assert "started_at" in d


class TestDemocraticDebateAgent:
    def test_init(self):
        debate = DemocraticDebate()
        assert len(debate.personas) == 7

    @pytest.mark.asyncio
    async def test_call_agent_handles_error(self):
        debate = DemocraticDebate(ollama_host="http://nonexistent:11434")
        persona = AGENT_PERSONAS[AgentRole.ARCHITECT]
        # Should not raise, should return error string
        result = await debate._call_agent(persona, "test prompt")
        assert "error" in result.lower() or "unavailable" in result.lower()
        await debate.close()

    @pytest.mark.asyncio
    async def test_voting_parses_vote_from_response(self):
        debate = DemocraticDebate()

        # Mock _call_agent to return a response with a vote keyword
        async def mock_call(persona, prompt):
            return f"I STRONGLY_AGREE. {persona.name} thinks this is great."

        debate._call_agent = mock_call

        votes = await debate._voting_phase("test topic", {"architect": "do X"})
        assert len(votes) == 7
        for v in votes:
            assert v.vote == VoteValue.STRONGLY_AGREE

        await debate.close()

    @pytest.mark.asyncio
    async def test_voting_defaults_to_neutral(self):
        debate = DemocraticDebate()

        async def mock_call(persona, prompt):
            return "I have no opinion on this matter."

        debate._call_agent = mock_call

        votes = await debate._voting_phase("test topic", {"architect": "do X"})
        for v in votes:
            assert v.vote == VoteValue.NEUTRAL

        await debate.close()
