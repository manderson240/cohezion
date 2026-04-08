# SKILL: FLUME_WIKI_OUROBOROS_PRIME - Unified Persistent Intelligence

## OVERVIEW

Integrated architecture combining three core Cohezion systems:
- **FLUME**: 256D latent thought vectors (Thinker manifold)
- **Wiki** (Karpathy): Persistent knowledge compilation
- **Ouroboros**: Recursive self-improvement

This PRIME skill documents the unified loop where execution exhaust generates embeddings,
knowledge persists in wiki, and patterns drive system evolution.

## THE UNIFIED LOOP

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         UNIFIED INTELLIGENCE ARCHITECTURE                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Execution          FLUME (256D)            Wiki                        Ouroboros
│   ┌────────┐        ┌──────────┐           ┌──────────┐              ┌──────────┐
│   │ Task   │───────→│ Embed    │──────────→ │ /exhaust/│──────────────→ │ Rewrite  │
│   │ Failure│        │ (VAE)    │            │          │                │ Analysis │
│   └────────┘        └──────────┘            └──────────┘                └────┬─────┘
│        │                 │                        │                        │
│        │                 ↓                        ↓                        │
│        │           ┌──────────┐            ┌──────────┐                  │
│        │           │ Trajectory│           │ Pattern  │←─────────────────┘
│        │           │ Capture  │            │ Cluster  │
│        │           └──────────┘            └──────────┘
│        │                 │                        │
│        │                 ↓                        ↓
│        │           ┌──────────┐            ┌──────────┐
│        │           │ Manifold │            │ Synthesis│
│        │           │ Navigate │            │ /wiki    │
│        │           └──────────┘            └──────────┘
│        │                 │                        │
│        └─────────────────┴────────────────────────┴──────────────────→ Improved System
│
└─────────────────────────────────────────────────────────────────────────────┘
```

## COMPONENTS

### 1. FLUME (256D Latent Space)
- **Encoder**: VAE mapping text → 256D thought vectors
- **Manifold**: "Thinker" space where similar concepts cluster
- **Trajectory**: Agent path through latent space during task execution
- **Bridge**: `HFEmbeddingBridge` (all-MiniLM-L6-v2 → 256D)

### 2. Wiki (Persistent Knowledge)
**3-Layer Karpathy Architecture:**
- **Raw**: Immutable execution logs, failures, captures
- **Wiki**: LLM-maintained summaries, entities, patterns
- **Schema**: AGENTS.md rules for knowledge management

**Ouroboros-Specific Paths:**
- `/wiki/ouroboros/exhaust/` - Execution failures (episodic)
- `/wiki/ouroboros/rewrites/` - System improvements (knowledge)
- `/wiki/ouroboros/patterns/` - Recurring issue clusters
- `/wiki/ouroboros/improvements/` - Validated changes

### 3. Ouroboros (Self-Improvement)
- **Consume**: Detect failures from execution exhaust
- **Analyze**: Pattern match via FLUME embeddings
- **Rewrite**: Generate system improvements
- **Validate**: TDD + consensus before deployment

## INTEGRATION POINTS

### Embedding Exhaust
```python
from cohezion.integrations.flume_wiki_bridge import FlumeOuroborosBridge

# Exhaust → 256D embedding
embedding = await bridge.encode_exhaust(exhaust)

# Store in both wiki and FLUME space
await bridge.wiki_bridge.log_exhaust(exhaust)  # Markdown
# Auto-saves: wiki/flume/embeddings/exhaust_{task_id}.vec
```

### Pattern Detection
```python
# Cluster exhaust embeddings in latent space
patterns = await bridge.analyze_exhaust_patterns(component="vault_mcp")

# Returns:
{
    "clusters": 3,          # Semantic clusters found
    "anomalies": 2,         # Outlier failures
    "mean_distance": 0.45,  # Cluster tightness
}
```

### Knowledge Distillation
```python
# Distill exhaust patterns to wiki synthesis
distilled = await bridge.distill_knowledge(
    source_category="ouroboros/exhaust",
    target_category="synthesis"
)

# Creates: /wiki/synthesis/distilled_exhaust.md
```

### Trajectory-Based Rewrite
```python
# Capture agent trajectory through wiki
trajectory = await bridge.capture_trajectory(
    agent_id="agent_1",
    path=[wiki.get_page(p) for p in navigation_path],
    task="diagnose_failure"
)

# Generate rewrite from trajectory analysis
rewrite = await bridge.generate_trajectory_rewrite(exhaust, trajectory)
```

## OPERATIONAL WORKFLOW

### 1. Failure Detection
```
Task Execution Failed
    ↓
Create ExecutionExhaust
    ↓
Embed → FLUME (256D)
    ↓
Log → Wiki (/exhaust/)
    ↓
Sync → MIRIX (episodic)
```

### 2. Pattern Analysis
```
Batch of Exhaust Embeddings
    ↓
Cluster in Latent Space
    ↓
Identify Anomalies
    ↓
Link Related Failures
    ↓
Generate Pattern Page (/patterns/)
```

### 3. System Improvement
```
Pattern Detected
    ↓
Query Wiki Lessons Learned
    ↓
Generate Rewrite Rule
    ↓
Validate (TDD + Consensus)
    ↓
Log Success (/improvements/)
    ↓
Update FLUME VAE (fine-tune)
```

### 4. Knowledge Query
```
User Query
    ↓
Embed Query → 256D
    ↓
Semantic Search (cosine similarity)
    ↓
Retrieve Wiki Pages
    ↓
Synthesize Answer
    ↓
File to /synthesis/
```

## DATA FLOW

### Exhaust → Embedding
| Field | Source | Embedding Text |
|-------|--------|----------------|
| task_id | ExecutionExhaust | "Task: {id}" |
| error_message | Exception | "Error: {msg}" |
| coherence_drop | Metrics | "Coherence: {drop}" |
| component | Diagnostics | "Component: {name}" |
| severity | Diagnostics | "Severity: {level}" |

### Wiki Page → Embedding
| Section | Processing |
|---------|-----------|
| title | Primary semantic anchor |
| content | Full text embedding |
| backlinks | Relationship edges |
| tags | Category encoding |

### Embedding Storage
```
wiki/flume/embeddings/
├── {page_title}.vec          # 256D torch.Tensor
├── exhaust_{task_id}.vec     # Failure embeddings
└── trajectory_{agent}.vec    # Path embeddings
```

## LATENT SPACE NAVIGATION

### Similarity Search
```python
# Find wiki pages semantically close to query
results = await bridge.search_by_embedding(
    query="coherence failure handling",
    limit=5
)

# Returns: [(path, similarity), ...]
# Sorted by cosine similarity in 256D space
```

### Trajectory Analysis
- **Smooth**: Consistent latent steps (validated path)
- **Discontinuities**: Jumps indicate context switches
- **Cluster Regions**: Dense areas = well-understood concepts
- **Frontier**: Sparse regions = knowledge gaps

## CONFIGURATION

### Environment
```bash
# FLUME
FLUME_Z_DIM=256
FLUME_EMBED_MODEL=all-MiniLM-L6-v2

# Wiki
WIKI_VAULT=./data/cohezion-wiki
WIKI_OUROBOROS_ENABLED=true

# Ouroboros
OUROBOROS_TARGET_COHERENCE=0.5
OUROBOROS_DIVERGENCE_PATIENCE=3
```

### Startup Sequence
```python
# 1. Initialize Wiki
wiki = ObsidianWiki(vault_path)

# 2. Initialize FLUME Bridge
bridge = FlumeOuroborosBridge(
    wiki=wiki,
    embedding_model="all-MiniLM-L6-v2"
)

# 3. Start Ouroboros
engine = OuroborosWikiEngine(
    wiki_bridge=bridge.wiki_bridge,
    flume_bridge=bridge,
    target_coherence=0.5,
)
```
## METRICS

### Coverage
- Pages embedded: % of wiki in FLUME
- Trajectory coverage: Agent paths captured
- Exhaust density: Failures per component

### Quality
- Embedding coherence: Intra-cluster similarity
- Prediction accuracy: Pattern recognition F1
- Rewrite effectiveness: TDD pass rate

### Performance
- Embed latency: ms per page
- Search latency: ms per query
- Distillation: pages/second

## DEPENDENCIES

- `cohezion/flume/` - VAE, encoders, trajectory
- `cohezion/integrations/obsidian_wiki.py` - Wiki operations
- `cohezion/integrations/wiki_mirix_bridge.py` - MIRIX sync
- `cohezion/ouroboros/wiki_integration.py` - Self-improvement
- `sentence-transformers` - Base embeddings (384D)
- `torch` - FLUME VAE operations

## SEE ALSO

- `FLUME_PRIME.md` - Core FLUME architecture
- `MEMORY_INTEGRATION_PRIME.md` - MIRIX integration
- `OuroborosWikiEngine` - Self-improvement loop
- `FlumeOuroborosBridge` - Unified interface

## VERSION

v1.0 - Unified FLUME + Wiki + Ouroboros integration

---
*Part of the Cohezion Persistent Intelligence System*
