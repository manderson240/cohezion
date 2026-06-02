---
name: database-prime
description: "Specialist in SQL/relational database patterns for AI applications: SQLite, PostgreSQL, connection pooling, migrations, query optimization, and hybrid SQL+NoSQL design. Use when implementing traditional RDBMS patterns or cross-database strategies. Skip: for SurrealDB-specific work use SURREALDB_CORE_PRIME or SURREALDB_CORE_PRIME; for vector stores use VECTOR_STORE_PRIME; for Redis caching use the caching skill."
metadata:
  version: "v1.0"
  concepts: ["SurrealDB", "SQLite", "PostgreSQL", "Redis", "Vector Stores"]
  source: "src/cohezion/skills/DATABASE_PRIME.md"
---

# SKILL: DATABASE_PRIME

## DOMAIN EXPERTISE
You are a specialist in **database systems** for AI applications. You understand SQL, NoSQL, graph databases, vector stores, and hybrid approaches for storing simulation data and knowledge graphs.

## KEY TEXTS & CONCEPTS
- **SurrealDB:** Multi-model database (SQL + Graph + Document)
- **SQLite:** Embedded SQL database for local storage
- **PostgreSQL:** Production-grade relational database
- **Redis:** In-memory key-value store
- **Vector Stores:** Qdrant, Chroma, Pinecone for embeddings

## INSTRUCTION

### 1. SurrealDB (Multi-Model)
```python
from surrealdb import AsyncSurreal

async def surreal_example():
    async with AsyncSurreal("ws://localhost:8001/rpc") as db:
        await db.signin({"user": "root", "pass": "root"})
        await db.use("cohezion", "universes")

        # Create record
        await db.create("universe", {
            "id": "u001",
            "coherence": 0.85,
            "stream": "physicist",
            "trajectory": [0.1, 0.2, 0.3]
        })

        # Graph query
        results = await db.query("""
            SELECT * FROM universe
            WHERE coherence > 0.7
            FETCH related_universes
        """)
```

### 2. SQLite (Local/Embedded)
```python
import sqlite3

conn = sqlite3.connect('cohezion.db')
cursor = conn.cursor()

# Create table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS trajectories (
        id TEXT PRIMARY KEY,
        stream TEXT,
        step INTEGER,
        coherence REAL,
        content TEXT,
        timestamp REAL
    )
''')

# Insert data
cursor.executemany(
    "INSERT INTO trajectories VALUES (?, ?, ?, ?, ?, ?)",
    trajectory_data
)
conn.commit()
```

### 3. PostgreSQL (Production)
```python
import asyncpg

async def pg_example():
    conn = await asyncpg.connect('postgresql://user:pass@localhost/cohezion')

    # Query with vector extension (pgvector)
    results = await conn.fetch('''
        SELECT id, content, embedding <-> $1 as distance
        FROM thoughts
        ORDER BY distance
        LIMIT 10
    ''', query_vector)
```

### 4. Vector Store Integration
```python
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance

client = QdrantClient("localhost", port=6333)

# Create collection
client.create_collection(
    collection_name="flume_vectors",
    vectors_config=VectorParams(size=256, distance=Distance.COSINE)
)

# Search
results = client.search(
    collection_name="flume_vectors",
    query_vector=query_embedding,
    limit=10
)
```

### 5. Schema Design Patterns
```sql
-- Universe State Table
CREATE TABLE universe_states (
    id UUID PRIMARY KEY,
    stream VARCHAR(50),
    epoch INTEGER,
    physics_state JSONB,
    flume_vector VECTOR(256),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Trajectory Relationship
CREATE TABLE trajectory_links (
    from_state UUID REFERENCES universe_states(id),
    to_state UUID REFERENCES universe_states(id),
    transition_type VARCHAR(20),
    weight REAL
);
```

## APPLICATIONS
- **Simulation Storage:** Persist universe states and trajectories
- **Knowledge Graph:** Store entity relationships (SurrealDB)
- **Vector Search:** Find similar thoughts/universes
- **Audit Trail:** Track simulation history

## VERSION
v1.0

## SEE ALSO
- VECTOR_STORE_PRIME.md
- KNOWLEDGE_GRAPH_INTEGRATION_PRIME.md
- CACHING_PRIME.md
