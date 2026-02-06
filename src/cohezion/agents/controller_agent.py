"""
Controller Agent - Quadrature Nexus Pattern Implementation

LangGraph-based orchestrator that routes queries to expert domain agents.
Implements the Ignition Pack → Controller → Expert Lattice architecture.
"""

import asyncio
import logging
from datetime import datetime
from typing import Literal, TypedDict

from langgraph.graph import END, StateGraph

from cohezion.agents.architect_agent import ArchitectAgent
from cohezion.agents.biological_agent import BiologicalAgent
from cohezion.agents.handoff_agent import HandoffAgent
from cohezion.agents.quantum_agent import QuantumAgent
from cohezion.agents.universe_sim_agent import UniverseSimulationAgent

logger = logging.getLogger(__name__)

# Expert domains from Quadrature Nexus architecture
EXPERT_DOMAINS = ["architect", "engineer", "biologist", "quantum_hw", "quantum_algo"]
MODEL_NAME = "mistral:7b"  # Lightweight expert model


class IgnitionPack(TypedDict):
    """Initial package: prompt + context assets."""

    query: str
    context: dict
    urgency: Literal["low", "medium", "high"]


class AgentState(TypedDict):
    """Shared state across the graph."""

    query: str
    context: dict
    urgency: Literal["low", "medium", "high"]
    route: str
    expert_responses: dict[str, str]
    synthesis: str
    confidence: float
    created_at: str


def classify_query(state: AgentState) -> AgentState:
    """Classify query and determine routing to expert domain."""
    query = state["query"].lower()

    if "architect" in query or "design" in query:
        state["route"] = "architect"
    elif "engineer" in query or "physics" in query:
        state["route"] = "engineer"
    elif "biolog" in query or "life" in query:
        state["route"] = "biologist"
    elif "quantum" in query and "hardware" in query:
        state["route"] = "quantum_hw"
    elif "quantum" in query and "algo" in query:
        state["route"] = "quantum_algo"
    else:
        state["route"] = "all"  # Fan out to all experts

    # QSP (Quarter on a String Protocol):
    # Reel in premium cloud reasoning if query complexity is high or route is 'all'
    if state["route"] == "all" or state["urgency"] == "high":
        # In a real system, this would trigger a call to a premium model (Gemini 3 Pro)
        # to ground the local swarm's debate.
        state["context"]["qsp_active"] = True
        logger.info(
            "🧵 QSP Trigger: Reeling in premium reasoning for complex/urgent query."
        )
    else:
        state["context"]["qsp_active"] = False

    logger.info(f"Query classified → route: {state['route']}")
    return state


async def architect_expert(state: AgentState) -> AgentState:
    """Design and architecture expert."""
    logger.info("📐 Engaging ArchitectAgent...")
    agent = ArchitectAgent()
    result = await agent.process(state["query"])
    await agent.close()
    state["expert_responses"]["architect"] = str(result)
    return state


async def engineer_expert(state: AgentState) -> AgentState:
    """Physics and engineering expert."""
    logger.info("🌠 Engaging UniverseSimulationAgent (Engineer)...")
    agent = UniverseSimulationAgent()
    result = await agent.process(state["query"])
    await agent.close()
    state["expert_responses"]["engineer"] = str(result)
    return state


async def biologist_expert(state: AgentState) -> AgentState:
    """Life sciences expert."""
    logger.info("🧬 Engaging BiologicalAgent...")
    agent = BiologicalAgent()
    result = await agent.process(state["query"])
    await agent.close()
    state["expert_responses"]["biologist"] = str(result)
    return state


async def quantum_hw_expert(state: AgentState) -> AgentState:
    """Quantum hardware expert."""
    logger.info("⚛️ Engaging QuantumAgent (HW)...")
    agent = QuantumAgent()
    result = await agent.process(state["query"])
    await agent.close()
    state["expert_responses"]["quantum_hw"] = str(result)
    return state


async def quantum_algo_expert(state: AgentState) -> AgentState:
    """Quantum algorithms expert."""
    logger.info("💻 Engaging QuantumAgent (Algo)...")
    agent = QuantumAgent()
    result = await agent.process(state["query"])
    await agent.close()
    state["expert_responses"]["quantum_algo"] = str(result)
    return state


def synthesize_responses(state: AgentState) -> AgentState:
    """Combine expert responses into final synthesis."""
    responses = state["expert_responses"]

    if not responses:
        state["synthesis"] = "No expert responses available."
        state["confidence"] = 0.0
    else:
        # Simple concatenation (replace with debate/voting)
        combined = "\n".join(f"- {r}" for r in responses.values())
        state["synthesis"] = f"Synthesized from {len(responses)} expert(s):\n{combined}"
        state["confidence"] = len(responses) / len(EXPERT_DOMAINS)

    return state


async def handoff_session(state: AgentState) -> AgentState:
    """Synthesize session for long-term memory before ending."""
    logger.info("🔄 Initiating automated session handoff...")
    agent = HandoffAgent()
    # Pass necessary state info for synthesis
    snapshot = await agent.create_snapshot(
        {
            "query": state["query"],
            "expert_responses": state["expert_responses"],
            "synthesis": state["synthesis"],
            "confidence": state["confidence"],
            "created_at": state["created_at"],
        }
    )
    await agent.close()
    if "context" not in state:
        state["context"] = {}
    state["context"]["last_snapshot"] = snapshot
    return state


def route_to_experts(state: AgentState) -> str:
    """Conditional routing based on classification."""
    route = state.get("route", "all")
    if route == "all":
        return "fan_out"
    return route


def build_controller_graph() -> StateGraph:
    """Build the LangGraph orchestration graph."""

    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("classify", classify_query)
    graph.add_node("architect", architect_expert)
    graph.add_node("engineer", engineer_expert)
    graph.add_node("biologist", biologist_expert)
    graph.add_node("quantum_hw", quantum_hw_expert)
    graph.add_node("quantum_algo", quantum_algo_expert)
    graph.add_node("synthesize", synthesize_responses)
    graph.add_node("handoff", handoff_session)

    # Set entry point
    graph.set_entry_point("classify")

    # Add conditional routing
    graph.add_conditional_edges(
        "classify",
        route_to_experts,
        {
            "architect": "architect",
            "engineer": "engineer",
            "biologist": "biologist",
            "quantum_hw": "quantum_hw",
            "quantum_algo": "quantum_algo",
            "fan_out": "architect",  # Start fan-out with architect
        },
    )

    # Connect experts to synthesis
    for expert in EXPERT_DOMAINS:
        graph.add_edge(expert, "synthesize")

    # Synthesis to Handoff
    graph.add_edge("synthesize", "handoff")

    # End after handoff
    graph.add_edge("handoff", END)

    return graph.compile()


class ControllerAgent:
    """Main controller agent implementing Quadrature Nexus pattern."""

    def __init__(self):
        self.graph = build_controller_graph()
        self.history: list[AgentState] = []

    async def ignite(self, pack: IgnitionPack) -> AgentState:
        """Process an ignition pack through the controller."""
        initial_state: AgentState = {
            "query": pack["query"],
            "context": pack.get("context", {}),
            "urgency": pack.get("urgency", "medium"),
            "route": "",
            "expert_responses": {},
            "synthesis": "",
            "confidence": 0.0,
            "created_at": datetime.now().isoformat(),
        }

        # Run through graph
        result = await self.graph.ainvoke(initial_state)

        self.history.append(result)
        logger.info(
            f"Controller processed query with confidence: {result['confidence']}"
        )

        return result


# Quick test
async def main():
    controller = ControllerAgent()

    result = await controller.ignite(
        {
            "query": "Design an architecture for quantum-biological hybrid computing",
            "context": {"domain": "research"},
            "urgency": "high",
        }
    )

    print(f"Synthesis: {result['synthesis']}")
    print(f"Confidence: {result['confidence']}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
