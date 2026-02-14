# Troubleshooting Guide

Comprehensive troubleshooting for common issues with Kyutai MCP Server and Obsidian Plugin.

## Table of Contents

1. [Server Issues](#server-issues)
2. [Plugin Issues](#plugin-issues)
3. [Model & Inference Issues](#model--inference-issues)
4. [Audio Issues](#audio-issues)
5. [Performance Issues](#performance-issues)
6. [GPU Issues](#gpu-issues)
7. [Network Issues](#network-issues)
8. [Diagnostic Checklist](#diagnostic-checklist)

---

## Server Issues

### Server Won't Start

**Symptoms:**
- `Address already in use` error
- `ModuleNotFoundError` when starting
- Server crashes immediately

**Diagnostic Steps:**

1. **Check if port is in use:**
   ```bash
   # macOS/Linux
   lsof -i :8000

   # Windows
   netstat -ano | findstr :8000
   ```

2. **Check Python environment:**
   ```bash
   python --version  # Should be 3.9+
   pip list | grep -E "fastapi|uvicorn|torch"
   ```

3. **Check dependencies:**
   ```bash
   pip install -r requirements.txt --force-reinstall
   ```

**Solutions:**

**If port is in use:**
```bash
# Kill process
kill <PID>  # macOS/Linux
taskkill /PID <PID> /F  # Windows

# Or use different port
python -m kyutai_mcp.server --port 8001
```

**If missing dependencies:**
```bash
# Reinstall all
pip install --upgrade pip
pip install -r requirements.txt -v

# Check installation
python -c "import fastapi, torch, transformers; print('OK')"
```

**If virtual environment issues:**
```bash
# Recreate venv
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

### Server Crashes Unexpectedly

**Symptoms:**
- Server exits with no error message
- Segmentation fault
- Out of memory errors

**Diagnostic Steps:**

1. **Check logs:**
   ```bash
   # Enable debug logging
   MCP_LOG_LEVEL=DEBUG python -m kyutai_mcp.server 2>&1 | tee server.log

   # Check for crash messages
   tail -100 server.log
   ```

2. **Monitor system resources:**
   ```bash
   # macOS/Linux
   watch 'free -h; nvidia-smi'

   # Windows
   Get-Process | Sort-Object WorkingSet | Select-Object Name, WorkingSet -Last 10
   ```

3. **Test with simple inference:**
   ```python
   python
   >>> from kyutai_mcp import MCPServer
   >>> server = MCPServer()
   >>> server.preload_models()
   # If it crashes here, it's a model issue
   ```

**Solutions:**

**If out of memory:**
```bash
# Reduce GPU memory usage
USE_GPU=true
GPU_MEMORY_FRACTION=0.5  # Use 50% instead of 100%
QUANTIZE_MODELS=true    # Use quantized (smaller) models

# Or disable GPU
USE_GPU=false
```

**If segmentation fault (especially on macOS):**
```bash
# Try with MPS instead of CPU
GPU_DEVICE=mps
USE_GPU=true
```

**If intermittent crashes:**
- Check disk space: `df -h`
- Check CPU temperature: `sensors` or Activity Monitor
- Check for memory leaks: Add max workers limit

```bash
MCP_WORKERS=2  # Reduce from default 4
```

---

### Slow Server Response

**Symptoms:**
- First request takes >30 seconds
- Subsequent requests are slow
- High CPU/GPU usage even when idle

**Diagnostic Steps:**

1. **Check model loading:**
   ```bash
   MCP_LOG_LEVEL=DEBUG python -m kyutai_mcp.server 2>&1 | head -50
   # Look for "Loading model" messages
   ```

2. **Measure response time:**
   ```bash
   time curl http://localhost:8000/health
   time curl -X POST http://localhost:8000/synthesize \
     -H "Content-Type: application/json" \
     -d '{"text":"hello"}'
   ```

3. **Check GPU status:**
   ```bash
   nvidia-smi  # If NVIDIA
   rocm-smi    # If AMD
   ```

**Solutions:**

**If first request is slow (normal):**
- Model is lazy-loaded, first request pays penalty
- Subsequent requests will be faster
- To avoid, enable preloading:

```bash
python -m kyutai_mcp.server --preload-models
```

**If all requests are slow:**
- Check GPU isn't over-subscribed

```bash
# Reduce concurrent requests
MCP_WORKERS=1

# Use smaller model
TTS_PROVIDER=pocket-tts  # Instead of moshi
STT_PROVIDER=stt-1b-en_fr  # Instead of stt-2.6b

# Enable quantization
QUANTIZE_MODELS=true
```

**If high CPU usage at idle:**
- Server thread pool may be contending
- Reduce workers:

```bash
MCP_WORKERS=1
```

---

## Plugin Issues

### Plugin Not Loading

**Symptoms:**
- Plugin appears disabled in Obsidian settings
- No ribbon icon visible
- "Failed to load plugin" error

**Diagnostic Steps:**

1. **Check plugin folder:**
   ```bash
   ls -la /path/to/vault/.obsidian/plugins/kyutai-mcp/

   # Should contain:
   # - manifest.json
   # - main.js (or esbuild.js)
   # - styles.css
   ```

2. **Check manifest.json:**
   ```bash
   cat .obsidian/plugins/kyutai-mcp/manifest.json
   # Should be valid JSON
   ```

3. **View console errors:**
   - Obsidian: Cmd+Shift+I → Console
   - Look for red error messages

**Solutions:**

**If plugin folder missing:**
```bash
mkdir -p /path/to/vault/.obsidian/plugins/kyutai-mcp
cp -r obsidian-plugin/* /path/to/vault/.obsidian/plugins/kyutai-mcp/
```

**If manifest.json invalid:**
```bash
# Validate JSON
python -m json.tool .obsidian/plugins/kyutai-mcp/manifest.json

# If error, fix manually:
nano .obsidian/plugins/kyutai-mcp/manifest.json
```

**If plugin code missing:**
```bash
# Rebuild plugin
cd obsidian-plugin
npm run build
cp esbuild.js /path/to/vault/.obsidian/plugins/kyutai-mcp/main.js
```

**Reload Obsidian:**
- Close and reopen Obsidian
- Or: Settings → Community Plugins → Reload plugins

---

### Connection Refused

**Symptoms:**
- "Cannot connect to MCP server"
- "Connection refused (127.0.0.1:8000)"
- "Network error" in plugin

**Diagnostic Steps:**

1. **Verify server is running:**
   ```bash
   curl http://localhost:8000/health
   # Should return JSON or connection error
   ```

2. **Check port configuration:**
   ```bash
   # MCP Server port
   echo $MCP_PORT  # Should be 8000

   # Plugin connection URL
   # In Obsidian Settings → Kyutai MCP → MCP Server URL
   # Should be http://localhost:8000
   ```

3. **Check firewall:**
   ```bash
   # macOS
   lsof -i :8000  # Is port listening?

   # Windows
   netstat -ano | findstr :8000
   ```

**Solutions:**

**If server not running:**
```bash
# Start server
python -m kyutai_mcp.server

# Or run with logging
python -m kyutai_mcp.server --log-level DEBUG
```

**If port mismatch:**
- MCP server: `MCP_PORT=8000`
- Obsidian plugin: Settings → `http://localhost:8000`
- Both must match!

**If firewall blocking:**
- macOS: System Preferences → Security & Privacy → Firewall Options
- Windows: Windows Defender Firewall → Allow apps
- Linux: `sudo ufw allow 8000/tcp`

---

### Settings Not Saving

**Symptoms:**
- Plugin settings disappear after reload
- Changes don't apply
- Settings file corrupted

**Solutions:**

1. **Check settings file:**
   ```bash
   cat /path/to/vault/.obsidian/plugins/kyutai-mcp/data.json
   ```

2. **Clear plugin data:**
   ```bash
   rm /path/to/vault/.obsidian/plugins/kyutai-mcp/data.json
   # Restart Obsidian to recreate defaults
   ```

3. **Verify folder permissions:**
   ```bash
   chmod -R 755 /path/to/vault/.obsidian/plugins/kyutai-mcp/
   ```

---

## Model & Inference Issues

### Model Not Found

**Symptoms:**
- "Model not found: stt-1b-en_fr"
- "Failed to load model from HuggingFace"
- "Model file corrupted"

**Diagnostic Steps:**

1. **Check model cache:**
   ```bash
   ls -lh ~/.cache/huggingface/hub/ | grep kyutai

   # Should show:
   # kyutai--stt-1b-en_fr
   # kyutai--pocket-tts
   ```

2. **Check Hugging Face token:**
   ```bash
   echo $HUGGING_FACE_HUB_TOKEN
   # Should be set if using gated models
   ```

3. **Try downloading manually:**
   ```python
   from transformers import AutoModel
   model = AutoModel.from_pretrained("kyutai/stt-1b-en_fr")
   # Will download or show specific error
   ```

**Solutions:**

**If model missing:**
```bash
# Set HF token
export HUGGING_FACE_HUB_TOKEN="hf_xxxxxxxxxxxxx"

# Create token at https://huggingface.co/settings/tokens

# Clear cache and redownload
rm -rf ~/.cache/huggingface/hub/
python -m kyutai_mcp.server --preload-models
```

**If cache corrupted:**
```bash
# Delete cache
rm -rf ~/.cache/huggingface/

# Restart server (will redownload)
python -m kyutai_mcp.server
```

**If model too large:**
```bash
# Use smaller model
TTS_PROVIDER=pocket-tts  # ~500MB

# Or enable quantization
QUANTIZE_MODELS=true
QUANTIZATION_BITS=4  # 4-bit quantization
```

---

### Inference Timeout

**Symptoms:**
- "Request timeout (504 Gateway Timeout)"
- Inference takes >5 minutes
- "Operation timed out" after 300 seconds

**Diagnostic Steps:**

1. **Check text/audio length:**
   - Text should be <4096 chars
   - Audio should be <1 hour

2. **Monitor system while inferencing:**
   ```bash
   watch nvidia-smi  # GPU usage
   top -p $(pgrep -f kyutai)  # CPU usage
   ```

3. **Check server logs:**
   ```bash
   MCP_LOG_LEVEL=DEBUG tail -f server.log | grep -i "timeout\|duration"
   ```

**Solutions:**

**If input too large:**
- Split text into chunks: <1000 chars each
- Split audio into segments: <5 min each
- Process sequentially

**If GPU out of memory:**
```bash
# Reduce batch size
CHUNK_SIZE=512  # Instead of 1024

# Use smaller model
TTS_PROVIDER=pocket-tts
STT_PROVIDER=stt-1b-en_fr

# Increase timeout
MCP_TIMEOUT=600  # 10 minutes instead of 5
```

**If CPU/system overloaded:**
```bash
# Reduce workers
MCP_WORKERS=1

# Check disk space
df -h

# Close other applications
# Restart server
```

---

## Audio Issues

### No Audio Output

**Symptoms:**
- Synthesis returns no error but no sound plays
- Audio file saved but empty
- Plugin shows success but silence

**Diagnostic Steps:**

1. **Check audio file:**
   ```bash
   # File exists and has size?
   ls -lh Audio\ Files/

   # Can it be played?
   ffplay audio_file.mp3
   # or
   afplay audio_file.mp3  # macOS
   paplay audio_file.wav  # Linux
   ```

2. **Check speaker/system volume:**
   ```bash
   # macOS
   osascript -e 'output volume of (get volume settings)'

   # Linux
   amixer get Master

   # Windows
   nircmd getvolume
   ```

3. **Check API response:**
   ```bash
   curl -X POST http://localhost:8000/synthesize \
     -H "Content-Type: application/json" \
     -d '{"text":"hello"}' \
     --output test.mp3

   # Check if test.mp3 has data
   ls -lh test.mp3
   ffprobe test.mp3  # Check format
   ```

**Solutions:**

**If no audio file created:**
- Ensure "Save audio files" is enabled in plugin settings
- Check folder permissions: `chmod 755 Obsidian\ Vault/Audio\ Files/`

**If audio file empty:**
- Model inference failed (check server logs)
- Try different text or voice
- Restart MCP server

**If audio file exists but silent:**
- Check synthesis parameters (speed, pitch)
- Try "default" voice instead of custom
- Verify text isn't empty

**If system audio disabled:**
- Increase system volume (not mute)
- Check speaker is default output device
- In Obsidian, enable "Auto-play" in settings

---

### Bad Audio Quality

**Symptoms:**
- Synthesized audio sounds robotic/distorted
- Transcription has many errors
- Audio is too fast/slow/high/low pitched

**Solutions:**

**For synthesis quality:**
```bash
# Use slower model (Moshi if available)
TTS_PROVIDER=moshi

# Adjust speech parameters
# In plugin UI:
# - Speed: 0.9 (slower than normal)
# - Pitch: 1.0 (keep normal)

# Use longer text (models work better with context)
# Instead of: "Hi"
# Try: "Hello, this is a proper sentence with context."
```

**For transcription quality:**
```bash
# Use more accurate model
STT_PROVIDER=stt-2.6b

# Improve audio input
# - Reduce background noise
# - Speak clearly
# - Use high-quality microphone/recording

# Check language matches audio
# Language: auto should detect, or set explicitly to "en"
```

---

## Performance Issues

### High Latency (>5 seconds per request)

**Symptoms:**
- Synthesis takes >5 seconds
- Transcription very slow
- System appears frozen during inference

**Diagnostic Steps:**

```bash
# Measure latency
time curl -X POST http://localhost:8000/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text":"hello","voice":"default"}'
# Note the "real" time

# Check GPU
nvidia-smi  # GPU utilization should be >90%

# Check if cold start
# First request after server start slower (~2x)
```

**Solutions:**

**If GPU not being used:**
```bash
# Verify GPU setting
echo $USE_GPU

# Check CUDA
python -c "import torch; print(torch.cuda.is_available())"

# Reinstall PyTorch for GPU
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

**If GPU memory too full:**
```bash
# Use smaller models
TTS_PROVIDER=pocket-tts  # Fastest
STT_PROVIDER=stt-1b-en_fr

# Or reduce memory allocation
GPU_MEMORY_FRACTION=0.5
```

**If many concurrent requests:**
```bash
# Queue builds up
MCP_WORKERS=8  # Increase workers if CPU available
```

**If cold start (first request slow):**
- This is normal (model loading)
- Subsequent requests will be fast
- Enable preloading:

```bash
python -m kyutai_mcp.server --preload-models
```

---

### High Memory Usage

**Symptoms:**
- Server uses >16GB RAM
- Obsidian becomes slow
- "Out of memory" errors

**Diagnostic Steps:**

```bash
# macOS/Linux
ps aux | grep kyutai_mcp | head -1 | awk '{print $6}'  # KB used

# Windows
Get-Process | Where-Object {$_.Name -match "python"} | Select-Object Name, WorkingSet

# Also check GPU memory
nvidia-smi
```

**Solutions:**

**Unload unused models:**
```bash
# Don't load all models
TTS_PROVIDER=pocket-tts   # Only load TTS
# Don't load STT if not needed
```

**Use quantized models:**
```bash
QUANTIZE_MODELS=true
QUANTIZATION_BITS=4  # 4-bit, smaller than 8-bit
```

**Reduce model size:**
```bash
# Use smaller models
TTS_PROVIDER=pocket-tts    # 500MB
STT_PROVIDER=stt-1b-en_fr  # 1.2GB (not 2.6B)
```

**Limit concurrent requests:**
```bash
MCP_WORKERS=1
MCP_TIMEOUT=60  # Kill slow requests
```

---

## GPU Issues

### GPU Not Detected

**Symptoms:**
- "CUDA not available" error
- `nvidia-smi` works but PyTorch can't see GPU
- Server uses CPU even with GPU available

**Diagnostic Steps:**

```bash
# Check GPU hardware
nvidia-smi  # NVIDIA
rocm-smi    # AMD

# Check CUDA/ROCm installation
nvcc --version  # NVIDIA CUDA compiler
```

```python
# Check PyTorch
import torch
print("CUDA available:", torch.cuda.is_available())
print("CUDA device:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "None")
```

**Solutions:**

**For NVIDIA:**
```bash
# Install CUDA toolkit (system-level)
# https://developer.nvidia.com/cuda-downloads

# Reinstall PyTorch for CUDA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Test
python -c "import torch; print(torch.cuda.is_available())"
```

**For AMD:**
```bash
# Install ROCm
# https://rocmdocs.amd.com/en/latest/deploy/linux/

# Reinstall PyTorch for ROCm
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm5.7

# Test
python -c "import torch; print(torch.version.hip)"
```

**For Apple Silicon:**
```bash
# Use MLX (optimized for Apple Silicon)
pip install torch-mlx

# Set device
GPU_DEVICE=mps
```

---

### GPU Out of Memory

**Symptoms:**
- "CUDA out of memory" or "RuntimeError: CUDA error: out of memory"
- Server crashes during inference
- Only happens on large text/audio

**Diagnostic Steps:**

```bash
# Check available VRAM
nvidia-smi | grep "Memory"

# Monitor during inference
watch -n 0.5 nvidia-smi

# Check model size
python -c "from transformers import AutoModel; m = AutoModel.from_pretrained('kyutai/stt-1b'); print(m)"
```

**Solutions:**

**Reduce model complexity:**
```bash
# Use smaller model
TTS_PROVIDER=pocket-tts    # 500MB (vs 14GB for Moshi)
STT_PROVIDER=stt-1b-en_fr  # 1.2GB (vs 5GB for stt-2.6b)

# Or use quantization
QUANTIZE_MODELS=true
QUANTIZATION_BITS=4        # 4-bit quantization
```

**Reduce GPU memory allocation:**
```bash
GPU_MEMORY_FRACTION=0.6    # Use 60% of GPU
GPU_MEMORY_GROWTH=true     # Dynamic allocation
```

**Use CPU fallback:**
```bash
USE_GPU=false              # Disable GPU
QUANTIZE_MODELS=true       # Make inference fast on CPU
```

**Reduce batch size:**
```bash
CHUNK_SIZE=512             # Smaller chunks
MCP_WORKERS=1              # Single worker
```

---

## Network Issues

### Cannot Reach Remote Server

**Symptoms:**
- "Connection refused" when connecting to remote MCP server
- Plugin configured for `http://gpu-server:8000` but fails
- Works locally, fails remotely

**Diagnostic Steps:**

```bash
# Test connectivity
ping gpu-server

# Test port
nc -zv gpu-server 8000  # macOS/Linux
Test-NetConnection gpu-server -Port 8000  # Windows

# Test HTTP endpoint
curl http://gpu-server:8000/health
```

**Solutions:**

**If host not reachable:**
- Verify hostname/IP: `nslookup gpu-server`
- Check network: `ip route` or `route -n`
- Ensure both machines on same network

**If port not open:**
- Server might not be listening on 0.0.0.0
- Change server to accept external connections:

```bash
MCP_HOST=0.0.0.0  # Listen on all interfaces
```

**If firewall blocking:**
```bash
# Linux
sudo ufw allow 8000/tcp

# Windows (PowerShell as Admin)
New-NetFirewallRule -DisplayName "MCP Server" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow

# macOS
# System Preferences → Security → Firewall Options
```

---

### Slow Network Connection

**Symptoms:**
- Remote MCP server very slow (>10s per request)
- Local MCP server fast (1-2s per request)
- Latency appears in network, not GPU

**Solutions:**

**Check network latency:**
```bash
time curl http://gpu-server:8000/health
# Note time to first response (TTFB)
```

**Optimize for network:**
- Use lossy audio formats (MP3) instead of WAV
- Compress audio before sending
- Enable caching on client

```bash
# Server-side
MCP_LOG_LEVEL=WARNING  # Reduce logging overhead
```

---

## Diagnostic Checklist

Use this checklist to systematically diagnose issues:

### Pre-flight Checks

- [ ] Python version: `python --version` (should be 3.9+)
- [ ] Node.js version: `node --version` (should be 18+)
- [ ] Disk space: `df -h` (should have >5GB free)
- [ ] RAM: `free -h` (should have >8GB)
- [ ] Firewall allows localhost:8000

### Server Diagnostics

```bash
# Check server startup
[ ] python -m kyutai_mcp.server  # Starts without errors?
[ ] curl http://localhost:8000/health  # Returns JSON?
[ ] Check server logs for errors
```

### Model Diagnostics

```bash
# Check model availability
[ ] python -c "from pocket_tts import TTSModel; m = TTSModel.load_model()"
[ ] python -c "from moshi import STTModel; m = STTModel.from_pretrained('kyutai/stt-1b')"
[ ] nvidia-smi  # GPU available? (if using GPU)
```

### Plugin Diagnostics

```bash
# Check plugin installation
[ ] ls ~/.obsidian/plugins/kyutai-mcp/manifest.json
[ ] Plugin appears in Obsidian settings
[ ] Test Connection shows "✓ Connected"
```

### End-to-End Test

```bash
# Test full workflow
[ ] Synthesize: "Hello world"
[ ] Transcribe: Sample audio file
[ ] Check output is correct
[ ] Check performance is acceptable
```

### If Still Stuck

1. **Collect diagnostic data:**
   ```bash
   python -m kyutai_mcp.server --log-level DEBUG 2>&1 | tee debug.log
   # Run test operation
   # Save debug.log
   ```

2. **Check related issues:**
   - Search GitHub Issues: https://github.com/kyutai-labs/kyutai-mcp-obsidian/issues
   - Check Kyutai discussions: https://github.com/kyutai-labs/moshi/discussions

3. **Report issue with:**
   - Error message (full stack trace)
   - System info: `uname -a`, `python --version`, `pip list`
   - Steps to reproduce
   - `debug.log` output
   - What you've already tried

---

**Last Updated**: 2026-02-10
**Version**: 0.1.0-alpha
