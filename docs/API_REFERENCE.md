# MCP API Reference

Complete specification of all MCP tools provided by the Kyutai MCP Server.

## Table of Contents

1. [API Overview](#api-overview)
2. [Authentication](#authentication)
3. [Tool Specifications](#tool-specifications)
4. [Request/Response Examples](#requestresponse-examples)
5. [Error Codes](#error-codes)
6. [Rate Limiting](#rate-limiting)
7. [Client Libraries](#client-libraries)

---

## API Overview

The Kyutai MCP Server exposes 7 tools via the Model Context Protocol (MCP):

| # | Tool | Purpose | Input | Output |
|---|------|---------|-------|--------|
| 1 | `synthesize_text` | Text-to-Speech | text, voice, speed | audio binary |
| 2 | `transcribe_audio` | Speech-to-Text | audio binary | text, timestamps |
| 3 | `clone_voice` | Voice Profiling | reference audio | voice state |
| 4 | `list_voices` | Voice Catalog | — | voice list |
| 5 | `list_models` | Model Catalog | — | model metadata |
| 6 | `get_status` | Server Status | — | health metrics |
| 7 | `stream_audio` | Real-time Streaming | audio stream | text stream |

### Protocol

- **Type**: Model Context Protocol (MCP)
- **Transport**: JSON-RPC over HTTP/WebSocket
- **Authentication**: None (local-only by default)
- **Base URL**: `http://localhost:8000`

---

## Authentication

### Current State

**No authentication implemented** (local-only deployment)

Suitable for:
- Local machine usage
- Internal networks
- Development/testing

### Production Authentication (Optional)

For remote deployments, add authentication via reverse proxy:

**Nginx with API Key:**
```nginx
location / {
    if ($http_authorization = "") {
        return 401;
    }
    proxy_pass http://localhost:8000;
}
```

**via .env:**
```bash
MCP_API_KEY=sk_live_xxxxxxxxxxxxx
```

**In client:**
```python
headers = {"Authorization": f"Bearer {MCP_API_KEY}"}
```

---

## Tool Specifications

### 1. synthesize_text

Convert text to speech with voice cloning support.

**Signature:**
```python
def synthesize_text(
    text: str,
    voice: str = "default",
    speed: float = 1.0,
    pitch: float = 1.0,
    language: str = "auto",
    format: str = "wav"
) -> bytes
```

**Parameters:**

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `text` | string | required | 1-4096 chars | Text to synthesize |
| `voice` | string | "default" | — | Voice profile name |
| `speed` | float | 1.0 | 0.5-2.0 | Speech speed multiplier |
| `pitch` | float | 1.0 | 0.5-2.0 | Voice pitch multiplier |
| `language` | string | "auto" | en, fr | Target language |
| `format` | string | "wav" | wav, mp3, ogg | Audio format |

**Returns:** Binary audio data

**Status Codes:**
- `200`: Success
- `400`: Invalid input
- `404`: Voice not found
- `500`: Server error

**Request Example (MCP):**
```json
{
  "tool": "synthesize_text",
  "arguments": {
    "text": "Hello, this is a test message.",
    "voice": "default",
    "speed": 1.0,
    "format": "mp3"
  }
}
```

**Response Example:**
```
[binary audio data - MP3 format]
(Content-Type: audio/mpeg)
```

**Python Example:**
```python
import mcp

client = mcp.MCPClient("http://localhost:8000")

audio = client.synthesize_text(text="Hello world!", voice="my_voice", speed=1.0, format="mp3")

with open("output.mp3", "wb") as f:
    f.write(audio)
```

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/synthesize" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello world!",
    "voice": "default",
    "format": "mp3"
  }' \
  --output output.mp3
```

---

### 2. transcribe_audio

Convert audio to text with word-level timestamps.

**Signature:**
```python
def transcribe_audio(
    audio_data: bytes,
    model: str = "stt-1b-en_fr",
    language: str = "auto",
    format: str = "json"
) -> dict
```

**Parameters:**

| Parameter | Type | Default | Options | Description |
|-----------|------|---------|---------|-------------|
| `audio_data` | bytes | required | — | Audio file binary data |
| `model` | string | "stt-1b-en_fr" | stt-1b, stt-2.6b, community | STT model to use |
| `language` | string | "auto" | en, fr, auto | Audio language |
| `format` | string | "json" | json, text, srt, vtt | Output format |

**Returns:** Transcription result (format-dependent)

**Response Format: JSON**
```json
{
  "text": "Complete transcription text",
  "segments": [
    {
      "id": 0,
      "start": 0.0,
      "end": 2.5,
      "text": "First segment",
      "confidence": 0.95
    }
  ],
  "language": "en",
  "duration_seconds": 45.2,
  "model": "stt-1b-en_fr"
}
```

**Response Format: Text**
```
Complete transcription text here
```

**Response Format: SRT** (subtitles)
```
1
00:00:00,000 --> 00:00:02,500
First segment

2
00:00:02,500 --> 00:00:05,000
Second segment
```

**Response Format: VTT** (video subtitles)
```
WEBVTT

00:00:00.000 --> 00:00:02.500
First segment

00:00:02.500 --> 00:00:05.000
Second segment
```

**Status Codes:**
- `200`: Success
- `400`: Invalid audio data
- `504`: Timeout (audio too long or GPU overloaded)

**Request Example (MCP with file upload):**
```json
{
  "tool": "transcribe_audio",
  "arguments": {
    "audio_data": "[base64-encoded audio]",
    "model": "stt-1b-en_fr",
    "language": "auto",
    "format": "json"
  }
}
```

**Python Example:**
```python
import mcp

client = mcp.MCPClient("http://localhost:8000")

# Read audio file
with open("meeting.mp3", "rb") as f:
    audio_data = f.read()

result = client.transcribe_audio(audio_data=audio_data, model="stt-2.6b", format="json")

print(result["text"])
# Output: "Complete transcription with all spoken words"

# Save as SRT
result_srt = client.transcribe_audio(audio_data=audio_data, format="srt")
with open("subtitles.srt", "w") as f:
    f.write(result_srt)
```

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/transcribe" \
  -H "Content-Type: audio/mpeg" \
  -F "audio=@meeting.mp3" \
  -F "model=stt-1b-en_fr" \
  -F "format=json" | jq .
```

---

### 3. clone_voice

Create voice profile from reference audio.

**Signature:**
```python
def clone_voice(
    audio_data: bytes,
    name: str,
    language: str = "auto"
) -> dict
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `audio_data` | bytes | Yes | Reference audio (5-30s) |
| `name` | string | Yes | Voice profile name |
| `language` | string | No | Language code (en, fr) |

**Returns:** Voice profile metadata

**Response:**
```json
{
  "voice_id": "voice_uuid_12345",
  "name": "My Voice",
  "duration_seconds": 15,
  "language": "en",
  "created_at": "2026-02-10T15:30:00Z",
  "status": "ready",
  "embedding_size": 768
}
```

**Status Codes:**
- `200`: Success
- `400`: Invalid audio (too short, wrong format)
- `409`: Voice name already exists
- `413`: Audio too large

**Request Example:**
```json
{
  "tool": "clone_voice",
  "arguments": {
    "audio_data": "[base64-encoded audio]",
    "name": "character_voice",
    "language": "en"
  }
}
```

**Python Example:**
```python
import mcp

client = mcp.MCPClient("http://localhost:8000")

# Upload reference audio
with open("reference_voice.wav", "rb") as f:
    audio_data = f.read()

voice = client.clone_voice(audio_data=audio_data, name="My Custom Voice", language="en")

print(f"Created voice: {voice['voice_id']}")
print(f"Ready for synthesis: {voice['status']}")

# Now use in synthesis
audio = client.synthesize_text(text="Using my custom voice!", voice=voice["voice_id"])
```

---

### 4. list_voices

Get available voice profiles.

**Signature:**
```python
def list_voices() -> list
```

**Returns:** List of voice profiles

**Response:**
```json
{
  "voices": [
    {
      "id": "default",
      "name": "Default Voice",
      "language": "en",
      "duration_seconds": 0,
      "created_at": null,
      "type": "builtin"
    },
    {
      "id": "voice_12345",
      "name": "My Voice",
      "language": "en",
      "duration_seconds": 15,
      "created_at": "2026-02-10T15:30:00Z",
      "type": "custom"
    }
  ],
  "total": 2
}
```

**Status Codes:**
- `200`: Success
- `500`: Server error

**Request Example:**
```json
{
  "tool": "list_voices",
  "arguments": {}
}
```

**Python Example:**
```python
import mcp

client = mcp.MCPClient("http://localhost:8000")

voices = client.list_voices()

for voice in voices["voices"]:
    print(f"{voice['name']} ({voice['id']})")
    if voice["type"] == "custom":
        print(f"  Created: {voice['created_at']}")
        print(f"  Duration: {voice['duration_seconds']}s")
```

---

### 5. list_models

Get available models and their capabilities.

**Signature:**
```python
def list_models() -> dict
```

**Returns:** Available models and metadata

**Response:**
```json
{
  "tts_models": [
    {
      "id": "pocket-tts",
      "name": "Pocket TTS",
      "provider": "kyutai",
      "version": "1.0.0",
      "parameters": 100000000,
      "device": "cuda:0",
      "status": "loaded",
      "capabilities": ["voice_cloning", "streaming"],
      "latency_ms": 75,
      "languages": ["en", "fr", "multilingual"]
    },
    {
      "id": "moshi",
      "name": "Moshi 7B",
      "provider": "kyutai",
      "version": "1.0.0",
      "parameters": 7000000000,
      "device": "cuda:0",
      "status": "available",
      "capabilities": ["full_duplex", "streaming"],
      "latency_ms": 200,
      "languages": ["en", "fr"]
    }
  ],
  "stt_models": [
    {
      "id": "stt-1b-en_fr",
      "name": "Delayed Streams STT 1B",
      "provider": "kyutai",
      "version": "1.0.0",
      "parameters": 1000000000,
      "device": "cuda:0",
      "status": "loaded",
      "capabilities": ["streaming", "vad"],
      "latency_ms": 160,
      "languages": ["en", "fr"]
    }
  ],
  "system": {
    "gpu_available": true,
    "gpu_memory_total_mb": 10240,
    "gpu_memory_used_mb": 2560,
    "version": "0.1.0"
  }
}
```

**Python Example:**
```python
import mcp

client = mcp.MCPClient("http://localhost:8000")

models = client.list_models()

print("Available TTS Models:")
for model in models["tts_models"]:
    print(f"- {model['name']} ({model['id']})")
    print(f"  Status: {model['status']}")
    print(f"  Latency: {model['latency_ms']}ms")

print("\nAvailable STT Models:")
for model in models["stt_models"]:
    print(f"- {model['name']} ({model['id']})")
    print(f"  Languages: {', '.join(model['languages'])}")
```

---

### 6. get_status

Get server health and performance metrics.

**Signature:**
```python
def get_status() -> dict
```

**Returns:** Server status and metrics

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "uptime_seconds": 3600,
  "timestamp": "2026-02-10T15:30:00Z",
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
    "count": 1,
    "devices": [
      {
        "id": 0,
        "name": "NVIDIA RTX 4090",
        "memory_total_mb": 24576,
        "memory_used_mb": 2560,
        "memory_free_mb": 22016,
        "utilization_percent": 15
      }
    ]
  },
  "performance": {
    "requests_total": 1523,
    "requests_per_minute": 2.3,
    "errors_total": 0,
    "avg_latency_ms": 125,
    "p95_latency_ms": 250,
    "p99_latency_ms": 400
  },
  "audio_pipeline": {
    "sample_rate_hz": 24000,
    "channels": 1,
    "chunk_size": 1024
  }
}
```

**Python Example:**
```python
import mcp

client = mcp.MCPClient("http://localhost:8000")

status = client.get_status()

print(f"Server Status: {status['status']}")
print(f"Uptime: {status['uptime_seconds']}s")
print(f"Requests: {status['performance']['requests_total']}")
print(f"GPU Available: {status['gpu']['available']}")
if status["gpu"]["available"]:
    for device in status["gpu"]["devices"]:
        print(f"  {device['name']}: {device['memory_used_mb']}/{device['memory_total_mb']}MB")
```

---

### 7. stream_audio

Real-time audio streaming (WebSocket).

**Signature:**
```python
async def stream_audio(
    audio_stream: AsyncIterator[bytes],
    model: str = "stt-1b-en_fr",
    language: str = "auto"
) -> AsyncIterator[dict]
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `audio_stream` | binary stream | Real-time audio chunks |
| `model` | string | STT model to use |
| `language` | string | Audio language |

**WebSocket Endpoint:** `ws://localhost:8000/stream`

**Message Protocol:**

**Client sends (binary):**
```
[audio_chunk_1]
[audio_chunk_2]
[audio_chunk_3]
...
[final_chunk + close signal]
```

**Server sends (JSON text messages):**
```json
{
  "type": "partial",
  "text": "Incremental transcription...",
  "timestamp": 0.0
}
```

```json
{
  "type": "complete",
  "text": "Full transcription with all words",
  "segments": [...],
  "language": "en",
  "duration_seconds": 45.2
}
```

**Python Example (asyncio):**
```python
import asyncio
import websockets
import json


async def stream_transcription():
    uri = "ws://localhost:8000/stream"
    async with websockets.connect(uri) as websocket:
        # Send audio chunks
        with open("audio.wav", "rb") as f:
            chunk_size = 4096
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                await websocket.send(chunk)

        # Receive transcription updates
        async for message in websocket:
            result = json.loads(message)
            if result["type"] == "partial":
                print(f"Interim: {result['text']}")
            elif result["type"] == "complete":
                print(f"Final: {result['text']}")


# Run
asyncio.run(stream_transcription())
```

**JavaScript Example:**
```javascript
async function streamTranscription() {
    const ws = new WebSocket('ws://localhost:8000/stream');

    ws.onopen = async () => {
        const response = await fetch('audio.wav');
        const arrayBuffer = await response.arrayBuffer();
        const chunks = chunkArray(new Uint8Array(arrayBuffer), 4096);

        for (const chunk of chunks) {
            ws.send(chunk);
        }
    };

    ws.onmessage = (event) => {
        const result = JSON.parse(event.data);
        if (result.type === 'partial') {
            console.log(`Interim: ${result.text}`);
        } else if (result.type === 'complete') {
            console.log(`Final: ${result.text}`);
        }
    };
}

streamTranscription();
```

---

## Request/Response Examples

### Example 1: Simple Text-to-Speech

**Request:**
```bash
curl -X POST http://localhost:8000/synthesize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello world",
    "voice": "default",
    "format": "mp3"
  }'
```

**Response:**
```
[Binary MP3 audio data]
Content-Type: audio/mpeg
Content-Length: 25432
```

### Example 2: Transcription with Timestamps

**Request:**
```bash
curl -X POST http://localhost:8000/transcribe \
  -F "audio=@meeting.mp3" \
  -F "model=stt-1b-en_fr" \
  -F "format=json"
```

**Response:**
```json
{
  "text": "Welcome to the meeting everyone",
  "segments": [
    {
      "id": 0,
      "start": 0.0,
      "end": 2.3,
      "text": "Welcome to the meeting",
      "confidence": 0.97
    },
    {
      "id": 1,
      "start": 2.3,
      "end": 3.2,
      "text": "everyone",
      "confidence": 0.95
    }
  ],
  "language": "en",
  "duration_seconds": 3.2
}
```

### Example 3: Multi-Step Workflow

**Step 1: Create voice profile**
```bash
curl -X POST http://localhost:8000/clone-voice \
  -F "audio=@reference_voice.wav" \
  -F "name=my_voice"
```

**Response:**
```json
{
  "voice_id": "voice_abc123",
  "name": "my_voice",
  "status": "ready"
}
```

**Step 2: Use voice in synthesis**
```bash
curl -X POST http://localhost:8000/synthesize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Speaking with my custom voice",
    "voice": "voice_abc123",
    "format": "wav"
  }'
```

---

## Error Codes

### HTTP Status Codes

| Code | Meaning | When to Expect |
|------|---------|----------------|
| 200 | OK | Successful request |
| 400 | Bad Request | Invalid parameters, malformed JSON |
| 401 | Unauthorized | Missing/invalid API key (if auth enabled) |
| 404 | Not Found | Voice/model ID doesn't exist |
| 409 | Conflict | Voice name already exists |
| 413 | Payload Too Large | Audio file > 500MB |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Server Error | Unexpected server error |
| 503 | Service Unavailable | Server overloaded or GPU out of memory |
| 504 | Gateway Timeout | Request took >300s |

### Error Response Format

```json
{
  "error": "Voice not found",
  "code": "VOICE_NOT_FOUND",
  "status": 404,
  "details": {
    "voice_id": "nonexistent_voice",
    "available_voices": ["default", "voice_123"]
  },
  "timestamp": "2026-02-10T15:30:00Z"
}
```

### Common Error Scenarios

**400: Invalid Text**
```json
{
  "error": "Text too long",
  "code": "TEXT_LENGTH_ERROR",
  "details": {
    "max_length": 4096,
    "provided_length": 5000
  }
}
```

**504: Timeout**
```json
{
  "error": "Request timeout",
  "code": "TIMEOUT",
  "details": {
    "timeout_seconds": 300,
    "operation": "transcribe_audio"
  }
}
```

**503: GPU Out of Memory**
```json
{
  "error": "GPU out of memory",
  "code": "GPU_OUT_OF_MEMORY",
  "details": {
    "required_mb": 8192,
    "available_mb": 512
  }
}
```

---

## Rate Limiting

### Current State

**No built-in rate limiting** (local deployment)

### Recommended Production Limits

**Per IP address:**
- 100 requests/minute
- 10 concurrent requests

**Per user (if auth enabled):**
- 1000 requests/day
- 20 concurrent requests

### Rate Limit Headers (if implemented)

**Response headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1644407400
```

**When limit exceeded:**
```
HTTP/1.1 429 Too Many Requests

{
  "error": "Rate limit exceeded",
  "code": "RATE_LIMIT",
  "retry_after": 60
}
```

---

## Client Libraries

### Python

**Using MCP Client:**
```python
import mcp

# Create client
client = mcp.MCPClient("http://localhost:8000")

# Synthesize
audio = client.synthesize_text(text="Hello", voice="default")

# Transcribe
result = client.transcribe_audio(audio_data=audio_bytes)

# List voices
voices = client.list_voices()
```

**Using httpx (async):**
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/synthesize", json={"text": "Hello", "voice": "default"}
    )
    audio = response.content
```

### JavaScript/TypeScript

**Using fetch API:**
```javascript
// Synthesize
const response = await fetch('http://localhost:8000/synthesize', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        text: "Hello world",
        voice: "default",
        format: "mp3"
    })
});
const audioBlob = await response.blob();

// Transcribe
const formData = new FormData();
formData.append('audio', audioFile);
formData.append('model', 'stt-1b-en_fr');

const result = await fetch('http://localhost:8000/transcribe', {
    method: 'POST',
    body: formData
});
const transcription = await result.json();
```

**Using TypeScript types:**
```typescript
interface SynthesizeRequest {
  text: string;
  voice?: string;
  speed?: number;
  format?: 'wav' | 'mp3' | 'ogg';
}

interface TranscribeResponse {
  text: string;
  segments: Segment[];
  language: string;
}

interface Segment {
  id: number;
  start: number;
  end: number;
  text: string;
  confidence: number;
}
```

### cURL (Bash)

```bash
# Synthesize
curl -X POST http://localhost:8000/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello","voice":"default"}' \
  --output output.wav

# Transcribe
curl -X POST http://localhost:8000/transcribe \
  -F "audio=@audio.mp3" \
  -F "model=stt-1b-en_fr" \
  | jq .

# Get status
curl http://localhost:8000/health | jq .
```

---

## Best Practices

### Error Handling

```python
import mcp
from mcp.errors import MCPError

client = mcp.MCPClient("http://localhost:8000")

try:
    audio = client.synthesize_text(text="Hello world", voice="my_voice")
except mcp.errors.NotFoundError:
    # Voice doesn't exist
    audio = client.synthesize_text(text="Hello world", voice="default")
except mcp.errors.TimeoutError:
    # Request took too long
    print("Request timeout, try shorter text")
except MCPError as e:
    print(f"MCP error: {e.code} - {e.message}")
```

### Streaming Large Files

```python
import mcp

client = mcp.MCPClient("http://localhost:8000")

# For large transcriptions, use streaming
async with client.stream_audio() as stream:
    with open("large_audio.wav", "rb") as f:
        # Send in chunks
        while chunk := f.read(4096):
            await stream.send(chunk)

    # Receive results
    async for result in stream:
        if result["type"] == "complete":
            print(f"Transcription: {result['text']}")
```

### Connection Pooling

```python
import mcp
import httpx

# Reuse connection pool
pool = httpx.AsyncClient(limits=httpx.Limits(max_connections=10))
client = mcp.MCPClient("http://localhost:8000", client=pool)

# Multiple requests efficiently
for text in texts:
    audio = await client.synthesize_text(text=text)
```

---

**Last Updated**: 2026-02-10
**Version**: 0.1.0-alpha
