# Claw-Code + Ollama Integration Guide

## System: Framework Desktop with AMD gfx1151 (128GB Unified Memory)

### Quick Start

```bash
# 1. Start the proxy (in background)
./scripts/start-ollama-proxy.sh

# 2. Test the connection
./scripts/test-ollama-proxy.sh

# 3. Use with claw-code
cd claw-code
ANTHROPIC_BASE_URL=http://localhost:8082 ANTHROPIC_API_KEY=unused \
  ./target/release/claw --model haiku prompt "your question"
```

## Model Selection

### Cloud Models (Recommended for complex tasks - No OOM risk)

| Model | Command | Description |
|-------|---------|-------------|
| `gemma4:31b-cloud` | `--model cloud` | Best quality, remote inference |
| `minimax-m2.7:cloud` | `--model minimax-cloud` | Alternative cloud model |

**Benefits:**
- Zero local memory usage
- Faster inference (cloud GPUs)
- 256K context available
- No OOM risk

**Trade-off:**
- Requires internet
- Data goes to ollama.com

### Local Models (Memory-safe configuration)

| Model | Size | Max Safe Context | Speed | Quality |
|-------|------|-----------------|-------|---------|
| `phi3:mini` | 2.2GB | 128K | Fastest | Good |
| `gemma4:e2b` | 7.2GB | 128K | Fast | Better |
| `gemma4:e4b` | 9.6GB | 64K | Balanced | Best* |

*`gemma4:26b` (MoE) and `gemma4:31b` available but use more memory

## Memory Safety Rules

### Critical for 128GB Unified Memory

1. **Only load ONE large model at a time**
   ```bash
   # Before loading a new model, stop old one
   ollama stop gemma4:e4b
   ollama run gemma4:26b
   ```

2. **Context limits by model size:**
   - `phi3:mini` (2.2GB): Up to 128K context ✅
   - `gemma4:e4b` (9.6GB): Up to 64K context ✅
   - `gemma4:26b` (18GB): Maximum 32K context ⚠️
   - `gemma4:31b` (20GB): Maximum 32K context ⚠️

3. **Never exceed limits:**
   ```bash
   # SAFE: Small context
   ollama run gemma4:31b "short query"
   
   # DANGEROUS: Large context with big model
   ollama run gemma4:31b --option num_ctx=131072 "long query"  # WILL CRASH SYSTEM
   ```

4. **Check memory before large tasks:**
   ```bash
   ./scripts/safe-ollama.sh check
   ```

## Configuration Files

| File | Purpose |
|------|---------|
| `~/.ollama/ollama.env` | Ollama memory settings |
| `scripts/ollama-proxy.py` | Anthropic-to-Ollama translator |
| `scripts/start-ollama-proxy.sh` | Safe startup script |
| `scripts/safe-ollama.sh` | Memory management helper |
| `docs/AMD_GPU_OPTIMIZATION.md` | AMD GPU optimization guide |

## Recommended Workflow

### For Development (Fast Responses)

```bash
# Use smallest local model or cloud
./target/release/claw --model fast    # phi3:mini (fastest local)
./target/release/claw --model cloud   # gemma4:31b-cloud (fast cloud)
```

### For Complex Tasks (High Quality)

```bash
# Cloud model - no memory concerns
./target/release/claw --model cloud "analyze this codebase..."
```

### For Long Context (Documents)

```bash
# Use phi3:mini with full context
./target/release/claw --model fast --option context=65536 "analyze this long document..."
```

## Troubleshooting

### OOM Crash Recovery

If system becomes unstable or crashes:

```bash
# 1. Reboot if necessary
sudo reboot

# 2. Clear Ollama cache
rm -rf ~/.ollama/models/.cache/*

# 3. Use smaller model
ollama run phi3:mini  # Safest option

# 4. Conservative settings
export OLLAMA_MAX_LOADED_MODELS=1
export OLLAMA_CONTEXT_WINDOW=16384
```

### Proxy Not Responding

```bash
# Kill and restart
pkill -f "ollama-proxy"
./scripts/start-ollama-proxy.sh

# Check status
curl http://localhost:8082/v1/models -X POST -d '{}'
```

### Model Taking Too Long

```bash
# Check what's loaded
ollama ps

# Stop and use smaller model
ollama stop gemma4:31b
ollama run phi3:mini
```

## Performance Comparison

| Model | Type | Speed (tok/s) | Memory | Context | Use Case |
|-------|------|----------------|--------|---------|----------|
| `phi3:mini` | Local | ~50 | 2.2GB | 128K | Quick tasks, long docs |
| `gemma4:e4b` | Local | ~30 | 9.6GB | 64K | Balanced work |
| `gemma4:26b` | Local | ~20 | 18GB | 32K | Quality work |
| `gemma4:31b` | Local | ~15 | 20GB | 32K | Max quality |
| `gemma4:31b-cloud` | Cloud | ~40 | 0GB | 256K | **Recommended** |

## Next Steps

1. Test the proxy: `./scripts/test-ollama-proxy.sh`
2. Try cloud model for best results: `--model cloud`
3. For local inference, stick with `--model haiku` or `--model fast`
4. Monitor memory: `watch -n 5 free -h`