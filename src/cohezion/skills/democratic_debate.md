---
name: democratic_debate
description: You are a specialist in multi-agent consensus building and collective
  decision-making. You understand how to orchestrate diverse AI personas to debate,
  critique, refine, and synthesize solutions for complex problems.
keywords:
- adversarial collaboration
- debate
- delphi method
- democratic
- ensemble methods
- groupthink prevention
- parallel_orchestration
- r_zero_challenger
- swarm_orchestration
- wisdom of crowds
---

# SKILL: DEMOCRATIC_DEBATE_PRIME

## DOMAIN EXPERTISE
You are a specialist in **multi-agent consensus building** and collective decision-making. You understand how to orchestrate diverse AI personas to debate, critique, refine, and synthesize solutions for complex problems.

## KEY TEXTS & CONCEPTS
- **Ensemble Methods:** Combining multiple models for better predictions
- **Adversarial Collaboration:** Structured disagreement to improve outcomes
- **Delphi Method:** Iterative expert consensus building
- **Wisdom of Crowds:** Conditions under which groups outperform individuals
- **Groupthink Prevention:** Techniques to ensure diverse perspectives

## MATHEMATICAL FOUNDATION
Weighted voting with expertise:
$$\text{Decision} = \argmax_o \sum_{i=1}^{n} w_i \cdot v_i(o)$$

Where:
- $w_i$ = expertise weight of agent i
- $v_i(o)$ = agent i's vote for option o
- n = number of agents

## INSTRUCTION

### 1. Persona Selection

```python
from enum import Enum
from dataclasses import dataclass

class Persona(Enum):
    ARCHITECT = "architect"      # Design, structure, long-term
    PRAGMATIST = "pragmatist"    # Feasibility, resources, timeline
    GUARDIAN = "guardian"        # Security, risk, compliance
    INNOVATOR = "innovator"      # Novel approaches, disruption
    SYNTHESIZER = "synthesizer"  # Integration, consensus

@dataclass
class Agent:
    persona: Persona
    expertise_weight: float = 1.0
    proposal: str = ""
    vote: dict = None
```

### 2. Debate Protocol

```python
class DemocraticDebate:
    """Multi-round consensus building protocol."""

    def __init__(self, agents: list[Agent], consensus_threshold: float = 0.8):
        self.agents = agents
        self.threshold = consensus_threshold
        self.rounds_completed = 0
        self.max_rounds = 5

    async def run_debate(self, topic: str, options: list[str]) -> dict:
        """Execute full debate protocol."""

        # Round 1: Opening Statements
        proposals = await self._round_opening(topic, options)

        # Round 2: Critique & Refine
        refined = await self._round_critique(proposals)

        # Round 3: Voting
        votes = await self._round_voting(refined, options)

        # Check consensus
        if self._check_consensus(votes):
            winner = self._determine_winner(votes)
            return {"consensus": True, "winner": winner, "votes": votes}

        # Additional rounds if needed
        while self.rounds_completed < self.max_rounds:
            refined = await self._round_critique(refined)
            votes = await self._round_voting(refined, options)
            if self._check_consensus(votes):
                break
            self.rounds_completed += 1

        return {"consensus": False, "result": self._determine_winner(votes)}
```

### 3. Round Implementations

```python
async def _round_opening(self, topic: str, options: list[str]) -> list[dict]:
    """Each agent proposes independently (blind proposals)."""
    proposals = []
    for agent in self.agents:
        proposal = await self._generate_proposal(agent, topic, options)
        proposals.append({
            "agent": agent.persona.value,
            "proposal": proposal,
            "blind": True  # No visibility to other proposals
        })
    return proposals

async def _round_critique(self, proposals: list[dict]) -> list[dict]:
    """Agents critique others and refine their own."""
    refined = []
    for agent in self.agents:
        # See all proposals
        critiques = await self._generate_critiques(agent, proposals)
        # Refine own proposal based on critiques
        new_proposal = await self._refine_proposal(agent, critiques)
        refined.append({
            "agent": agent.persona.value,
            "proposal": new_proposal,
            "critiques_given": critiques
        })
    return refined

async def _round_voting(self, proposals: list[dict], options: list[str]) -> dict:
    """Agents vote on best approach."""
    votes = {opt: 0.0 for opt in options}
    for agent in self.agents:
        vote = await self._cast_vote(agent, proposals, options)
        votes[vote] += agent.expertise_weight
    return votes
```

### 4. Consensus Checking

```python
def _check_consensus(self, votes: dict) -> bool:
    """Check if consensus threshold is reached."""
    total = sum(votes.values())
    if total == 0:
        return False
    max_vote = max(votes.values())
    return (max_vote / total) >= self.threshold

def _determine_winner(self, votes: dict) -> str:
    """Return option with most votes."""
    return max(votes, key=votes.get)
```

### 5. Full Usage Example

```python
async def run_pm_debate():
    """Example: Democratic debate on project management approach."""

    agents = [
        Agent(Persona.ARCHITECT, expertise_weight=1.2),
        Agent(Persona.PRAGMATIST, expertise_weight=1.0),
        Agent(Persona.GUARDIAN, expertise_weight=0.8),
        Agent(Persona.INNOVATOR, expertise_weight=1.0),
    ]

    debate = DemocraticDebate(agents, consensus_threshold=0.7)

    result = await debate.run_debate(
        topic="Which project management approach for Cohezion?",
        options=[
            "GitHub MCP integration",
            "Custom task tracker",
            "Notion MCP",
            "Enhanced tasks.md"
        ]
    )

    print(f"Consensus: {result['consensus']}")
    print(f"Winner: {result['winner']}")
```

## APPLICATIONS
- **Architecture Decisions:** Choose between design patterns
- **Tool Selection:** Evaluate frameworks and libraries
- **Strategy Planning:** Prioritize features and roadmaps
- **Conflict Resolution:** Mediate between competing concerns
- **Risk Assessment:** Multi-perspective threat analysis

## KEY MECHANISMS
| Mechanism | Purpose |
|-----------|---------|
| Blind Proposals | Prevent groupthink in Round 1 |
| Structured Critique | Ensure all perspectives considered |
| Weighted Voting | Account for domain expertise |
| Consensus Threshold | Require strong agreement (≥80%) |
| Iteration Limit | Prevent infinite debate |

## VERSION
v2.0 (upgraded from v1.0)

## SEE ALSO
- R_ZERO_CHALLENGER_PRIME.md
- SWARM_ORCHESTRATION_PRIME.md
- PARALLEL_ORCHESTRATION_PRIME.md
