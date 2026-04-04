# Claw-Code Complete User Guide with Ollama

## System Overview

This guide is optimized for **AMD Radeon gfx1151 (Strix Halo)** with **128GB unified memory**.

### Key Constraint: Unified Memory

Your system uses unified memory where GPU and CPU share RAM. This means:
- GPU doesn't have dedicated VRAM
- System RAM is used for both GPU and CPU
- Running out of memory **crashes the entire system** (not just the app)
- **Memory management is critical**

### Memory Budget (128GB Total)

| Allocation | Amount | Purpose |
|------------|--------|---------|
| System Reserved | ~60GB | Desktop, browser, other apps |
| Available for Models | ~60GB | Safe zone for LLM inference |
| **Max Single Model** | ~40GB | Largest safe model (gemma4:31b) |

## Quick Start

### 1. Build Claw-Code

```bash
cd claw-code
cargo build --release
```

### 2. Start the Safe Proxy

```bash
# Start with safe default settings
./scripts/start-ollama-proxy.sh

# Or manually with safety checks:
./scripts/safe-ollama.sh check  # Check memory before starting
OLLAMA_MAX_LOADED_MODELS=1 ./scripts/start-ollama-proxy.sh
```

### 3. Run Claw-Code

```bash
cd claw-code
ANTHROPIC_BASE_URL=http://localhost:8082 ANTHROPIC_API_KEY=unused \
  ./target/release/claw --model haiku prompt "your question"
```

## Safe Model Selection

### Recommended Models for 128GB Unified Memory

| Model | Size | Max Safe Context | Use Case |
|-------|------|------------------|----------|
| `phi3:mini` | 2.2GB | 128K | Fast responses, quick tasks |
| `gemma4:e2b` | 7.2GB | 128K | Edge workloads, long context |
| `gemma4:e4b` | 9.6GB | 64K | **Default choice, balanced** |
| `gemma4:26b` | 18GB | 32K | High quality, MoE efficiency |
| `gemma4:31b` | 20GB | 32K | Maximum quality |

### Model Alias Mapping

```bash
# These all work:
--model haiku      # -> gemma4:e4b (default)
--model sonnet    # -> gemma4:26b
--model opus      # -> gemma4:31b
--model fast      # -> phi3:mini
```

## Memory-Safe Usage Patterns

### Pattern 1: Single Model Workflow

```bash
# Start proxy
./scripts/start-ollama-proxy.sh &

# Use one model at a time
ANTHROPIC_BASE_URL=http://localhost:8082 ANTHROPIC_API_KEY=unused \
  ./target/release/claw --model haiku prompt "task 1"

# Done - model stays loaded (30 min timeout)
```

### Pattern 2: Model Switching

```bash
# Check memory before switching
./scripts/safe-ollama.sh check

# Stop current model
ollama stop gemma4:e4b

# Load new model
ollama run gemma4:26b "test"  # Warm up
# Now use with claw-code
```

### Pattern 3: Large Context (CAREFUL!)

```bash
# Only use large context with small models
# phi3:mini can handle 128K context safely
ollama run phi3:mini --option num_ctx=131072 "long document analysis"

# gemma4:e4b can handle up to 64K safely
ollama run gemma4:e4b --option num_ctx=65536 "medium document"

# gemma4:26b - STAY UNDER 32K
ollama run gemma4:26b --option num_ctx=32768 "task"

# NEVER run gemma4:31b with >32K context - WILL CRASH SYSTEM
```

## OOM Prevention Checklist

Before running large tasks, verify:

```bash
# 1. Check available RAM
free -h | awk '/^Mem:/{print "Available: " $7}'

# 2. Check loaded models
ollama ps

# 3. Stop unused models
ollama stop <model-name>

# 4. Verify GPU memory (if applicable)
rocm-smi --showmeminfo vram
```

### Danger Zone Warning

```
┌─────────────────────────────────────────────────────────────┐
│ ⚠️  DANGER: DO NOT DO THESE (will crash your system)  ⚠️   │
├─────────────────────────────────────────────────────────────┤
│ ❌ Load multiple large models simultaneously                 │
│ ❌ Run gemma4:31b with 256K context                         │
│ ❌ Run context >32K with gemma4:26b or 31b                   │
│ ❌ Ignore memory warnings                                    │
│ ❌ Run without checking ollama ps first                     │
└─────────────────────────────────────────────────────────────┘
```

## Context Window Guidelines

| Model | Safe Context | Maximum Context | Memory Impact |
|-------|--------------|-----------------|----------------|
| `phi3:mini` | 32K | 128K | +8GB at max |
| `gemma4:e2b` | 32K | 128K | +8GB at max |
| `gemma4:e4b` | 32K | 128K* | +15GB at max |
| `gemma4:26b` | 16K | 256K | +17GB at max |
| `gemma4:31b` | 16K | 256K | +30GB at max |

\* Use 64K or less for safety with gemma4:e4b

## Troubleshooting

### System Becomes Slow

```bash
# Check if model is loaded
ollama ps

# Stop to free memory
ollama stop gemma4:26b

# Or restart Ollama service
sudo systemctl restart ollama
```

### OOM Crash Occurred

```bash
# 1. Reboot if system is unstable
sudo reboot

# 2. On restart, clear Ollama cache
rm -rf ~/.ollama/models/.cache/*

# 3. Use smaller model or context next time
ollama run phi3:mini  # Safest option
```

### GPU Not Detected

```bash
# Verify ROCm
rocm-smi --showid

# Should show: GPU[0]: gfx1151

# If not, check environment
echo $HSA_OVERRIDE_GFX_VERSION
# Should be: 11.5.1 (for older Ollama) or unset (for 0.18+)
```

## Configuration Files

| File | Purpose |
|------|---------|
| `~/.ollama/ollama.env` | Ollama environment variables |
| `scripts/ollama-proxy.py` | Anthropic-to-Ollama proxy |
| `scripts/safe-ollama.sh` | Memory-safe helpers |
| `claw-code/.claude/settings.json` | Claw-code MCP config |
| `claw-code/.claude.json` | MCP server definitions |

## Performance Tips

### Use MoE for Efficiency

```bash
# gemma4:26b is MoE - only 4B active params per token
# Delivers 26B quality at near-e4b speed
--model sonnet  # gemma4:26b - best bang for buck
```

### Keep Models Loaded

```bash
# Models stay loaded for 30 minutes by default
# Reusing same model is instant
ollama run gemma4:e4b  # First call: 10 seconds to load
ollama run gemma4:e4b  # Subsequent calls: instant
```

### Batch Requests

```bash
# Process multiple prompts efficiently
# Stay with same model to avoid reload
for file in *.txt; do
  ANTHROPIC_BASE_URL=http://localhost:8082 \
  ./target/release/claw --model haiku \
    prompt "$(cat $file)" > "output_$file"
done
```

## Emergency Recovery

If system crashes due to OOM:

```bash
# 1. Reboot
sudo reboot

# 2. On restart, set conservative limits
export OLLAMA_MAX_LOADED_MODELS=1
export OLLAMA_CONTEXT_WINDOW=16384

# 3. Use smallest safe model
ollama run phi3:mini "recovery test"

# 4. Gradually increase limits if stable
```

## Additional Resources

- [AMD GPU Optimization Guide](./AMD_GPU_OPTIMIZATION.md)
- [Gemma 4 Model Card](https://ollama.com/library/gemma4)
- [Ollama GitHub Issues](https://github.com/ollama/ollama/issues)