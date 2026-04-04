# Ollama Context Window Settings

> **Research Summary**: Ollama `num_ctx` configuration for Gemma 4 models

## Overview

The `num_ctx` parameter controls the maximum context window (tokens) for a model. This is critical for:
- Long documents and code analysis
- Multi-turn conversations
- RAG applications
- Memory management on unified memory systems

## Context Window by Model

### Native Context Limits

| Model | Native Context | Size | Architecture |
|-------|---------------|------|--------------|
| `gemma4:e2b` | 128K tokens | 7.2GB | Edge, multimodal |
| `gemma4:e4b` | 128K tokens | 9.6GB | Edge, multimodal |
| `gemma4:26b` | 256K tokens | 18GB | MoE (4B active) |
| `gemma4:31b` | 256K tokens | 20GB | Dense |
| `gemma4:31b-cloud` | 256K tokens | - | Cloud (no local memory) |
| `phi3:mini` | 128K tokens | 2.2GB | Small model |

### Recommended Context for Unified Memory (128GB)

| Model | Safe Context | Reason |
|-------|-------------|--------|
| `gemma4:e2b` | 128K | Edge models are memory efficient |
| `gemma4:e4b` | 64K-128K | Edge models are memory efficient |
| `gemma4:26b` | 32K | MoE efficiency, but dense parameters matter |
| `gemma4:31b` | 32K | Dense model needs careful limits |
| `gemma4:31b-cloud` | 256K | No local memory! Use for complex tasks |
| `phi3:mini` | 128K | Small enough for full context |

## Configuration Methods

### 1. API Request Level (Highest Priority)

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "gemma4:e4b",
  "prompt": "Hello",
  "options": {
    "num_ctx": 65536
  }
}'
```

### 2. Chat API Level

```bash
curl http://localhost:11434/api/chat -d '{
  "model": "gemma4:e4b",
  "messages": [{"role": "user", "content": "Hello"}],
  "options": {
    "num_ctx": 65536
  }
}'
```

### 3. Modelfile Level (Persistent)

```modelfile
FROM gemma4:e4b
PARAMETER num_ctx 131072
```

Create with: `ollama create my-model -f Modelfile`

### 4. Environment Variable (Server Default)

```bash
OLLAMA_CONTEXT_LENGTH=65536 ollama serve
```

Or in systemd:
```ini
[Service]
Environment="OLLAMA_CONTEXT_LENGTH=65536"
```

### 5. CLI Runtime Parameter

```bash
ollama run gemma4:e4b
/set parameter num_ctx 65536
```

## Priority Hierarchy

1. **API Request** (`options.num_ctx`) - Overrides everything
2. **Modelfile** (`PARAMETER num_ctx`) - Persistent for custom model
3. **Environment** (`OLLAMA_CONTEXT_LENGTH`) - Server-wide default
4. **Ollama Default** - Automatic based on VRAM

## Default Context by VRAM

| VRAM | Default Context | ~Words |
|------|-----------------|--------|
| < 24GB | 4K tokens | ~3K words |
| 24-48GB | 32K tokens | ~24K words |
| ≥ 48GB | 256K tokens | ~192K words |

## Memory Calculation (Approximate)

```
VRAM ≈ Model Size + (Context Length × Hidden Dim × Layers × 2 bytes)
```

For Gemma 4 E4B with 128K context:
- Model: ~9.6GB
- KV Cache: varies by context
- Compute graph: ~2GB overhead

### With Flash Attention

```bash
OLLAMA_FLASH_ATTENTION=1
```

- Uses less memory for attention
- Better long-context performance
- **Recommended for Gemma 4 models**

## Known Issue: Gemma 4 GPU/CPU Split (GitHub #15237)

### Problem
Gemma 4 models show "100% GPU" in `ollama ps` but **run significant computation on CPU**.

Evidence:
```
model weights device=CUDA0 size="18.4 GiB"
model weights device=CPU size="1.2 GiB"    # Vision encoder NOT offloaded!
compute graph device=CPU size="2.3 GiB"
```

### Impact
- Slower than expected inference
- CPU competes for RAM on unified memory systems
- Vision processing especially affected

### Workaround
1. Enable Flash Attention: `OLLAMA_FLASH_ATTENTION=1`
2. Use cloud model for vision tasks: `gemma4:31b-cloud`
3. For text-only: Works better

### Status
- **Open bug**: [GitHub Issue #15237](https://github.com/ollama/ollama/issues/15237)
- Affects all Gemma 4 variants
- Vision encoder not properly offloaded to GPU

## Best Practices for Framework Desktop (128GB Unified Memory)

### 1. Use Cloud Model for Complex Tasks

```bash
# For large codebases or long documents
ollama run gemma4:31b-cloud
```

- Zero local memory usage
- Full 256K context
- Runs on ollama.com infrastructure

### 2. Set Context Explicitly

```bash
# In proxy request or directly
OLLAMA_CONTEXT_LENGTH=32768 ollama run gemma4:26b
```

### 3. Monitor Memory

```bash
# Check current model status
ollama ps

# Output shows:
# NAME           SIZE     PROCESSOR    CONTEXT
# gemma4:26b    18 GB    100% GPU      32768
```

### 4. Enable Flash Attention

```bash
# In ~/.ollama/ollama.env or system service
OLLAMA_FLASH_ATTENTION=1
```

### 5. Set Model Limit

```bash
# Prevent multiple models from loading
OLLAMA_MAX_LOADED_MODELS=1
```

## Context and Model Selection Guide

| Use Case | Model | Context | Memory |
|----------|-------|---------|--------|
| Quick queries | `phi3:mini` | 64K | ~2-4GB |
| Balanced quality/speed | `gemma4:e4b` | 64K | ~12-16GB |
| Complex reasoning | `gemma4:26b` | 32K | ~22-28GB |
| Maximum local quality | `gemma4:31b` | 32K | ~24-32GB |
| Long documents/code | `gemma4:31b-cloud` | 256K | ~0GB (cloud) |

## Troubleshooting

### Out of Memory

```
Symptom: Model fails to load or system freezes
Solutions:
1. Reduce num_ctx
2. Use smaller model
3. Use cloud model
```

### Context Length Exceeded

```
Symptom: API error about context length
Solutions:
1. Increase num_ctx
2. Enable truncation: "truncate": true
3. Enable shifting: "shift": true
```

### Slow Generation

```
Symptom: Responses very slow
Solutions:
1. Check GPU offload: ollama ps (should show 100% GPU)
2. Note: Gemma 4 has known CPU usage bug
3. Use smaller context if not needed
```

## References

- [Ollama Model Library: Gemma 4](https://ollama.com/library/gemma4)
- [Ollama Context and Memory](https://www.mintlify.com/ollama/ollama/context-and-memory)
- [GitHub Issue #15237: Gemma 4 GPU/CPU Split](https://github.com/ollama/ollama/issues/15237)