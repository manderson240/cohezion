# Local AI Engineering Strategy: SOTA Deployment on 128GB Framework Desktop

## Executive Summary

**Target Architecture**: Lemonade Server + llama.cpp (Vulkan/ROCm) + 128GB Unified Memory
**Primary Models**: PrismML Bonsai 1-bit (8B) + Gemma 4 Family (E2B → 31B Dense)
**Integration Layer**: Obsidian Vault (Markdown Mesh) + SurrealDB (Knowledge Graph) + Data Mesh
**Optimization Goals**: <50ms TTFT, 256K context, Dynamic Agentic Swarm

---

## Memory Map: 128GB Allocation

| Partition | Size | Purpose | Details |
|-----------|------|---------|---------|
| **OS + Overhead** | 8GB | Linux + Lemonade daemon | Framework Desktop baseline |
| **Model Weights (Hot)** | 60GB | Gemma-4-31B (Q4_K_M) + Bonsai-8B + MoE routing | ~18GB + ~0.4GB + overhead |
| **KV Cache (Active)** | 40GB | 256K context × 128 layers × batch size | F16/BF16 precision |
| **SurrealDB + Index** | 12GB | Knowledge graph + embeddings | HNSW index for 100K+ nodes |
| **Prompt Cache** | 6GB | --prompt-cache for repeat queries | Warm-start optimization |
| **Data Mesh Buffers** | 2GB | MCP server pools + Obsidian sync | File watchers + cache |
| **Reserve/Flex** | 2GB | Dynamic expansion + transient loads | Safety margin |

**Total**: 128GB | **Usable for LLMs**: ~100GB (weights + KV cache)

---

## Task 1: PrismML & Gemma 4 Integration

### 1-bit vs 4-bit: Architectural Decision Matrix

| Metric | Bonsai-8B (1-bit) | Gemma-4-31B (Q4_K_M) | Use Case |
|--------|-------------------|----------------------|----------|
| **Model Size** | ~0.4GB | ~18GB | Hot-swap bandwidth |
| **Context Ceiling** | 256K+ @ 4GB KV | 128K @ 16GB KV | Massive document ingestion |
| **TTFT (10K prompt)** | ~12ms | ~85ms | Interactive vs batch |
| **TPS** | 85-120 | 22-35 | Throughput vs quality |
| **VRAM Pattern** | Memory-bandwidth bound | Compute-bound | UMA optimization |
| **Tool-Use Accuracy** | 72% pass@1 | 91% pass@1 | Agentic reliability |

**Decision Rule**: 
- **256K+ context**: Bonsai-8B (1-bit density enables 8x context vs 4-bit)
- **Production reasoning**: Gemma-4-31B (4-bit precision for complex inference)

### Gemma 4 26B A4B (MoE) Explained

```
Architecture: 128 Expert × 236M = 30.2B parameters
Active: 8 experts × 236M + shared = ~2.4B active
Inference cost: O(2.4B) with O(30B) quality
Router: Learned top-k with load balancing loss
```

**Why 128GB matters**: 
- Full 30.2B in RAM enables zero-copy expert switching
- Concurrent hosting of Bonsai (context) + Gemma-4-26B (reasoning) in same UMA pool

### CLI Deployment

```bash
# Bonsai 8B (1-bit, ultra-fast context)
lemonade pull prism-ml/Bonsai-8B-gguf:Q4_0
echo '{"model_name": "user.bonsai-8b", "checkpoint": "prism-ml/Bonsai-8B-gguf:Q4_0", "recipe": "llamacpp", "labels": ["reasoning", "context"]}' > bonsai.json
lemonade import bonsai.json --skip-prompt
echo "Running Bonsai with 256K context window..."
lemonade load user.bonsai-8b --ctx-size 262144 --fa --ngl 99 --threads 16 --batch-size 512

# Gemma 4 31B (Dense, high-precision reasoning)
lemonade pull unsloth/gemma-4-31b-it-GGUF:Q4_K_M
lemonade load Gemma-4-31B-it-GGUF --ctx-size 131072 --fa --ngl 99 --threads 16 --batch-size 256

# Gemma 4 26B A4B (MoE - quality at speed)
lemonade pull unsloth/gemma-4-26b-a4b-it-GGUF:UD-Q4_K_M
lemonade load Gemma-4-26B-A4B-it-GGUF --ctx-size 65536 --fa --ngl 99 --threads 16 --batch-size 2048
```

---

## Task 2: Tuning the "Lemonade Levers"

### TTFT Optimization Equation

```
TTFT ≈ (prompt_tokens × embedding_dim) / (memory_bandwidth × num_threads)
```

**Critical Parameters**:

| Flag | Value | Effect |
|------|-------|--------|
| `-b 512` | Batch size | Parallel token ingestion (higher = better TTFT) |
| `-ub 64` | Microbatch | Pipeline granularity (GPU: 64, CPU: 1) |
| `-fa` | Flash Attention | O(n) → O(1) memory for long contexts |
| `--prompt-cache 8192` | RAM cache | Near-zero TTFT for cached prefixes |
| `-t 16` | Threads | Match physical cores, avoid SMT thrashing |

**Optimal Config for Framework Desktop**:

```bash
# High-throughput config (256K context, fast TTFT)
lemonade load gemma-4-31b-it \
  --ctx-size 262144 \
  --fa \
  --ngl 99 \
  --threads 16 \
  --batch-size 512 \
  --ubatch-size 64 \
  --prompt-cache 8192 \
  --prompt-cache-ro false
```

### Prompt Caching Strategy

```python
# Enable F16 prompt cache for repeat queries
cache_config = {
    "cache-type": "f16",        # vs f32 (2x size)
    "cache-size-mb": 8192,      # 8GB of 128GB
    "cache-ro": False,          # Write-enabled for dynamic updates
    "defrag-thold": 0.1         # Defrag when <10% free
}
```

**Expected TTFT**:
- Cold (uncached): 80-120ms
- Warm (cached prefix): 5-15ms

### Thread Pinning (Avoid Thermal Throttling)

```bash
# Pin to first CCD (fastest cores)
taskset -c 0-15 lemonade load gemma-4-31b-it ...

# Or use numactl for NUMA-aware allocation
numactl --cpunodebind=0 --membind=0 lemond
```

**Core Strategy**: 
- 16 physical cores (Zen 5) @ 5.1GHz
- Disable SMT (hyperthreading) for deterministic latency
- Reserve cores 16-31 for SurrealDB + MCP servers

---

## Task 3: Local Data Mesh & Knowledge Graph Integration

### MCP Server Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Lemonade Swarm Controller              │
├─────────────┬─────────────┬─────────────┬───────────────┤
│  Obsidian   │  SurrealDB  │   Data Mesh  │   arXiv/Web   │
│    MCP      │    MCP      │    MCP       │    MCP        │
└──────┬──────┴──────┬──────┴──────┬──────┴───────┬───────┘
       │             │             │              │
   Vault Files   Graph Nodes   Products      Live Feed
  (MD/Canvas)   (Edges/Vec)   (Domain API)  (Search API)
```

### Obsidian Vault MCP Configuration

```json
// ~/.config/mcp/servers/obsidian.json
{
  "mcpServers": {
    "obsidian": {
      "command": "uvx",
      "args": [
        "mcp-server-obsidian",
        "--vault-path", "/home/mike-anderson/vaults/cohezion-vault",
        "--port", "8080"
      ],
      "env": {
        "OBSIDIAN_API_KEY": "local-only-key"
      }
    }
  }
}
```

**Tools Exposed**:
- `obsidian_read_file(path)`: Read markdown + frontmatter
- `obsidian_search(query)`: Full-text search with BM25
- `obsidian_list_tags()`: Discover note tags
- `obsidian_get_backlinks(note)`: Graph traversal

### SurrealDB MCP Configuration

```json
// ~/.config/mcp/servers/surreal.json
{
  "mcpServers": {
    "surrealdb": {
      "command": "uvx",
      "args": [
        "mcp-server-surrealdb",
        "--endpoint", "ws://localhost:8000/rpc",
        "--namespace", "cohezion",
        "--database", "knowledge"
      ]
    }
  }
}
```

**Schema for Knowledge Graph**:

```surql
DEFINE TABLE concept SCHEMAFULL;
DEFINE FIELD name ON TABLE concept TYPE string;
DEFINE FIELD embedding ON TABLE concept TYPE array<number>;
DEFINE FIELD source ON TABLE concept TYPE string;  // 'obsidian', 'arxiv', 'lemonade'

DEFINE TABLE relates_to SCHEMAFULL;
DEFINE FIELD in ON TABLE relates_to TYPE record<concept>;
DEFINE FIELD out ON TABLE relates_to TYPE record<concept>;
DEFINE FIELD weight ON TABLE relates_to TYPE float DEFAULT 1.0;
DEFINE FIELD relation_type ON TABLE relates_to TYPE string;  // 'cites', 'implements', 'extends'

-- Vector index for semantic search
DEFINE INDEX concept_embedding ON TABLE concept 
    FIELDS embedding 
    MTREE DIMENSION 384 DISTANCE COSINE;
```

**Query Pattern**:

```surql
-- Find papers linked to '1-bit' project
SELECT 
    <-relates_to.in.name as project,
    ->relates_to.out.name as related_papers,
    vector::similarity::cosine(embedding, $query_vec) as score
FROM concept 
WHERE name CONTAINS "1-bit" 
ORDER BY score DESC;
```

### Data Mesh Domains

| Domain | Type | API | Access Pattern |
|--------|------|-----|----------------|
| **Research Notes** | Obsidian | `read_file`, `search` | Interactive exploration |
| **Knowledge Graph** | SurrealDB | `query`, `relate` | Relational inference |
| **arXiv Feed** | Web MCP | `arxiv_search`, `download` | Daily ingestion |
| **Codebase** | Git MCP | `grep`, `read_file` | TDD generation |
| **Benchmarks** | Lemonade | `benchmark_all` | Performance tracking |

---

## Task 4: Dynamic Modularity (Hot-Swapping & Adapters)

### Model Hot-Swapping Protocol

```python
# Swarm Router: Dynamically select model based on task
class SwarmRouter:
    MODEL_POOL = {
        "context": "user.bonsai-8b",      # 256K context, 120 TPS
        "reasoning": "gemma-4-31b-it",     # 91% accuracy
        "coding": "qwen2.5-coder-32b",     # Code-specialized
        "vision": "gemma-4-26b-a4b-it",    # Multi-modal
    }
    
    async def route(self, prompt: str, context_length: int) -> str:
        if context_length > 100_000:
            return self.MODEL_POOL["context"]
        elif "code" in prompt.lower() or "implement" in prompt.lower():
            return self.MODEL_POOL["coding"]
        elif any(img_ext in prompt for img_ext in [".png", ".jpg"]):
            return self.MODEL_POOL["vision"]
        else:
            return self.MODEL_POOL["reasoning"]
    
    async def hot_swap(self, model_id: str) -> float:
        """Unload old, load new. Return swap time (ms)."""
        start = time.time()
        await self.client.post("/v1/unload")
        await self.client.post(f"/v1/models/{model_id}/load")
        return (time.time() - start) * 1000
```

**Expected Swap Time**: 200-500ms (UMA benefits on 128GB)

### LoRA Adapter Injection

```bash
# Base model stays loaded, adapter hot-swapped
lemonade load gemma-4-31b-it --lora research_lora.bin --lora-scale 0.8
lemonade load gemma-4-31b-it --lora coding_lora.bin --lora-scale 1.0
```

**Adapter Strategy**:

| Adapter | Task | Base | Memory |
|---------|------|------|--------|
| Research-LoRA | Paper analysis | Gemma-4-31B | +256MB |
| Coding-LoRA | Python/Go gen | Gemma-4-31B | +256MB |
| Creative-LoRA | Writing | Gemma-4-31B | +256MB |

**Dynamic Loading**:

```python
async def apply_adapter(task_type: str):
    adapters = {
        "research": " adapters/research_gemma31_256mlora.bin",
        "coding": "adapters/coding_gemma31_256mlora.bin",
        "default": None
    }
    lora_path = adapters.get(task_type)
    if lora_path:
        await lemonade_client.load_lora(lora_path, scale=0.8)
```

### Modular Plugin Mesh API

```python
# Mount/unmount data sources dynamically
class DataMeshPlugin:
    async def mount_source(self, source_id: str, mcp_config: dict):
        """Add new data product to mesh."""
        await self.mcp_registry.register(source_id, mcp_config)
        
    async def unmount_source(self, source_id: str):
        """Remove data product."""
        await self.mcp_registry.unregister(source_id)
        
    async def query_mesh(self, query: str, sources: list[str] = None):
        """Query across mounted sources."""
        results = []
        for source in sources or self.active_sources:
            mcp = self.mcp_registry.get(source)
            results.append(await mcp.query(query))
        return self.fusion_layer.merge(results)
```

---

## Task 5: Novel Solution Synthesis (The "Invention" Loop)

### Cross-Pollination Engine

```python
class NovelSynthesizer:
    async def find_gaps(self, project_goals: list[str], recent_papers: list[dict]):
        """Identify knowledge gaps between current work and SOTA."""
        
        prompt = f"""
        PROJECT GOALS:
        {chr(10).join(f"- {g}" for g in project_goals)}
        
        RECENT ARXIV BREAKTHROUGHS:
        {chr(10).join(f"- {p['title']} ({p['date']})" for p in recent_papers[:10])}
        
        TASK: Identify 3 specific gaps where recent SOTA could accelerate project goals.
        Novelty constraint: Solutions must be non-obvious (not direct implementation).
        """
        
        response = await self.llm.generate(
            model="gemma-4-31b-it",
            prompt=prompt,
            temperature=0.8,
            max_tokens=2000
        )
        return self.parse_gaps(response)
```

### Hybrid Architecture Generator

```python
    async def propose_hybrid(self, constraints: dict):
        """Design novel hybrid architectures."""
        
        prompt = f"""
        DESIGN CHALLENGE:
        Create a hybrid architecture combining:
        - PrismML Bonsai (1-bit efficiency)
        - Gemma 4 (attention norms stability)
        - MoE (expert routing)
        
        CONSTRAINTS:
        - Max active params: 4B (inference budget)
        - Context: 256K tokens
        - Target TPS: >60 on Strix Halo
        
        Output format:
        1. Architecture diagram (text)
        2. Novel components (what's new)
        3. Expected metrics (VRAM, TTFT, perplexity)
        4. Implementation sketch (PyTorch pseudo-code)
        """
        
        return await self.llm.generate(prompt=prompt, temperature=0.9)
```

### Simulated Execution

```python
    async def simulate_performance(self, architecture: dict):
        """Simulate without full training."""
        
        # Parameter count estimation
        active_params = architecture["experts"] * architecture["expert_size_m"]
        total_params = architecture["total_experts"] * architecture["expert_size_m"]
        
        # VRAM estimation
        model_vram = total_params * 0.5 / 8  # 1-bit = 0.5 bytes per param
        kv_vram = (architecture["context_length"] * architecture["layers"] * 
                   2 * 2 * 64) / 1e9  # GB
        
        # TPS estimation (empirical from Bonsai benchmarks)
        tps = 85 * (4 / active_params) * 0.7  # Scale with active params
        
        return {
            "active_params_b": active_params,
            "total_params_b": total_params,
            "model_vram_gb": model_vram,
            "kv_vram_gb": kv_vram,
            "total_vram_gb": model_vram + kv_vram + 2,  # +2GB overhead
            "estimated_tps": tps,
            "estimated_ttft_ms": 15 if architecture.get("prompt_cache") else 80,
            "feasible_on_128gb": (model_vram + kv_vram) < 110
        }
```

---

## Task 6: Auto-Research & Self-Upgrade Loops

### Autonomous Research Agent

```python
class AutoResearcher:
    def __init__(self, lemonade_client, obsidian_mcp, surreal_mcp):
        self.llm = lemonade_client
        self.vault = obsidian_mcp
        self.kg = surreal_mcp
        self.keywords = ["BitNet", "Gemma-4", "1-bit LLM", "Mixture of Experts", "KV Cache"]
    
    async def daily_discovery(self):
        """Run at 6 AM daily via cron."""
        for keyword in self.keywords:
            papers = await arxiv_search(keyword, max_results=5, sort_by="submittedDate")
            
            for paper in papers:
                # Check if already in graph
                exists = await self.kg.query(
                    f"SELECT * FROM concept WHERE name = '{paper.title}'"
                )
                if not exists:
                    # Generate summary
                    summary = await self.summarize(paper)
                    
                    # Write to Obsidian
                    note_path = f"Research/ArXiv/{paper.arxiv_id}.md"
                    await self.vault.write_file(note_path, summary)
                    
                    # Add to knowledge graph
                    await self.kg.create_concept(
                        name=paper.title,
                        embedding=await self.embed(summary),
                        source="arxiv",
                        date=paper.published
                    )
                    
                    # Link to existing concepts
                    related = await self.find_related(summary)
                    for rel in related:
                        await self.kg.relate(rel.source, paper.title, "cites")
    
    async def synthesize_hypotheses(self):
        """Generate novel research directions."""
        
        # Query knowledge graph for clusters
        clusters = await self.kg.query("""
            SELECT 
                vector::cluster::kmeans(embedding, 5) as cluster_id,
                count() as size
            FROM concept 
            GROUP BY cluster_id
        """)
        
        for cluster in clusters:
            papers = await self.kg.query(f"""
                SELECT name, summary 
                FROM concept 
                WHERE vector::distance::cosine(embedding, {cluster.centroid}) < 0.3
            """)
            
            hypothesis = await self.generate_hypothesis(papers)
            
            # Write to Obsidian
            await self.vault.write_file(
                f"Research/Hypotheses/{cluster.cluster_id}.md",
                hypothesis
            )
```

### Self-Upgrade Trigger

```python
async def self_upgrade_check():
    """Monitor for model improvements."""
    
    # Check Lemonade registry for new models
    available = await lemonade.list_models()
    current = await get_current_models()
    
    new_models = [m for m in available if m.id not in current]
    
    for model in new_models:
        # Quick benchmark
        benchmark = await quick_benchmark(model.id)
        
        if benchmark.accuracy > current_best.accuracy * 1.05:  # 5% improvement
            # Propose upgrade
            await obsidian.write_file(
                f"Upgrades/{model.id}.md",
                f"New model {model.id} shows {benchmark.accuracy:.1f}% accuracy "
                f"({benchmark.accuracy/current_best.accuracy:.2f}x improvement)\n\n"
                f"Benchmark details: {benchmark.json()}"
            )
```

---

## Task 7: Engineering Protocol (System Prompt)

```python
SYSTEM_PROMPT = """
You are a Senior AI Infrastructure Engineer operating within the Cohezion ecosystem.
Your mandate is Compound Engineering: decompose, execute, review, iterate.

## Protocol

1. COMPOUND ENGINEERING (Deconstruction)
   - Break all tasks into:
     * Atomic operations (single responsibility)
     * Contract interfaces (inputs/outputs)
     * Failure modes (what could go wrong)

2. TDD (Test-Driven Development)
   - Generate tests BEFORE implementation
   - Tests must cover:
     * Happy path
     * Edge cases (null, overflow, race conditions)
     * Performance bounds

3. ADVERSARIAL REVIEW (Self-Critique)
   - SECURITY: "How could this be exploited?"
   - PERFORMANCE: "Where does this OOM or thrash?"
   - MAINTAINABILITY: "How does this fail in 6 months?"

4. IMPLEMENTATION
   - Follow langauge idioms
   - Document intent, not mechanics
   - Include ASI (Actionable Side Information)

## Available Tools

- **Lemonade**: Local LLM inference (http://localhost:13305)
- **Obsidian**: Personal knowledge vault (MCP)
- **SurrealDB**: Knowledge graph (ws://localhost:8000)
- **Data Mesh**: Domain-specific MCPs

## Response Format

```
[DECOMPOSE]
- Atomic steps
- Data contracts

[TESTS]
- test_happy_path()
- test_edge_case()
- test_performance()

[IMPLEMENTATION]
```

[ADVERSARIAL REVIEW]
- Security vectors
- Performance limits
- Failure modes
```

## Constraints

- Max context: 256K tokens
- Model pool: Bonsai-8B (fast), Gemma-4-31B (smart)
- TTFT target: <50ms
- Safety: All code runs in sandbox first
"""
```

---

## Task 8: Agentic Hooks

### Proactive Hooks (Cron / Scheduled)

```python
# crontab entries for autonomous agent

# 6 AM: Daily research discovery
0 6 * * * cd /home/mike-anderson/dev/cohezion && uv run python -m agent.discovery

# 12 PM: Midday graph maintenance (defrag, prune)
0 12 * * * cd /home/mike-anderson/dev/cohezion && uv run python -m agent.maintenance

# 6 PM: Evening synthesis (generate hypotheses)
0 18 * * * cd /home/mike-anderson/dev/cohezion && uv run python -m agent.synthesis

# Weekly: Self-upgrade check (Sundays)
0 9 * * 0 cd /home/mike-anderson/dev/cohezion && uv run python -m agent.upgrade_check
```

### Reactive Hooks (Event-Driven)

```python
class ReactiveHooks:
    
    async def on_code_generation(self, code: str, language: str):
        """Trigger TDD validation."""
        
        # Generate tests
        tests = await self.llm.generate(
            model="qwen2.5-coder-32b",
            prompt=f"Generate pytest tests for:\n```\n{code}\n```",
            temperature=0.2  # Low for deterministic tests
        )
        
        # Execute tests in sandbox
        result = await self.execute_sandbox(tests, code, language)
        
        if result.failed:
            return {"action": "regenerate", "failures": result.errors}
        return {"action": "accept", "coverage": result.coverage}
    
    async def on_domain_detected(self, query: str):
        """Swap to specialized model/adapter."""
        
        domains = {
            "research": ("gemma-4-31b-it", "research_lora.bin"),
            "coding": ("qwen2.5-coder-32b", None),
            "vision": ("gemma-4-26b-a4b-it", None),
        }
        
        detected = self.classify_domain(query)
        model, adapter = domains.get(detected, ("gemma-4-31b-it", None))
        
        # Hot-swap if different from current
        if model != self.current_model:
            await self.router.hot_swap(model)
            if adapter:
                await self.router.load_adapter(adapter)
        
        return {"model": model, "adapter": adapter}
    
    async def on_tps_drop(self, current_tps: float, baseline_tps: float):
        """Adjust batch size if TPS degrades."""
        
        if current_tps < baseline_tps * 0.7:  # 30% degradation
            # Reduce batch size
            new_batch = max(64, self.current_batch // 2)
            await lemonade.update_config(batch-size=new_batch)
            
            return {
                "action": "throttle",
                "old_batch": self.current_batch,
                "new_batch": new_batch,
                "reason": f"TPS dropped to {current_tps:.1f}"
            }
```

---

## Task 9: Framework Hardware Optimization (128GB Ceiling)

### KV Cache Allocation Strategy

```python
def calculate_kv_cache_config(
    model_params: int,      # 30B
    context_length: int,   # 32768
    batch_size: int,        # 1
    precision: str          # "f16" or "bf16"
) -> dict:
    
    # Gemma 4 has 128 layers
    n_layers = 128
    
    # Per-token KV cache size (bytes)
    # Each layer stores K and V vectors
    # dims = 4096 (hidden), heads = 32 for KV
    bytes_per_token = n_layers * 2 * 4096 * 2  # F16 = 2 bytes
    
    # Total KV cache
    kv_cache_bytes = context_length * batch_size * bytes_per_token
    kv_cache_gb = kv_cache_bytes / (1024**3)
    
    return {
        "kv_cache_gb": kv_cache_gb,
        "max_context": context_length,
        "safe_context": int(context_length * 0.8),  # 20% margin
        "total_vram_required": kv_cache_gb + (model_params * 0.5 / 8)  # 1-bit
    }

# Configurations for 128GB system
CONFIGS = {
    "bonsai_256k": calculate_kv_cache_config(8, 262144, 1, "f16"),
    # → 67.1GB KV + 0.5GB model = 67.6GB
    
    "gemma31_64k": calculate_kv_cache_config(30, 65536, 1, "f16"),
    # → 33.6GB KV + 18GB model = 51.6GB
    
    "dual_model": {
        # Run Bonsai (256K context) + Gemma 31B (32K context) concurrently
        "total": 67.6 + 25.8 + 8 + 12,  # +8GB OS + 12GB SurrealDB
        "feasible": True  # Total: 113.4GB < 128GB
    }
}
```

### Precision Sensitivity Matrix

| Model Component | Precision | Reason |
|-----------------|-----------|--------|
| **Gemma 4 Weights** | Q4_K_M | Tradeoff: 4-bit, 0.1% accuracy loss vs 8-bit |
| **Gemma 4 KV Cache** | BF16 | Better stability than F16 for long context |
| **Bonsai Weights** | 1-bit (BitNet) | Native 1-bit architecture |
| **Bonsai KV Cache** | F16 | Simpler, fewer numerical issues |
| **Activations** | F16 | Speed vs precision tradeoff |

### Persistent Swarm Configuration

```python
# models/swarm_config.yaml
swarm:
  concurrent_models: 2
  
  models:
    - id: bonsai-8b-context
      role: context_stretcher
      ctx_size: 262144
      priority: high  # Keep hot
      
    - id: gemma-4-31b-reasoner
      role: reasoning_engine
      ctx_size: 32768
      priority: medium  # Load on demand
      
    - id: gemma-4-26b-moe
      role: tool_use_agent
      ctx_size: 8192
      priority: low  # Hot-swap in
      
  memory_budget:
    total_gb: 128
    reserved_os_gb: 8
    reserved_db_gb: 12
    max_kv_cache_gb: 80
    model_weights_gb: 28  # 18 + 0.4 + hot-swap reserve
```

---

## Task 10: Connectivity, Routing & Mesh Script

```python
# swarm/mesh_orchestrator.py
from typing import Optional
import openai
from surrealdb import Surreal
from dataclasses import dataclass

@dataclass
class MeshContext:
    obsidian_notes: list[str]
    kg_relations: list[dict]
    modularity_flags: dict

class MeshOrchestrator:
    def __init__(self):
        # Lemonade client
        self.llm = openai.OpenAI(
            base_url="http://localhost:13305/api/v1",
            api_key="lemonade"
        )
        
        # SurrealDB connection
        self.db = Surreal("ws://localhost:8000/rpc")
        self.db.signin({"user": "root", "pass": "root"})
        self.db.use("cohezion", "knowledge")
    
    async def query_mesh(self, prompt: str) -> str:
        """Intelligent routing with knowledge synthesis."""
        
        # 1. Check Knowledge Graph for context
        kg_context = await self.query_kg(prompt)
        
        # 2. Check Obsidian vault for personal notes
        vault_context = await self.query_vault(prompt)
        
        # 3. Detect domain for model routing
        target_model = self.route_model(prompt, kg_context)
        
        # 4. Check if hot-swap needed
        if target_model != self.current_model:
            await self.hot_swap_model(target_model)
        
        # 5. Assemble prompt with context
        augmented_prompt = self.assemble_prompt(prompt, kg_context, vault_context)
        
        # 6. Generate with system context
        response = self.llm.chat.completions.create(
            model=target_model,
            messages=[
                {
                    "role": "system",
                    "content": self.get_system_prompt(kg_context)
                },
                {"role": "user", "content": augmented_prompt}
            ],
            temperature=0.7 if "research" in prompt.lower() else 0.3
        )
        
        return response.choices[0].message.content
    
    def route_model(self, prompt: str, kg_context: dict) -> str:
        """Dynamic model selection."""
        
        if len(prompt) > 100_000:
            return "user.bonsai-8b"  # Massive context
        
        if "code" in prompt.lower() or "implement" in prompt.lower():
            return "qwen2.5-coder-32b"
        
        if any(ext in prompt for ext in [".png", ".jpg", "image"]):
            return "gemma-4-26b-a4b-it"
        
        if kg_context.get("novelty_score", 0) > 0.8:
            return "gemma-4-31b-it"  # High reasoning
        
        return "gemma-4-31b-it"  # Default
    
    async def query_kg(self, prompt: str) -> dict:
        """Query SurrealDB for relevant concepts."""
        
        # Embed prompt
        embedding = await self.embed(prompt)
        
        # Vector similarity search
        results = await self.db.query("""
            SELECT 
                name, 
                summary, 
                source,
                vector::similarity::cosine(embedding, $embedding) as score
            FROM concept
            WHERE embedding <-> $embedding < 0.3
            ORDER BY score DESC
            LIMIT 5
        """, {"embedding": embedding})
        
        return {
            "concepts": results,
            "novelty_score": 1.0 - (results[0]["score"] if results else 0.5)
        }
    
    async def query_vault(self, prompt: str) -> list[str]:
        """Query Obsidian vault via MCP."""
        
        # Extract keywords
        keywords = await self.extract_keywords(prompt)
        
        # Search vault
        notes = []
        for keyword in keywords[:3]:
            results = await self.mcp.obsidian.search(keyword)
            notes.extend(results)
        
        # Deduplicate and read
        unique_notes = list({n["path"]: n for n in notes}.values())[:3]
        contents = []
        for note in unique_notes:
            content = await self.mcp.obsidian.read_file(note["path"])
            contents.append(content)
        
        return contents
    
    def assemble_prompt(self, user_prompt: str, kg: dict, vault: list) -> str:
        """Augment user prompt with local context."""
        
        context_parts = []
        
        if kg.get("concepts"):
            context_parts.append("## RELEVANT KNOWLEDGE GRAPH NODES:")
            for c in kg["concepts"][:3]:
                context_parts.append(f"- {c['name']}: {c['summary']}")
        
        if vault:
            context_parts.append("## RELEVANT VAULT NOTES:")
            for note in vault:
                context_parts.append(f"```markdown\n{note[:500]}...\n```")
        
        return f"""
{chr(10).join(context_parts)}

## USER QUERY:
{user_prompt}

Generate a response that synthesizes insights from the provided context.
"""

# Usage
orchestrator = MeshOrchestrator()
response = await orchestrator.query_mesh(
    "Design a 1-bit MoE architecture combining Bonsai efficiency with Gemma 4 stability"
)
```

---

## Task 11: Research & Resources Quick Reference

### MCP Servers

| Server | Repo | Purpose |
|--------|------|---------|
| **SurrealDB** | `github.com/surrealdb/mcp-server-surrealdb` | Knowledge graph queries |
| **Obsidian** | `github.com/coddingtonbear/obsidian-local-rest-api` | Vault file access |
| **Git** | Built-in | Codebase operations |
| **Filesystem** | Built-in | General file I/O |

### Key Papers

1. **The Era of 1-bit LLMs** (2024) - Microsoft Research
2. **Gemma 4 Technical Report** (2025) - Google DeepMind  
3. **Mixture-of-Depths** (2024) - Google Research
4. **SURFER: GUI Automation** (2025) - H Company

### Benchmark Targets (Strix Halo)

| Model | Context | Expected TPS | Expected TTFT |
|-------|---------|--------------|---------------|
| Bonsai-8B | 256K | 85-120 | 12ms |
| Gemma-4-26B | 64K | 35-50 | 45ms |
| Gemma-4-31B | 32K | 22-35 | 80ms |

---

## Execution Checklist

- [ ] Lemonade server running on 13305
- [ ] Bonsai-8B loaded with 256K context
- [ ] Gemma-4-31B loaded with 64K context (hot-swappable)
- [ ] SurrealDB running on 8000
- [ ] Obsidian MCP configured
- [ ] Auto-discovery cron jobs active
- [ ] Mesh orchestrator tested
- [ ] Performance benchmarks recorded

**Target State**: Fully autonomous local AI swarm with 256K context, dynamic model routing, and knowledge graph integration.
