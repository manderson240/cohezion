# MCP Server Configuration & Deployment

Complete guide for configuring, deploying, and managing the Kyutai MCP Server.

## Table of Contents

1. [Server Overview](#server-overview)
2. [Architecture](#architecture)
3. [Configuration Options](#configuration-options)
4. [Starting the Server](#starting-the-server)
5. [Model Management](#model-management)
6. [Health Checks & Monitoring](#health-checks--monitoring)
7. [Performance Tuning](#performance-tuning)
8. [GPU Configuration](#gpu-configuration)
9. [Logging & Debugging](#logging--debugging)
10. [Production Deployment](#production-deployment)

---

## Server Overview

The Kyutai MCP Server is a Python/FastAPI application that:
- Exposes Kyutai voice AI tools via the Model Context Protocol (MCP)
- Handles model loading, inference, and streaming
- Provides REST/WebSocket endpoints for voice operations
- Manages GPU/CPU resource allocation
- Monitors health and performance

**Technology Stack:**
- Framework: FastAPI + Uvicorn
- MCP Library: python-mcp
- GPU: CUDA (NVIDIA), ROCm (AMD), MLX (Apple Silicon)
- Async: asyncio, websockets
- Monitoring: Prometheus metrics (optional)

---

## Architecture

### System Components

```
┌─────────────────────────────────────┐
│      Obsidian Plugin (Client)       │
└─────────────────────────────────────┘
              ↓ MCP Protocol
┌─────────────────────────────────────┐
│      MCP Server (FastAPI)           │
│  ┌─────────────────────────────────┐│
│  │  Tool Registry (7 tools)        ││
│  ├─────────────────────────────────┤│
│  │  Model Manager                  ││
│  │  ├─ Pocket TTS                  ││
│  │  ├─ Delayed Streams STT         ││
│  │  ├─ Moshi                       ││
│  │  └─ Community APIs              ││
│  ├─────────────────────────────────┤│
│  │  Audio Pipeline                 ││
│  │  ├─ Input Stream Handler        ││
│  │  ├─ Inference Engine            ││
│  │  └─ Output Formatter            ││
│  ├─────────────────────────────────┤│
│  │  GPU/Resource Manager           ││
│  │  ├─ Memory Allocation           ││
│  │  ├─ Thread Pool                 ││
│  │  └─ Error Recovery              ││
│  └─────────────────────────────────┘│
└─────────────────────────────────────┘
         ↓ Local/GPU Hardware
┌─────────────────────────────────────┐
│   Kyutai Models (PyTorch/MLX)       │
└─────────────────────────────────────┘
```

### Tool Registry

The server exposes 7 MCP tools:

| Tool | Purpose | Input | Output |
|------|---------|-------|--------|
| `synthesize_text` | Text-to-Speech | text, voice | audio binary |
| `transcribe_audio` | Speech-to-Text | audio binary | text + timestamps |
| `clone_voice` | Voice Profile | reference audio | voice state |
| `list_voices` | Available Voices | — | voice list |
| `list_models` | Available Models | — | model metadata |
| `get_status` | Server Status | — | health metrics |
| `stream_audio` | Real-time Streaming | audio stream | text stream |

---

## Configuration Options

### Environment Variables

Create `.env` file with:

```bash
# ========== SERVER SETTINGS ==========
MCP_HOST=127.0.0.1              # Bind address
MCP_PORT=8000                   # Bind port
MCP_LOG_LEVEL=INFO              # DEBUG, INFO, WARNING, ERROR
MCP_WORKERS=4                   # Worker processes
MCP_TIMEOUT=300                 # Request timeout (seconds)

# ========== MODEL SELECTION ==========
TTS_PROVIDER=pocket-tts         # pocket-tts, moshi, community-api
STT_PROVIDER=stt-1b-en_fr       # stt-1b, stt-2.6b, community-api
STT_LANGUAGE=en_fr              # en_fr, en (depends on model)

# ========== GPU CONFIGURATION ==========
USE_GPU=true                    # Enable GPU acceleration
GPU_DEVICE=auto                 # auto, cuda:0, cuda:1, mps, cpu
CUDA_VISIBLE_DEVICES=0          # GPU IDs to use (0,1,2,...)
GPU_MEMORY_FRACTION=0.8         # GPU memory limit (0.0-1.0)
GPU_MEMORY_GROWTH=true          # Dynamic memory allocation

# ========== QUANTIZATION ==========
QUANTIZE_MODELS=false           # 4-bit/8-bit quantization
QUANTIZATION_BITS=8             # 4 or 8
MODEL_CACHE_DIR=~/.cache/huggingface  # Model cache location

# ========== HUGGING FACE ==========
HUGGING_FACE_HUB_TOKEN=hf_xxx   # Required for gated models
HF_CACHE_DIR=~/.cache/huggingface
HF_DATASETS_OFFLINE=false

# ========== AUDIO SETTINGS ==========
SAMPLE_RATE=24000               # Audio sample rate (Hz)
CHUNK_SIZE=1024                 # Processing chunk size
CHANNELS=1                      # Mono (1) or Stereo (2)
BIT_DEPTH=16                    # 16 or 32-bit

# ========== COMMUNITY API ENDPOINTS ==========
COMMUNITY_TTS_URL=http://localhost:8001/v1
COMMUNITY_STT_URL=http://localhost:8002/v1

# ========== MONITORING ==========
ENABLE_METRICS=true             # Prometheus metrics
METRICS_PORT=9090               # Prometheus port
HEALTH_CHECK_INTERVAL=30        # Health check interval (seconds)

# ========== LOGGING ==========
LOG_DIR=./logs
LOG_MAX_SIZE=100MB
LOG_BACKUP_COUNT=10
LOG_FORMAT=json                 # json or text
```

### YAML Configuration File

**`config.yaml`:**
```yaml
server:
  host: 127.0.0.1
  port: 8000
  workers: 4
  timeout: 300
  log_level: INFO

models:
  tts:
    provider: pocket-tts          # pocket-tts, moshi, community-api
    device: auto                  # auto, cuda, cpu, mps
    cache_dir: ~/.cache/huggingface

  stt:
    provider: stt-1b-en_fr        # stt-1b, stt-2.6b, community-api
    device: auto
    language: en_fr               # en_fr or en
    cache_dir: ~/.cache/huggingface

audio:
  sample_rate: 24000
  channels: 1
  chunk_size: 1024
  bit_depth: 16

gpu:
  enabled: true
  memory_fraction: 0.8            # Fraction of GPU memory to use
  memory_growth: true             # Dynamic allocation
  device_id: 0                    # Single GPU or auto
  quantize: false                 # Enable quantization

voices:
  default:
    audio: ./data/default_voice.wav
    name: "Default"
    language: en
  - name: Character
    audio: ./data/character.wav

community_apis:
  tts:
    url: http://localhost:8001/v1
    enabled: false

  stt:
    url: http://localhost:8002/v1
    enabled: false

monitoring:
  enabled: true
  port: 9090
  health_check_interval: 30
  log_requests: true

logging:
  level: INFO
  dir: ./logs
  format: json                    # json or text
  max_size: 100MB
  backup_count: 10
```

### Loading Configuration

**From environment:**
```python
from kyutai_mcp import MCPServer

server = MCPServer()  # Auto-loads from .env
```

**From file:**
```python
from kyutai_mcp import MCPServer

server = MCPServer(config_file="config.yaml")
```

**From dict:**
```python
config = {"server": {"port": 8000}, "models": {"tts": {"provider": "pocket-tts"}}}
server = MCPServer(config=config)
```

---

## Starting the Server

### Command Line

**Basic startup:**
```bash
python -m kyutai_mcp.server
```

**With options:**
```bash
python -m kyutai_mcp.server \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --log-level DEBUG
```

**With config file:**
```bash
python -m kyutai_mcp.server --config config.yaml
```

### Python API

```python
from kyutai_mcp import MCPServer

server = MCPServer(host="127.0.0.1", port=8000, log_level="INFO")

server.start()  # Blocking call
```

### Docker

```bash
docker run -p 8000:8000 \
  -e HUGGING_FACE_HUB_TOKEN=hf_xxx \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  kyutai-mcp:latest
```

### Systemd Service (Linux)

**Create `/etc/systemd/system/kyutai-mcp.service`:**
```ini
[Unit]
Description=Kyutai MCP Server
After=network.target

[Service]
Type=simple
User=kyutai
WorkingDirectory=/opt/kyutai-mcp
Environment="HUGGING_FACE_HUB_TOKEN=hf_xxx"
ExecStart=/opt/kyutai-mcp/venv/bin/python -m kyutai_mcp.server
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable kyutai-mcp
sudo systemctl start kyutai-mcp
sudo systemctl status kyutai-mcp
```

---

## Model Management

### Preloading Models

Models are lazily loaded on first use. To preload:

```python
from kyutai_mcp import MCPServer

server = MCPServer()
server.preload_models()  # Load all configured models
server.start()
```

**Via CLI:**
```bash
python -m kyutai_mcp.server --preload-models
```

### Model Caching

Models are cached in `~/.cache/huggingface`:

```bash
# View cache
ls ~/.cache/huggingface/hub/

# Clear cache (removes all models)
rm -rf ~/.cache/huggingface/hub/

# Set custom cache dir
export HF_HOME=/mnt/large_ssd/models
```

### Switching Models

**At runtime:**
```python
# List available models
models = server.list_models()

# Switch TTS model
server.set_model("tts", "moshi")

# Switch STT model
server.set_model("stt", "stt-2.6b")
```

**Via MCP tool:**
```json
{
  "tool": "set_model",
  "arguments": {
    "model_type": "tts",
    "model_name": "pocket-tts"
  }
}
```

### Model Versions

```bash
# List available versions
huggingface-cli repo-list kyutai --limit 100

# Pin specific version (in .env)
TTS_MODEL=kyutai/pocket-tts@v1.0.0
STT_MODEL=kyutai/stt-1b-en_fr@v2.0.0
```

---

## Health Checks & Monitoring

### Health Endpoint

**Endpoint:** `GET /health`

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "uptime_seconds": 3600,
  "models": {
    "tts": {
      "name": "pocket-tts",
      "device": "cuda:0",
      "memory_mb": 512,
      "loaded": true
    },
    "stt": {
      "name": "stt-1b-en_fr",
      "device": "cuda:0",
      "memory_mb": 2048,
      "loaded": true
    }
  },
  "gpu": {
    "available": true,
    "devices": [
      {
        "id": 0,
        "name": "NVIDIA RTX 3080",
        "memory_total_mb": 10240,
        "memory_used_mb": 2560
      }
    ]
  },
  "performance": {
    "avg_latency_ms": 125,
    "requests_total": 1523,
    "requests_per_second": 2.3,
    "errors": 0
  }
}
```

### Check Health

```bash
curl http://localhost:8000/health | jq
```

### Prometheus Metrics

**Enable in `.env`:**
```bash
ENABLE_METRICS=true
METRICS_PORT=9090
```

**Access metrics:**
```bash
curl http://localhost:9090/metrics

# Output includes:
# kyutai_requests_total{method="POST",path="/synthesize"}
# kyutai_request_duration_seconds{...}
# kyutai_gpu_memory_bytes{device="cuda:0"}
# kyutai_model_inference_seconds{model="pocket-tts"}
```

### Custom Monitoring

```python
from kyutai_mcp import MCPServer

server = MCPServer()


# Register custom health check
@server.health_check()
def check_models():
    return {"models_loaded": len(server.models) > 0}


# Register metrics callback
@server.metrics()
def report_metrics():
    return {"inference_count": server.inference_count, "total_time_ms": server.total_time_ms}
```

---

## Performance Tuning

### Optimize for Latency

**Goal: Minimal response time**

```bash
# .env configuration
USE_GPU=true
GPU_DEVICE=cuda:0
GPU_MEMORY_FRACTION=1.0          # Use full GPU
QUANTIZE_MODELS=false             # Higher precision = higher latency
MCP_WORKERS=8                      # More workers
TTS_PROVIDER=pocket-tts            # Fastest provider
STT_PROVIDER=stt-1b-en_fr         # Faster than 2.6B
SAMPLE_RATE=16000                 # Lower sample rate
CHUNK_SIZE=512                    # Smaller chunks
```

**Expected latency:**
- Voice synthesis: 50-100ms
- Speech transcription: 160-200ms

### Optimize for Throughput

**Goal: Maximum concurrent requests**

```bash
# .env configuration
USE_GPU=true
GPU_DEVICE=cuda:0
QUANTIZE_MODELS=true              # 8-bit quantization
MCP_WORKERS=16                     # Many workers
GPU_MEMORY_FRACTION=0.9            # Leave headroom
CHUNK_SIZE=2048                    # Larger chunks
```

**Expected throughput:**
- Pocket TTS: 10+ concurrent
- STT 1B: 64 concurrent streams
- STT 2.6B: 32 concurrent streams

### Optimize for Memory

**Goal: Minimal GPU memory usage**

```bash
# .env configuration
USE_GPU=true
QUANTIZE_MODELS=true              # 4-bit quantization
GPU_MEMORY_FRACTION=0.5            # Conservative allocation
CHUNK_SIZE=512
TTS_PROVIDER=pocket-tts            # Smallest model
STT_PROVIDER=stt-1b-en_fr
```

**Memory requirements:**
- Pocket TTS: ~500MB
- STT 1B: ~2.5GB
- STT 2.6B: ~6GB
- Total: ~9GB

---

## GPU Configuration

### NVIDIA CUDA

**Check GPU:**
```bash
nvidia-smi              # List GPUs
nvidia-smi -l           # Monitor in loop

# Output example:
# GPU  Name            Memory-Usage  Volatile GPU Util.
# 0    NVIDIA RTX 4090  2560/24576MB  42%
```

**Configure:**
```bash
# .env
USE_GPU=true
GPU_DEVICE=cuda:0
CUDA_VISIBLE_DEVICES=0,1,2        # Use GPUs 0, 1, 2
GPU_MEMORY_FRACTION=0.8
GPU_MEMORY_GROWTH=true            # Dynamic allocation
```

**Multi-GPU Usage:**
```python
# Load model on specific GPU
server.set_model("tts", "pocket-tts", device="cuda:0")
server.set_model("stt", "stt-1b-en_fr", device="cuda:1")
```

### AMD ROCm

**Check GPU:**
```bash
rocm-smi
```

**Configure:**
```bash
USE_GPU=true
GPU_DEVICE=rocm:0
HIP_VISIBLE_DEVICES=0
```

### Apple Silicon (MLX)

**Check GPU:**
```bash
python -c "import mlx.core as mx; print(mx.metal.is_available())"
```

**Configure:**
```bash
USE_GPU=true
GPU_DEVICE=mps
TORCH_MPS_FALLBACK=0               # Don't fall back to CPU
```

### CPU-Only Mode

```bash
USE_GPU=false
GPU_DEVICE=cpu
QUANTIZE_MODELS=true              # Essential for performance
CHUNK_SIZE=1024
TTS_PROVIDER=pocket-tts            # Must be lightweight
```

---

## Logging & Debugging

### Log Levels

| Level | When to Use |
|-------|------------|
| DEBUG | Detailed troubleshooting, model loading info |
| INFO | Normal operation, request counts |
| WARNING | Recoverable issues, slow requests |
| ERROR | Failures that affect service |
| CRITICAL | Service unavailable |

**Set in `.env`:**
```bash
MCP_LOG_LEVEL=DEBUG
```

### Log Output

**Console (default):**
```bash
python -m kyutai_mcp.server
# Output to stdout
```

**File logging:**
```bash
# Enable in .env
LOG_DIR=./logs
LOG_FORMAT=json
LOG_MAX_SIZE=100MB
LOG_BACKUP_COUNT=10
```

**View logs:**
```bash
tail -f logs/kyutai-mcp.log | jq  # Pretty-print JSON logs
```

### Debug Model Loading

```python
from kyutai_mcp import MCPServer
import logging

logging.basicConfig(level=logging.DEBUG)
server = MCPServer(log_level="DEBUG")
server.preload_models()  # Will print detailed model loading info
```

**Expected debug output:**
```
DEBUG:kyutai_mcp.models:Loading Pocket TTS model...
DEBUG:kyutai_mcp.models:Config loaded: b6369a24
DEBUG:kyutai_mcp.models:Model weights: 523MB
DEBUG:kyutai_mcp.models:Placed on device: cuda:0
DEBUG:kyutai_mcp.models:Cache saved to ~/.cache/huggingface/...
```

### Trace Requests

```bash
# Enable request logging
MCP_LOG_LEVEL=DEBUG

# Each request will show:
# INFO:kyutai_mcp.server:POST /synthesize (200) - 145ms
# INFO:kyutai_mcp.server:POST /transcribe (200) - 2341ms
```

### Performance Profiling

```python
from kyutai_mcp import MCPServer
import cProfile

server = MCPServer()

# Profile inference
profiler = cProfile.Profile()
profiler.enable()

# Run some operations...
server.synthesize_text("Hello world")

profiler.disable()
profiler.print_stats(sort="cumulative")
```

---

## Production Deployment

### Pre-Deployment Checklist

- [ ] Test all MCP tools with sample data
- [ ] Verify GPU/CPU performance baselines
- [ ] Configure monitoring (health checks, metrics)
- [ ] Set up log aggregation
- [ ] Configure resource limits
- [ ] Test failover procedures
- [ ] Document runbook

### Deployment Architectures

#### Option 1: Single Machine

```
┌──────────────────┐
│  Obsidian + MCP  │
│  (Same machine)  │
└──────────────────┘
```

**Setup:**
```bash
python -m kyutai_mcp.server --host 127.0.0.1 --port 8000
```

**Pros:** Simple, lowest latency
**Cons:** Resource contention, no redundancy

#### Option 2: Separate Server

```
┌────────────────┐           ┌──────────────────┐
│  Obsidian PC   │-----------|  MCP Server      |
│                │  HTTP/WS  │  (Linux/GPU)     │
└────────────────┘           └──────────────────┘
```

**Setup:**
```bash
# On GPU server
python -m kyutai_mcp.server --host 0.0.0.0 --port 8000

# Configure Obsidian to connect to remote server
# Settings → Kyutai MCP → MCP Server URL: http://gpu-server:8000
```

**Pros:** Better resource isolation, dedicated GPU
**Cons:** Network latency (~50-100ms), firewall needed

#### Option 3: Kubernetes

**Deployment file (`k8s-deployment.yaml`):**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kyutai-mcp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: kyutai-mcp
  template:
    metadata:
      labels:
        app: kyutai-mcp
    spec:
      containers:
      - name: mcp-server
        image: kyutai-mcp:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "8Gi"
            nvidia.com/gpu: "1"
          limits:
            memory: "16Gi"
            nvidia.com/gpu: "1"
        env:
        - name: HUGGING_FACE_HUB_TOKEN
          valueFrom:
            secretKeyRef:
              name: huggingface-token
              key: token
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
```

**Deploy:**
```bash
kubectl apply -f k8s-deployment.yaml
kubectl get pods -l app=kyutai-mcp
```

### Production Environment Variables

```bash
# Security
HUGGING_FACE_HUB_TOKEN=<secure-token>    # Use secrets manager
MCP_SECRET_KEY=<random-32-char-string>

# Performance
MCP_WORKERS=8
GPU_MEMORY_FRACTION=0.9
QUANTIZE_MODELS=true

# Monitoring
ENABLE_METRICS=true
LOG_LEVEL=INFO
LOG_FORMAT=json

# Network
MCP_HOST=0.0.0.0                         # Accept remote connections
MCP_PORT=8000
MCP_CORS_ORIGINS=https://example.com    # Restrict origins

# Resource limits
MCP_MAX_CONTENT_SIZE=52428800             # 50MB
MCP_REQUEST_TIMEOUT=300                   # 5 minutes
```

### Reverse Proxy (Nginx)

**`/etc/nginx/sites-available/kyutai-mcp`:**
```nginx
upstream kyutai_mcp {
    server localhost:8000;
}

server {
    listen 443 ssl http2;
    server_name mcp.example.com;

    ssl_certificate /etc/letsencrypt/live/mcp.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mcp.example.com/privkey.pem;

    client_max_body_size 50M;

    location / {
        proxy_pass http://kyutai_mcp;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts for long-running inference
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=mcp_limit:10m rate=10r/s;
    limit_req zone=mcp_limit burst=20 nodelay;
}
```

### Load Balancing

**Multiple server instances:**
```nginx
upstream kyutai_mcp {
    least_conn;  # Route to least busy server
    server gpu-server-1:8000;
    server gpu-server-2:8000;
    server gpu-server-3:8000;
}
```

### Monitoring in Production

**Prometheus scrape config:**
```yaml
scrape_configs:
  - job_name: 'kyutai-mcp'
    static_configs:
      - targets: ['localhost:9090']
    scrape_interval: 15s
```

**Alerting rules (`alerts.yml`):**
```yaml
- alert: KyutaiMCPDown
  expr: up{job="kyutai-mcp"} == 0
  for: 1m
  annotations:
    summary: "Kyutai MCP Server Down"

- alert: HighGPUMemory
  expr: kyutai_gpu_memory_bytes > 0.9 * kyutai_gpu_memory_total_bytes
  annotations:
    summary: "GPU Memory Usage High"

- alert: HighErrorRate
  expr: rate(kyutai_errors_total[5m]) > 0.05
  annotations:
    summary: "Error Rate > 5%"
```

---

## Next Steps

1. ✅ Configure server with appropriate settings
2. ✅ Start server and verify health
3. 📖 Read [PLUGIN_USAGE.md](./PLUGIN_USAGE.md) for client usage
4. 📖 Read [API_REFERENCE.md](./API_REFERENCE.md) for tool details
5. 📖 Read [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for support

---

**Last Updated**: 2026-02-10
**Version**: 0.1.0-alpha
