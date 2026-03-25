# Local Model Optimization Strategy — Ollama Context + Fine-Tuning

## System Profile

| Resource | Specification | Implication |
|----------|---------------|-------------|
| CPU | AMD Ryzen AI MAX+ 395 (32 cores) | Parallel inference, large batch |
| RAM | 128GB total, ~96GB available | **96GB for models + context** |
| GPU | gfx1151 (RDNA 3.5, 512MB VRAM) | **No useful GPU acceleration for Ollama** |
| Ollama | v0.18.0 | 41 models available |
| Context Leaders | glm-5: 1M, minimax-m2.7: 204K | Large context models available |

**Key Insight:** 96GB RAM can hold 2-3 large models simultaneously with massive context windows. GPU is NOT useful for Ollama inference here.

---

## Part I: Ollama Context Window Optimization

### Current Model Context Windows

| Model | Native Ctx | In Use? | Notes |
|-------|-----------|---------|-------|
| glm-5:cloud | 1,048,576 | ❌ (cloud API) | 1M context — largest available |
| minimax-m2.7:cloud | 204,800 | ❌ (cloud API) | 204K context |
| deepseek-r1:7b | 131,072 | ✅ (Ollama) | Good for chain-thought |
| qwen2.5-coder:14b-256k | 262,144 | ❌ (Ollama) | Full 256K not utilized |
| qwen2.5-coder:7b | 32,768 | ✅ (Ollama) | Too small for our use case |
| gemma3:4b-256k | 256,000 | ❌ (Ollama) | FP16, not loaded |
| cohezion_v2 | 40,960 | ✅ (Ollama) | Too small for complex reasoning |

### Ollama Context Configuration

Ollama supports `num_ctx` parameter per request, but models have maximum context limits. Key optimization:

```bash
# For models that support larger context, override at request time:
curl -s http://localhost:11434/api/generate -d '{
  "model": "qwen2.5-coder:14b",
  "prompt": "...",
  "options": {
    "num_ctx": 131072,  # Override default (32K) to 128K
    "num_gpu": 0,       # CPU inference (GPU is useless here)
    "num_thread": 16    # Parallel CPU threads
  }
}'
```

### Recommended Ollama Modelfile Configuration

Create optimized Modelfiles for each use case:

#### 1. Long-Context Research Model (qwen2.5-coder:14b)

```modelfile
FROM qwen2.5-coder:14b
PARAMETER num_ctx 131072
PARAMETER num_gpu 0
PARAMETER num_thread 16
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER repeat_penalty 1.05

TEMPLATE """
<|im_start|>system
You are a GPU kernel optimization expert. Analyze the provided kernel code and suggest improvements.
Consider: instruction-level parallelism, memory access patterns, register pressure, wave occupancy.
<|im_end|>
<|im_start|>user
{{ .Prompt }}
<|im_end|>
<|im_start|>assistant
"""
```

#### 2. Chain-Thought Reasoning Model (deepseek-r1:7b)

```modelfile
FROM deepseek-r1:7b
PARAMETER num_ctx 131072
PARAMETER num_gpu 0
PARAMETER num_thread 16
PARAMETER temperature 0.6
PARAMETER top_p 0.95
PARAMETER num_keep 32  # Keep last 32 tokens for thinking budget

TEMPLATE """
<｜begin_of_sentence｜>{{ .Prompt }}<｜end_of_sentence｜>
"""
```

#### 3. Fast Coder Model (qwen2.5-coder:7b)

```modelfile
FROM qwen2.5-coder:7b
PARAMETER num_ctx 32768
PARAMETER num_gpu 0
PARAMETER num_thread 8
PARAMETER temperature 0.8
PARAMETER top_k 40
```

---

## Part II: Context Optimization Techniques

### 1. KV Cache Compression

For long contexts, Ollama uses KV cache which grows linearly. Key optimizations:

```bash
# Enable KV cache compression (if supported)
export OLLAMA_KEEP_KV_CACHE=1
export OLLAMA_KV_CACHE_TYPE=int8  # Quantize KV cache to int8

# For very long contexts (>64K), consider chunked processing
# Break long documents into overlapping chunks, summarize, then combine
```

### 2. Chunked Context Processing

For contexts exceeding available memory:

```python
def chunked_inference(
    model: str,
    prompt: str,
    max_ctx: int,
    chunk_size: int = 32768,
    overlap: int = 512
) -> str:
    """
    Process long prompts by chunking with overlap.
    
    For 131K context with 32K chunk size:
    - Chunk 1: tokens 0-32K
    - Chunk 2: tokens 31.5K-63.5K (512 token overlap)
    - etc.
    
    Each chunk: summarize + extract key points
    Final: combine summaries
    """
    import ollama
    
    chunks = split_with_overlap(prompt, chunk_size, overlap)
    summaries = []
    
    for i, chunk in enumerate(chunks):
        response = ollama.generate(
            model=model,
            prompt=f"Analyze this chunk {i+1}/{len(chunks)}:\n\n{chunk}\n\n"
                   f"Extract key technical details and patterns.",
            options={"num_ctx": max_ctx}
        )
        summaries.append(response['response'])
    
    # Final synthesis
    final = ollama.generate(
        model=model,
        prompt=f"Synthesize these chunk summaries into a coherent analysis:\n\n"
               f"{'\n\n'.join(summaries)}",
        options={"num_ctx": max_ctx}
    )
    return final['response']
```

### 3. Sliding Window Attention

For models that support it (Gemma3, Qwen2.5):

```bash
# Enable sliding window (reduces KV cache memory)
export OLLAMA_SLIDING_WINDOW=4096

# For gemma3:4b, this limits attention to 4K window, 
# reducing memory from O(n²) to O(n)
```

---

## Part III: Fine-Tuning Strategy

### When to Fine-Tune

Fine-tuning is expensive. Consider only when:
1. ✅ Base model lacks domain knowledge (GPU kernel optimization)
2. ✅ You have high-quality training data (successful session outputs)
3. ✅ You have compute budget (GPU fine-tuning or cloud)

**For this machine:** No useful GPU, so fine-tuning would be slow on CPU.

### Alternative: RAG with Embeddings

Instead of fine-tuning, use retrieval-augmented generation:

```python
# Use snowflake-arctic-embed2 or nomic-embed-text for embeddings
# Embed successful kernel patterns, store in vector DB
# Retrieve relevant patterns at inference time

from sentence_transformers import SentenceTransformer
import chromadb

# Embed kernel optimization patterns
embedder = SentenceTransformer('snowflake-arctic-embed2')

patterns = [
    "MFMA instruction fusion for CDNA 3 attention kernel",
    "Split-K adaptation based on K dimension in MoE GEMM",
    "Shape-adaptive tile selection for MXFP4 GEMM",
    "Wave-level online softmax for MLA decode",
    "Persistent kernel mode for MLA on MI355X",
]

# Store in ChromaDB
client = chromadb.Client()
collection = client.create_collection("kernel_patterns")
collection.add(
    embeddings=embedder.encode(patterns),
    documents=patterns,
    ids=[f"pattern_{i}" for i in range(len(patterns))]
)

# Retrieve at inference time
def query_pattern(query: str, top_k: int = 3) -> list[str]:
    results = collection.query(
        query_embeddings=embedder.encode([query]),
        n_results=top_k
    )
    return results['documents'][0]

# Use in prompt
context = query_pattern("How to optimize MLA attention kernel")
prompt = f"Context from successful patterns:\n{context}\n\nQuestion: {user_question}"
```

### Fine-Tuning Data Preparation

If you do decide to fine-tune (cloud GPU or future hardware), prepare data now:

```python
def prepare_kernel_finetune_data(
    session_dirs: list[str],
    output_file: str
) -> list[dict]:
    """
    Extract successful kernel optimization sessions as fine-tuning data.
    
    Format: instruction-tuning format with:
    - system: GPU kernel expertise context
    - user: Problem/question
    - assistant: Successful solution with reasoning
    """
    import json
    from pathlib import Path
    
    training_data = []
    
    for session_dir in session_dirs:
        session_path = Path(session_dir)
        
        # Extract orchestrator plan
        plan_file = session_path / "ORCHESTRATION_PLAN.md"
        if plan_file.exists():
            plan_content = plan_file.read_text()
            
            # Extract key decisions
            decisions_file = session_path / "vault/decisions/20260319_decisions.md"
            decisions = decisions_file.read_text() if decisions_file.exists() else ""
            
            # Extract challengers
            for challenger in session_path.glob("challengers/**/*.py"):
                if "variant" in challenger.name.lower():
                    # Extract the thinking/reasoning from file header
                    content = challenger.read_text()
                    docstring = content.split('"""')[1] if '"""' in content else ""
                    
                    training_data.append({
                        "instruction": f"Analyze this kernel optimization approach:\n{docstring}",
                        "input": f"Problem: {challenger.stem}\n{plan_content[:2000]}",
                        "output": f"Key insight: {decisions[:1000]}\n\nApproach: {docstring}",
                        "category": "kernel_optimization"
                    })
    
    # Deduplicate
    seen = set()
    unique_data = []
    for item in training_data:
        key = item["instruction"][:100]
        if key not in seen:
            seen.add(key)
            unique_data.append(item)
    
    with open(output_file, "w") as f:
        json.dump(unique_data, f, indent=2)
    
    return unique_data
```

### Lightweight Fine-Tuning: LoRA

If you have a cloud GPU later:

```bash
# Use axolotl or unsloth for efficient fine-tuning
# Example: Fine-tune qwen2.5-coder:7b on kernel patterns

# Install unsloth
pip install unsloth

# Fine-tune
from unsloth import FastLanguageModel
import torch

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="qwen2.5-coder:7b",
    max_seq_length=32768,
    dtype=torch.float16,
    load_in_4bit=True,  # 4-bit quantization for memory efficiency
)

model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_alpha=32,
    lora_dropout=0.05,
)

# Train on prepared data
# ...
```

---

## Part IV: Ollama Service Optimization

### Ollama Server Configuration

Create `/etc/systemd/system/ollama.service.d/override.conf`:

```ini
[Service]
Environment="OLLAMA_HOST=0.0.0.0"
Environment="OLLAMA_MODELS=/usr/share/ollama/.ollama/models"
Environment="OLLAMA_KEEP_KV_CACHE=1"
Environment="OLLAMA_MAX_LOADED_MODELS=2"
Environment="OLLAMA_NUM_PARALLEL=2"
Environment="OLLAMA_FLASH_ATTENTION=1"
```

### Memory-Efficient Loading

For 96GB RAM, load 2 models simultaneously:

```bash
# Load two models: one for reasoning, one for coding
ollama pull qwen2.5-coder:14b  # ~9GB
ollama pull deepseek-r1:7b     # ~4.7GB

# Set max loaded models
export OLLAMA_MAX_LOADED_MODELS=2
export OLLAMA_NUM_PARALLEL=1  # One request at a time per model
```

### Context Size Limits Per Model

```python
# Ollama will respect model max context but can be overridden
# Up to the model's compiled limit

CONTEXT_LIMITS = {
    "qwen2.5-coder:14b": 131072,  # 128K safe limit
    "qwen2.5-coder:14b-256k": 262144,  # 256K max
    "deepseek-r1:7b": 131072,  # 128K
    "gemma3:4b-256k": 131072,  # Gemma3 benefits from smaller ctx
    "cohezion_v2": 40960,  # Capped by model
}
```

---

## Part V: Integration with Orchestration

### Local Model as Research Agent

```
┌──────────────────────────────────────────────────────────────────┐
│ HERMES (this agent — cloud reasoning)                            │
│ Role: Strategic planning, orchestration, vault management         │
└──────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
    ┌─────────────────┐ ┌──────────────┐ ┌────────────────┐
    │ Local Ollama    │ │ Local Ollama │ │ popcorn-cli     │
    │ qwen2.5-coder   │ │ deepseek-r1  │ │ MI355X Runner  │
    │ (128K ctx)      │ │ (chain-thought)│ │ (GPU kernels) │
    │ Code generation │ │ Reasoning    │ │ Benchmarking   │
    │ Variant writing │ │ Analysis     │ │ Submission     │
    └─────────────────┘ └──────────────┘ └────────────────┘
```

### Usage in Orchestration Loop

```python
import ollama

def local_research(
    task: str,
    context: str,
    model: str = "qwen2.5-coder:14b"
) -> str:
    """
    Use local Ollama model for research assistance.
    
    - 128K context can hold full kernel code + references
    - CPU inference (no GPU available)
    - Fast enough for iterative development
    """
    response = ollama.generate(
        model=model,
        prompt=f"""Context:
{context}

Task: {task}

Provide a detailed analysis with specific code recommendations.
""",
        options={
            "num_ctx": 131072,
            "num_gpu": 0,  # CPU only
            "temperature": 0.7,
        }
    )
    return response['response']


def chain_thought_reasoning(
    hypothesis: str,
    evidence: str
) -> dict:
    """
    Use deepseek-r1 for chain-thought reasoning.
    
    Think step-by-step through optimization hypotheses.
    """
    response = ollama.generate(
        model="deepseek-r1:7b",
        prompt=f"""Hypothesis: {hypothesis}

Evidence:
{evidence}

Think step by step. Is the hypothesis valid? What evidence supports or refutes it?
What additional experiments would validate?
""",
        options={
            "num_ctx": 131072,
            "temperature": 0.6,
        }
    )
    return {
        "reasoning": response['response'],
        "model": "deepseek-r1:7b",
        "hypothesis": hypothesis
    }
```

---

## Part VI: Immediate Actions

### This Session

- [ ] Create optimized Modelfiles for qwen2.5-coder:14b and deepseek-r1:7b
- [ ] Test Ollama inference with 128K context
- [ ] Verify RAM usage with multiple models loaded
- [ ] Set up chunked context processing for very long prompts
- [ ] Create RAG pipeline with kernel pattern embeddings

### Future (Cloud GPU)

- [ ] Prepare fine-tuning dataset from successful sessions
- [ ] Fine-tune qwen2.5-coder:7b on kernel optimization patterns
- [ ] Use unsloth for memory-efficient LoRA training
- [ ] Evaluate fine-tuned model vs base model on kernel tasks

### Infrastructure

- [ ] Configure Ollama service with optimized environment variables
- [ ] Set up vector DB (ChromaDB) for pattern retrieval
- [ ] Create embedding pipeline for session analysis
- [ ] Monitor RAM usage with multiple models loaded

---

## Summary

| Optimization | Impact | Effort |
|-------------|--------|--------|
| Increase num_ctx to 128K | HIGH — enables full kernel context | LOW |
| Load 2 models simultaneously | HIGH — enables parallel reasoning | LOW |
| Chunked context processing | MEDIUM — enables >128K prompts | MEDIUM |
| RAG with embeddings | HIGH — retrieval vs memorization | MEDIUM |
| LoRA fine-tuning | HIGH — specialized knowledge | HIGH (cloud GPU) |
| Ollama service tuning | MEDIUM — better memory efficiency | LOW |

**Priority:** RAG with embeddings + increased context is the highest-impact, lowest-effort path.
