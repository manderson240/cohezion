# Karpathy LLM-Wiki + MIRIX + Obsidian + SurrealDB Integration

## Overview

Integration of Karpathy's LLM-Wiki pattern with Cohezion's infrastructure:
- **Karpathy LLM-Wiki**: 3-layer architecture (raw → wiki → schema)
- **MIRIX**: Multi-agent memory system (Core, Episodic, Semantic, Procedural, Resource, Knowledge Vault)
- **Obsidian**: Local-first markdown vault
- **SurrealDB**: Graph + vector database for 12D physics state
- **Cohezion MCP**: Skills, agents, and orchestration

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        KARPATHY LLM-WIKI PATTERN                       │
├─────────────────────────────────────────────────────────────────────────┤
│  Layer 1: RAW SOURCES (Immutable)                                      │
│  ├── /raw/articles/      → Web clips, PDFs, transcripts              │
│  ├── /raw/books/         → Book chapters, reading notes              │
│  └── /raw/daily/         → Journal entries, voice memos                │
│                                                                         │
│  Layer 2: WIKI (LLM-Maintained)                                         │
│  ├── /wiki/entities/      → People, places, concepts                   │
│  ├── /wiki/concepts/     → Abstract ideas, theories                    │
│  ├── /wiki/sources/      → Summaries of raw sources                    │
│  ├── /wiki/synthesis/     → Compounded knowledge (queries → pages)       │
│  ├── index.md            → Content catalog (updated per ingest)        │
│  └── log.md              → Chronological audit trail                  │
│                                                                         │
│  Layer 3: SCHEMA (Configuration)                                        │
│  ├── AGENTS.md           → Agent behavior (Cohezion)                     │
│  ├── CLAUDE.md (opt)     → Claude Code specific                        │
│  └── wiki-rules.md       → Domain conventions                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      COHEZION INTEGRATION LAYER                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐  │
│  │ Wiki MCP     │  │ MIRIX Bridge │  │ Surreal MCP  │  │ Obsidian │  │
│  │ (Ingest/     │  │ (6 Memory    │  │ (Graph/      │  │ Bridge   │  │
│  │  Query/Lint) │  │  Agents)     │  │  Vector DB)  │  │ (Vault)  │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └────┬─────┘  │
└───────┬────────────────┬────────────────┬────────────────┬───────────┘
        │                │                │                │
        ▼                ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        MIRIX MEMORY SYSTEM                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │   Core   │ │ Episodic │ │ Semantic │ │Resource  │ │Knowledge │       │
│  │  Memory  │ │  Memory  │ │   Wiki   │ │  Agent   │ │  Vault   │       │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘       │
└──────┬──────────────┬────────────┼────────────┼────────────┬───────────┘
       │              │            │            │            │
       ▼              ▼            ▼            ▼            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      SURREALDB (Universe Knowledge Graph)                │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  Entity Types: raw_source, wiki_page, mirix_memory, concept      │  │
│  │  Relations:    derives_from, relates_to, contradicts, supports   │  │
│  │  Physics:      coherence, salience, recency, certainty         │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Ingest Pipeline

```
Raw Source (PDF/URL/Markdown)
    │
    ▼
┌─────────────────────┐
│  Wiki MCP Ingest   │ ──→ Create /raw/ entry (immutable)
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│  LLM Processing    │ ──→ Extract entities, summarize, link
└─────────────────────┘
    │
    ├──→ Create /wiki/sources/ summary
    ├──→ Update /wiki/entities/ (auto-create if new)
    ├──→ Update /wiki/concepts/ (link related ideas)
    ├──→ Update index.md
    └──→ Append to log.md
    │
    ▼
┌─────────────────────┐
│  MIRIX Integration   │ ──→ Sync to appropriate memory type
└─────────────────────┘
    │
    ├──→ Episodic: "Read article X on Y date"
    ├──→ Semantic: Link to existing concept graph
    ├──→ Knowledge Vault: Store full summary
    └──→ Resource: Track source provenance
    │
    ▼
┌─────────────────────┐
│  SurrealDB Persist │ ──→ Store with 12D physics coordinates
└─────────────────────┘
    │
    ├──→ node:wiki_page with physics.salience
    ├──→ relation:derives_from → raw_source
    └──→ relation:relates_to → existing concepts
```

### 2. Query Pipeline

```
User Query
    │
    ▼
┌─────────────────────┐
│  Wiki MCP Query    │ ──→ Read index.md → find relevant pages
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│  Multi-Source Fetch │
└─────────────────────┘
    │
    ├──→ Read wiki pages (local)
    ├──→ Query MIRIX memories (semantic search)
    ├──→ Query SurrealDB (graph traversal)
    └──→ Search Obsidian vault (BM25/vector)
    │
    ▼
┌─────────────────────┐
│  LLM Synthesis     │ ──→ Compile answer with citations
└─────────────────────┘
    │
    ├──→ Return answer to user
    └──→ (Optional) File to /wiki/synthesis/
```

### 3. Lint Pipeline

```
Periodic Health Check
    │
    ▼
┌─────────────────────┐
│  Wiki MCP Lint     │ ──→ Scan for issues
└─────────────────────┘
    │
    ├──→ Orphan pages (no inbound links)
    ├──→ Dead links (broken [[wiki_links]])
    ├──→ Contradictions (flagged by LLM)
    ├──→ Stale claims (vs. newer sources)
    ├──→ Missing concepts (mentioned but no page)
    └──→ Suggest new sources to fill gaps
    │
    ▼
┌─────────────────────┐
│  Auto-Fix or Report │
└─────────────────────┘
```

## Integration Points

### A. Karpathy Wiki → MIRIX Bridge

```python
# src/cohezion/integrations/wiki_mirix_bridge.py

class WikiMirixBridge:
    """Connect Karpathy LLM-Wiki to MIRIX memory agents."""
    
    async def sync_wiki_to_mirix(self, wiki_path: Path):
        """
        Sync wiki entities to MIRIX memory types:
        
        Mapping:
        - /wiki/entities/person/*.md → Core Memory (human profile)
        - /wiki/sources/*.md → Episodic Memory (reading events)
        - /wiki/concepts/*.md → Semantic Memory (concept graph)
        - /wiki/synthesis/*.md → Knowledge Vault (compiled knowledge)
        """
        
    async def query_cross_system(self, query: str) -> dict:
        """
        Query both wiki and MIRIX for comprehensive results.
        Returns unified view with provenance.
        """
```

### B. Wiki → SurrealDB Schema

```sql
-- SurrealDB schema for LLM-Wiki

DEFINE TABLE raw_source SCHEMAFULL;
DEFINE FIELD url ON raw_source TYPE string;
DEFINE FIELD content_hash ON raw_source TYPE string;
DEFINE FIELD added_at ON raw_source TYPE datetime;
DEFINE FIELD source_type ON raw_source TYPE string 
    ASSERT $value IN ['article', 'book', 'paper', 'video', 'transcript'];

DEFINE TABLE wiki_page SCHEMAFULL;
DEFINE FIELD title ON wiki_page TYPE string;
DEFINE FIELD content ON wiki_page TYPE string;
DEFINE FIELD category ON wiki_page TYPE string
    ASSERT $value IN ['entity', 'concept', 'source_summary', 'synthesis'];
DEFINE FIELD created_at ON wiki_page TYPE datetime;
DEFINE FIELD updated_at ON wiki_page TYPE datetime;
DEFINE FIELD source_refs ON wiki_page TYPE array<record<raw_source>>;

-- 12D Physics coordinates for knowledge nodes
DEFINE FIELD physics.coherence ON wiki_page TYPE float;
DEFINE FIELD physics.salience ON wiki_page TYPE float;
DEFINE FIELD physics.recency ON wiki_page TYPE float;
DEFINE FIELD physics.certainty ON wiki_page TYPE float;

-- Relations
DEFINE TABLE derives_from TYPE RELATION FROM wiki_page TO raw_source;
DEFINE TABLE relates_to TYPE RELATION FROM wiki_page TO wiki_page;
DEFINE TABLE contradicts TYPE RELATION FROM wiki_page TO wiki_page;
DEFINE TABLE supports TYPE RELATION FROM wiki_page TO wiki_page;

-- Full-text search
DEFINE INDEX wiki_search ON wiki_page COLUMNS title, content SEARCH ANALYZER simple;
```

### C. Obsidian Integration

```python
# src/cohezion/integrations/obsidian_wiki.py

class ObsidianWiki:
    """Obsidian vault as Karpathy LLM-Wiki frontend."""
    
    VAULT_PATH = Path("/home/mike-anderson/vaults/cohezion-wiki")
    
    # Karpathy structure
    RAW_DIR = VAULT_PATH / "raw"
    WIKI_DIR = VAULT_PATH / "wiki"
    INDEX_FILE = VAULT_PATH / "index.md"
    LOG_FILE = VAULT_PATH / "log.md"
    
    async def ingest_source(self, source_path: Path, source_type: str):
        """
        Ingest a new source into the wiki:
        1. Copy to /raw/ (immutable)
        2. Create /wiki/sources/ summary (LLM-generated)
        3. Update entities/concepts
        4. Update index.md
        5. Append to log.md
        """
        
    async def query_wiki(self, query: str) -> str:
        """
        Query using Karpathy's progressive disclosure:
        1. Read index.md (token budget: ~1-2K)
        2. Identify relevant pages
        3. Read full pages (token budget: ~5-20K)
        4. Synthesize answer
        """
```

## File Structure

```
cohezion-wiki/                          # Obsidian vault root
├── .obsidian/                           # Obsidian config
├── AGENTS.md                            # Schema layer (Cohezion)
├── index.md                             # Content catalog
├── log.md                               # Chronological log
│
├── raw/                                 # Layer 1: Immutable sources
│   ├── articles/                        # Web clips, PDFs
│   ├── books/                           # Book chapters
│   ├── papers/                          # Research papers
│   └── daily/                            # Journal, voice memos
│
└── wiki/                                # Layer 2: LLM-maintained
    ├── entities/                         # People, orgs, places
    │   ├── people/
    │   ├── organizations/
    │   └── places/
    ├── concepts/                         # Abstract ideas
    │   ├── theories/
    │   ├── methods/
    │   └── domains/
    ├── sources/                           # Source summaries
    │   ├── articles/
    │   ├── books/
    │   └── papers/
    └── synthesis/                         # Compounded knowledge
        ├── questions/                     # Filed Q&A
        ├── comparisons/                   # Comparisons
        └── insights/                      # Connections found
```

## MCP Server: wiki_mcp.py

```python
# src/cohezion/mcp/wiki_mcp.py
"""MCP server implementing Karpathy LLM-Wiki operations."""

class WikiMCP:
    """
    Three core operations: ingest, query, lint
    """
    
    async def wiki_ingest(
        self,
        source: str,           # URL, file path, or text
        source_type: str,       # article, book, paper, etc.
        auto_extract: bool = True
    ) -> dict:
        """
        Ingest a source into the wiki.
        
        Returns:
            {
                "raw_path": "/raw/articles/...",
                "wiki_pages_created": ["wiki/sources/...", "wiki/entities/..."],
                "entities_extracted": ["Person A", "Concept B"],
                "linked_to": ["wiki/concepts/existing"]
            }
        """
    
    async def wiki_query(
        self,
        query: str,
        depth: str = "standard",  # quick, standard, deep
        file_back: bool = False   # Save answer to wiki/synthesis/
    ) -> dict:
        """
        Query the wiki with progressive disclosure.
        
        Args:
            depth: quick (index only), standard (index+pages), deep (+related)
            file_back: If True, save synthesis to wiki/synthesis/
        """
    
    async def wiki_lint(
        self,
        fix: bool = False        # Auto-fix if True
    ) -> dict:
        """
        Health check the wiki.
        
        Returns:
            {
                "orphans": [...],           # Pages with no inbound links
                "dead_links": [...],         # Broken [[wiki_links]]
                "contradictions": [...],     # Flagged by LLM
                "stale_claims": [...],       # Superseded by newer sources
                "suggested_sources": [...]    # Web search suggestions
            }
        """
```

## Usage Examples

### From Pi/Claude Code

```
# Ingest a new article
> wiki_ingest(source="https://arxiv.org/abs/...", source_type="paper")
✓ Created: /raw/papers/arxiv_2401_...
✓ Created: /wiki/sources/attention_is_all_you_need.md
✓ Created: /wiki/entities/transformer.md
✓ Updated: /wiki/concepts/self_attention.md
✓ Updated: index.md
✓ Appended to: log.md

# Query the wiki
> wiki_query("How does transformer attention work?", depth="deep", file_back=True)
Answer: [...synthesis with citations...]
✓ Saved to: /wiki/synthesis/transformer_attention_explained.md

# Health check
> wiki_lint(fix=True)
Found: 3 orphan pages, 2 dead links
Fixed: Re-linked orphans, removed dead links
Suggestion: Search for "transformer alternatives" (gap in knowledge)
```

### From Cohezion Agent

```python
# Agent uses wiki as persistent memory
from cohezion.integrations import WikiMirixBridge

async def research_topic(topic: str):
    wiki = WikiMirixBridge()
    
    # Query existing knowledge
    existing = await wiki.query_wiki(topic)
    
    # Identify gaps
    gaps = await wiki.identify_gaps(topic)
    
    # Search for new sources
    new_sources = await web_search(gaps)
    
    # Ingest and compound
    for source in new_sources:
        await wiki.ingest(source)
    
    return await wiki.query(topic)  # Now enriched
```

## Sync Strategy

| System | Direction | Trigger | Data |
|--------|-----------|---------|------|
| Obsidian Wiki | ↔ | Real-time | Markdown files |
| MIRIX | ← | Post-ingest | Memory agents update |
| SurrealDB | ← | Post-ingest | Graph nodes + relations |
| Cohezion Skills | ← | Query time | Context injection |

## Implementation Priority

1. **Week 1**: Basic wiki_mcp.py with ingest/query/lint
2. **Week 2**: Obsidian bridge (file I/O)
3. **Week 3**: MIRIX integration (6 memory types)
4. **Week 4**: SurrealDB graph persistence

## References

- [Karpathy LLM-Wiki Gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- [MIRIX GitHub](https://github.com/Mirix-AI/MIRIX)
- [SurrealDB Docs](https://surrealdb.com/docs)
- [Obsidian Publish](https://obsidian.md/publish)

---
*Integration spec v1.0 - 2026-04-08*
