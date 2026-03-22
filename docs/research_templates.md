# Research Workflow Templates for Open-Notebook

## Template 1: Multi-Perspective Analysis

### Purpose
Use the SLM swarm to analyze a topic from technical, ethical, and historical perspectives.

### API Call
```bash
curl -X POST http://localhost:8080/swarm/debate \
  -H "Content-Type: application/json" \
  -d '{"query": "Analyze [TOPIC] and its implications"}'
```

### Expected Output
- Synthesized analysis with 3 perspectives
- Confidence score (0-100%)
- Contradiction resolution

---

## Template 2: Knowledge Discovery

### Purpose
Search the Cohezion knowledge base for relevant skills and documents.

### API Call
```bash
curl -X POST http://localhost:8080/knowledge/search \
  -H "Content-Type: application/json" \
  -d '{"query": "[SEARCH_TERM]", "limit": 10}'
```

---

## Template 3: Skill Invocation

### Purpose
Load and apply a specific skill to a task.

### Steps
1. List skills: `GET /knowledge/skills`
2. Get skill: `GET /knowledge/skills/{name}`
3. Apply guidance from skill content

---

## Template 4: Physics-Based Visualization

### Purpose
Store and visualize semantic data in 12D physics space.

### API Call (via SurrealDB MCP)
```python
from cohezion.mcp.surreal_server import get_server
server = get_server()

# Store node with physics state
await server.store_node(
    content="My research finding",
    node_type="research",
    physics={"sentiment": 0.8, "novelty": 0.9}
)
```

---

## Template 5: Continuous Thought Trajectory

### Purpose
Predict the evolution of an idea using CALM.

### API Call
```python
from cohezion.calm import TrajectoryPredictor, ThoughtAutoencoder

# Encode text to thought vector
autoencoder = ThoughtAutoencoder()
z = autoencoder.encode("Initial idea")

# Predict trajectory
predictor = TrajectoryPredictor()
trajectory = predictor.predict_sequence(z, steps=10)
```

---

## Integration with Open-Notebook

1. Create new notebook in Open-Notebook UI
2. Add source document
3. Use Cohezion API endpoints for analysis
4. Store results back in notebook

### Shared Database
Both Open-Notebook and Cohezion use SurrealDB, enabling:
- Cross-referencing research notes
- Physics-based organization
- Persistent knowledge graphs
