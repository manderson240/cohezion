# Unified Memory Architecture: Karpathy ulogme + MIRIX + Obsidian + SurrealDB + Cohezion MCP

## Overview

Integration of five systems into a unified personal memory and productivity stack:

| System | Role | Data Type |
|--------|------|-----------|
| **Karpathy ulogme** | Time/activity tracking | Temporal logs, window titles, keystrokes |
| **MIRIX** | Multi-agent memory layer | Core, Episodic, Semantic, Procedural, Resource, Knowledge Vault |
| **Obsidian Vault** | Knowledge base (local-first) | Markdown notes, daily notes, projects |
| **SurrealDB** | Graph + Time-series database | 12D physics state, entity relationships |
| **Cohezion MCP** | Orchestration layer | Skills, agents, APIs |

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        OBSIDIAN VAULT (Local)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Daily Notes  │  │  Projects    │  │  Concepts    │  │  Research    │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
└───────┬────────────────┬─────────────────┬────────────────┬───────────────┘
        │                │                 │                │
        ▼                ▼                 ▼                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      COHEZION MCP SERVERS                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Vault MCP    │  │ Surreal MCP  │  │ Skills MCP   │  │ Knowledge    │  │
│  │ (Obsidian)   │  │ (Graph DB)   │  │ (PRIME docs) │  │ (RAG/Search) │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘  └──────────────┘  │
└───────┬────────────────┬──────────────────────────────────────────────────┘
        │                │
        ▼                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        MIRIX (Local Memory)                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │   Core   │ │ Episodic │ │ Semantic │ │Resource  │ │Knowledge │       │
│  │  Memory  │ │  Memory  │ │  Graph   │ │  Agent   │ │  Vault   │       │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘       │
└──────┬──────────────┬────────────┼────────────┼────────────┬────────────┘
       │              │            │            │            │
       ▼              ▼            ▼            ▼            ▼
┌───────────────────────────────────────────────────────────────────────┐
│                      SURREALDB (Universe State)                          │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  12D Physics State + Time-series + Graph (Nodes/Edges)           │  │
│  │  - activity:ulogme (temporal events)                             │  │
│  │  - entity:mirix (memory entries)                                 │  │
│  │  - note:obsidian (vault documents)                               │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────┘
```

## Integration Points

### 1. ulogme → SurrealDB (Time Tracking Pipeline)

**Data Flow:**
```python
# ulogme captures window titles + keystrokes every 2s
# → SurrealDB stores as temporal nodes with 12D physics coordinates

# Schema: activity:ulogme
{
    "id": "activity:ulogme:2024-01-15T10:30:00Z",
    "type": "focus_session",
    "window_title": "benchmark_research.py - cohezion",
    "keystrokes": 450,
    "duration_sec": 120,
    "app_category": "coding",  # classified
    "physics": {
        "coherence": 0.92,     # focus score from keystroke velocity
        "energy": 0.85,          # derived from activity density
        "time": 1705314600
    }
}
```

**Implementation:**
```python
# src/cohezion/integrations/ulogme_bridge.py
class UlogmeBridge:
    """Bridge ulogme time tracking to SurrealDB."""
    
    async def sync_activity(self, log_path: Path) -> list[str]:
        """Parse ulogme logs and store in SurrealDB."""
        # Parse ulogme JSON/CSV
        # Create UniverseNode with physics state
        # Link to Obsidian daily note via date
```

### 2. MIRIX ↔ SurrealDB (Memory Sync)

**Bidirectional Sync:**
```python
# MIRIX memory agents → SurrealDB graph nodes
# SurrealDB queries → MIRIX retrieval for Cohezion agents

# Schema: entity:mirix
{
    "id": "entity:mirix:conv_123",
    "memory_type": "episodic",  # core|episodic|semantic|procedural|resource|knowledge
    "content": "Discussion about autoresearch optimization...",
    "embedding": [0.1, -0.2, ...],  # 768-dim from Gemini embedding
    "timestamp": "2024-01-15T10:30:00Z",
    "source": "obsidian://daily/2024-01-15",
    "entities": ["autoresearch", "benchmark"],  # extracted entities
    "physics": {
        "salience": 0.85,  # importance score
        "recency": 0.90    # temporal decay factor
    }
}
```

### 3. Obsidian Vault → MCP Bridge

**Vault MCP Server Extensions:**
```python
# src/cohezion/mcp/servers/vault/obsidian_bridge.py

class ObsidianBridge:
    """Bidirectional sync between Obsidian vault and Cohezion."""
    
    async def create_daily_note(self, date: str, content: str) -> str:
        """Create Obsidian daily note from MIRIX summary."""
        
    async def sync_to_surreal(self, vault_path: Path) -> int:
        """Index all vault markdown to SurrealDB with embeddings."""
        
    async def query_vault(self, query: str) -> list[dict]:
        """Semantic search over vault via SurrealDB vectors."""
```

### 4. Cohezion Skills Integration

**New PRIME Skill: `MEMORY_INTEGRATION_PRIME.md`:**

```markdown
# SKILL: MEMORY_INTEGRATION_PRIME

## Capabilities
- Query unified memory across ulogme + MIRIX + Obsidian
- Correlate time spent (ulogme) with knowledge gain (Obsidian)
- Auto-generate daily notes from MIRIX episodic memory
- Cross-reference: "What was I working on 3 days ago?"

## Tools
- `memory.query`: Search across all memory sources
- `memory.timeline`: Visualize activity + notes + conversations
- `memory.correlate`: Find patterns between time and output
- `memory.summarize`: Generate Obsidian notes from MIRIX data
```

## MCP Server Extensions

### New: `activity_mcp.py`

```python
# src/cohezion/mcp/activity_mcp.py
"""MCP server for unified activity/memory queries."""

class ActivityMCP:
    """Query across ulogme, MIRIX, and Obsidian."""
    
    async def query_unified_memory(
        self,
        query: str,
        time_range: str = "7d",
        sources: list[str] = ["ulogme", "mirix", "obsidian"]
    ) -> dict:
        """
        Query unified memory graph.
        
        Example: "What did I work on Tuesday?"
        → Queries ulogme for Tuesday activity
        → Queries MIRIX for Tuesday conversations  
        → Queries Obsidian for Tuesday notes
        → Returns unified timeline
        """
        
    async def correlate_productivity(
        self,
        metric: str = "focus_score",
        correlate_with: str = "note_creation"
    ) -> dict:
        """
        Correlate ulogme metrics with knowledge work output.
        
        Example: Does high keystroke activity correlate with 
        more Obsidian notes created?
        """
```

### New: `mirix_bridge.py`

```python
# src/cohezion/integrations/mirix_bridge.py
"""Bridge to MIRIX multi-agent memory system."""

from mirix import MirixClient

class MirixBridge:
    """Integrate MIRIX memory into Cohezion."""
    
    def __init__(self):
        self.client = MirixClient(
            api_key=os.getenv("MIRIX_API_KEY"),
            base_url="http://localhost:8531"
        )
        
    async def sync_episodic_to_surreal(self) -> int:
        """Sync MIRIX episodic memories to SurrealDB graph."""
        memories = self.client.retrieve_with_conversation(
            user_id="cohezion-user",
            messages=[{"role": "user", "content": [{"type": "text", "text": "Last 7 days"}]}],
            limit=100
        )
        for mem in memories:
            await self._store_in_surreal(mem, type="episodic")
            
    async def query_cross_memory(self, query: str) -> dict:
        """Query both MIRIX and SurrealDB for comprehensive results."""
        # MIRIX for semantic search
        mirix_results = self.client.retrieve_with_conversation(
            user_id="cohezion-user",
            messages=[{"role": "user", "content": [{"type": "text", "text": query}]}],
            limit=5
        )
        # SurrealDB for time-series/physics
        surreal_results = await surreal.query_similar(query)
        return {"mirix": mirix_results, "surreal": surreal_results}
```

## Data Schemas

### SurrealDB Unified Schema

```sql
-- activity:ulogme (from Karpathy ulogme)
DEFINE TABLE activity TYPE NORMAL;
DEFINE FIELD window_title ON activity TYPE string;
DEFINE FIELD keystrokes ON activity TYPE int;
DEFINE FIELD duration ON activity TYPE duration;
DEFINE FIELD created ON activity TYPE datetime;
DEFINE FIELD physics.coherence ON activity TYPE float;
DEFINE FIELD physics.energy ON activity TYPE float;

-- entity:mirix (from MIRIX memory agents)
DEFINE TABLE entity TYPE NORMAL;
DEFINE FIELD memory_type ON entity TYPE string 
    ASSERT $value IN ['core','episodic','semantic','procedural','resource','knowledge'];
DEFINE FIELD content ON entity TYPE string;
DEFINE FIELD embedding ON entity TYPE array<float>;
DEFINE FIELD source ON entity TYPE string; -- obsidian:// link
DEFINE FIELD physics.salience ON entity TYPE float;
DEFINE FIELD physics.recency ON entity TYPE float;

-- note:obsidian (from vault)
DEFINE TABLE note TYPE NORMAL;
DEFINE FIELD path ON note TYPE string;
DEFINE FIELD title ON note TYPE string;
DEFINE FIELD content ON note TYPE string;
DEFINE FIELD tags ON note TYPE array<string>;
DEFINE FIELD backlinks ON note TYPE array<record<note>>;

-- Relations
DEFINE TABLE relates_to TYPE RELATION FROM entity TO entity;
DEFINE TABLE happened_during TYPE RELATION FROM activity TO entity;
DEFINE TABLE referenced_in TYPE RELATION FROM entity TO note;
```

## Setup Instructions

### 1. Install MIRIX
```bash
# Clone and run MIRIX
cd /home/mike-anderson/vaults/mirix
docker compose up -d --pull always
# Dashboard: http://localhost:5173
# API: http://localhost:8531
```

### 2. Configure ulogme
```bash
# Install ulogme (Karpathy)
git clone https://github.com/karpathy/ulogme.git
cd ulogme
python setup.py install

# Configure to write to SurrealDB
export ULOGME_SURREAL_URL="ws://localhost:8000/rpc"
export ULOGME_NAMESPACE="cohezion"
export ULOGME_DATABASE="activity"
```

### 3. Enable in Cohezion
```bash
# Add to .env
MIRIX_API_KEY="your-key"
MIRIX_URL="http://localhost:8531"
OBSIDIAN_VAULT="/home/mike-anderson/vaults/cohezion-vault"
ULOGME_ENABLED=true
```

## Use Cases

### Daily Note Auto-Generation
```python
# Cohezion agent creates daily notes from activity
async def generate_daily_note(date: str):
    # Get ulogme activity for the day
    activity = await activity_mcp.query_day(date)
    
    # Get MIRIX conversations from that day
    conversations = await mirix_bridge.retrieve_day(date)
    
    # Summarize with LLM
    summary = await llm.summarize(activity + conversations)
    
    # Create Obsidian note
    await vault_bridge.create_daily_note(date, summary)
```

### Focus Score Tracking
```python
# Correlate coding time (ulogme) with research progress (obsidian)
async def analyze_productivity(week: str):
    hours_coding = await activity_mcp.get_category_hours(week, "coding")
    notes_created = await vault_bridge.count_notes(week)
    mirix_memories = await mirix_bridge.count_memories(week)
    
    return {
        "focus_hours": hours_coding,
        "knowledge_gain": notes_created,
        "context_retention": mirix_memories
    }
```

### Context Restoration
```python
# Ask: "What was I thinking about before I took a break?"
async def restore_context(before_time: datetime):
    # Query last 30 min of activity
    activity = await activity_mcp.get_recent(before_time, minutes=30)
    
    # Get related MIRIX memories
    mirix_context = await mirix_bridge.get_near_time(before_time)
    
    # Get relevant Obsidian notes
    notes = await vault_bridge.query_by_time(before_time)
    
    return {"activity": activity, "memories": mirix_context, "notes": notes}
```

## File Structure

```
cohezion/
├── src/cohezion/
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── ulogme_bridge.py      # Karpathy ulogme → SurrealDB
│   │   ├── mirix_bridge.py       # MIRIX ↔ SurrealDB
│   │   └── obsidian_bridge.py    # Vault ↔ SurrealDB
│   ├── mcp/
│   │   ├── servers/
│   │   │   └── vault/
│   │   │       ├── __init__.py
│   │   │       ├── server.py
│   │   │       └── obsidian_bridge.py  # Vault sync
│   │   ├── activity_mcp.py       # Unified query interface
│   │   └── surreal_server.py     # Existing SurrealDB MCP
│   └── skills/
│       └── MEMORY_INTEGRATION_PRIME.md
│
├── docs/integrations/
│   └── UNIFIED_MEMORY_ARCHITECTURE.md  # This doc
│
└── scripts/
    └── setup_unified_memory.py   # One-command setup
```

## Next Steps

1. **Phase 1**: Implement ulogme → SurrealDB bridge (activity tracking)
2. **Phase 2**: Implement MIRIX ↔ SurrealDB sync (memory layer)
3. **Phase 3**: Create Activity MCP server (unified queries)
4. **Phase 4**: Auto-generate Obsidian notes from activity data
5. **Phase 5**: Productivity correlation analysis

## References

- [Karpathy ulogme](https://cs.stanford.edu/people/karpathy/ulogme/)
- [MIRIX](https://github.com/Mirix-AI/MIRIX)
- [Cohezion SurrealDB MCP](../src/cohezion/mcp/surreal_server.py)
- [Cohezion Vault MCP](../src/cohezion/mcp/servers/vault/)

---
*Created: 2026-04-08*
*Integration Architecture v1.0*
