# Installation Guide

Complete setup instructions for Kyutai MCP Server and Obsidian Plugin on all platforms.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [MCP Server Setup](#mcp-server-setup)
3. [Obsidian Plugin Installation](#obsidian-plugin-installation)
4. [Configuration](#configuration)
5. [Verification](#verification)
6. [Troubleshooting](#troubleshooting)
7. [Docker Setup](#docker-setup)

## System Requirements

### Operating Systems
- **macOS**: 10.15 (Catalina) or newer
- **Linux**: Ubuntu 20.04+, Fedora 32+, Debian 10+
- **Windows**: 10 or 11 (WSL2 recommended for best performance)

### Software
- **Python**: 3.9 or newer (check with `python3 --version`)
- **Node.js**: 18+ (for Obsidian plugin development only)
- **npm**: 8+ (bundled with Node.js)
- **Git**: 2.20+ (for cloning repositories)

### Hardware

**Minimum** (CPU-only processing):
- RAM: 8GB
- Disk: 5GB free
- CPU: Quad-core

**Recommended** (GPU acceleration):
- RAM: 16GB
- Disk: 15GB free
- GPU: NVIDIA with CUDA 12.0+ (4GB+ VRAM)
- GPU RAM: 6GB+

**GPU Options**:
- NVIDIA (CUDA): RTX 3060 or better, RTX 4080 for production
- AMD (ROCm): Radeon RX 6800 or better
- Apple Silicon (MLX): M1/M2/M3 MacBook Pro/Max

---

## MCP Server Setup

### Step 1: Clone Repository

```bash
git clone https://github.com/kyutai-labs/kyutai-mcp-obsidian
cd kyutai-mcp-obsidian
```

### Step 2: Create Virtual Environment

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

### Step 3: Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install core dependencies
pip install -r requirements.txt

# GPU support (NVIDIA CUDA)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# GPU support (macOS/Apple Silicon)
pip install torch-mlx

# GPU support (AMD ROCm)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm5.7
```

### Step 4: Download Models

Models are downloaded automatically on first use. To pre-download:

```bash
# Set Hugging Face token (required for gated models)
export HUGGING_FACE_HUB_TOKEN="hf_xxxxxxxxxxxxx"

# Download Pocket TTS (100MB)
python -c "from pocket_tts import TTSModel; TTSModel.load_model()"

# Download Delayed Streams STT 1B (1.2GB)
python -c "from moshi import STTModel; STTModel.from_pretrained('kyutai/stt-1b-en_fr')"

# Download Moshi (14GB - optional, high-latency)
python -c "from transformers import AutoModelForCausalLM; AutoModelForCausalLM.from_pretrained('kyutai/moshika-pytorch-bf16')"
```

Model sizes:
- Pocket TTS: ~100MB
- STT 1B: ~1.2GB
- STT 2.6B: ~5GB
- Moshi 7B: ~14GB (bf16) or ~7GB (int8)
- Total (all): ~25GB

### Step 5: Configure Environment

Create `.env` file in project root:

```bash
# Create from template
cp .env.example .env

# Edit with your settings
nano .env  # macOS/Linux
# or
notepad .env  # Windows
```

**.env Configuration:**
```bash
# Hugging Face
HUGGING_FACE_HUB_TOKEN=hf_xxxxxxxxxxxxx

# MCP Server
MCP_HOST=127.0.0.1
MCP_PORT=8000
MCP_LOG_LEVEL=INFO

# Model Selection
TTS_MODEL=pocket-tts  # pocket-tts, moshi, community-api
STT_MODEL=stt-1b     # stt-1b, stt-2.6b

# Quantization (for slower hardware)
QUANTIZE_MODELS=false  # true = slower startup, faster inference

# GPU Configuration
CUDA_VISIBLE_DEVICES=0      # GPU index
USE_GPU=true
GPU_MEMORY_FRACTION=0.8

# Community API Endpoints (if using OpenAI-compatible APIs)
COMMUNITY_TTS_URL=http://localhost:8001/v1
COMMUNITY_STT_URL=http://localhost:8002/v1

# Audio Settings
SAMPLE_RATE=24000
CHUNK_SIZE=1024
```

### Step 6: Start MCP Server

```bash
# Activate venv (if not already)
source venv/bin/activate  # macOS/Linux
# or
.\venv\Scripts\activate  # Windows

# Start server
python -m kyutai_mcp.server

# Expected output:
# INFO:kyutai_mcp.server:Starting MCP server on 127.0.0.1:8000
# INFO:kyutai_mcp.server:Loading models...
# INFO:kyutai_mcp.server:Server ready. Listening on http://127.0.0.1:8000
```

### Step 7: Verify Server

In a new terminal:
```bash
curl http://localhost:8000/health

# Expected response:
# {"status":"ok","models":["pocket-tts","stt-1b"],"version":"0.1.0"}
```

---

## Obsidian Plugin Installation

### Option A: Manual Installation (Recommended for Testing)

**Step 1: Prepare Plugin Folder**

```bash
# Navigate to your Obsidian vault
cd /path/to/your/vault

# Create plugin directory
mkdir -p .obsidian/plugins/kyutai-mcp

# Copy plugin files
cp -r /path/to/kyutai-mcp-obsidian/obsidian-plugin/* \
  .obsidian/plugins/kyutai-mcp/
```

**Step 2: Update Plugin Manifest**

Edit `.obsidian/plugins/kyutai-mcp/manifest.json`:

```json
{
  "id": "kyutai-mcp",
  "name": "Kyutai MCP",
  "version": "0.1.0",
  "minAppVersion": "1.4.0",
  "description": "Voice AI integration for Obsidian",
  "author": "Kyutai Labs",
  "authorUrl": "https://kyutai.org"
}
```

**Step 3: Reload Obsidian**

1. Close and reopen Obsidian
2. Go to Settings → Community Plugins
3. Look for "Kyutai MCP" - should show as installed
4. Click "Enable" to activate

**Step 4: Configure Plugin**

1. Go to Settings → Kyutai MCP
2. Set MCP Server URL: `http://localhost:8000`
3. Select default TTS voice: `alloy`
4. Select default STT model: `stt-1b-en_fr`
5. Click "Test Connection" to verify

### Option B: Build from Source (For Development)

**Step 1: Install Build Tools**

```bash
cd obsidian-plugin
npm install
```

**Step 2: Build Plugin**

```bash
npm run build

# Output: esbuild.js (bundled plugin)
```

**Step 3: Install in Vault**

```bash
mkdir -p /path/to/vault/.obsidian/plugins/kyutai-mcp

# Copy built plugin
cp esbuild.js /path/to/vault/.obsidian/plugins/kyutai-mcp/main.js
cp manifest.json /path/to/vault/.obsidian/plugins/kyutai-mcp/
cp styles.css /path/to/vault/.obsidian/plugins/kyutai-mcp/
```

**Step 4: Enable in Obsidian**

See "Option A, Step 3" above.

### Option C: Obsidian Community Marketplace (Coming Soon)

Once approved:
1. Open Obsidian
2. Settings → Community Plugins
3. Search "Kyutai MCP"
4. Click "Install"
5. Click "Enable"

---

## Configuration

### MCP Server Configuration

**Via Environment Variables** (`.env`):
```bash
MCP_HOST=127.0.0.1
MCP_PORT=8000
MCP_LOG_LEVEL=DEBUG
TTS_MODEL=pocket-tts
STT_MODEL=stt-1b
USE_GPU=true
```

**Via Configuration File** (`config.yaml`):

```yaml
server:
  host: 127.0.0.1
  port: 8000
  workers: 4
  log_level: INFO

models:
  tts:
    provider: pocket-tts
    device: cuda  # cpu, cuda, mps

  stt:
    provider: stt-1b-en_fr
    device: cuda

audio:
  sample_rate: 24000
  channels: 1
  chunk_size: 1024

voices:
  - name: default
    audio: /path/to/voice.wav
  - name: character
    audio: /path/to/character.wav

gpu:
  memory_fraction: 0.8
  quantize: false
```

Load configuration:
```python
from kyutai_mcp import MCPServer
server = MCPServer(config_file="config.yaml")
```

### Obsidian Plugin Configuration

Access in Obsidian: Settings → Kyutai MCP

**Key Settings:**

| Setting | Default | Description |
|---------|---------|-------------|
| MCP Server URL | `http://localhost:8000` | MCP server endpoint |
| Default TTS Voice | `alloy` | Voice for synthesis |
| Default STT Model | `stt-1b-en_fr` | Model for transcription |
| Chunk Size | `8192` | Audio processing chunk size |
| TTS Speed | `1.0` | Speech speed (0.5-2.0) |
| Auto-Save Audio | `false` | Save generated audio files |
| Output Folder | `Audio Files` | Where to save audio |
| Keyboard Shortcut | `Ctrl+Shift+V` | Global hotkey for voice |

### Voice Profiles (Optional)

Create voice profiles for consistent TTS:

**In Obsidian Plugin Settings:**
1. Click "Add Voice Profile"
2. Enter profile name: "My Voice"
3. Upload reference audio (5-30 seconds)
4. Click "Test"
5. Save

**Via MCP API:**
```python
mcp.create_voice_profile(
    name="my_voice",
    audio_path="/path/to/reference.wav"
)
```

---

## Verification

### Check Installation

**1. Verify Python Environment**
```bash
python --version  # Should be 3.9+
pip show torch    # Should show PyTorch installed
pip show pocket-tts  # Should show installed
```

**2. Verify MCP Server**
```bash
# Start server
python -m kyutai_mcp.server &

# In another terminal, test endpoint
curl http://localhost:8000/health

# Expected: {"status":"ok",...}
```

**3. Verify Obsidian Plugin**
1. Obsidian Settings → Community Plugins
2. Look for "Kyutai MCP"
3. Click "Test Connection" in plugin settings
4. Should show: "✓ Connected to MCP Server"

### Run Tests

```bash
# Unit tests
pytest tests/unit

# Integration tests
pytest tests/integration

# Full test suite
pytest tests
```

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'pocket_tts'"

**Solution:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # macOS/Linux
.\venv\Scripts\activate   # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: "CUDA out of memory"

**Solution:**
```bash
# Reduce GPU memory usage
export CUDA_VISIBLE_DEVICES=0  # Use single GPU

# Edit .env
USE_GPU=true
GPU_MEMORY_FRACTION=0.5  # Use 50% of GPU memory

# Or use CPU mode
USE_GPU=false
```

### Issue: "Connection refused (127.0.0.1:8000)"

**Solution:**
1. Verify MCP server is running: `curl http://localhost:8000/health`
2. Check port: `lsof -i :8000` (macOS/Linux) or `netstat -ano | findstr :8000` (Windows)
3. Change port in `.env` if 8000 is in use
4. Verify firewall settings

### Issue: "Obsidian plugin not loading"

**Solution:**
1. Check manifest.json exists and is valid JSON
2. Verify plugin folder: `~/.obsidian/plugins/kyutai-mcp/`
3. Check Obsidian console for errors: Settings → Developer → Developer Tools
4. Reload plugins: Cmd+Shift+R (macOS) or Ctrl+Shift+R (Windows/Linux)

### Issue: "Hugging Face token not found"

**Solution:**
```bash
# Generate token at https://huggingface.co/settings/tokens
# Add to .env
export HUGGING_FACE_HUB_TOKEN="hf_xxxxxxxxxxxxx"

# Or create ~/.huggingface/token
mkdir -p ~/.huggingface
echo "hf_xxxxxxxxxxxxx" > ~/.huggingface/token
```

### Issue: "GPU not detected"

**Solution:**
```bash
# Verify CUDA installation
python -c "import torch; print(torch.cuda.is_available())"

# Update GPU drivers
# NVIDIA: https://www.nvidia.com/Download/driverDetails.aspx
# AMD: https://www.amd.com/en/support
# Apple: Update macOS

# Reinstall PyTorch for your GPU
pip install --force-reinstall torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

---

## Docker Setup

### Quick Start with Docker Compose

```bash
# Clone repository
git clone https://github.com/kyutai-labs/kyutai-mcp-obsidian
cd kyutai-mcp-obsidian

# Start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f kyutai-mcp
```

### Docker Compose Configuration

**`docker-compose.yml`:**
```yaml
version: '3.8'

services:
  kyutai-mcp:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - HUGGING_FACE_HUB_TOKEN=${HUGGING_FACE_HUB_TOKEN}
      - USE_GPU=true
      - CUDA_VISIBLE_DEVICES=0
    volumes:
      - ./data:/app/data
      - ~/.cache/huggingface:/root/.cache/huggingface
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]

  obsidian:
    image: node:18-alpine
    working_dir: /app
    volumes:
      - ./obsidian-plugin:/app
    command: npm run dev
    ports:
      - "3000:3000"
```

### Build Custom Docker Image

```bash
docker build -t kyutai-mcp:latest .

# Run container
docker run --gpus all \
  -p 8000:8000 \
  -e HUGGING_FACE_HUB_TOKEN=hf_xxx \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  kyutai-mcp:latest
```

### Docker with CPU Only

```bash
docker run --cpus 8 \
  -p 8000:8000 \
  -e USE_GPU=false \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  kyutai-mcp:latest
```

---

## Platform-Specific Notes

### macOS (Intel & Apple Silicon)

**Intel Macs:**
```bash
# Use CUDA (if external GPU available) or CPU
pip install torch torchvision torchaudio

# Or use MLX for better performance (recommended)
pip install torch-mlx
```

**Apple Silicon (M1/M2/M3):**
```bash
# Install MLX for native performance
pip install torch-mlx

# Enable in .env
USE_GPU=true
GPU_DEVICE=mps  # Metal Performance Shaders
```

### Linux (Ubuntu)

```bash
# Install CUDA toolkit
sudo apt-get install nvidia-cuda-toolkit

# Verify CUDA
nvcc --version
nvidia-smi

# Then follow standard installation steps
```

### Windows

**PowerShell (Recommended):**
```powershell
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Start server
python -m kyutai_mcp.server
```

**Windows Subsystem for Linux 2 (WSL2):**
```bash
# Inside WSL2
wsl

# Install CUDA for WSL
https://developer.nvidia.com/cuda/wsl

# Follow Linux instructions
```

---

## Next Steps

1. ✅ Install MCP Server and Obsidian Plugin
2. ✅ Verify connections (test health endpoints)
3. 📖 Read [MCP_SERVER.md](./MCP_SERVER.md) for server configuration
4. 📖 Read [PLUGIN_USAGE.md](./PLUGIN_USAGE.md) for plugin features
5. 📖 Read [API_REFERENCE.md](./API_REFERENCE.md) for advanced usage

## Getting Help

- **Installation Issues**: See Troubleshooting section above
- **Feature Questions**: Check [PLUGIN_USAGE.md](./PLUGIN_USAGE.md)
- **API Questions**: Check [API_REFERENCE.md](./API_REFERENCE.md)
- **Report Bugs**: [GitHub Issues](https://github.com/kyutai-labs/kyutai-mcp-obsidian/issues)

---

**Last Updated**: 2026-02-10
**Version**: 0.1.0-alpha
