# Quick Test Script for BMAD Doc Retriever

This is a test script to verify the Doc Retriever works correctly.

## Testing Steps

### 1. Start Prerequisites

```bash
# Start Redis
docker run -d --name redis-mcp -p 6379:6379 redis:7-alpine redis-server --appendonly yes

# Start SurrealDB (if you have it)
docker run -d --name surrealdb-mcp -p 8000:8000 surrealdb/surrealdb:latest start --log trace --user root --pass root memory

# Or use local SurrealDB
```

### 2. Pull Ollama Model

```bash
ollama pull nomic-embed-text
```

### 3. Test Indexing

```python
import asyncio
from pathlib import Path
from cohezion.mcp.servers.doc.indexer import create_indexer, index_bmad_docs

async def test_indexing():
    # Create indexer
    indexer = await create_indexer()
    
    # Index BMAD docs
    results = await index_bmad_docs()
    
    print(f"Indexed {len(results)} modules")
    for lib_id, result in results.items():
        print(f"  {lib_id}: {result['chunks_created']} chunks")

asyncio.run(test_indexing())
```

### 4. Test Retrieval

```python
from cohezion.mcp.servers.doc.indexer import create_indexer

async def test_retrieval():
    indexer = await create_indexer()
    
    # Retrieve docs
    result = await indexer.retrieve(
        query="create a PRD",
        library_id="bmad/bmm",
        max_tokens=2000
    )
    
    print(f"Found {result['chunk_count']} chunks")
    print(f"Total tokens: {result['total_tokens']}")
    
    for chunk in result['chunks']:
        print(f"\nChunk: {chunk['content'][:200]}...")

asyncio.run(test_retrieval())
```

### 5. Start Doc Server

```bash
# Set environment
export MCP_PORT=8364
export SURREAL_URL=ws://localhost:8000/rpc

# Start server
python3 -m cohezion.mcp.servers.doc.server
```

### 6. Test via HTTP

```bash
# Health check
curl http://localhost:8364/health

# Resolve library
curl -X POST http://localhost:8364/tools/resolve-library-id \
  -H "Content-Type: application/json" \
  -d '{"libraryName": "bmm"}'

# Query docs
curl -X POST http://localhost:8364/tools/query-docs \
  -H "Content-Type: application/json" \
  -d '{"libraryId": "bmad/bmm", "query": "create PRD"}'
```

## Expected Output

```json
{
  "tool": "query-docs",
  "libraryId": "bmad/bmm",
  "query": "create PRD",
  "chunks": [
    {
      "content": "## Creating a PRD\n\nFirst, define the problem...",
      "source": "bmad/bmm/workflows/create-prd.md",
      "token_count": 523,
      "metadata": {"score": 0.94}
    }
  ],
  "chunkCount": 3,
  "totalTokens": 1423,
  "source": "local"
}
```

## Troubleshooting

**Ollama not available:**
- Install: `curl https://ollama.ai/install.sh | sh`
- Pull model: `ollama pull nomic-embed-text`
- Start: `ollama serve`

**SurrealDB connection failed:**
- Check if running: `docker ps | grep surrealdb`
- Or use file fallback: Set `SURREAL_URL=file:///tmp/doc_store.db`

**Import errors:**
- Ensure PYTHONPATH includes `src/`
- Or run from project root: `python3 -m cohezion.mcp.servers.doc.server`
