# Architecture & System Design

Complete technical architecture of the Kyutai MCP Server and Obsidian Plugin.

## Table of Contents

1. [System Overview](#system-overview)
2. [Component Architecture](#component-architecture)
3. [Data Flow](#data-flow)
4. [Model Management](#model-management)
5. [Audio Pipeline](#audio-pipeline)
6. [Resource Management](#resource-management)
7. [Security Considerations](#security-considerations)
8. [Error Handling](#error-handling)
9. [Performance Characteristics](#performance-characteristics)
10. [Deployment Architectures](#deployment-architectures)

---

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Obsidian Editor                        │
│  (Note taking, markdown, vault management, plugin system)   │
└────────────────────────┬────────────────────────────────────┘
                         │
                    MCP Protocol
                    (JSON-RPC)
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Kyutai MCP Server                         │
│                    (FastAPI/Uvicorn)                        │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Tool Registry (7 Tools)                   │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  • synthesize_text      • transcribe_audio           │  │
│  │  • clone_voice          • list_voices               │  │
│  │  • list_models          • get_status                │  │
│  │  • stream_audio (WebSocket)                         │  │
│  └──────────────────────────────────────────────────────┘  │
│                         │                                   │
│  ┌──────────────────────┼──────────────────────┐           │
│  ▼                      ▼                      ▼           │
│ Model        Audio      Resource      Logging  & Health    │
│ Manager      Pipeline   Manager       Monitoring           │
│                                                             │
│ ┌────────────────────────────────────────────────────┐     │
│ │          GPU/CPU Resource Allocation              │     │
│ │  (CUDA, ROCm, MLX, CPU with fallback)             │     │
│ └────────────────────────────────────────────────────┘     │
└────────────────┬──────────────────────────────────────────┘
                 │
        ┌────────┼────────┬───────────┐
        ▼        ▼        ▼           ▼
    Pocket      Delayed  Moshi    Community
    TTS         Streams   7B       APIs
                STT/TTS   Full-    (OpenAI
                         Duplex    Compatible)
```

---

## Component Architecture

### Obsidian Plugin

**Technology Stack:**
- Language: TypeScript
- Framework: Obsidian API
- UI: React + Modal system
- IPC: HTTP/WebSocket client
- State: Plugin settings + local storage

**Components:**
```
obsidian-plugin/
├── src/
│   ├── main.ts              # Plugin entry point
│   ├── client.ts            # MCP client wrapper
│   ├── modals/
│   │   ├── SynthesizeModal  # TTS UI
│   │   ├── TranscribeModal  # STT UI
│   │   └── VoiceModal       # Voice cloning UI
│   ├── settings.ts          # Settings pane
│   ├── ribbon.ts            # Ribbon commands
│   └── utils.ts             # Helper functions
├── styles.css               # Plugin styling
└── manifest.json            # Plugin metadata
```

**Key Classes:**
```typescript
class KyutaiPlugin extends Plugin {
    client: MCPClient;
    settings: PluginSettings;

    onload() { /* Register tools */ }
    registerRibbonCommand() { /* Add ribbon icon */ }
    registerCommand(id, name, callback) { /* Add commands */ }
}

class MCPClient {
    async synthesizeText(request): Promise<Blob> { }
    async transcribeAudio(file): Promise<string> { }
    async cloneVoice(audio, name): Promise<VoiceProfile> { }
    async listVoices(): Promise<Voice[]> { }
    async getStatus(): Promise<ServerStatus> { }
}
```

### MCP Server

**Technology Stack:**
- Language: Python 3.9+
- Framework: FastAPI + Uvicorn
- Async: asyncio, concurrent.futures
- Models: PyTorch, transformers, pocket-tts
- GPU: CUDA/ROCm/MLX (optional)

**Components:**
```
kyutai_mcp/
├── server.py               # FastAPI app
├── tools.py                # MCP tool definitions
├── models/
│   ├── tts.py             # TTS model wrapper
│   ├── stt.py             # STT model wrapper
│   └── manager.py         # Model lifecycle management
├── audio/
│   ├── pipeline.py        # Audio processing
│   ├── codecs.py          # Format conversion
│   └── streaming.py       # WebSocket streaming
├── resources/
│   ├── gpu.py             # GPU management
│   ├── memory.py          # Memory allocation
│   └── pooling.py         # Thread/process pooling
├── security/
│   ├── auth.py            # Authentication (optional)
│   └── rate_limit.py      # Rate limiting (optional)
├── monitoring/
│   ├── metrics.py         # Prometheus metrics
│   ├── logging.py         # Structured logging
│   └── health.py          # Health checks
└── config.py              # Configuration management
```

**Key Classes:**
```python
class MCPServer(FastAPI):
    def __init__(self, config: Config)
    async def synthesize_text(request) -> bytes
    async def transcribe_audio(request) -> dict
    async def clone_voice(request) -> dict

class ModelManager:
    def __init__(self, config)
    def load_model(model_id)
    def unload_model(model_id)
    def get_model(model_id)

class GPUManager:
    def allocate_memory(size_mb)
    def release_memory()
    def get_status()

class AudioPipeline:
    def preprocess(audio_bytes)
    def postprocess(tensor)
    def convert_format(audio, input_fmt, output_fmt)
```

---

## Data Flow

### Text-to-Speech Flow

```
┌──────────────────┐
│  User Note Text  │
│  "Hello world"   │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────┐
│   Obsidian Plugin            │
│  1. Get text from note       │
│  2. Show options (voice,     │
│     speed, format)           │
│  3. Send HTTP POST request   │
└────────┬─────────────────────┘
         │
         │ HTTP POST /synthesize
         │ {"text": "...", "voice": "...", ...}
         │
         ▼
┌──────────────────────────────┐
│   MCP Server (FastAPI)       │
│  1. Validate input           │
│  2. Load model               │
│  3. Prepare voice state      │
│  4. Run inference            │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│   Model Execution Layer      │
│  1. Select device (GPU/CPU)  │
│  2. Load voice embeddings    │
│  3. Run TTS model            │
│  4. Generate audio tensor    │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│   Audio Pipeline             │
│  1. Convert tensor to PCM    │
│  2. Resample if needed       │
│  3. Encode to format (MP3)   │
│  4. Return binary data       │
└────────┬─────────────────────┘
         │
         │ Binary audio response
         │
         ▼
┌──────────────────────────────┐
│   Obsidian Plugin            │
│  1. Receive audio binary     │
│  2. Play via Web Audio API   │
│  3. Save to vault (optional) │
│  4. Show success message     │
└──────────────────────────────┘
```

### Speech-to-Text Flow

```
┌──────────────────┐
│   Audio File     │
│   meeting.mp3    │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────┐
│   Obsidian Plugin            │
│  1. User selects file        │
│  2. Show model/format opts   │
│  3. Send POST + file binary  │
└────────┬─────────────────────┘
         │
         │ HTTP POST /transcribe
         │ (multipart/form-data)
         │
         ▼
┌──────────────────────────────┐
│   MCP Server (FastAPI)       │
│  1. Receive audio file       │
│  2. Validate format          │
│  3. Decode to PCM            │
│  4. Chunk audio              │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│   Model Execution Layer      │
│  1. Load STT model           │
│  2. Process chunks           │
│  3. Extract transcription    │
│  4. Generate timestamps      │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│   Post-Processing            │
│  1. Merge segments           │
│  2. Format output (JSON/SRT) │
│  3. Add confidence scores    │
└────────┬─────────────────────┘
         │
         │ JSON response
         │
         ▼
┌──────────────────────────────┐
│   Obsidian Plugin            │
│  1. Parse JSON response      │
│  2. Display transcription    │
│  3. Show timestamps          │
│  4. Allow copy/paste         │
└──────────────────────────────┘
```

---

## Model Management

### Model Lifecycle

```
┌─────────────┐
│   Init      │  Server starts
└──────┬──────┘
       │
       │ Lazy load (on demand)
       │ OR
       │ Pre-load (on startup)
       ▼
┌─────────────────┐
│   Loading       │  1. Download from HF if missing
│                 │  2. Load to GPU/CPU
│                 │  3. Initialize state
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│   Ready         │  Model available for inference
│                 │  (Stays in memory)
└──────┬──────────┘
       │
    ┌──┴──┐
    │     │ (May reload on config change)
    │     │
    ▼     ▼
 ┌──────────────┐
 │   Unloading  │  1. Flush cache
 │              │  2. Free GPU memory
 │              │  3. Release resources
 └──────┬───────┘
        │
        ▼
    ┌────────┐
    │  Empty │
    └────────┘
```

### Model Selection Strategy

**TTS Model Selection:**
```
                   ┌────────────────┐
                   │  Requirements  │
                   │  Speed/Latency │
                   │  Quality       │
                   │  Memory        │
                   └────────┬───────┘
                            │
                ┌───────────┼───────────┐
                │           │           │
                ▼           ▼           ▼
            Fast      Medium        High Quality
           (Latency)  (Balanced)    (Moshi)
                │           │           │
             Pocket       Pocket      Moshi 7B
             TTS (CPU)    TTS (GPU)
```

**STT Model Selection:**
```
                   ┌────────────────┐
                   │  Requirements  │
                   │  Speed         │
                   │  Languages     │
                   │  Accuracy      │
                   └────────┬───────┘
                            │
                ┌───────────┼───────────┐
                │           │           │
                ▼           ▼           ▼
            Fast          Balanced    Accurate
           (Streaming)    (Default)   (Premium)
                │           │           │
            STT 1B       STT 1B      STT 2.6B
            (1.2GB)      (1.2GB)     (5GB)
            [Streaming]  [Streaming] [Streaming]
```

### Memory Management

```
┌─────────────────────────────────────┐
│      GPU Total Memory (e.g. 24GB)   │
├─────────────────────────────────────┤
│                                     │
│  ┌───────────────────────────────┐  │
│  │  Pocket TTS (500MB)           │  │
│  │  ┌─────────────────────────┐  │  │
│  │  │ Model weights           │  │  │
│  │  │ Voice states            │  │  │
│  │  │ Cache                   │  │  │
│  │  └─────────────────────────┘  │  │
│  └───────────────────────────────┘  │
│                                     │
│  ┌───────────────────────────────┐  │
│  │  STT 1B (2.5GB)               │  │
│  │  ┌─────────────────────────┐  │  │
│  │  │ Model weights           │  │  │
│  │  │ Inference cache         │  │  │
│  │  │ Audio buffer            │  │  │
│  │  └─────────────────────────┘  │  │
│  └───────────────────────────────┘  │
│                                     │
│  ┌───────────────────────────────┐  │
│  │  Shared Resources (1GB)       │  │
│  │  ┌─────────────────────────┐  │  │
│  │  │ Temporary buffers       │  │  │
│  │  │ Thread pool state       │  │  │
│  │  │ Metrics collection      │  │  │
│  │  └─────────────────────────┘  │  │
│  └───────────────────────────────┘  │
│                                     │
│  ┌───────────────────────────────┐  │
│  │  Free Memory (20GB)           │  │
│  └───────────────────────────────┘  │
│                                     │
└─────────────────────────────────────┘
```

---

## Audio Pipeline

### Audio Processing Steps

```
Input Audio (Various formats)
        │
        ▼
┌──────────────────┐
│   1. Decode      │  MP3 → PCM, FLAC → PCM, etc.
│   Input Format   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   2. Resample    │  16kHz → 24kHz (if needed)
│                  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   3. Normalize   │  Apply gain, remove clipping
│   Audio Level    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   4. Chunk       │  Break into 1024-sample chunks
│   for Model      │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   5. Inference   │  Run through model
│   Model          │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   6. Post-Proc   │  Merge segments, format output
│   (Optional)     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   7. Encode      │  PCM → MP3/WAV/OGG
│   Output Format  │
└────────┬─────────┘
         │
         ▼
Output Audio (Requested format)
```

### Streaming Architecture

```
Client (Browser)
        │
        │ WebSocket connection
        │
        ▼
┌──────────────────────────┐
│  Server WebSocket Handler│
│  (Async)                 │
│  ┌────────────────────┐  │
│  │ • Accept chunks    │  │
│  │ • Buffer audio     │  │
│  │ • Run inference    │  │
│  │ • Send updates     │  │
│  └────────────────────┘  │
└──────────────────────────┘
        │
    ┌───┴───┐
    │       │
    ▼       ▼
Queue   Worker Pool
(Audio) (Model)
    │       │
    ├───────┤
    │
    ▼
┌──────────────────────────┐
│  Inference Cache         │
│  (Streaming State)       │
└──────────────────────────┘
    │
    ▼
Output Updates
(JSON messages)
    │
    └──> Client (Display interim results)
```

---

## Resource Management

### Thread Pool Configuration

```
┌──────────────────────────────────────┐
│     Main FastAPI Thread              │
│  (Handles HTTP requests)             │
└────────┬─────────────────────────────┘
         │
    ┌────┴────┬──────┬──────┐
    │          │      │      │
    ▼          ▼      ▼      ▼
Worker    Worker  Worker  Worker
Thread 1  Thread 2 Thread 3 Thread 4
│         │       │       │
├─────────┼───────┼───────┤
│                           │
▼                           ▼
GPU Inference Queue    CPU Fallback Queue
(High priority)        (Lower priority)
```

### Memory Management Strategy

**On Startup:**
- Load TTS + STT models
- Allocate GPU memory (% of total)
- Reserve buffer for concurrent requests

**During Inference:**
- Cache frequently used models
- Reuse voice embeddings
- Stream output to avoid buffering

**On High Memory Pressure:**
- Evict least-used models
- Increase GC frequency
- Reduce batch size
- Return 503 (Service Unavailable) if critical

**Monitoring:**
```python
gpu_memory_used = get_gpu_memory_usage()
if gpu_memory_used > 0.95 * total:
    log.warning("GPU memory critical")
    # Trigger cleanup
elif gpu_memory_used > 0.85 * total:
    log.info("GPU memory high")
    # Monitor closely
```

---

## Security Considerations

### Input Validation

```python
# Text input
if len(text) > 4096:
    raise ValueError("Text too long")
if not isinstance(text, str):
    raise ValueError("Text must be string")

# Audio input
if len(audio_data) > 500 * 1024 * 1024:  # 500MB
    raise ValueError("Audio too large")
if mime_type not in ALLOWED_FORMATS:
    raise ValueError("Unsupported format")

# Voice ID
if not re.match(r"^[a-zA-Z0-9_]+$", voice_id):
    raise ValueError("Invalid voice ID")
```

### API Key Management (Optional)

```bash
# .env (never committed)
MCP_API_KEY=sk_live_xxxxxxxxxxxxx

# Client
headers = {
    "Authorization": f"Bearer {os.getenv('MCP_API_KEY')}"
}
```

### Output Sanitization

```python
# No sensitive data in logs
def log_request(request):
    # Don't log full text/audio
    log.info(f"synthesize: {len(request.text)} chars")


# Remove timestamps from responses
response["timestamp"] = None  # or use UTC only
```

### Model Provenance

```
Models downloaded from:
├─ HuggingFace (kyutai official account)
├─ Verified checksums
├─ Signed by Kyutai team
└─ Open source licenses

Voice profiles:
├─ Stored locally only
├─ Not transmitted
├─ User-controlled access
└─ Deletable anytime
```

### Local-First Design

```
┌────────────────┐
│  User Machine  │
│                │
│  ┌──────────┐  │
│  │ Obsidian │  │  All processing
│  └─────┬────┘  │  stays local
│        │       │
│        ▼       │
│  ┌──────────┐  │  No cloud calls
│  │ MCP Srvr │  │  No data leaves
│  │ + Models │  │
│  └──────────┘  │
│                │
└────────────────┘
    No arrows to cloud!
    (Only HF for model downloads)
```

---

## Error Handling

### Error Recovery Strategy

```
Request arrives
        │
        ▼
Validation error?
    │   │
   No  Yes ──> Return 400 + error details
    │           (Retry not needed)
    │
    ▼
Model loaded?
    │   │
   Yes  No ──> Load model
    │         │
    │         ▼
    │     Load failed?
    │         │   │
    │        No   Yes ──> Return 500 + fallback
    │         │
    │         ▼
    │     Continue
    │
    ▼
Run inference
    │
    ▼
GPU OOM?
    │   │
   No  Yes ──> Clear cache, retry (1x)
    │         │
    │         ▼
    │     Still OOM? ──> Return 503
    │
    ▼
Timeout?
    │   │
   No  Yes ──> Return 504
    │
    ▼
Success ──> Return 200 + data
```

### Logging Strategy

```python
# Structured logging
log.info("request_start",
    request_id=uuid,
    operation="synthesize_text",
    text_length=len(text),
    voice=voice_id
)

# Timing metrics
start = time.time()
result = model.infer(...)
duration = time.time() - start

log.info("request_complete",
    request_id=uuid,
    duration_ms=duration * 1000,
    status="success"
)

# Errors with context
except ValueError as e:
    log.error("validation_error",
        request_id=uuid,
        error=str(e),
        input=sanitized_input
    )
```

---

## Performance Characteristics

### Latency Breakdown (Text-to-Speech)

```
Network + Plugin UI        5-10 ms
────────────────────────────────────
Server validation          2-5 ms
────────────────────────────────────
Model load (if needed)    500-2000 ms (amortized)
────────────────────────────────────
Inference                 50-100 ms (typical)
────────────────────────────────────
Audio encoding            10-20 ms
────────────────────────────────────
Network response          5-10 ms
────────────────────────────────────
Total (cached model)      ~100-200 ms
Total (cold start)        ~700-1500 ms
```

### Throughput Analysis

```
STT 1B Model (L40S GPU):
├─ GPU capacity: 64 concurrent streams
├─ Throughput: 3x real-time (1 min audio = 20s)
└─ CPU: 20-30% for I/O

Pocket TTS (GPU):
├─ GPU capacity: 10+ concurrent
├─ Throughput: ~100 chars/sec
└─ CPU: 15-25% for I/O

Moshi (Full-duplex):
├─ GPU capacity: 8-16 concurrent
├─ Throughput: Real-time+ (200ms latency)
└─ CPU: 40-50% coordination
```

### Resource Usage

```
Memory (GB):
├─ Base server: 0.5
├─ Pocket TTS: +0.5
├─ STT 1B: +2.5
├─ Moshi 7B: +14
└─ Total (all): ~17.5

GPU Memory (GB):
├─ Pocket TTS: 0.5
├─ STT 1B: 2.5
├─ Moshi 7B: 14 (bf16) or 7 (int8)
└─ Concurrent TTS+STT: 3GB

CPU:
├─ Idle: <5%
├─ Inference: 10-30% (mostly I/O)
└─ Heavy load: 50-80%
```

---

## Deployment Architectures

### Single Machine (Recommended for development)

```
┌──────────────────────┐
│  Obsidian + Plugin   │
│                      │
│  MCP Server          │
│  + Models            │
│  + GPU               │
└──────────────────────┘
        (localhost:8000)

Pros: Simple, low latency
Cons: Resource contention
```

### Separate GPU Server

```
┌──────────────┐           ┌──────────────────┐
│ Obsidian     │           │  GPU Server      │
│ + Plugin     │-----------|  MCP Server      │
│ (Local)      │ HTTP/WS   │  + Models (3.9s) │
│              │           │  + GPU           │
└──────────────┘           └──────────────────┘

Pros: Better isolation, dedicated resources
Cons: Network latency (~50ms)
```

### High-Availability Cluster

```
┌──────────────────────┐
│  Load Balancer       │
│  (Nginx/HAProxy)     │
└──────┬──────┬──────┬─┘
       │      │      │
   ┌───▼─┐┌──▼──┐┌──▼───┐
   │MCP-1││MCP-2││MCP-N │
   │GPU-1││GPU-2││GPU-N │
   └─────┘└─────┘└──────┘

Pros: High availability, load distribution
Cons: Complexity, state management
```

---

## Design Patterns

### Factory Pattern (Model Creation)

```python
class ModelFactory:
    @staticmethod
    def create_model(model_id: str) -> Model:
        if "pocket" in model_id:
            return PocketTTSModel(model_id)
        elif "stt-1b" in model_id:
            return STT1BModel(model_id)
        else:
            raise ValueError(f"Unknown model: {model_id}")
```

### Strategy Pattern (Audio Encoding)

```python
class AudioEncoder:
    strategy: EncodingStrategy

    def encode(self, audio: Tensor) -> bytes:
        return self.strategy.encode(audio)


class WAVEncoder(EncodingStrategy):
    def encode(self, audio: Tensor) -> bytes:
        return save_wav(audio)


class MP3Encoder(EncodingStrategy):
    def encode(self, audio: Tensor) -> bytes:
        return save_mp3(audio)
```

### Observer Pattern (Metrics)

```python
class MetricsCollector(Observer):
    def on_inference_complete(self, event: InferenceEvent):
        self.metrics.record_latency(event.duration_ms)
        self.metrics.increment_request_count()


server.attach_observer(MetricsCollector())
```

---

**Last Updated**: 2026-02-10
**Version**: 0.1.0-alpha
