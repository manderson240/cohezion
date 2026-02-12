---
title: "Ollama Context Management - Model Wrangler Extension"
date: 2026-02-09
status: proposed
tags: [decision, ollama, context-management, model-wrangler]

decision_reasoning:
  chosen_option: "Extend Model Wrangler to handle Ollama-specific context management (loading, chunking, memory)"
  rationale: "Ollama models require dynamic context window management; consolidating into Model Wrangler prevents scattered optimization scripts"
  confidence_score: 0.88
  alternatives_rejected:
    - "Scattered Ollama optimization scripts (not maintainable, duplicated logic)"
    - "Ignore context management (leads to truncation, OOM errors)"
  reasoning_chain:
    - "Observed Ollama model loading times (5-30s) causing timeouts"
    - "Identified context window mismatches (2K-128K across models)"
    - "Realized memory pressure from multiple loaded models"
    - "Decided to consolidate into Model Wrangler: pre-loading, chunking, LRU cache"

metrics:
  estimated_cost: 0.0  # Infrastructure tuning only
  estimated_time_hours: 12.0  # Context management implementation
  actual_cost: 0.0  # All local
  actual_time_hours: 0.0  # Not yet implemented
  tokens_used: 0  # Pending implementation
  cost_per_lesson: 0.0
  lessons_generated: []
---

# Ollama Context Management Strategy

**Problem**: Ollama models need dynamic context window management, loading optimization, and performance tuning
**Solution**: Model Wrangler handles Ollama-specific optimizations OR collaborates with Ollama Specialist

---

## Ollama-Specific Challenges

### 1. Model Loading Time
- **Issue**: First request loads model into RAM (5-30 seconds)
- **Impact**: Timeouts, poor UX for first query
- **Solution**: Pre-load frequently used models, keep-alive configuration

### 2. Context Window Management
- **Issue**: Models have different context limits (2K-128K tokens)
- **Impact**: Long papers get truncated, analysis incomplete
- **Solution**: Chunking strategy, context rotation, model selection by task

### 3. Memory Pressure
- **Issue**: Multiple models loaded = high RAM usage
- **Impact**: System slowdown, OOM errors
- **Solution**: Dynamic unloading, LRU cache, model swapping

### 4. Concurrent Requests
- **Issue**: Ollama processes one request at a time per model
- **Impact**: Queue buildup, slow batch processing
- **Solution**: Multiple model instances, request batching

---

## Model Wrangler Responsibilities (Extended)

### Core (Already Defined)
- Daily monitoring, benchmarking, swapping, fine-tuning

### Ollama-Specific (NEW)

#### **1. Pre-Loading Strategy**
```bash
# Keep critical models always loaded
ollama run qwen3:8b --keep-alive 60m &  # Gap analysis (60 min keep-alive)
ollama run nomic-embed-text --keep-alive forever &  # Embeddings (always loaded)
```

**Config**: `/home/mike-anderson/.ollama/preload.yaml`
```yaml
preload_models:
  - name: qwen3:8b
    keep_alive: 60m
    purpose: gap_analysis
    priority: high

  - name: nomic-embed-text
    keep_alive: forever
    purpose: embeddings
    priority: critical

  - name: deepseek-r1:7b
    keep_alive: 30m
    purpose: reasoning_tasks
    priority: medium
```

#### **2. Context Window Management**
```python
class OllamaContextManager:
    """Manage context windows for different Ollama models."""

    MODEL_LIMITS = {
        "qwen3:8b": 8192,
        "deepseek-r1:7b": 32768,
        "phi4-256k:latest": 262144,  # 256K context!
    }

    def chunk_paper(self, paper: str, model: str) -> list[str]:
        """Chunk paper to fit model context window."""
        limit = self.MODEL_LIMITS.get(model, 2048)
        # Reserve 20% for prompt + output
        usable_context = int(limit * 0.8)

        # Simple chunking (production would use semantic chunking)
        chunks = []
        words = paper.split()
        chunk_size = usable_context // 4  # ~4 tokens per word

        for i in range(0, len(words), chunk_size):
            chunks.append(" ".join(words[i:i + chunk_size]))

        return chunks

    def select_model_for_content(self, content_length: int) -> str:
        """Select best model based on content length."""
        if content_length > 200000:  # Very long
            return "phi4-256k:latest"  # Use 256K context model
        elif content_length > 30000:  # Long
            return "deepseek-r1:7b"  # Use 32K context model
        else:  # Normal
            return "qwen3:8b"  # Use fast 8K model
```

#### **3. Memory Management**
```python
class OllamaMemoryManager:
    """Monitor and manage Ollama RAM usage."""

    def get_loaded_models(self) -> list[dict]:
        """Check which models are currently loaded."""
        response = httpx.get("http://localhost:11434/api/ps")
        return response.json()["models"]

    def unload_least_used(self):
        """Unload least recently used model if RAM > 80%."""
        import psutil

        if psutil.virtual_memory().percent > 80:
            loaded = self.get_loaded_models()
            if not loaded:
                return

            # Sort by last used time
            lru_model = min(loaded, key=lambda m: m.get("until", 0))

            # Unload via API
            httpx.post(
                "http://localhost:11434/api/stop",
                json={"name": lru_model["name"]}
            )
            print(f"🗑️  Unloaded {lru_model['name']} (RAM cleanup)")

    def optimize_model_mix(self):
        """Keep optimal set of models loaded."""
        # Always keep embeddings (small, frequently used)
        # Rotate analysis models based on usage
        # Unload large models (70B+) when not active
        pass
```

#### **4. Request Batching**
```python
class OllamaBatchProcessor:
    """Batch requests to Ollama for efficiency."""

    def batch_gap_analysis(self, papers: list[str], batch_size: int = 5):
        """Process papers in batches to avoid queue buildup."""
        results = []

        for i in range(0, len(papers), batch_size):
            batch = papers[i:i + batch_size]

            # Combine into single prompt
            combined_prompt = f"""Analyze these {len(batch)} papers for gaps:

{"\n\n".join([f"Paper {j+1}: {p[:500]}" for j, p in enumerate(batch)])}

Output JSON array with {len(batch)} gap analyses."""

            # Single API call for batch
            response = httpx.post(
                "http://localhost:11434/api/generate",
                json={"model": "qwen3:8b", "prompt": combined_prompt},
                timeout=120.0
            )

            results.extend(parse_batch_response(response.json()))

        return results
```

---

## Alternative: Ollama Specialist Agent

**If complexity grows, spawn dedicated specialist:**

### **Ollama Specialist** (Agent #7)
- **Responsibility**: Ollama-specific optimization, context management, performance tuning
- **Collaborates with**: Model Wrangler (selects models), AI Features Specialist (uses optimized Ollama)

**Division of Labor**:

| Task | Model Wrangler | Ollama Specialist |
|------|----------------|-------------------|
| **Monitor new models** | ✅ Daily digest | Uses recommendations |
| **Benchmark models** | ✅ Run benchmarks | Provides Ollama config |
| **Context management** | - | ✅ Chunking, window optimization |
| **Memory management** | - | ✅ Loading/unloading, RAM monitoring |
| **Request batching** | - | ✅ Batch processing logic |
| **Model selection** | ✅ Choose model | ✅ Choose for context length |

**When to spawn Ollama Specialist**:
- If Ollama issues cause >3 failures per week
- If context management becomes complex (multi-turn conversations, long papers)
- If performance tuning needed (GPU acceleration, quantization, etc.)

**When NOT needed**:
- Simple use cases (single-shot queries)
- Model Wrangler handles 90% of cases
- Context windows are sufficient

---

## Immediate Fixes for Timeout Issue

### Fix 1: Increase Timeout
```python
# Current (too short):
timeout=60.0

# Better:
timeout=180.0  # 3 minutes for first load
```

### Fix 2: Pre-Load Model
```bash
# Before running analysis:
ollama run qwen3:8b "test" --keep-alive 60m

# Now model is loaded, future requests fast
```

### Fix 3: Use Faster Model
```python
# Instead of qwen3:8b (5.2 GB):
model = "phi3:mini"  # 2.2 GB, loads faster

# Or use already-loaded:
model = "nomic-embed-text"  # Already in RAM (from `ollama ps`)
```

### Fix 4: Streaming Response
```python
# Instead of waiting for full response:
response = httpx.post(
    "http://localhost:11434/api/generate",
    json={"model": "qwen3:8b", "prompt": prompt, "stream": True}
)

# Process tokens as they arrive (better UX)
for line in response.iter_lines():
    print(line)
```

---

## Decision: Model Wrangler vs Ollama Specialist

### **Start with: Extended Model Wrangler** (Recommended)
- Add Ollama context management to Model Wrangler role
- Implement pre-loading, timeout handling, basic memory management
- ~20% more complexity for Model Wrangler

### **Spawn Ollama Specialist if**:
- Performance issues persist after basic optimizations
- Need GPU acceleration, quantization, advanced tuning
- Multi-user scenarios (concurrent requests, queue management)

**Current assessment**: Extended Model Wrangler sufficient for COHEZION use case

---

## Immediate Actions (Next 5 Minutes)

```bash
# 1. Pre-load qwen3:8b with long keep-alive
ollama run qwen3:8b "Ready for analysis" --keep-alive 60m

# 2. Re-run gap analysis (should work now, model loaded)
python /tmp/gap_analysis_poc.py

# 3. If still timeout, use phi3:mini (faster):
sed -i 's/qwen3:8b/phi3:mini/g' /tmp/gap_analysis_poc.py
python /tmp/gap_analysis_poc.py
```

---

**Status**: Ollama context management strategy defined
**Next**: Extend Model Wrangler role OR spawn Ollama Specialist (TBD based on needs)
**Related**: [[2026-02-09-model-wrangler-strategy]], [[2026-02-09-12d-graph-refined-plan]]

## Related
**Domains**: ai-ml, data, performance
