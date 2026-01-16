# Cohezion

**Transparent, Observable AI Cognition System**

A living portfolio demonstrating capabilities for the Anthropic Research Engineer (Universes) role.

## Quick Start

```bash
# Install dependencies
uv sync

# Start SurrealDB
docker run -d --name surrealdb -p 8000:8000 surrealdb/surrealdb:latest start --user root --pass root

# Run debate workflow
uv run python -m cohezion.swarm.workflows.debate_protocol --test
```

## Architecture

```
cohezion/
├── swarm/          # SLM Swarm (Gemma/Phi/Mistral agents)
├── db/             # SurrealDB + 12D PhysicsState
├── calm/           # Continuous thought vectors
├── viz/            # Manim + HyperTools visualization
├── cloud/          # Cloud Run hybrid orchestration
├── mcp/            # MCP servers for token efficiency
└── knowledge_graph/ # Entity-relationship persistence
```

## Core Components

| Component | Purpose |
|-----------|---------|
| **DebateWorkflow** | Multi-perspective analysis with hierarchical voting |
| **PhysicsState** | 12-dimensional semantic vectors |
| **ThoughtAutoencoder** | CALM continuous thought representation |
| **MCP Servers** | Token-efficient tool access |

## MCP Servers

| Server | Tools |
|--------|-------|
| cohezion-knowledge | search_knowledge, get_skill, list_skills |
| cohezion-skills | invoke_skill, register_skill, search_skills |
| cohezion-surreal | query_nodes, store_node, search_similar |
| cohezion-swarm | run_debate, get_perspectives |

## Development

```bash
# Install pre-commit hooks
pre-commit install

# Run tests
uv run pytest tests/ -v

# Type check
uv run mypy src/cohezion
```

## System Requirements

- **RAM**: 128GB recommended
- **CPU**: Multi-core (32+ threads optimal)
- **Ollama Models**: gemma3:4b, phi3:mini, mistral:7b

## Citations

- [Model Context Protocol](https://modelcontextprotocol.io)
- [CALM](https://arxiv.org/abs/CALM) - Continuous Autoregressive Language Models
- [ReAct](https://arxiv.org/abs/2210.03629) - Reasoning + Acting
- [Reflexion](https://arxiv.org/abs/2303.11366) - Self-reflection

## License

Apache 2.0
