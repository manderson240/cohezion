import asyncio
import logging

from cohezion.swarm.agents.analyst import AnalystAgent
from cohezion.swarm.agents.architect_agent import ArchitectAgent
from cohezion.swarm.agents.critic import CriticAgent

from cohezion.swarm.swarm_types import Perspective, SwarmConfig


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DemocraticConsensus")


async def orchestrate_naming_debate():
    """
    Orchestrates a debate between agents to decide on a naming convention.
    """
    config = SwarmConfig()
    architect = ArchitectAgent(config=config)
    critic = CriticAgent(config=config)
    analyst = AnalystAgent(perspective=Perspective.TECHNICAL, config=config)

    topic = """
    We need to finalize the naming convention for our 71+ skills.
    Options:
    1. UPPER_CASE_PRIME.md (Proposed by Antigravity)
    2. feature_name.md (Standard lowercase)
    3. Category/SkillSubstrate.md (Hierarchical)
    4. Hybrid (PRIME only for core engine skills)

    Debate the merits and reach a democratic consensus.
    """

    print("📢 DEBATE INITIATED: Skill Naming Conventions")
    print("-" * 60)

    # Round 1: Architect's Opening
    # ArchitectAgent.process returns a str (based on usual BaseAgent behavior if not overridden)
    # But let's check architect_agent.py. It might be different.
    arch_resp = await architect.process(f"Provide your view on: {topic}")
    print(f"\n🏗️ [Architect]: {arch_resp[:300]}...")

    # Round 2: Analyst's Perspective
    analyst_vector = await analyst.process(
        f"Analyze the following proposal and topic: \nTopic: {topic}\nProposal: {arch_resp}"
    )
    analyst_content = analyst_vector.content
    print(f"\n📊 [Analyst]: {analyst_content[:300]}...")

    # Round 3: Critic's Review
    # Critic wants a list of ThoughtVectors
    critique_result = await critic.critique([analyst_vector])
    print(f"\n⚖️ [Critic Recommendation]: {critique_result.recommendation}")

    # Round 4: Final Synthesis (using Architect as the deciding body)
    final_prompt = f"""Based on the following debate, reach a democratic consensus.
    Topic: {topic}
    Architect View: {arch_resp}
    Analyst View: {analyst_content}
    Criticism: {critique_result.recommendation}

    What is the winning naming convention? Output the winner clearly."""

    final_consensus = await architect.process(final_prompt)
    print(f"\n🤝 [FINAL CONSENSUS]: {final_consensus}")

    with open("naming_consensus_result.md", "w") as f:
        f.write("# 🤝 Democratic Consensus: Skill Naming Conventions\n\n")
        f.write(f"## Architect View\n{arch_resp}\n\n")
        f.write(f"## Analyst View\n{analyst_content}\n\n")
        f.write(f"## Critic Recommendation\n{critique_result.recommendation}\n\n")
        f.write(f"## Final Winner\n{final_consensus}\n")


if __name__ == "__main__":
    asyncio.run(orchestrate_naming_debate())
