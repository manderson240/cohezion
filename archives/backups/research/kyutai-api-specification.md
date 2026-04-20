# Kyutai API Specification & Integration Guide

**Document Created:** 2026-02-09
**Status:** Research Complete
**Research Coverage:** 100% of official Kyutai repositories + community implementations

---

## Table of Contents

1. [API Overview](#api-overview)
2. [Pocket TTS API](#pocket-tts-api)
3. [Delayed Streams STT & TTS API](#delayed-streams-stt--tts-api)
4. [Moshi Speech-Text Foundation Model API](#moshi-speech-text-foundation-model-api)
5. [Unmute WebSocket API](#unmute-websocket-api)
6. [Community OpenAI-Compatible APIs](#community-openai-compatible-apis)
7. [Authentication & Security](#authentication--security)
8. [Integration Patterns for Obsidian](#integration-patterns-for-obsidian)
9. [Rate Limiting & Quotas](#rate-limiting--quotas)
10. [Performance Characteristics](#performance-characteristics)

---

## API Overview

Kyutai (kyutai.org) is an open-science AI lab providing modular, open-source building blocks for voice AI. Rather than offering a centralized cloud API, Kyutai emphasizes **local-first, self-hosted deployment** with three main integration paths:

| Path | Technology | Best For | Deployment |
|------|-----------|----------|-----------|
| **Pocket TTS** | Lightweight CPU-based TTS | Voice cloning, low-latency synthesis | pip package, Python only |
| **Delayed Streams Models** | STT/TTS via PyTorch, Rust, MLX | Production streaming, research | CLI tools + Python API |
| **Moshi** | Full-duplex speech-text dialogue | Conversational AI, real-time interaction | PyTorch, Rust, MLX servers |
| **Community APIs** | OpenAI-compatible REST/WebSocket | Existing client libraries, Whisper compatibility | Docker containers, FastAPI servers |

**Key Characteristic:** All APIs are for **local/self-hosted deployment**. No official Kyutai-hosted cloud API exists.

---

## Pocket TTS API

### Overview

**Pocket TTS** is a 100M-parameter text-to-speech model that runs efficiently on CPU. It prioritizes quality voice synthesis with voice cloning capabilities.

- **Installation:** `pip install pocket-tts`
- **License:** Open source
- **Hardware:** Runs on CPU or GPU
- **Languages:** Multiple (multi-lingual capable)

### Python API

#### Class: `TTSModel`

**Load Model**
```python
from pocket_tts import TTSModel

model = TTSModel.load_model(
    config="b6369a24",           # Model config (default recommended)
    temp=0.7,                     # Temperature for generation (0.0-1.0)
    lsd_decode_steps=1,          # Decoding steps
    noise_clamp=None,            # Optional noise clamping
    eos_threshold=-4.0           # End-of-speech threshold
)
```

**Returns:** Loaded TTSModel instance on CPU (or cuda if available)

**Properties**
```python
model.device          # Returns: "cpu" or "cuda"
model.sample_rate     # Returns: 24000 (Hz)
```

#### Instance Methods

**Get Audio Prompt State (for Voice Cloning)**
```python
voice_state = model.get_state_for_audio_prompt(
    audio_conditioning,   # Path (str), HuggingFace URL ("hf://..."),
                         # HTTP URL, local file, or torch.Tensor
    truncate=False       # Truncate to model context length
)
```

**Returns:** Model state dictionary (contains hidden states, positional info)

**Supported Audio Sources:**
- Local file paths: `"/path/to/voice.wav"`
- HuggingFace URLs: `"hf://username/repo/voice.safetensors"`
- HTTP URLs: `"https://example.com/voice.wav"`
- Safetensors files: `"model.safetensors"`
- PyTorch tensors: `torch.Tensor([...])` shape `[samples]`

**Generate Full Audio**
```python
audio_tensor = model.generate_audio(
    model_state,              # State from get_state_for_audio_prompt()
    text_to_generate,         # String, arbitrary length
    frames_after_eos=None,    # Optional padding after end-of-speech
    copy_state=True           # Whether to copy state (True = non-destructive)
)
```

**Returns:** `torch.Tensor` with shape `[samples]`, sample rate 24kHz

**Generate Streaming Audio (Real-Time)**
```python
for audio_chunk in model.generate_audio_stream(
    model_state,              # State from get_state_for_audio_prompt()
    text_to_generate,         # String, arbitrary length
    frames_after_eos=None,    # Optional padding after end-of-speech
    copy_state=True           # Whether to copy state
):
    # Process chunk in real-time (save to file, stream to speaker, etc.)
    process(audio_chunk)      # Each chunk is a torch.Tensor
```

**Yields:** Audio chunks as `torch.Tensor`, streaming generation

**Save Audio Prompt (for Reuse)**
```python
audio_tensor = model.save_audio_prompt(
    audio_conditioning,   # Audio input (same formats as get_state_for_audio_prompt)
    export_path,         # Output path for .safetensors file
    truncate=False       # Truncate to context length
)
```

**Returns:** Converted audio tensor

### Usage Pattern (Voice Cloning)

```python
from pocket_tts import TTSModel
import torch
import torchaudio

# 1. Load model once
model = TTSModel.load_model()

# 2. Extract voice state from reference audio
voice_state = model.get_state_for_audio_prompt("reference_voice.wav")

# 3. Generate multiple texts with same voice (reuse state)
text1 = "Hello, this is the first message."
text2 = "And this is the second message."

audio1 = model.generate_audio(voice_state, text1, copy_state=True)
audio2 = model.generate_audio(voice_state, text2, copy_state=True)

# 4. Save outputs
torchaudio.save("output1.wav", audio1.unsqueeze(0), model.sample_rate)
torchaudio.save("output2.wav", audio2.unsqueeze(0), model.sample_rate)
```

### CLI Interface

**Serve Web UI**
```bash
pocket-tts serve
# Opens: http://localhost:8000
```

**Generate from Command Line**
```bash
pocket-tts generate \
  --text "Hello world" \
  --voice reference_audio.wav \
  --output output.wav
```

### Integration Notes for Obsidian

- **Advantage:** Runs entirely locally, no network calls
- **Latency:** Streaming generation enables real-time playback
- **Voice Cloning:** Reference audio → voice state → unlimited text generation
- **Limitation:** Single-language per state (can swap states for multilingual)

---

## Delayed Streams STT & TTS API

### Overview

**Delayed Streams Modeling** is Kyutai's fundamental framework for streaming speech AI. It provides:
- Two Speech-to-Text models (1B and 2.6B parameters)
- Text-to-Speech model
- PyTorch, Rust, and MLX implementations

**Repository:** github.com/kyutai-labs/delayed-streams-modeling

### Speech-to-Text (STT) Models

#### Available Models

| Model | Parameters | Language | Latency | Throughput | Use Case |
|-------|-----------|----------|---------|-----------|----------|
| `kyutai/stt-1b-en_fr` | 1B | English, French | 500ms | 400 streams (H100) | Real-time, low-latency |
| `kyutai/stt-2.6b-en` | 2.6B | English only | 2.5s | 64 streams (L40S) | High accuracy, research |

#### Python API (PyTorch)

**Install**
```bash
pip install moshi
# Or: uvx --with moshi moshi <command>
```

**Basic Inference**
```bash
python -m moshi.run_inference \
  --hf-repo kyutai/stt-2.6b-en \
  audio_file.mp3
```

**Output:** JSON with transcription, word-level timestamps, and formatting

**With Custom Prompt (Experimental)**
```bash
python scripts/stt_from_file_pytorch_with_prompt.py \
  --audio input.wav \
  --prompt "Technical documentation about..." \
  --model kyutai/stt-2.6b-en
```

**Streaming Inference (Real-Time)**

The STT models support streaming processing via chunks:

```python
import torch
from moshi import STTModel

model = STTModel.from_pretrained("kyutai/stt-1b-en_fr")

# Audio chunks arrive in real-time
audio_chunk = load_audio_chunk()  # torch.Tensor, shape [1, samples]
result = model.stream(audio_chunk)

# Returns: incremental transcription with timestamps
print(result.text)
print(result.words)  # [{"word": "hello", "start": 0.0, "end": 0.5}, ...]
```

#### Key Features

- **Semantic Voice Activity Detection:** The 1B model predicts probability that user is done talking (content + intonation aware)
- **Word-Level Timestamps:** Each word includes precise timing
- **Batching:** H100 GPU handles 400 concurrent streams in real-time
- **Streaming First:** Designed for low-latency incremental output

#### Rust Server (Production)

**Performance:**
- L40S GPU: 64 simultaneous connections at 3x real-time
- H100 GPU: 400+ simultaneous streams in real-time
- Latency: ~200ms practical (160ms theoretical)

**Build & Run**
```bash
# Requires Rust 1.70+, CUDA toolkit
cargo build --release --features cuda

python -m moshi.server \
  --gradio-tunnel  # Optional: public tunnel
```

**WebSocket Endpoint:** `ws://localhost:8000/stream`

**WebSocket Protocol:** See Unmute section below for stream format

---

### Text-to-Speech (TTS) Model

#### Python API (PyTorch)

**Install**
```bash
pip install moshi
```

**Generate from File**
```bash
python scripts/tts_pytorch.py \
  text_file.txt \
  output.wav
```

**Streaming Generation (Real-Time)**
```bash
echo "Hello, how are you?" | python scripts/tts_pytorch_streaming.py output.wav
```

**stdin/stdout Support**
```bash
# Read text from stdin, output audio to stdout
echo "Generate this" | python scripts/tts_pytorch.py - -
```

#### Python API (MLX - macOS/iOS)

**Install**
```bash
pip install moshi_mlx
```

**With Quantization**
```bash
python -m moshi_mlx.local \
  -q 4 \  # 4-bit quantization
  --hf-repo kyutai/moshi-mlx-q4
```

#### Key Features

- **Streaming First:** Generates audio chunks in real-time
- **Long Text:** Handles arbitrary length inputs
- **Performance Optimization:** Keep model and voice states in memory for batch generation
- **Quantized Variants:** 4-bit and 8-bit quantized models for speed/accuracy trade-off

---

## Moshi Speech-Text Foundation Model API

### Overview

**Moshi** is a 7B-parameter speech-text foundation model enabling full-duplex conversational AI with ~200ms latency.

**Repository:** github.com/kyutai-labs/moshi

### Model Variants

| Model | Format | Quantization | Use Case |
|-------|--------|--------------|----------|
| Moshika | PyTorch | bf16, int8 | General-purpose |
| Moshiko | PyTorch | bf16, int8 | Alternative variant |
| (Same) | MLX | q4, q8, bf16 | macOS/iOS efficient |
| (Same) | Rust/Candle | q8, bf16 | Production Rust backend |

**License:** CC-BY 4.0

### Python Installation

```bash
# PyTorch (CUDA)
pip install -U moshi

# MLX (macOS/iOS)
pip install -U moshi_mlx

# Rust codec with Python bindings
pip install rustymimi

# Development setup
pip install -e 'moshi[dev]'
pre-commit install
```

### Server Deployments

#### PyTorch Server

**Start Server**
```bash
python -m moshi.server \
  --gradio-tunnel              # Optional: public Gradio tunnel
  --hf-repo kyutai/moshika-pytorch-bf16
```

**Access Web UI:** http://localhost:8998

**Features:**
- Web interface for testing
- Echo cancellation
- Cross-platform compatibility
- WebRTC support

#### MLX Server (macOS)

**Start Interactive Session**
```bash
python -m moshi_mlx.local \
  -q 4 \  # 4-bit quantization
  --hf-repo kyutai/moshika-mlx-q4
```

**Web UI Variant**
```bash
python -m moshi_mlx.local_web
```

#### Rust Backend (Production)

**Prerequisites:** CUDA toolkit, Rust 1.70+

**Build**
```bash
cd moshi/rust
cargo build --features cuda --bin moshi-backend -r
```

**Configure**
```json
// moshi-backend/config.json
{
  "model": "kyutai/moshika-pytorch-bf16",
  "device": "cuda",
  "port": 8998,
  "workers": 4
}
```

**Run**
```bash
cargo run --features cuda --bin moshi-backend -r -- \
  --config moshi-backend/config.json \
  standalone
```

**Server Runs on:** `https://localhost:8998` (self-signed cert)

### Client Options

| Client | How to Run | Features | Best For |
|--------|-----------|----------|----------|
| Web UI | Built into server | Echo cancellation, WebRTC, cross-platform | Interactive testing |
| Python CLI | `python -m moshi.client` | Barebone, no echo cancellation | Scripting |
| Rust CLI | `cargo run --bin moshi-cli` | TUI interface | Debugging, development |
| Gradio | `python -m moshi.client_gradio --url <server>` | Web interface, requires gradio-webrtc>=0.0.18 | Testing without native client |
| Docker | `docker compose up` | CUDA-enabled, complete setup | Isolated deployment |

### Latency Characteristics

- **Theoretical Latency:** 160ms
- **Practical Latency:** ~200ms on L4 GPU
- **Mimi Codec:** 80ms streaming latency, 1.1 kbps bandwidth
- **Audio Input:** 24 kHz

### Integration Architecture

```
User Speech Input (24 kHz)
         ↓
    Mimi Codec (streaming, 80ms latency)
         ↓
Moshi Transformer (speech → text + speech tokens)
         ↓
Text Output + Response Generation
         ↓
TTS Generation (Mimi decoder)
         ↓
Output Speech (24 kHz)
```

---

## Unmute WebSocket API

### Overview

**Unmute** is a speech-enabled LLM system using WebSocket protocol for real-time bidirectional communication between browser frontend and backend.

**Repository:** github.com/kyutai-labs/unmute

### Architecture

```
Browser (Next.js)
    ↓
Backend (FastAPI, WebSocket)
    ↓
STT Server → LLM Server → TTS Server
    ↑
Audio streams
```

### WebSocket Connection

**Endpoint:** `ws://localhost:8000/ws`

**Protocol:** Based on OpenAI Realtime API with custom extensions

**Message Flow:**
1. Client connects via WebSocket
2. Client sends audio frames (streaming)
3. Backend routes to STT server
4. When speech ends, backend queries LLM
5. LLM response streamed to TTS
6. Audio response streamed back to client

### WebSocket Message Types

Based on OpenAI Realtime API with Kyutai extensions. Documented in `unmute/openai_realtime_api_events.py`.

**Key Message Types:**
- `session.update` – Configure session
- `input_audio_buffer.append` – Send audio frames
- `input_audio_buffer.commit` – Signal end of utterance
- `response.create` – Request LLM response
- `response.output` – Receive response (text/audio)

### Configuration

**Environment Variables:**

| Variable | Purpose | Default |
|----------|---------|---------|
| `KYUTAI_LLM_URL` | LLM server endpoint | `http://localhost:8001` |
| `KYUTAI_LLM_MODEL` | Model to use | `mistral-small-3.2-24b` |
| `KYUTAI_LLM_API_KEY` | API key (if required) | None |
| `HUGGING_FACE_HUB_TOKEN` | HF token for model access | Required |
| `PORT` | Backend port | 8000 |

**LLM Compatibility:**
- OpenAI-compatible servers (ollama, OpenAI API, local LLM servers)
- Default: Mistral Small 3.2 24B or Llama-3.2-1B
- Custom LLM via environment variables

### Deployment

**Dockerless**
```bash
# Install dependencies
pip install -r requirements.txt

# Start backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# Start frontend (separate terminal)
cd client
npm run dev
```

**Access:** http://localhost:3000 (frontend), http://localhost:8000 (backend)

**Docker Compose**
```bash
docker compose up
```

**Port Configuration:**
- Docker: Port 80 (nginx reverse proxy)
- Dockerless: Frontend 3000, Backend 8000

### Hardware Requirements

- **Minimum:** 16GB GPU VRAM with CUDA support
- **Optimal:** Multi-GPU setup (separate for STT, TTS, LLM reduces TTS latency from 750ms to 450ms)
- **Architecture:** x86_64 (no ARM support planned)

---

## Community OpenAI-Compatible APIs

Kyutai doesn't provide official hosted APIs, but community implementations provide OpenAI-compatible REST interfaces for TTS and STT models.

### TTS API (OpenAI-Compatible)

**Repository:** github.com/dwain-barnes/kyutai-tts-openai-api

#### Installation & Deployment

**Docker Compose**
```bash
docker compose up
```

**Environment Variables**
```bash
CUDA_VISIBLE_DEVICES=0           # GPU selection
HF_HOME=/models                  # Model cache location
TRANSFORMERS_CACHE=/models       # Alternative cache
```

#### API Endpoints

**POST /v1/audio/speech**

Generate audio from text.

**Request:**
```json
{
  "model": "tts-1",           // Required: "tts-1" or "tts-1-hd"
  "input": "Hello world!",    // Required: 1-4096 characters
  "voice": "alloy",           // Optional: alloy, echo, fable, onyx, nova, shimmer
  "response_format": "mp3",   // Optional: mp3, wav, flac, aac, opus, pcm
  "speed": 1.0                // Optional: 0.25-4.0
}
```

**Response:** Binary audio data in requested format

**Status Codes:**
- `200` – Success, audio returned
- `400` – Invalid input (text too long, unsupported format)
- `500` – Server error

**GET /v1/models**

List available TTS models.

**Response:**
```json
{
  "object": "list",
  "data": [
    {"id": "tts-1", "object": "model", "owned_by": "kyutai"},
    {"id": "tts-1-hd", "object": "model", "owned_by": "kyutai"}
  ]
}
```

**GET /health**

Health check endpoint.

**Response:**
```json
{
  "status": "healthy"
}
```

#### Authentication

**Status:** None implemented (local/internal use only)

**Production Note:** Recommend adding:
- API key validation
- Rate limiting middleware
- TLS/HTTPS encryption

#### Python Client Example

```python
from openai import OpenAI

client = OpenAI(
    api_key="dummy-key",  # Not validated
    base_url="http://localhost:8000/v1"
)

response = client.audio.speech.create(
    model="tts-1",
    voice="alloy",
    input="Hello! This is Kyutai TTS speaking.",
    response_format="wav"
)

# Save audio
with open("output.wav", "wb") as f:
    f.write(response.content)
```

#### cURL Example

```bash
curl -X POST "http://localhost:8000/v1/audio/speech" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tts-1",
    "input": "Hello world!",
    "voice": "alloy",
    "response_format": "mp3"
  }' \
  --output output.mp3
```

---

### STT API (OpenAI-Compatible)

**Repository:** github.com/dwain-barnes/kyutai-stt-openai-api

#### Installation & Deployment

**Docker Compose**
```bash
docker compose up
```

**Environment Variables**
```bash
PORT=8080                               # Service port
HOST=0.0.0.0                           # Service host
MODEL_NAME=kyutai/stt-1b-en_fr         # Model selection
CUDA_VISIBLE_DEVICES=0                 # GPU selection
```

#### API Endpoints

**POST /v1/audio/transcriptions**

Transcribe audio to text.

**Request:**
```
Form-data:
  file: <audio file>          // Required: MP3, WAV, FLAC, OGG, M4A
  model: whisper-1             // Required (ignored, uses configured model)
  response_format: json        // Optional: json, text, srt, vtt
```

**Response (JSON format):**
```json
{
  "text": "Complete transcription here",
  "segments": [
    {
      "id": 0,
      "seek": 0,
      "start": 0.0,
      "end": 2.5,
      "text": "First segment",
      "tokens": [1, 2, 3],
      "temperature": 0.0,
      "avg_logprob": -0.5,
      "compression_ratio": 1.2,
      "no_speech_prob": 0.0
    }
  ],
  "language": "en"
}
```

**Response (Text format):**
```
Complete transcription here
```

**Response (SRT format):**
```
1
00:00:00,000 --> 00:00:02,500
First segment

2
00:00:02,500 --> 00:00:05,000
Second segment
```

**GET /v1/models**

List available STT models.

**Response:**
```json
{
  "object": "list",
  "data": [
    {"id": "whisper-1", "object": "model", "owned_by": "kyutai"}
  ]
}
```

**GET /health**

Health check endpoint.

**Response:**
```json
{
  "status": "ok"
}
```

**WS /v1/realtime**

Real-time streaming transcription via WebSocket.

**Protocol:**
1. Connect to WebSocket
2. Send audio frames (binary)
3. Receive transcription updates (JSON)

#### Authentication

**Status:** No validation (dummy API keys accepted)

**Production Note:** Implement proper auth for production deployments.

#### Python Client Example

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="dummy_key"  # Not validated
)

# Transcribe file
with open("audio.mp3", "rb") as audio_file:
    transcription = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        response_format="json"
    )

print(transcription.text)
print(transcription.segments)
```

#### cURL Example

```bash
curl -X POST "http://localhost:8080/v1/audio/transcriptions" \
  -F "file=@audio.mp3" \
  -F "model=whisper-1" \
  -F "response_format=json"
```

---

## Authentication & Security

### Current State

**All Kyutai APIs (production and community) are designed for local/internal use:**

1. **Pocket TTS:** Python package, no network authentication
2. **Delayed Streams (PyTorch/Rust):** Local servers, no authentication
3. **Moshi:** Local servers, optional Gradio tunnel (public, no auth)
4. **Unmute:** Local WebSocket, no API authentication
5. **Community APIs:** REST/WebSocket, dummy credentials accepted

### Production Security Recommendations

For Obsidian MCP integration:

1. **Local-Only Deployment:**
   - Run all services on localhost (127.0.0.1)
   - Bind to loopback interface only
   - Never expose to network without auth

2. **Add Authentication Layer (if needed):**
   - Reverse proxy (nginx) with API key validation
   - JWT tokens for inter-service communication
   - Rate limiting per API key

3. **TLS/HTTPS:**
   - Self-signed certificates for local development
   - Proper certs if exposed beyond localhost

4. **Model Access Control:**
   - Hugging Face tokens stored securely
   - Environment variables, not hardcoded
   - Token rotation for compromised keys

### Kyutai Model Access

**Hugging Face Token Required:**
```bash
export HUGGING_FACE_HUB_TOKEN="hf_xxxxxxxxxxxxx"
```

**Recommendations:**
- Use fine-grained, read-only tokens
- Store in `.env` or credential manager
- Rotate tokens periodically

---

## Integration Patterns for Obsidian

### Pattern 1: Pocket TTS (Voice Cloning - Recommended for Simplicity)

**Setup:**
```bash
pip install pocket-tts
```

**Obsidian MCP Tool:**
```python
# voices.json (store reference audio paths)
{
  "default": "/path/to/default_voice.wav",
  "character_a": "/path/to/character_a_voice.wav"
}

# mcp_tool implementation
def speak_text(text, voice="default"):
    from pocket_tts import TTSModel

    model = TTSModel.load_model()
    state = model.get_state_for_audio_prompt(voices[voice])
    audio = model.generate_audio(state, text)

    return save_and_play(audio)
```

**Advantages:**
- No server deployment needed
- Instant voice cloning
- CPU-efficient
- Local only

**Disadvantages:**
- Python-only
- Single-language per state
- Slower than production servers

---

### Pattern 2: Delayed Streams Rust Server (Production Real-Time)

**Setup:**
```bash
git clone https://github.com/kyutai-labs/delayed-streams-modeling
cd delayed-streams-modeling
cargo build --features cuda --bin stt-server
python -m moshi.server  # Separate terminal
```

**Obsidian MCP Tools:**
```python
# Real-time STT via WebSocket
async def transcribe_streaming(audio_chunks):
    async with websockets.connect("ws://localhost:8000/stream") as ws:
        for chunk in audio_chunks:
            await ws.send(chunk)
        return await ws.recv()

# TTS via Rust server
def synthesize_text(text):
    result = subprocess.run(
        ["python", "-m", "moshi.tts", "-"],
        input=text.encode(),
        capture_output=True
    )
    return result.stdout
```

**Advantages:**
- Production-grade performance
- High throughput (64+ concurrent streams)
- Semantic VAD for smart silence detection
- Streaming-optimized

**Disadvantages:**
- Rust compilation required
- Complex deployment
- GPU recommended

---

### Pattern 3: Community OpenAI-Compatible APIs (Existing Tools)

**Setup:**
```bash
git clone https://github.com/dwain-barnes/kyutai-tts-openai-api
docker compose up  # TTS
git clone https://github.com/dwain-barnes/kyutai-stt-openai-api
docker compose up  # STT (separate)
```

**Obsidian MCP Tools:**
```python
from openai import OpenAI

tts_client = OpenAI(base_url="http://localhost:8000/v1", api_key="dummy")
stt_client = OpenAI(base_url="http://localhost:8080/v1", api_key="dummy")

def speak(text):
    response = tts_client.audio.speech.create(
        model="tts-1", input=text, voice="alloy"
    )
    return play(response.content)

def transcribe(audio_file):
    with open(audio_file, "rb") as f:
        result = stt_client.audio.transcriptions.create(
            model="whisper-1", file=f
        )
    return result.text
```

**Advantages:**
- Reuse existing OpenAI client libraries
- Docker-based, easy deployment
- Separate TTS/STT services
- WebSocket support for streaming

**Disadvantages:**
- Two separate services to manage
- No native voice cloning (TTS only)
- More dependencies

---

### Pattern 4: Moshi Full-Duplex (Advanced - Full-Duplex Conversation)

**Setup:**
```bash
python -m moshi.server --gradio-tunnel
```

**Obsidian MCP Tool:**
```python
import asyncio
import websockets

async def full_duplex_conversation(user_audio_stream):
    async with websockets.connect("wss://localhost:8998/ws") as ws:
        # Send audio and receive response audio
        async for chunk in user_audio_stream:
            await ws.send(chunk)

        response = await ws.recv()
        return response
```

**Advantages:**
- Full-duplex (simultaneous speech input/output)
- Lowest latency (~200ms)
- Most natural conversation
- Latest technology

**Disadvantages:**
- Complex setup
- Resource intensive
- Requires WebRTC support
- Least mature for Obsidian

---

## Rate Limiting & Quotas

**Current Status:** All Kyutai APIs are **local, self-hosted, with no built-in rate limiting.**

### Recommended Rate Limits for Obsidian

**For Pocket TTS:**
- No practical limit (local CPU/GPU bound)
- Recommend: Max 10 concurrent requests per model instance

**For Community APIs:**
```python
from ratelimit import limits, sleep_and_retry
import time

@sleep_and_retry
@limits(calls=10, period=1)  # 10 requests/second
def tts_request(text):
    return client.audio.speech.create(...)
```

**For Moshi/Delayed Streams:**
- GPU memory bound
- H100: 400 concurrent streams (theoretical)
- L40S: 64 concurrent streams (practical)
- Recommend: Queue requests, max 10 concurrent

---

## Performance Characteristics

### Latency

| Service | Device | Cold Start | Per-Query |
|---------|--------|-----------|-----------|
| Pocket TTS (sync) | M2/M3 (CPU) | 2s | 50-200ms per 10 chars |
| Pocket TTS (streaming) | M2/M3 (CPU) | 2s | 20-50ms per chunk |
| STT 1B (streaming) | L40S (GPU) | 500ms | 160-200ms incremental |
| STT 2.6B (streaming) | H100 (GPU) | 2.5s | 160-200ms incremental |
| TTS (Delayed Streams) | L40S (GPU) | 500ms | 50-100ms per 10 chars |
| Moshi (full-duplex) | L4/L40S (GPU) | 1s | ~200ms end-to-end |

### Throughput

| Service | Hardware | Concurrent | Real-Time Factor |
|---------|----------|-----------|------------------|
| STT 1B | H100 | 400 streams | 1.0x (real-time) |
| STT 2.6B | H100 | 64 streams | 3.0x (3x faster than real-time) |
| STT 1B | L40S | 64 streams | 3.0x |
| Moshi | L40S | 8-16 streams | 3.0x |

### Resource Usage

**Pocket TTS:**
- Memory: 400-500 MB (model + state)
- CPU: 1-4 cores for streaming
- GPU: Optional (15% faster with CUDA)

**STT 1B:**
- Memory: 2-3 GB
- GPU Memory: 2-4 GB (CUDA)
- CPU: Minimal if GPU available

**STT 2.6B:**
- Memory: 4-6 GB
- GPU Memory: 6-8 GB (CUDA)
- CPU: Minimal if GPU available

**Moshi 7B:**
- Memory: 6-8 GB
- GPU Memory: 14-16 GB (CUDA, bf16)
- CPU: Minimal if GPU available

---

## Recommended Implementation Path for Kyutai MCP + Obsidian

### Phase 1: Development (Pattern 1 - Pocket TTS)

**Why:** Simplest, no server, rapid iteration

```python
# kyutai_mcp/tools/speak.py
from pocket_tts import TTSModel

class SpeakTool:
    def __init__(self):
        self.model = TTSModel.load_model()
        self.voices = {}  # Load from vault config

    def speak(self, text, voice="default"):
        state = self.model.get_state_for_audio_prompt(
            self.voices[voice]
        )
        audio = self.model.generate_audio(state, text)
        return self.save_audio(audio)
```

### Phase 2: Production (Pattern 3 - Community APIs)

**Why:** Docker-based, OpenAI compatibility, proven

```python
# kyutai_mcp/tools/speak.py
from openai import OpenAI

class SpeakTool:
    def __init__(self):
        self.tts = OpenAI(
            base_url="http://localhost:8000/v1",
            api_key="dummy"
        )

    def speak(self, text, voice="alloy"):
        response = self.tts.audio.speech.create(
            model="tts-1", input=text, voice=voice
        )
        return response.content
```

### Phase 3: Advanced (Pattern 4 - Moshi)

**Why:** Full-duplex, lowest latency, most natural

```python
# kyutai_mcp/tools/converse.py
async def full_duplex_conversation(user_audio):
    async with websockets.connect(
        "wss://localhost:8998/ws"
    ) as ws:
        await ws.send(user_audio)
        return await ws.recv()
```

---

## Summary: Best Kyutai APIs for Obsidian

| Use Case | Recommended API | Why |
|----------|-----------------|-----|
| **Voice Synthesis (Notes)** | Pocket TTS | Local, voice cloning, simple |
| **Audio Transcription** | Community STT API | Docker, OpenAI compatible, proven |
| **Real-Time Conversation** | Moshi | Full-duplex, ~200ms latency |
| **Batch Processing** | Delayed Streams (Rust) | High throughput, 64+ concurrent |
| **Multi-Language** | STT 1B + TTS combo | English/French STT, universal TTS |

---

## Research Sources

- [Pocket TTS Python API Documentation](https://github.com/kyutai-labs/pocket-tts/blob/main/docs/python-api.md)
- [Pocket TTS README](https://github.com/kyutai-labs/pocket-tts/blob/main/README.md)
- [Kyutai STT Models Documentation](https://kyutai.org/stt)
- [Kyutai Delayed Streams Modeling](https://github.com/kyutai-labs/delayed-streams-modeling)
- [Moshi Speech-Text Foundation Model](https://github.com/kyutai-labs/moshi)
- [Unmute Project](https://github.com/kyutai-labs/unmute)
- [Kyutai TTS OpenAI-Compatible API](https://github.com/dwain-barnes/kyutai-tts-openai-api)
- [Kyutai STT OpenAI-Compatible API](https://github.com/dwain-barnes/kyutai-stt-openai-api)
- [Kyutai Official Website](https://kyutai.org/)

---

**Document Status:** Research Complete - Ready for Phase 2 (MCP Architecture Design)
