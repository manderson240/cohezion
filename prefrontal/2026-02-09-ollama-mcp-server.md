---
title: "Ollama MCP Server - Model Management as Infrastructure"
date: 2026-02-09
status: implemented
tags: [decision, mcp, ollama, infrastructure, claude-code]

decision_reasoning:
  chosen_option: "Build reusable MCP server for Ollama model management instead of scattered scripts"
  rationale: "Scripts duplicate Ollama API logic and aren't reusable; MCP server centralizes context management, model selection, and batching as infrastructure"
  confidence_score: 0.92
  alternatives_rejected:
    - "Continue with scattered scripts (duplicated logic, not reusable)"
    - "Use Ollama API directly (no context management, manual model selection)"
  reasoning_chain:
    - "Identified multiple one-off scripts calling Ollama API"
    - "Realized context window management needed by multiple tools"
    - "Model selection logic duplicated across scripts"
    - "Decided to build infrastructure: MCP server with auto context/model selection"
    - "Enables reuse across Claude Code, agents, web UI, other clients"

metrics:
  estimated_cost: 0.0  # Infrastructure, all local Ollama
  estimated_time_hours: 18.0  # Full implementation
  actual_cost: 0.0  # All local inference
  actual_time_hours: 16.0  # Slightly ahead of schedule
  tokens_used: 0  # Local models only
  cost_per_lesson: 0.0
  lessons_generated:
    - patterns/ollama-mcp-context-management
aspect: thinker
neural:
  activation: 1.0
  stage: mature
  synapse_in: 19
  synapse_out: 15
---

# Ollama MCP Server - Elevate Model Wrangling to Infrastructure

**Vision**: MCP server that handles Ollama model management, context windows, batching → usable by Claude Code, other agents, any client

**Value**: Model wrangling becomes **infrastructure** (reusable) instead of **scripts** (one-off)

---

## Why MCP Server (Not Scripts)

### Current Approach (Scripts)
```python
# One-off script for gap analysis
python gap_analysis_poc.py

# Another script for embeddings
python generate_embeddings.py

# Another for context management
python chunk_papers.py
```

**Problems**:
- Duplicated Ollama API calls
- No context management
- No model selection logic
- Not reusable by other tools

### MCP Server Approach
```python
# Claude Code uses MCP tools:
ollama_query(prompt="Analyze gaps", context="auto")
ollama_embed(text="paper content")
ollama_batch(prompts=[...], model="auto")

# Other agents use same tools
# Scripts use same tools
# Web UI uses same tools
```

**Benefits**:
- ✅ Single source of truth (Ollama management)
- ✅ Context windows handled automatically
- ✅ Model selection optimized
- ✅ Reusable across ALL tools
- ✅ Integrates with Claude Code natively

---

## Ollama MCP Server Architecture

### Server Location
```
/home/mike-anderson/dev/cohezion/ollama-mcp/
├── src/
│   ├── server.py          # FastMCP server
│   ├── context_manager.py # Context window management
│   ├── model_selector.py  # Auto model selection
│   ├── batch_processor.py # Request batching
│   └── memory_manager.py  # RAM optimization
├── pyproject.toml
└── README.md
```

### MCP Tools Exposed

#### 1. **ollama_query()** - Smart Query with Auto Context Management
```python
@mcp.tool()
def ollama_query(
    prompt: str,
    model: str = "auto",  # Auto-select best model
    context: str = "auto",  # Auto-chunk if needed
    max_tokens: int = 1000
) -> str:
    """Query Ollama with automatic model selection and context management.

    - If prompt > model context → auto-chunks and merges results
    - If model not loaded → loads with optimal keep-alive
    - If RAM > 80% → unloads LRU model first
    - Returns consolidated response

    Args:
        prompt: Query text
        model: Model name OR "auto" for automatic selection
        context: Additional context OR "auto" to extract from conversation
        max_tokens: Maximum output tokens
    """
    # 1. Select model based on prompt length
    if model == "auto":
        model = model_selector.select_for_prompt(prompt)

    # 2. Check if chunking needed
    chunks = context_manager.chunk_if_needed(prompt, model)

    # 3. Ensure model loaded
    memory_manager.ensure_loaded(model)

    # 4. Execute query (batch if chunked)
    if len(chunks) > 1:
        results = batch_processor.process_chunks(chunks, model)
        return merge_results(results)
    else:
        return ollama_client.generate(model, prompt)
```

#### 2. **ollama_embed()** - Embeddings with Caching
```python
@mcp.tool()
def ollama_embed(text: str, cache: bool = True) -> list[float]:
    """Generate embeddings with automatic caching.

    - Uses nomic-embed-text (always loaded)
    - Caches embeddings in SurrealDB (optional)
    - Batch-processes if multiple texts

    Args:
        text: Text to embed
        cache: Whether to cache result
    """
    # Check cache first
    if cache:
        cached = embedding_cache.get(text)
        if cached:
            return cached

    # Generate embedding
    embedding = ollama_client.embed("nomic-embed-text", text)

    # Cache if requested
    if cache:
        embedding_cache.set(text, embedding)

    return embedding
```

#### 3. **ollama_batch()** - Efficient Batch Processing
```python
@mcp.tool()
def ollama_batch(
    prompts: list[str],
    model: str = "auto",
    batch_size: int = 5
) -> list[str]:
    """Process multiple prompts efficiently.

    - Combines prompts into batches
    - Single API call per batch
    - Automatic model selection
    - Progress tracking

    Args:
        prompts: List of prompts to process
        model: Model name OR "auto"
        batch_size: Prompts per batch
    """
    results = []

    for batch in chunk_prompts(prompts, batch_size):
        # Combine into single request
        combined = combine_batch(batch)

        # Single API call
        response = ollama_query(combined, model=model)

        # Parse batch response
        results.extend(parse_batch(response))

    return results
```

#### 4. **ollama_select_model()** - Smart Model Selection
```python
@mcp.tool()
def ollama_select_model(
    task: str,
    content_length: int = 0,
    quality: str = "balanced"
) -> str:
    """Select optimal model for task.

    Args:
        task: "gap_analysis", "embeddings", "reasoning", "coding"
        content_length: Input text length (chars)
        quality: "fast", "balanced", "best"

    Returns:
        Model name (e.g., "qwen3:8b")
    """
    # Select based on task + content + quality
    if task == "embeddings":
        return "nomic-embed-text"

    if task == "gap_analysis":
        if content_length > 30000:
            return "deepseek-r1:7b"  # 32K context
        return "qwen3:8b"  # Fast, 8K context

    if task == "reasoning":
        if quality == "best":
            return "deepseek-r1:7b"
        return "qwen3:8b"

    # Default
    return "qwen3:8b"
```

#### 5. **ollama_status()** - Model Status + Metrics
```python
@mcp.tool()
def ollama_status() -> str:
    """Get Ollama server status and loaded models.

    Returns JSON with:
    - Loaded models (name, RAM, context window)
    - RAM usage (total, available)
    - Request queue depth
    - Performance metrics
    """
    loaded = ollama_client.ps()
    ram = psutil.virtual_memory()

    return json.dumps({
        "loaded_models": [
            {
                "name": m["name"],
                "size_mb": m["size"] / 1024 / 1024,
                "context_window": MODEL_CONTEXTS[m["name"]],
                "until": m.get("until", "unknown")
            }
            for m in loaded["models"]
        ],
        "ram": {
            "total_gb": ram.total / 1024**3,
            "used_gb": ram.used / 1024**3,
            "percent": ram.percent
        },
        "performance": {
            "requests_today": metrics.get_count(),
            "avg_latency_ms": metrics.get_avg_latency()
        }
    }, indent=2)
```

#### 6. **ollama_preload()** - Pre-Load Models
```python
@mcp.tool()
def ollama_preload(models: list[str], keep_alive: str = "60m") -> str:
    """Pre-load models to avoid first-request latency.

    Args:
        models: List of model names
        keep_alive: Keep-alive duration ("60m", "forever")
    """
    for model in models:
        ollama_client.generate(model, "Ready", keep_alive=keep_alive)

    return f"Pre-loaded {len(models)} models"
```

---

## Integration with Claude Code

### Configuration (~/.claude/config.json)
```json
{
  "mcpServers": {
    "ollama": {
      "command": "python",
      "args": [
        "/home/mike-anderson/dev/cohezion/ollama-mcp/src/server.py"
      ],
      "env": {
        "OLLAMA_URL": "http://localhost:11434",
        "CACHE_ENABLED": "true"
      }
    },
    "cloud-vault": {
      "command": "python",
      "args": ["-m", "mcp_server.main"],
      "cwd": "/home/mike-anderson/dev/cohezion/cloud-vault-mcp"
    }
  }
}
```

### Claude Code Usage
```
User: "Analyze my vault for research gaps"

Claude Code:
> Using MCP tool: ollama_query()
> Prompt: "Analyze these 20 papers for conceptual gaps..."
> Model: auto-selected qwen3:8b
> Context: auto-chunked (content > 8K)
> Result: [5 gaps identified]

User: "Generate embeddings for all papers"

Claude Code:
> Using MCP tool: ollama_batch()
> Processing 20 papers in batches of 5
> Model: nomic-embed-text (already loaded)
> Progress: ████████████ 100%
> Result: [20 embeddings cached in SurrealDB]
```

---

## Compound Engineering Benefits

### Before (Scripts)
```bash
# Manual model management:
ollama run qwen3:8b "query" --keep-alive 60m

# Manual chunking:
python chunk_paper.py --max-tokens 8000

# Manual batching:
for paper in papers/*.md; do
    ollama run qwen3:8b "analyze $paper"
done

# No caching, no optimization
```

### After (MCP Server)
```python
# Claude Code (or any client) just uses tools:
result = ollama_query("analyze vault", context="auto")

# All handled automatically:
# ✅ Model selection (qwen3 vs deepseek vs phi4)
# ✅ Context chunking (if > 8K)
# ✅ Model loading (pre-load with keep-alive)
# ✅ Batching (combine multiple requests)
# ✅ Caching (embeddings, frequent queries)
# ✅ Memory management (unload LRU if RAM > 80%)
```

---

## Implementation Plan

### Phase 1: Core MCP Server (Week 1)
- Setup FastMCP server skeleton
- Implement `ollama_query()` with basic functionality
- Implement `ollama_status()`
- Test with Claude Code

### Phase 2: Context Management (Week 2)
- Implement `ContextManager` class
- Auto-chunking for long prompts
- Model selection based on content length
- Test with 20 papers from vault

### Phase 3: Batching + Caching (Week 3)
- Implement `ollama_batch()`
- Embedding cache (SurrealDB)
- Query result cache
- Performance metrics

### Phase 4: Memory Optimization (Week 4)
- RAM monitoring
- Auto model unloading
- Pre-loading strategy
- Production-ready

---

## Model Wrangler + Ollama MCP Collaboration

**Model Wrangler** (Daily driver):
- Monitors new models (Hugging Face, Reddit, etc.)
- Benchmarks new models
- Updates Ollama MCP config when swapping models
- Example: "New model phi-5:14b released → benchmark → update `ollama_select_model()` logic"

**Ollama MCP Server** (Infrastructure):
- Provides tools for using Ollama
- Handles context, batching, caching
- Used by Claude Code, agents, scripts
- Example: Claude Code calls `ollama_query()` → server selects best model → executes

**Division**:
- Model Wrangler: **WHAT** models to use (selection, benchmarking)
- Ollama MCP: **HOW** to use models (context, batching, caching)

---

## Success Metrics

### Developer Experience
- ✅ Claude Code can query Ollama with single tool call
- ✅ No manual model loading/unloading
- ✅ No manual chunking for long prompts
- ✅ Automatic batching for multiple requests

### Performance
- ✅ First request < 2s (pre-loading works)
- ✅ Batch processing 10x faster than sequential
- ✅ 80%+ cache hit rate for embeddings
- ✅ RAM usage stays < 80%

### Cost
- ✅ $0/month for local inference (vs $50+ for Claude)
- ✅ 95% of queries use local LLMs
- ✅ Only complex reasoning uses Claude Opus

---

## Next Steps

**Immediate** (This session):
1. Create Ollama MCP server skeleton
2. Implement `ollama_query()` basic version
3. Test with Claude Code

**This Week**:
1. Add context management
2. Add model selection logic
3. Production-ready core tools

**Next Week**:
1. Batching + caching
2. Memory optimization
3. Integrate with Model Wrangler

---

## Implementation Status

**PHASE 1 COMPLETE** (2026-02-09):
- ✅ FastMCP server created at `/home/mike-anderson/dev/cohezion/ollama-mcp/`
- ✅ 5 MCP tools implemented and tested:
  - `ollama_query()` - Smart querying with auto model selection
  - `ollama_embed()` - Embedding generation with nomic-embed-text
  - `ollama_status()` - Server status and RAM monitoring
  - `ollama_select_model()` - Model recommendation engine
  - `ollama_batch()` - Batch processing for multiple prompts
- ✅ `ModelSelector` class with intelligent task-based selection
- ✅ `OllamaClient` wrapper with error handling
- ✅ Configured in Claude Code (`~/.claude/mcp.json`)
- ✅ Package installed in development mode
- ✅ Git repository initialized with initial commit

**Next phases**: Context management (Week 2), Caching (Week 3), Optimization (Week 4)

---

**Status**: Phase 1 implemented, ready for use
**Value**: Ollama becomes **infrastructure** (MCP server) not **scripts**
**Impact**: Claude Code + all tools benefit from smart Ollama management
**Cost**: ~1 week implementation, $0 ongoing (all local)

## Related
**Domains**: ai-ml, architecture, data, infrastructure, integration, performance
**Categories**: strategic, technical


[[mcp-infrastructure-architecture]], [[mcp-model-context-protocol]], [[machine-learning-optimization]]

## Relevance to Cohezion

[[mcp-infrastructure-architecture]]
[[context-management]]

## Related Patterns

- [[quick-start-mcp-tool]] — scaffold pattern for building the MCP server infrastructure decided here
- [[fastmcp-asgi-builder-pattern]] — FastMCP builder pattern that powers this server's HTTP transport

## Related Lessons

- [[lesson-31-operation-specific-modulation]] (operational validation)

## Related Concepts

- [[3d-graph-plugin-selection]]
- [[2026-02-09-ollama-context-management]]
- [[2026-02-12-claude-code-context-awareness-codification]]
- [[2026-02-12-charter-aligned-scoring-formula]]
- [[2026-02-13-local-model-roster-update-february-2026-sota-assessment]]
- [[2026-02-17-phase-2-full-verification-plan]]
- [[2026-02-13-gitlab-to-github-consolidation-with-artifact-governance]]
- [[2026-02-14-adversarial-multi-agent-review-protocol]]
