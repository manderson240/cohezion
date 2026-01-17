# Capability Matrix Analysis

## Current Skill Coverage

| Domain | Skill | Components Covered | Gap Analysis |
|--------|-------|-------------------|--------------|
| **Infrastructure** | MCP_SERVER_PRIME | mcp/ | ✅ Complete |
| **Infrastructure** | OLLAMA_MANAGEMENT_PRIME | model_manager | ✅ Complete |
| **Workflow** | SWARM_ORCHESTRATION_PRIME | swarm/ | ✅ Complete |
| **Workflow** | BMAD_WORKFLOW_PRIME | legacy/ | ✅ Complete |
| **Cognition** | CALM_ABSTRACTION_PRIME | calm/ | ✅ Complete |
| **Reliability** | SELF_HEALING_PRIME | healing/ | ✅ Complete |
| **Security** | SECURITY_GUARDRAILS_PRIME | security/ | ✅ Complete |
| **Learning** | KNOWLEDGE_MINING_PRIME | learning/ | ✅ Complete |
| **Visualization** | UNIVERSE_VISUALIZATION_PRIME | viz/, physics/ | ✅ Complete |

## Gap Analysis

### Missing Skills Identified

| Gap | Description | Recommendation |
|-----|-------------|----------------|
| **API Development** | No skill for FastAPI patterns | CREATE: API_PATTERNS_PRIME |
| **Testing** | No skill for test patterns | CREATE: TESTING_PRIME |
| **Research** | No skill for paper writing | CREATE: RESEARCH_SYNTHESIS_PRIME |
| **Database** | SurrealDB lacks dedicated skill | MERGE into UNIVERSE_VISUALIZATION |
| **Cloud Deploy** | Cloud Run patterns undocumented | CREATE: CLOUD_DEPLOYMENT_PRIME |

### Skill Consolidation Opportunities

| Current Skills | Action | Rationale |
|----------------|--------|-----------|
| SWARM + BMAD | KEEP SEPARATE | Different execution models |
| SELF_HEALING + KNOWLEDGE_MINING | KEEP SEPARATE | Different concerns |
| MCP + API | KEEP SEPARATE | MCP is protocol-specific |

### Skills to Create

1. **API_PATTERNS_PRIME** - FastAPI, Pydantic, REST patterns
2. **TESTING_PRIME** - Pytest, coverage, adversarial testing
3. **RESEARCH_SYNTHESIS_PRIME** - Paper writing, citations, methodology
4. **CLOUD_DEPLOYMENT_PRIME** - Docker, Cloud Run, deployment

## Capability-Component Matrix

```
                    │ MCP │ Swarm │ CALM │ Physics │ Viz │ Security │ Healing │ Learning │ Legacy │
────────────────────┼─────┼───────┼──────┼─────────┼─────┼──────────┼─────────┼──────────┼────────┤
Token Reduction     │  ●  │       │      │         │     │          │         │          │        │
Tool Access         │  ●  │       │      │         │     │          │         │          │        │
Multi-Perspective   │     │   ●   │      │         │     │          │         │          │    ●   │
Consensus           │     │   ●   │      │         │     │          │         │          │    ●   │
Thought Compression │     │       │  ●   │         │     │          │         │          │        │
Trajectory Predict  │     │       │  ●   │         │     │          │         │          │        │
Vector Embedding    │     │       │      │    ●    │     │          │         │          │        │
Similarity Search   │     │       │      │    ●    │     │          │         │          │        │
3D Rendering        │     │       │      │         │  ●  │          │         │          │        │
Input Validation    │     │       │      │         │     │    ●     │         │          │        │
Prompt Defense      │     │       │      │         │     │    ●     │         │          │        │
Drift Detection     │     │       │      │         │     │          │    ●    │          │        │
Auto Correction     │     │       │      │         │     │          │    ●    │          │        │
Pattern Mining      │     │       │      │         │     │          │         │     ●    │        │
Skill Generation    │     │       │      │         │     │          │         │     ●    │        │
Workflow Execution  │     │       │      │         │     │          │         │          │    ●   │
Menu Interaction    │     │       │      │         │     │          │         │          │    ●   │
```

## Recommendations

1. **CREATE** 4 new skills (API, Testing, Research, Cloud)
2. **KEEP** all existing skills as-is
3. **NO MERGES** needed - current skills are well-scoped
4. **ADD** SurrealDB examples to UNIVERSE_VISUALIZATION_PRIME
