# ruff: noqa: E501  # long lines: SQL/URLs/docstrings — wrapping reduces readability
"""
Democratic Debate Orchestrator - Multi-agent consensus building.

Runs N rounds of debate between agents with different perspectives,
tracks votes, and reaches democratic consensus on improvements.
"""

import asyncio
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from cohezion.swarm.token_client import TokenEfficientClient
    from cohezion.swarm.token_client import TokenEfficientClient as _TC

import httpx


logger = logging.getLogger(__name__)


class AgentRole(Enum):
    ARCHITECT = "architect"  # System design, high-level vision
    BUILDER = "builder"  # Implementation, code quality
    GUARDIAN = "guardian"  # Security, reliability, ethics
    EXPLORER = "explorer"  # Innovation, novel approaches
    SYNTHESIZER = "synthesizer"  # Integration, consensus
    RED_TEAM = "red_team"  # Adversarial, entropy, novelty
    BLUE_TEAM = "blue_team"  # Defensive, stability, coherence


@dataclass
class AgentPersona:
    """Unique personality and voice for each agent."""

    role: AgentRole
    name: str
    voice: str  # TTS voice profile
    model: str  # Ollama model
    style: str  # Communication style
    priorities: list[str]
    catchphrase: str

    def system_prompt(self) -> str:
        priorities_str = ", ".join(self.priorities)
        return f"""You are {self.name}, the {self.role.value} of the Cohezion platform.

Your priorities: {priorities_str}

Your communication style: {self.style}

Your catchphrase that guides your thinking: "{self.catchphrase}"

When debating, be concise but insightful. Propose specific improvements.
Vote clearly: STRONGLY_AGREE, AGREE, NEUTRAL, DISAGREE, STRONGLY_DISAGREE.
Always explain your reasoning in 2-3 sentences."""


# Define the 5 agent personas
AGENT_PERSONAS = {
    AgentRole.ARCHITECT: AgentPersona(
        role=AgentRole.ARCHITECT,
        name="Aurora",
        voice="azelma",  # Calm, thoughtful
        model="gemma3:4b",
        style="Visionary and systematic, sees the big picture and long-term implications",
        priorities=["system coherence", "scalability", "elegant design"],
        catchphrase="The architecture must breathe with the system's evolution.",
    ),
    AgentRole.BUILDER: AgentPersona(
        role=AgentRole.BUILDER,
        name="Marcus",
        voice="marius",  # Neutral, steady
        model="gemma3:4b",
        style="Practical and detail-oriented, focused on shipping quality code",
        priorities=["code quality", "test coverage", "performance"],
        catchphrase="If it's not tested, it doesn't exist.",
    ),
    AgentRole.GUARDIAN: AgentPersona(
        role=AgentRole.GUARDIAN,
        name="Helena",
        voice="cosette",  # Expressive, passionate
        model="phi3:mini",
        style="Vigilant and principled, protects system integrity and user trust",
        priorities=["security", "reliability", "ethical AI"],
        catchphrase="Trust is earned through transparency and resilience.",
    ),
    AgentRole.EXPLORER: AgentPersona(
        role=AgentRole.EXPLORER,
        name="Phoenix",
        voice="cosette",  # Expressive for excitement
        model="gemma3:4b",
        style="Creative and bold, pushes boundaries and explores novel solutions",
        priorities=["innovation", "experimentation", "paradigm shifts"],
        catchphrase="Every constraint is an invitation to reimagine.",
    ),
    AgentRole.SYNTHESIZER: AgentPersona(
        role=AgentRole.SYNTHESIZER,
        name="Sage",
        voice="valjean",  # Deep, authoritative
        model="gemma3:4b",
        style="Integrative and diplomatic, finds common ground and builds consensus",
        priorities=["harmony", "synthesis", "collective wisdom"],
        catchphrase="In the tension of perspectives lies the path forward.",
    ),
    AgentRole.RED_TEAM: AgentPersona(
        role=AgentRole.RED_TEAM,
        name="Vortex",
        voice="azelma",
        model="qwen2.5-coder:7b",
        style="Disruptive and entropic, challenges assumptions and injects novelty",
        priorities=["entropy", "complexity", "disruption", "novelty"],
        catchphrase="Chaos is the forge where reality is tempered.",
    ),
    AgentRole.BLUE_TEAM: AgentPersona(
        role=AgentRole.BLUE_TEAM,
        name="Aegis",
        voice="marius",
        model="phi3:mini",
        style="Stabilizing and rigorous, enforces coherence and simplicity",
        priorities=["stability", "coherence", "simplicity", "resilience"],
        catchphrase="Stability is the vessel that holds the light of consciousness.",
    ),
}


class VoteValue(Enum):
    STRONGLY_AGREE = 2
    AGREE = 1
    NEUTRAL = 0
    DISAGREE = -1
    STRONGLY_DISAGREE = -2


@dataclass
class AgentVote:
    role: AgentRole
    vote: VoteValue
    reasoning: str
    proposal_modifications: list[str] = field(default_factory=list)


@dataclass
class DebateRound:
    round_number: int
    topic: str
    proposals: dict[str, str]  # role -> proposal
    votes: list[AgentVote] = field(default_factory=list)
    consensus_reached: bool = False
    winning_proposal: str | None = None

    def calculate_consensus(self) -> tuple[bool, float]:
        """Calculate if consensus was reached and the score."""
        if not self.votes:
            return False, 0.0
        total = sum(v.vote.value for v in self.votes)
        max_possible = len(self.votes) * 2
        score = (total + max_possible) / (2 * max_possible)  # Normalize to 0-1
        consensus = score >= 0.7  # 70% threshold
        return consensus, score


@dataclass
class DebateSession:
    session_id: str
    topic: str
    rounds: list[DebateRound] = field(default_factory=list)
    final_consensus: dict[str, Any] | None = None
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "topic": self.topic,
            "rounds": [asdict(r) for r in self.rounds],
            "final_consensus": self.final_consensus,
            "started_at": self.started_at,
        }


class DemocraticDebate:
    """
    Orchestrates multi-round democratic debate between agents.

    Each round:
    1. Present topic/question
    2. Each agent proposes improvements
    3. All agents vote on proposals
    4. Synthesizer integrates feedback
    5. Check for consensus
    6. If no consensus, iterate with refined proposals
    """

    def __init__(
        self,
        ollama_host: str = "http://localhost:11434",
        token_client: "TokenEfficientClient | None" = None,
    ):

        self.ollama_host = ollama_host
        self.personas = AGENT_PERSONAS
        self.client = httpx.AsyncClient(timeout=120.0)
        self._token_client: _TC | None = token_client  # type: ignore[assignment]
        self.output_dir = Path("src/cohezion/knowledge_graph/universe_nodes/debates")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def _call_agent(self, persona: AgentPersona, prompt: str) -> str:
        """Call an agent via Ollama, using TokenEfficientClient if available."""
        if self._token_client is not None:
            try:
                result = await self._token_client.generate(
                    prompt=prompt,
                    system=persona.system_prompt(),
                    model=persona.model,
                    num_predict=512,
                )
                return result[0] if isinstance(result, tuple) else result
            except Exception as e:
                logger.error(f"TokenEfficientClient call for {persona.name} failed: {e}")
                return f"[{persona.name} error: {e}]"

        # Fallback: direct httpx POST (original path)
        try:
            response = await self.client.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": persona.model,
                    "prompt": prompt,
                    "system": persona.system_prompt(),
                    "stream": False,
                    "options": {"temperature": 0.8, "num_predict": 512},
                },
            )
            if response.status_code == 200:
                return response.json().get("response", "").strip()
            return f"[{persona.name} unavailable]"
        except Exception as e:
            logger.error(f"Agent {persona.name} failed: {e}")
            return f"[{persona.name} error: {e}]"

    async def run_debate(
        self,
        topic: str,
        max_rounds: int = 10,
        min_rounds: int = 3,
    ) -> DebateSession:
        """
        Run a full democratic debate on the topic.

        Args:
            topic: The improvement topic to debate
            max_rounds: Maximum debate rounds
            min_rounds: Minimum rounds before checking consensus
        """
        import time

        session_id = f"debate_{int(time.time())}"
        session = DebateSession(session_id=session_id, topic=topic)

        logger.info(f"Starting debate session {session_id} on: {topic}")

        for round_num in range(1, max_rounds + 1):
            logger.info(f"=== Round {round_num} ===")

            # Phase 1: Gather proposals from each agent
            proposals = await self._gather_proposals(topic, round_num, session.rounds)

            # Phase 2: Voting on proposals
            votes = await self._voting_phase(topic, proposals)

            # Create round record
            debate_round = DebateRound(
                round_number=round_num,
                topic=topic,
                proposals=proposals,
                votes=votes,
            )

            # Check consensus
            consensus, score = debate_round.calculate_consensus()
            debate_round.consensus_reached = consensus

            # Find winning proposal
            if proposals:
                # Simple: use synthesizer's proposal as the integrated view
                debate_round.winning_proposal = proposals.get(
                    "synthesizer", next(iter(proposals.values()))
                )

            session.rounds.append(debate_round)

            logger.info(f"Round {round_num} consensus score: {score:.2f}")

            # Check if we can conclude
            if round_num >= min_rounds and consensus:
                logger.info(f"Consensus reached in round {round_num}!")
                break

            # Update topic for next round based on feedback
            topic = await self._refine_topic(topic, debate_round)

        # Final synthesis
        session.final_consensus = await self._final_synthesis(session)

        # Save session
        session_file = self.output_dir / f"{session_id}.json"
        with open(session_file, "w") as f:
            json.dump(session.to_dict(), f, indent=2, default=str)

        logger.info(f"Debate session saved to {session_file}")
        return session

    async def _gather_proposals(
        self,
        topic: str,
        round_num: int,
        previous_rounds: list[DebateRound],
    ) -> dict[str, str]:
        """Gather proposals from all agents in parallel."""
        context = ""
        if previous_rounds:
            last_round = previous_rounds[-1]
            context = f"\nPrevious round proposals received {len(last_round.votes)} votes.\n"
            for v in last_round.votes:
                context += f"- {v.role.value}: {v.vote.name}\n"

        prompt_template = f"""Round {round_num} of Cohezion improvement debate.

Topic: {topic}
{context}

As {"{role}"}, propose ONE specific improvement for Cohezion.
Be concise (2-3 sentences) and actionable.

Your proposal:"""

        async def get_proposal(persona: AgentPersona) -> tuple[str, str]:
            prompt = prompt_template.format(role=persona.name)
            response = await self._call_agent(persona, prompt)
            return persona.role.value, response

        tasks = [get_proposal(p) for p in self.personas.values()]
        results = await asyncio.gather(*tasks)
        return dict(results)

    async def _voting_phase(
        self,
        topic: str,
        proposals: dict[str, str],
    ) -> list[AgentVote]:
        """Each agent votes on the combined proposals."""
        proposals_str = "\n".join([f"- {role}: {prop}" for role, prop in proposals.items()])

        vote_prompt = f"""Topic: {topic}

Proposals from all agents:
{proposals_str}

As {"{role}"}, evaluate these proposals and vote on the overall direction.

Vote: [STRONGLY_AGREE/AGREE/NEUTRAL/DISAGREE/STRONGLY_DISAGREE]
Reasoning: (2-3 sentences)"""

        async def get_vote(persona: AgentPersona) -> AgentVote:
            prompt = vote_prompt.format(role=persona.name)
            response = await self._call_agent(persona, prompt)

            # Parse vote
            vote = VoteValue.NEUTRAL
            for v in VoteValue:
                if v.name in response.upper():
                    vote = v
                    break

            return AgentVote(
                role=persona.role,
                vote=vote,
                reasoning=response,
            )

        tasks = [get_vote(p) for p in self.personas.values()]
        return await asyncio.gather(*tasks)

    async def _refine_topic(self, topic: str, last_round: DebateRound) -> str:
        """Use synthesizer to refine the topic based on feedback."""
        synthesizer = self.personas[AgentRole.SYNTHESIZER]

        feedback = "\n".join(
            [f"- {v.role.value} ({v.vote.name}): {v.reasoning[:100]}..." for v in last_round.votes]
        )

        prompt = f"""Based on this round's feedback, refine the topic for the next round.

Original topic: {topic}
Feedback:
{feedback}

Refined topic (one sentence):"""

        response = await self._call_agent(synthesizer, prompt)
        return response or topic

    async def _final_synthesis(self, session: DebateSession) -> dict[str, Any]:
        """Create final consensus document."""
        synthesizer = self.personas[AgentRole.SYNTHESIZER]

        all_proposals = []
        for r in session.rounds:
            all_proposals.extend(r.proposals.values())

        prompt = f"""After {len(session.rounds)} rounds of debate on "{session.topic}",
synthesize the key improvements agreed upon by the team.

List the TOP 5 actionable improvements with highest consensus:"""

        response = await self._call_agent(synthesizer, prompt)

        # Calculate overall consensus metrics
        total_votes = sum(len(r.votes) for r in session.rounds)
        positive_votes = sum(1 for r in session.rounds for v in r.votes if v.vote.value > 0)

        return {
            "synthesis": response,
            "total_rounds": len(session.rounds),
            "total_votes": total_votes,
            "positive_vote_rate": positive_votes / max(total_votes, 1),
            "final_round_consensus": session.rounds[-1].consensus_reached
            if session.rounds
            else False,
        }

    async def close(self):
        await self.client.aclose()


async def run_improvement_debate():
    """Run a debate on improving Cohezion."""
    debate = DemocraticDebate()

    try:
        session = await debate.run_debate(
            topic="How should we improve the Cohezion platform to better support autonomous agentic development?",
            max_rounds=10,
            min_rounds=3,
        )
        return session
    finally:
        await debate.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    session = asyncio.run(run_improvement_debate())
    print(f"\nFinal consensus:\n{json.dumps(session.final_consensus, indent=2)}")
