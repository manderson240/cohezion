# AMD GPU Optimization for Ollama

## System Configuration

This system has an AMD Radeon GPU with gfx1151 architecture (Strix Halo/Radeon 8060S) with 128GB unified memory.

### GPU Architecture: gfx1151

The gfx1151 is AMD's RDNA 3.5 architecture used in Ryzen AI MAX+ (Strix Halo) processors with unified memory.

## Optimized Ollama Settings

Create or edit `~/.ollama/ollama.env`:

```bash
# AMD ROCm Optimization for gfx1151

# === GPU Detection ===
# Ollama 0.18+ has native gfx1151 support
# For older versions, uncomment:
# HSA_OVERRIDE_GFX_VERSION=11.5.1

# === Performance ===
# Flash attention for faster inference
OLLAMA_FLASH_ATTENTION=1

# Keep models loaded (prevents cold starts)
OLLAMA_KEEP_ALIVE=-1

# Single parallel inference for stability
OLLAMA_NUM_PARALLEL=1

# Maximum loaded models (with 128GB RAM)
OLLAMA_MAX_LOADED_MODELS=2

# Queue depth
OLLAMA_MAX_QUEUE=100

# === Memory Management ===
# For unified memory systems, limit context to avoid OOM
# Default context window (can be overridden per request)
OLLAMA_CONTEXT_WINDOW=32768

# === Model Selection Recommendations ===
# gemma4:e4b  - 9.6GB  - Best for general use, 128K context
# gemma4:26b  - 18GB   - Sweet spot for quality/speed, 256K context
# gemma4:31b  - 20GB   - Maximum quality, 256K context
# phi3:mini   - 2.2GB  - Fast responses
```

## Systemd Service Override

Create `/etc/systemd/system/ollama.service.d/override.conf`:

```ini
[Service]
Environment="OLLAMA_FLASH_ATTENTION=1"
Environment="OLLAMA_KEEP_ALIVE=-1"
Environment="HSA_OVERRIDE_GFX_VERSION=11.5.1"
```

Then reload:

```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

## Memory Guidelines for 128GB Unified Memory

With unified memory, GPU shares system RAM. Be careful with context windows:

| Model | Context | VRAM Usage | Recommendation |
|-------|---------|------------|----------------|
| gemma4:e4b (9.6GB) | 128K | ~15GB | Safe |
| gemma4:26b (18GB) | 128K | ~25GB | Safe |
| gemma4:26b (18GB) | 256K | ~35GB | Safe |
| gemma4:31b (20GB) | 128K | ~28GB | Safe |
| gemma4:31b (20GB) | 256K | ~50GB | Monitor system RAM |

**Safe limits**: Keep VRAM usage under ~50% of total RAM to avoid system instability.

## Verification

### Check GPU Detection

```bash
# Should show gfx1151 or ROCm device
OLLAMA_DEBUG=1 ollama run gemma4:e4b "hello" 2>&1 | grep -E "compute|library"
```

### Check ROCm is Working

```bash
# Monitor GPU usage during inference
watch -n 1 'rocm-smi --showuse --showmeminfo vram'
```

## Model Recommendations for This System

### Fast Responses (Quick Tasks)
```bash
ollama run gemma4:e2b    # 7.2GB, fastest
ollama run phi3:mini     # 2.2GB, fastest
```

### Balanced (General Use)
```bash
ollama run gemma4:e4b   # 9.6GB, default
```

### Best Quality (Complex Tasks)
```bash
ollama run gemma4:26b   # 18GB, MoE efficiency
```

### Maximum Quality (Heavy Tasks)
```bash
ollama run gemma4:31b   # 20GB, dense model
```

## Gemma 4 Best Practices

### Sampling Parameters

Use these settings for best results:

```bash
# Temperature
temperature=1.0

# Top-p sampling  
top_p=0.95

# Top-k sampling
top_k=64
```

### Thinking Mode

Enable extended reasoning:

```bash
ollama run gemma4:26b "<|think|>Analyze this problem step by step..."
```

### Context Window

Override context per request:

```bash
ollama run gemma4:26b --option num_ctx=65536 "Long document analysis..."
```

## Benchmark Results

On AMD gfx1151 with 128GB unified memory:

| Model | Quant | Context | Speed | Quality |
|-------|-------|---------|-------|---------|
| gemma4:e2b | Q4_K_M | 128K | ~80 tok/s | Good |
| gemma4:e4b | Q4_K_M | 128K | ~50 tok/s | Better |
| gemma4:26b | Q4_K_M | 256K | ~40 tok/s | Best* |
| gemma4:31b | Q4_K_M | 256K | ~30 tok/s | Best |

*26B MoE has 4B active parameters per token, making it nearly as fast as e4b while delivering better quality.

## Troubleshooting

### GPU Not Detected

```bash
# Check ROCm sees the GPU
rocm-smi --showid

# Should show: GPU[0]: AMD Radeon Graphics (gfx1151)
```

### Out of Memory

```bash
# Reduce context window
ollama run gemma4:26b --option num_ctx=16384 "..."

# Or use smaller model
ollama run gemma4:e4b "..."
```

### Slow Inference

```bash
# Ensure flash attention is enabled
echo $OLLAMA_FLASH_ATTENTION  # Should be 1

# Check model is loaded
ollama ps  # Should show model
```

### System Instability

If system becomes unstable with large context:

```bash
# Reduce OLLAMA_MAX_LOADED_MODELS
export OLLAMA_MAX_LOADED_MODELS=1

# Limit context
ollama run gemma4:26b --option num_ctx=32768 "..."
```

## Additional Resources

- [Gemma 4 Model Card](https://ollama.com/library/gemma4)
- [AMD ROCm Documentation](https://rocm.docs.amd.com/)
- [Ollama GPU Guide](https://github.com/ollama/ollama/blob/main/docs/gpu.md)
- [Claw-Code User Guide](../docs/CLAW_CODE_USER_GUIDE.md)