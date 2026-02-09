# SKILL: CONTROLLER_AGENT_PRIME

## DOMAIN EXPERTISE

Expert in LangGraph-based multi-agent orchestration implementing the Quadrature Nexus pattern. Specializes in routing queries to domain experts through an "Expert Domain Lattice" using stateful graph-based workflows with state persistence and human-in-the-loop checkpoints.

## KEY TEXTS & CONCEPTS

- **Ignition Pack**: Bundle of query + context assets as initialization payload
- **Controller Agent**: Central orchestrator using LangGraph for stateful routing
- **Expert Domain Lattice**: Diamond-shaped router distributing to 5 expert streams
- **LangGraph + CrewAI**: LangGraph as skeleton, CrewAI for role-based teams
- **State Persistence**: SurrealDB for cross-session memory
- **Conditional Routing**: Query classification → expert selection → synthesis

## INSTRUCTION

### 1. Implement Ignition Pack
```python
class IgnitionPack(TypedDict):
    query: str
    context: dict
    urgency: Literal["low", "medium", "high"]
```

### 2. Create Controller with LangGraph
```python
from langgraph.graph import StateGraph, END

graph = StateGraph(AgentState)
graph.add_node("classify", classify_query)
graph.add_node("architect", architect_expert)
graph.add_node("engineer", engineer_expert)
# ... add all domain experts
graph.add_node("synthesize", synthesize_responses)
graph.set_entry_point("classify")
graph.add_conditional_edges("classify", route_to_experts, {...})
```

### 3. Domain Expert Functions
Each expert is a synchronous function that processes state:
```python
def architect_expert(state: AgentState) -> AgentState:
    result = call_ollama("gemma3", state["query"])
    state["expert_responses"]["architect"] = result
    return state
```

### 4. Synthesis Layer
Combine expert responses with confidence weighting:
```python
def synthesize_responses(state: AgentState) -> AgentState:
    responses = state["expert_responses"]
    state["synthesis"] = combine_with_voting(responses)
    state["confidence"] = len(responses) / total_experts
    return state
```

## VERSION
v1.0

## SEE ALSO
- SWARM_ORCHESTRATION_PRIME.md - Debate protocols
- DEMOCRATIC_DEBATE_PRIME.md - Voting mechanisms
- LANGGRAPH_PATTERNS.md (future) - Advanced graph patterns
