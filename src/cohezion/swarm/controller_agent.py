"""
Controller Agent - Quadrature Nexus Pattern Implementation

LangGraph-based orchestrator that routes queries to expert domain agents.
Implements the Ignition Pack → Controller → Expert Lattice architecture.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Literal, TypedDict

import httpx
from langgraph.graph import END, StateGraph

from cohezion.swarm.agents.handoff_agent import HandoffAgent

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
    """Route query to appropriate expert(s) based on content."""
    query = state["query"].lower()

    # Simple keyword-based routing (replace with LLM classification)
    if any(kw in query for kw in ["design", "architecture", "structure"]):
        state["route"] = "architect"
    elif any(kw in query for kw in ["physics", "force", "energy", "equation"]):
        state["route"] = "engineer"
    elif any(kw in query for kw in ["biology", "life", "evolution", "organism"]):
        state["route"] = "biologist"
    elif any(kw in query for kw in ["quantum", "qubit", "hardware", "chip"]):
        state["route"] = "quantum_hw"
    elif any(kw in query for kw in ["algorithm", "compute", "circuit", "gate"]):
        state["route"] = "quantum_algo"
    else:
        state["route"] = "all"  # Fan out to all experts

    logger.info(f"Query classified → route: {state['route']}")
    return state


async def call_expert(domain: str, query: str, context: dict) -> str:
    """Call a single domain expert via Ollama."""
    prompt = f"""You are an expert {domain.upper()} representing one node in the Quadrature Nexus.

CONTEXT: {json.dumps(context)}
QUERY: {query}

Provide a specialized analysis from your domain perspective.
Focus on emergent properties, risks, and novel connections.
Keep it concise (2-3 paragraphs).
"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "http://localhost:11434/api/generate",
                json={"model": MODEL_NAME, "prompt": prompt, "stream": False},
            )
            if resp.status_code == 200:
                return resp.json().get(
                    "response", f"[{domain.upper()}] Error: Empty response"
                )
            else:
                return f"[{domain.upper()}] Error: {resp.status_code}"
    except Exception as e:
        logger.error(f"Expert {domain} failed: {e}")
        return f"[{domain.upper()}] System Failure: {e}"


async def architect_expert(state: AgentState) -> AgentState:
    """Design and architecture expert."""
    result = await call_expert("architect", state["query"], state["context"])
    state["expert_responses"]["architect"] = result
    return state


async def engineer_expert(state: AgentState) -> AgentState:
    """Physics and engineering expert."""
    result = await call_expert("engineer", state["query"], state["context"])
    state["expert_responses"]["engineer"] = result
    return state


async def biologist_expert(state: AgentState) -> AgentState:
    """Life sciences expert."""
    result = await call_expert("biologist", state["query"], state["context"])
    state["expert_responses"]["biologist"] = result
    return state


async def quantum_hw_expert(state: AgentState) -> AgentState:
    """Quantum hardware expert."""
    result = await call_expert("quantum_hw", state["query"], state["context"])
    state["expert_responses"]["quantum_hw"] = result
    return state


async def quantum_algo_expert(state: AgentState) -> AgentState:
    """Quantum algorithms expert."""
    result = await call_expert("quantum_algo", state["query"], state["context"])
    state["expert_responses"]["quantum_algo"] = result
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

    # Synthesis to Handoff (disabled for speed)
    # graph.add_edge("synthesize", "handoff")
    graph.add_edge("synthesize", END)

    # End after handoff
    # graph.add_edge("handoff", END)

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
