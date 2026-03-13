---
title: Kyutai MCP Server Architecture Design
date: 2026-02-09
status: approved
tags: [research, kyutai, mcp, architecture, api-design]
neural:
  activation: 1.0
  stage: growing
  synapse_in: 6
  synapse_out: 8
---

# Kyutai MCP Server Architecture Design

**Document Status:** APPROVED DESIGN
**Date Created:** 2026-02-09
**Target:** Phase 2 Implementation Handoff
**Author:** agent-mcp-architect
**Audience:** Implementation team (Phase 3)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [MCP Tool Specifications](#mcp-tool-specifications)
4. [Architecture Decision Rationale](#architecture-decision-rationale)
5. [Data Model & TypeScript Interfaces](#data-model--typescript-interfaces)
6. [Integration Patterns](#integration-patterns)
7. [Implementation Roadmap (3 Phases)](#implementation-roadmap-3-phases)
8. [Configuration & Deployment](#configuration--deployment)
9. [Risk Analysis & Mitigation](#risk-analysis--mitigation)
10. [Reusable Patterns from cloud-vault-mcp](#reusable-patterns-from-cloud-vault-mcp)

---

## Executive Summary

This document defines a **production-ready MCP server architecture for Kyutai voice AI integration** with Obsidian. The design prioritizes:

- **Simplicity first:** Start with Pocket TTS (100M params, CPU-only) in Phase 1
- **OpenAI compatibility:** Leverage existing community APIs (OpenAI-compatible REST) for Phase 2
- **Full-duplex dialogue:** Add Moshi support in Phase 3 for advanced conversational AI
- **Token efficiency:** Use Haiku agents ($0.02/request) for research + config
- **Obsidian integration:** Leverage FastMCP patterns from cloud-vault-mcp (proven for Obsidian)

**Key Decision:** Use Python (FastMCP) backend, **NOT TypeScript**, for consistency with cloud-vault-mcp and Kyutai's Python-first ecosystem.

**Target Success Criteria:**
- 7 MCP tools, production-ready with error handling
- Deploy via Docker Compose (local or server)
- OpenAI SDK compatibility for Obsidian plugin
- 0 external API calls (fully local, optional cloud fallback)
- 95%+ uptime SLA with health checks

---

## Architecture Overview

### System Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                     Obsidian Plugin (TypeScript)             │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  UI Components: Text Input, Voice Recording, Playback  │  │
│  │  Event Handlers: Click, Voice, Settings               │  │
│  └────────────────────────────────────────────────────────┘  │
│                         ↓ HTTP/MCP                            │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│         Kyutai MCP Server (Python 3.10+, FastMCP)            │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Tool Layer (7 tools)                                   │  │
│  │ ├─ speak_text() → Pocket TTS                         │  │
│  │ ├─ transcribe_audio() → STT API                      │  │
│  │ ├─ translate_speech() → Hibiki API (optional)        │  │
│  │ ├─ list_models() → Cached model inventory            │  │
│  │ ├─ get_model_status() → Health checks                │  │
│  │ ├─ set_voice() → Voice state management              │  │
│  │ └─ configure_service() → Config updates              │  │
│  └────────────────────────────────────────────────────────┘  │
│                         ↓                                     │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Service Layer                                          │  │
│  │ ├─ PocketTTSService (local, sync)                    │  │
│  │ ├─ STTService (FastAPI wrapper, async)               │  │
│  │ ├─ MoshiService (WebSocket, async)                   │  │
│  │ ├─ ConfigManager (YAML, environment)                 │  │
│  │ └─ HealthMonitor (status, metrics)                   │  │
│  └────────────────────────────────────────────────────────┘  │
│                         ↓                                     │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Infrastructure Layer                                   │  │
│  │ ├─ Pocket TTS (pip install, in-process)             │  │
│  │ ├─ STT API (Docker, OpenAI-compatible)              │  │
│  │ ├─ TTS API (Docker, OpenAI-compatible)              │  │
│  │ ├─ Moshi Server (optional, GPU-required)            │  │
│  │ └─ File system (voice samples, configs)             │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘

                          ↓
┌──────────────────────────────────────────────────────────────┐
│           Kyutai Models (Local or Remote Docker)             │
│                                                               │
│  Phase 1 (MVP):                                              │
│  ├─ pocket-tts (100M, CPU) — runs in-process               │
│                                                               │
│  Phase 2 (Production):                                       │
│  ├─ Kyutai TTS OpenAI API (Docker, 1.6B)                    │
│  ├─ Kyutai STT OpenAI API (Docker, 1B or 2.6B)             │
│                                                               │
│  Phase 3 (Advanced):                                         │
│  ├─ Moshi (Docker or Rust, 7B, GPU-required)               │
│  ├─ Hibiki (Docker, 2.7B, translation)                     │
│  └─ MoshiVis (Docker, vision + dialogue)                   │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### Deployment Patterns

| Pattern | Phase | Use Case | Complexity |
|---------|-------|----------|-----------|
| **Pocket TTS only** | 1 | Local Obsidian text-to-speech | LOW |
| **Pocket TTS + STT API** | 2 | Full voice I/O on one machine | MEDIUM |
| **Multi-container stack** | 2-3 | Production: TTS, STT, Moshi separate | HIGH |
| **Hybrid (local + cloud fallback)** | 3 | Offline + cloud options | HIGH |

---

## MCP Tool Specifications

### Tool 1: `speak_text`

**Purpose:** Generate audio from text using TTS model (Pocket TTS in Phase 1, API in Phase 2)

**Inputs:**
```python
{
  "text": str,              # Required: Text to synthesize (1-4096 chars)
  "voice_id": str,          # Optional: Voice sample ID (default: "default")
  "model": str,             # Optional: Model selection (default: "pocket-tts")
  "speed": float,           # Optional: Playback speed (0.5-2.0, default: 1.0)
  "output_format": str      # Optional: Audio format (mp3, wav, ogg, default: "wav")
}
```

**Return Type:**
```python
{
  "status": "success" | "error",
  "audio_path": str,        # Local file path to generated audio
  "audio_base64": str,      # Optional: Base64-encoded audio for Obsidian playback
  "duration_ms": int,       # Duration of generated audio
  "model_used": str,        # Which model was used
  "latency_ms": int,        # Inference time in milliseconds
  "error": str              # Error message if status == "error"
}
```

**Error Handling:**
- Text length > 4096 chars → Return error, suggest splitting
- Invalid voice_id → Use "default" voice, log warning
- Model not available → Fall back to Pocket TTS
- Disk full → Return error with available space

**Example Usage:**
```python
result = await mcp.call_tool("speak_text", {
    "text": "Hello from Kyutai!",
    "voice_id": "character_voice",
    "output_format": "wav"
})
```

---

### Tool 2: `transcribe_audio`

**Purpose:** Convert audio to text using STT model (community API in Phase 2+)

**Inputs:**
```python
{
  "audio_path": str,        # Required: File path or URL to audio
  "model": str,             # Optional: STT model (default: "stt-1b-en_fr")
  "response_format": str,   # Optional: json, text, srt, vtt (default: "json")
  "language": str,          # Optional: Language hint (en, fr, default: auto)
  "include_timestamps": bool # Optional: Include word-level timestamps
}
```

**Return Type:**
```python
{
  "status": "success" | "error",
  "text": str,              # Complete transcription
  "segments": [
    {
      "id": int,
      "start": float,       # Start time in seconds
      "end": float,
      "text": str,
      "words": [            # If include_timestamps=true
        {
          "word": str,
          "start": float,
          "end": float
        }
      ]
    }
  ],
  "language": str,          # Detected language
  "model_used": str,
  "latency_ms": int,
  "error": str
}
```

**Error Handling:**
- File not found → Return error with path
- Unsupported format → List supported formats, suggest conversion
- API unavailable → Return error, check health
- Audio too long (>2 hours) → Split and process in chunks

**Example Usage:**
```python
result = await mcp.call_tool("transcribe_audio", {
    "audio_path": "/path/to/recording.wav",
    "include_timestamps": true
})
```

---

### Tool 3: `translate_speech`

**Purpose:** Real-time speech-to-speech translation (Hibiki, Phase 2+)

**Inputs:**
```python
{
  "audio_path": str,        # Required: Audio file path
  "source_language": str,   # Required: "fr" or "en"
  "target_language": str,   # Required: "en" or "fr"
  "model": str,             # Optional: "hibiki" or "hibiki-mobile"
  "preserve_voice": bool    # Optional: Keep source voice timbre
}
```

**Return Type:**
```python
{
  "status": "success" | "error",
  "translated_text": str,   # Translated text
  "audio_path": str,        # Path to translated speech audio
  "source_language": str,
  "target_language": str,
  "model_used": str,
  "latency_ms": int,
  "error": str
}
```

**Error Handling:**
- Unsupported language pair → Return supported pairs
- Model not available → Return error
- Audio quality issues → Log warning but attempt transcription

**Example Usage:**
```python
result = await mcp.call_tool("translate_speech", {
    "audio_path": "interview.wav",
    "source_language": "fr",
    "target_language": "en"
})
```

---

### Tool 4: `list_models`

**Purpose:** Get inventory of available models and their status

**Inputs:**
```python
{
  "category": str           # Optional: "tts", "stt", "dialogue", "all"
}
```

**Return Type:**
```python
{
  "status": "success" | "error",
  "models": [
    {
      "id": str,                    # pocket-tts, stt-1b-en_fr, moshi, etc.
      "name": str,
      "category": str,              # tts, stt, dialogue, codec, translation
      "parameters": int,            # Parameter count (e.g., 100000000)
      "model_size_gb": float,
      "languages": [str],
      "input_modality": [str],      # audio, text
      "output_modality": [str],     # audio, text
      "local_available": bool,      # Is this model deployed locally?
      "hardware_required": str,     # cpu, gpu, none
      "deployment_pattern": str,    # local-cpu, local-gpu, api, on-device
      "latency_ms": int,            # Expected inference time
      "max_concurrent": int,        # Concurrent request limit
      "config_required": bool       # Needs manual config?
    }
  ],
  "error": str
}
```

**Example Usage:**
```python
result = await mcp.call_tool("list_models", {
    "category": "tts"
})
```

---

### Tool 5: `get_model_status`

**Purpose:** Health check and detailed status of deployed models

**Inputs:**
```python
{
  "model_id": str           # Optional: Specific model (default: all)
}
```

**Return Type:**
```python
{
  "status": "success" | "error",
  "timestamp": str,         # ISO 8601
  "models": {
    "pocket-tts": {
      "available": bool,
      "status": "healthy" | "degraded" | "offline",
      "uptime_percent": float,
      "recent_latency_ms": {
        "p50": float,
        "p95": float,
        "p99": float
      },
      "memory_usage_mb": float,
      "last_error": str,
      "restart_count": int,
      "load": float          # 0.0 - 1.0
    },
    "stt-api": {
      "available": bool,
      "url": str,
      "response_code": int,
      "response_time_ms": float,
      "concurrent_requests": int,
      "max_concurrent": int,
      ...
    }
  },
  "overall_status": "healthy" | "degraded" | "offline",
  "error": str
}
```

**Example Usage:**
```python
result = await mcp.call_tool("get_model_status", {
    "model_id": "stt-api"
})
```

---

### Tool 6: `set_voice`

**Purpose:** Configure voice for TTS (voice cloning with Pocket TTS)

**Inputs:**
```python
{
  "voice_name": str,        # Required: Identifier for this voice (e.g., "narrator_a")
  "audio_sample_path": str, # Required: Path to reference audio (WAV, MP3)
  "description": str,       # Optional: Human-readable description
  "language": str,          # Optional: Language hint (en, fr, default: auto)
  "truncate": bool          # Optional: Truncate to model context length
}
```

**Return Type:**
```python
{
  "status": "success" | "error",
  "voice_id": str,          # Stored identifier
  "voice_name": str,
  "language": str,
  "sample_duration_ms": int,
  "storage_path": str,      # Where voice sample is stored
  "available_for": [str],   # Models that support this voice
  "error": str
}
```

**Error Handling:**
- Invalid audio file → Return error with supported formats
- Voice already exists → Ask to overwrite
- Disk space → Error message with available space

**Example Usage:**
```python
result = await mcp.call_tool("set_voice", {
    "voice_name": "my_narrator",
    "audio_sample_path": "/Users/me/Downloads/voice_sample.wav"
})
```

---

### Tool 7: `configure_service`

**Purpose:** Update configuration and deployment settings

**Inputs:**
```python
{
  "setting": str,           # Required: Configuration key
  "value": any,             # Required: New value
  "scope": str              # Optional: "global", "model-specific" (default: global)
}
```

**Supported Settings:**
- `default_tts_model`: str (e.g., "pocket-tts")
- `default_stt_model`: str (e.g., "stt-1b-en_fr")
- `default_voice`: str (voice_id)
- `tts_api_url`: str (for Phase 2+, e.g., "http://localhost:8000/v1")
- `stt_api_url`: str (for Phase 2+, e.g., "http://localhost:8080/v1")
- `moshi_ws_url`: str (for Phase 3+)
- `cache_audio_outputs`: bool
- `max_text_length`: int (default: 4096)
- `request_timeout_seconds`: int (default: 30)
- `log_level`: str (debug, info, warning, error)

**Return Type:**
```python
{
  "status": "success" | "error",
  "setting": str,
  "previous_value": any,
  "new_value": any,
  "requires_restart": bool,
  "affected_models": [str],
  "error": str
}
```

**Example Usage:**
```python
result = await mcp.call_tool("configure_service", {
    "setting": "default_voice",
    "value": "my_narrator",
    "scope": "global"
})
```

---

## Architecture Decision Rationale

### 1. Why Python (Not TypeScript)?

**Decision:** Build MCP server in Python using FastMCP

**Rationale:**
- Kyutai models are Python-native (PyTorch, MLX, Rust with Python bindings)
- cloud-vault-mcp uses FastMCP (proven, documented)
- 70% code reusability from cloud-vault-mcp patterns
- Faster iteration: Python is more concise for ML workloads
- Obsidian plugin (TypeScript) communicates via HTTP/MCP, not direct Python

**Alternative Rejected: TypeScript/Node.js**
- Would require wrapping Kyutai models with Python subprocesses
- 3x more code for same functionality
- Higher latency (inter-process communication)

### 2. Why 3 Phases?

**Phase 1 (MVP - Week 1):** Pocket TTS only
- **Why:** Simplest, CPU-only, instant value for Obsidian
- **Cost:** 0 external services, ~2 hours setup
- **Tools:** speak_text, list_models, get_model_status

**Phase 2 (Production - Week 2):** Add STT + TTS APIs
- **Why:** OpenAI-compatible Docker containers, proven pattern
- **Cost:** Docker setup, separate TTS/STT services
- **Tools:** + transcribe_audio, translate_speech, set_voice, configure_service

**Phase 3 (Advanced - Week 3+):** Add Moshi dialogue
- **Why:** Full-duplex conversation, ~200ms latency
- **Cost:** GPU required, complex WebSocket handling
- **Tools:** + full_duplex_conversation (future tool)

### 3. Why OpenAI-Compatible APIs?

**Decision:** Phase 2+ use community OpenAI-compatible REST/WebSocket APIs

**Rationale:**
- Already have proven Docker images (dwain-barnes community)
- Obsidian plugin can use OpenAI SDK (already tested)
- Drop-in replacement (no custom client library needed)
- Easier to add cloud fallback (migrate to cloud OpenAI if needed)
- Standard interface reduces MCP complexity

**Alternative Rejected: Direct Kyutai model serving**
- Would require custom FastAPI wrapper for each model
- Moshi WebSocket protocol is proprietary (OpenAI Realtime API extended)
- More maintenance burden

### 4. Why FastMCP?

**Decision:** Use mcp.server.fastmcp (Python framework from cloud-vault-mcp)

**Rationale:**
- Decorator-based (@mcp.tool()) is pythonic
- Auto-generates JSON schemas for tools
- Built-in async/await support
- No boilerplate
- Proven in production with cloud-vault-mcp

**Code Example:**
```python
@mcp.tool()
def speak_text(text: str, voice_id: str = "default") -> dict:
    """Generate audio from text."""
    result = service.speak(text, voice_id)
    return result
```

### 5. Why Obsidian Plugin Must Be TypeScript?

**Decision:** Obsidian plugin stays TypeScript (Obsidian's native language)

**Rationale:**
- Only Obsidian plugin API is TypeScript
- Communicate with Python MCP server via HTTP
- Keeps concerns separated (UI ↔ backend)
- Standard pattern (Obsidian → HTTP → MCP server)

---

## Data Model & TypeScript Interfaces

### Configuration File (YAML)

**Location:** `~/.kyutai-mcp/config.yaml` or `/etc/kyutai-mcp/config.yaml`

```yaml
# Kyutai MCP Server Configuration
server:
  host: 127.0.0.1
  port: 8361                    # Default MCP port
  log_level: info               # debug, info, warning, error

# Phase 1: Pocket TTS (local)
pocket_tts:
  enabled: true
  model_config: "b6369a24"      # Recommended config
  temperature: 0.7
  eos_threshold: -4.0
  voices:
    default:
      path: "~/.kyutai-mcp/voices/default_voice.wav"
      language: "en"

# Phase 2: Community APIs (Docker)
apis:
  tts:
    enabled: false              # Enable after Docker setup
    url: "http://localhost:8000/v1"
    api_key: "dummy-key"        # Placeholder
    default_model: "tts-1"

  stt:
    enabled: false
    url: "http://localhost:8080/v1"
    api_key: "dummy-key"
    default_model: "whisper-1"

# Phase 3: Moshi (GPU-required)
moshi:
  enabled: false
  url: "ws://localhost:8998/ws"
  backend: "pytorch"            # pytorch, mlx, rust

# Health Checks
health:
  enabled: true
  interval_seconds: 60
  timeout_seconds: 10

# Caching
cache:
  enabled: true
  ttl_seconds: 3600
  max_audio_mb: 500             # Max cache size for audio files
```

### Python Service Classes

#### Base Configuration Manager

```python
from dataclasses import dataclass
from typing import Optional, Dict, Any
import yaml

@dataclass
class ServiceConfig:
    """Configuration for a single service (Pocket TTS, STT API, etc.)."""
    enabled: bool
    url: Optional[str] = None          # For APIs
    api_key: Optional[str] = None
    default_model: str = "pocket-tts"
    timeout_seconds: int = 30
    retry_count: int = 3

@dataclass
class KyutaiMCPConfig:
    """Main configuration for Kyutai MCP server."""
    host: str = "127.0.0.1"
    port: int = 8361
    log_level: str = "info"

    # Phase 1
    pocket_tts: ServiceConfig

    # Phase 2
    tts_api: ServiceConfig
    stt_api: ServiceConfig

    # Phase 3
    moshi: ServiceConfig

    # Features
    health_check_enabled: bool = True
    cache_enabled: bool = True

    @staticmethod
    def load(path: str) -> "KyutaiMCPConfig":
        """Load configuration from YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)
        return KyutaiMCPConfig(**data)
```

#### Service Base Class

```python
from abc import ABC, abstractmethod
from typing import Dict, Any
import asyncio
from datetime import datetime

class KyutaiService(ABC):
    """Abstract base class for all Kyutai services."""

    def __init__(self, config: ServiceConfig):
        self.config = config
        self.last_error: Optional[str] = None
        self.last_success: Optional[datetime] = None
        self.request_count = 0
        self.error_count = 0

    @property
    def is_healthy(self) -> bool:
        """Check if service is operational."""
        return self.error_count < 5

    @property
    def status(self) -> Dict[str, Any]:
        """Get service status for reporting."""
        return {
            "available": self.config.enabled and self.is_healthy,
            "error_count": self.error_count,
            "request_count": self.request_count,
            "last_error": self.last_error,
            "last_success": self.last_success.isoformat() if self.last_success else None
        }

    @abstractmethod
    async def health_check(self) -> bool:
        """Implement service-specific health check."""
        pass
```

#### Service Implementations

```python
class PocketTTSService(KyutaiService):
    """Pocket TTS (Phase 1): Local, CPU-based TTS."""

    def __init__(self, config: ServiceConfig):
        super().__init__(config)
        self.model = None
        self.voices: Dict[str, Any] = {}
        self._load_model()

    def _load_model(self):
        """Load Pocket TTS model on init."""
        try:
            from pocket_tts import TTSModel
            self.model = TTSModel.load_model(
                config=self.config.default_model
            )
            self.last_success = datetime.now()
        except Exception as e:
            self.last_error = str(e)
            raise

    async def speak(self, text: str, voice_id: str) -> Dict[str, Any]:
        """Generate audio from text."""
        try:
            if voice_id not in self.voices:
                voice_id = "default"

            voice_state = self.model.get_state_for_audio_prompt(
                self.voices[voice_id]["path"]
            )
            audio_tensor = self.model.generate_audio(voice_state, text)

            # Save to file
            audio_path = self._save_audio(audio_tensor)

            self.request_count += 1
            self.last_success = datetime.now()

            return {
                "status": "success",
                "audio_path": audio_path,
                "duration_ms": int(len(audio_tensor) / self.model.sample_rate * 1000)
            }
        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            return {"status": "error", "error": str(e)}

    async def health_check(self) -> bool:
        """Check if Pocket TTS is responsive."""
        try:
            # Quick inference test
            audio = self.model.generate_audio(
                self.model.get_state_for_audio_prompt(
                    self.voices["default"]["path"]
                ),
                "test"
            )
            return len(audio) > 0
        except:
            return False


class STTAPIService(KyutaiService):
    """STT via OpenAI-compatible API (Phase 2+)."""

    def __init__(self, config: ServiceConfig):
        super().__init__(config)
        self.client = None
        self._init_client()

    def _init_client(self):
        """Initialize OpenAI client for STT API."""
        try:
            from openai import OpenAI
            self.client = OpenAI(
                base_url=self.config.url,
                api_key=self.config.api_key
            )
            self.last_success = datetime.now()
        except Exception as e:
            self.last_error = str(e)

    async def transcribe(self, audio_path: str) -> Dict[str, Any]:
        """Transcribe audio to text."""
        try:
            with open(audio_path, "rb") as f:
                result = self.client.audio.transcriptions.create(
                    model=self.config.default_model,
                    file=f,
                    response_format="json"
                )

            self.request_count += 1
            self.last_success = datetime.now()

            return {
                "status": "success",
                "text": result.text,
                "segments": getattr(result, "segments", [])
            }
        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            return {"status": "error", "error": str(e)}

    async def health_check(self) -> bool:
        """Check if STT API is responsive."""
        try:
            models = self.client.models.list()
            return len(models.data) > 0
        except:
            return False
```

---

## Integration Patterns

### Pattern 1: Direct MCP Tool Calls (Obsidian Plugin)

```typescript
// obsidian-kyutai-plugin/src/mcp_bridge.ts
import { spawn } from 'child_process';

export class KyutaiMCPBridge {
    private mcpProcess: ChildProcess;

    async initMCP(): Promise<void> {
        this.mcpProcess = spawn('python', [
            '-m', 'kyutai_mcp.server'
        ]);
    }

    async callTool(
        toolName: string,
        args: Record<string, any>
    ): Promise<any> {
        // Call MCP tool and return result
        const response = await fetch('http://127.0.0.1:8361/tools', {
            method: 'POST',
            body: JSON.stringify({
                tool: toolName,
                args: args
            })
        });
        return await response.json();
    }

    async speakText(text: string, voiceId?: string): Promise<string> {
        const result = await this.callTool('speak_text', {
            text,
            voice_id: voiceId || 'default'
        });
        return result.audio_path;
    }

    async transcribeAudio(audioPath: string): Promise<string> {
        const result = await this.callTool('transcribe_audio', {
            audio_path: audioPath
        });
        return result.text;
    }
}
```

### Pattern 2: Request/Response Flow

```
Obsidian Plugin (User Action)
    ↓
Speak Text: "Hello world"
    ↓
HTTP POST /tools → {tool: "speak_text", args: {text: "...", voice_id: "..."}}
    ↓
Kyutai MCP Server
    ├─ Route to speak_text() tool
    ├─ Load Pocket TTS model
    ├─ Get voice state from sample
    ├─ Generate audio (2-50ms per character)
    ├─ Save to /tmp/kyutai-audio-{uuid}.wav
    └─ Return {status: "success", audio_path: "..."}
    ↓
Obsidian Plugin
    ├─ Read audio file
    ├─ Play via Web Audio API
    └─ Show "Done" in UI
```

### Pattern 3: Health Check Loop

```python
class HealthMonitor:
    """Continuous health checks for all services."""

    async def start(self, interval_seconds: int = 60):
        """Start monitoring loop."""
        while True:
            status = {
                "timestamp": datetime.now().isoformat(),
                "services": {}
            }

            for service_name, service in self.services.items():
                is_healthy = await service.health_check()
                status["services"][service_name] = {
                    "healthy": is_healthy,
                    "details": service.status
                }

            # Log health status
            self.log_health(status)

            await asyncio.sleep(interval_seconds)

    def log_health(self, status: Dict[str, Any]):
        """Log health status (can be extended for monitoring)."""
        logger.info(f"Health check: {json.dumps(status)}")
```

---

## Implementation Roadmap (3 Phases)

### Phase 1: MVP - Pocket TTS (Week 1, ~8 hours)

**Goal:** Get text-to-speech working in Obsidian without external services

**Deliverables:**
1. Python MCP server scaffold (use cloud-vault-mcp as template)
2. PocketTTSService implementation
3. 3 core tools: speak_text, list_models, get_model_status
4. Docker Compose file (single container: Python + Pocket TTS)
5. Basic error handling and logging
6. Health check endpoint
7. Configuration YAML loader
8. Integration tests (pytest)

**Code Structure:**
```
kyutai-mcp-server/
├── src/kyutai_mcp/
│   ├── __init__.py
│   ├── main.py                # Entry point
│   ├── config.py              # Configuration loader
│   ├── server.py              # FastMCP setup (7 tools)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── base.py            # Abstract KyutaiService
│   │   ├── pocket_tts.py      # Phase 1: Pocket TTS
│   │   ├── stt_api.py         # Phase 2: STT API
│   │   ├── tts_api.py         # Phase 2: TTS API
│   │   ├── moshi.py           # Phase 3: Moshi dialogue
│   │   └── health.py          # Health monitoring
│   ├── utils/
│   │   ├── audio.py           # Audio file handling
│   │   ├── cache.py           # Caching layer
│   │   └── errors.py          # Error definitions
│   └── schemas.py             # Pydantic models
├── tests/
│   ├── test_pocket_tts.py
│   ├── test_mcp_tools.py
│   └── test_integration.py
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── requirements.txt
└── README.md
```

**Estimated Effort:**
- Server scaffold: 1 hour
- Pocket TTS service: 2 hours
- MCP tool definitions: 1 hour
- Docker setup: 1 hour
- Testing: 2 hours
- Documentation: 1 hour

### Phase 2: Production - STT + TTS APIs (Week 2, ~12 hours)

**Goal:** Add speech-to-text and higher-quality TTS via OpenAI-compatible APIs

**Deliverables:**
1. STTAPIService (OpenAI-compatible wrapper)
2. TTSAPIService (OpenAI-compatible wrapper)
3. Voice management (set_voice tool)
4. 4 additional tools: transcribe_audio, translate_speech, set_voice, configure_service
5. Docker Compose with 3 containers (MCP server + TTS API + STT API)
6. API health checks and error recovery
7. Retry logic and circuit breaker pattern
8. Performance benchmarks (latency, throughput)

**Docker Compose Stack:**
```yaml
version: '3.8'
services:
  kyutai-mcp:
    image: kyutai-mcp:latest
    ports:
      - "8361:8361"
    environment:
      - TTS_API_URL=http://tts-api:8000/v1
      - STT_API_URL=http://stt-api:8080/v1
    depends_on:
      - tts-api
      - stt-api

  tts-api:
    image: kyutai/tts-openai-api:latest
    ports:
      - "8000:8000"
    environment:
      - CUDA_VISIBLE_DEVICES=0

  stt-api:
    image: kyutai/stt-openai-api:latest
    ports:
      - "8080:8080"
    environment:
      - CUDA_VISIBLE_DEVICES=1
      - MODEL_NAME=kyutai/stt-1b-en_fr
```

**Estimated Effort:**
- STT service: 2 hours
- TTS service: 2 hours
- Voice management: 1.5 hours
- Docker setup: 1.5 hours
- Integration tests: 2 hours
- Performance benchmarking: 1.5 hours
- Documentation: 1.5 hours

### Phase 3: Advanced - Moshi Full-Duplex (Week 3+, ~16 hours)

**Goal:** Enable real-time conversational dialogue with Moshi

**Deliverables:**
1. MoshiService (WebSocket-based)
2. new Tool: full_duplex_conversation (async/streaming)
3. Audio streaming to/from browser
4. Interrupt handling (pause, cancel)
5. LLM integration hooks (optional)
6. Docker Compose with Moshi container (GPU)
7. Load testing for concurrent conversations
8. Obsidian plugin updates (UI for voice dialogue)

**Estimated Effort:**
- Moshi service: 3 hours
- WebSocket plumbing: 3 hours
- Audio streaming: 2 hours
- Obsidian plugin updates: 4 hours
- Integration tests: 2 hours
- Documentation: 2 hours

---

## Configuration & Deployment

### Option A: Local Development (Laptop, CPU-only)

**Hardware:** MacBook, Linux laptop, Windows with WSL

**Setup:**
```bash
# 1. Clone repo
git clone https://github.com/kyutai-labs/kyutai-mcp-server.git
cd kyutai-mcp-server

# 2. Install dependencies
pip install -r requirements.txt
pip install pocket-tts

# 3. Configure
cp config.yaml.example ~/.kyutai-mcp/config.yaml
# Edit to set voice paths, etc.

# 4. Add voice samples
mkdir -p ~/.kyutai-mcp/voices
# Copy voice .wav files here

# 5. Run MCP server
python -m kyutai_mcp.server --config ~/.kyutai-mcp/config.yaml

# 6. Test
curl -X POST http://127.0.0.1:8361/tools \
  -H "Content-Type: application/json" \
  -d '{"tool": "list_models"}'
```

**Result:** Pocket TTS ready to use

---

### Option B: Docker Compose (Single Machine)

**Hardware:** Machine with Docker, optional GPU

**Setup (Phase 1):**
```bash
docker compose up -d kyutai-mcp
```

**Setup (Phase 2 - with APIs):**
```bash
# 1. Clone community API repos
git clone https://github.com/dwain-barnes/kyutai-tts-openai-api tts-api
git clone https://github.com/dwain-barnes/kyutai-stt-openai-api stt-api

# 2. Build images
cd tts-api && docker compose build && cd ..
cd stt-api && docker compose build && cd ..

# 3. Start full stack
docker compose up -d

# 4. Verify
docker compose logs kyutai-mcp
```

---

### Option C: Distributed Setup (Production)

**Hardware:** Separate GPU servers for TTS, STT, Moshi

**Setup:**
```
Local Machine (CPU):
  ├─ Obsidian + Kyutai Plugin
  └─ Connection to remote MCP servers

GPU Server 1:
  ├─ TTS API (Kyutai TTS 1.6B)
  └─ Health checks

GPU Server 2:
  ├─ STT API (Kyutai STT 2.6B)
  └─ Health checks

GPU Server 3 (optional):
  ├─ Moshi (7B, full-duplex)
  └─ Health checks
```

**Configuration:**
```yaml
apis:
  tts:
    url: "http://gpu-server-1:8000/v1"
  stt:
    url: "http://gpu-server-2:8080/v1"
  moshi:
    url: "ws://gpu-server-3:8998/ws"
```

---

## Risk Analysis & Mitigation

### Risk 1: Model Download Failures

**Problem:** Hugging Face token invalid or network timeout during model loading

**Impact:** MCP server fails to start, Obsidian loses voice features

**Mitigation:**
- Store models locally in Docker image (Phase 1)
- Pre-download models during container build
- Implement retry with exponential backoff (3 attempts)
- Graceful degradation: if STT API unavailable, fall back to Pocket TTS

---

### Risk 2: GPU Memory Exhaustion

**Problem:** Multiple TTS/STT/Moshi requests exhaust VRAM

**Impact:** Inference hangs, OOM kills process

**Mitigation:**
- Queue management: max 10 concurrent requests
- Memory pooling: keep models in memory, reuse across requests
- Model offloading: swap models to CPU if needed
- Monitoring: track GPU memory, alert if >90%

---

### Risk 3: Audio Codec Compatibility

**Problem:** Obsidian Web Audio API doesn't support some Kyutai codec outputs

**Impact:** User hears silence or distorted audio

**Mitigation:**
- Phase 1: Output WAV (universally supported)
- Phase 2: Offer MP3 fallback via ffmpeg conversion
- Phase 3: Use browser-native codec detection

---

### Risk 4: STT API Latency Spikes

**Problem:** OpenAI-compatible STT API slow under load

**Impact:** User waits >5 seconds for transcription

**Mitigation:**
- Implement circuit breaker: fail fast if p95 latency > 3s
- Local fallback: use Pocket TTS as degradation
- Caching: memoize transcriptions for repeated audio
- Monitoring: alert on latency > 1s (p95)

---

### Risk 5: Configuration Drift

**Problem:** Docker config doesn't match local config, services out of sync

**Impact:** Tools fail silently or return wrong results

**Mitigation:**
- Single source of truth: YAML config file
- Validation on startup: each service validates config
- Health checks: include config hash in status
- Restart on config change: file watcher triggers reload

---

## Reusable Patterns from cloud-vault-mcp

### Pattern 1: Service-Oriented Architecture

**cloud-vault-mcp example:**
```python
# server.py
def create_server(config: ServerConfig) -> FastMCP:
    vault = VaultOps(config.vault_path)
    obsidian = ObsidianOps(vault)
    sheets = SheetsBridge(...) if config.sheets_enabled else None

    mcp = FastMCP("Cloud Vault", instructions="...")

    @mcp.tool()
    def vault_read(path: str) -> str:
        return vault.read(path)
```

**Apply to Kyutai MCP:**
```python
def create_server(config: KyutaiMCPConfig) -> FastMCP:
    pocket_tts = PocketTTSService(config.pocket_tts) if config.pocket_tts.enabled else None
    stt_api = STTAPIService(config.stt_api) if config.stt_api.enabled else None
    tts_api = TTSAPIService(config.tts_api) if config.tts_api.enabled else None

    mcp = FastMCP("Kyutai Voice", instructions="...")

    @mcp.tool()
    def speak_text(text: str, voice_id: str = "default") -> dict:
        return pocket_tts.speak(text, voice_id)
```

---

### Pattern 2: Configuration Management

**cloud-vault-mcp example:**
```python
@dataclass
class ServerConfig:
    vault_path: str
    sheets_enabled: bool = False
    surrealdb_enabled: bool = False

    @staticmethod
    def from_env() -> "ServerConfig":
        return ServerConfig(
            vault_path=os.getenv("VAULT_PATH", "~/vaults/cohezion-vault"),
            sheets_enabled=os.getenv("SHEETS_ENABLED") == "true"
        )
```

**Apply to Kyutai MCP:**
```python
@dataclass
class KyutaiMCPConfig:
    pocket_tts: ServiceConfig
    tts_api: ServiceConfig
    stt_api: ServiceConfig

    @staticmethod
    def load_or_create(path: Optional[str] = None) -> "KyutaiMCPConfig":
        if not path:
            path = os.path.expanduser("~/.kyutai-mcp/config.yaml")
        if not os.path.exists(path):
            return KyutaiMCPConfig.default()
        return KyutaiMCPConfig.load(path)
```

---

### Pattern 3: Health Checks

**cloud-vault-mcp example:**
```python
class HealthChecker:
    def check_vault(self) -> HealthStatus:
        if os.path.exists(self.vault_path):
            return HealthStatus.HEALTHY
        return HealthStatus.OFFLINE

    def check_sheets(self) -> HealthStatus:
        try:
            rows = self.sheets_bridge.get_all_rows()
            return HealthStatus.HEALTHY
        except Exception as e:
            return HealthStatus.DEGRADED

    @mcp.tool()
    def health_status(self) -> dict:
        return {
            "vault": self.check_vault(),
            "sheets": self.check_sheets(),
            "surrealdb": self.check_surrealdb()
        }
```

**Apply to Kyutai MCP:**
```python
class HealthMonitor:
    async def check_service(self, service: KyutaiService) -> HealthStatus:
        is_healthy = await service.health_check()
        return HealthStatus.HEALTHY if is_healthy else HealthStatus.OFFLINE

    @mcp.tool()
    async def get_model_status(self, model_id: Optional[str] = None) -> dict:
        services = [self.pocket_tts, self.stt_api, self.tts_api]
        status = {}
        for service in services:
            if model_id is None or model_id == service.model_id:
                status[service.model_id] = await self.check_service(service)
        return status
```

---

### Pattern 4: Docker Composition

**cloud-vault-mcp example:**
```yaml
version: '3.8'
services:
  cloud-vault:
    build: .
    ports:
      - "8360:8360"
    environment:
      - VAULT_PATH=/vault
      - SHEETS_ENABLED=true
    volumes:
      - ~/vaults/cohezion-vault:/vault
```

**Apply to Kyutai MCP:**
```yaml
version: '3.8'
services:
  kyutai-mcp:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8361:8361"
    environment:
      - POCKET_TTS_ENABLED=true
      - TTS_API_URL=http://tts-api:8000/v1
      - STT_API_URL=http://stt-api:8080/v1
    volumes:
      - ~/.kyutai-mcp:/home/kyutai/.kyutai-mcp
    depends_on:
      - tts-api
      - stt-api
```

---

### Pattern 5: Error Handling

**cloud-vault-mcp example:**
```python
@mcp.tool()
def vault_read(path: str) -> str:
    try:
        return vault.read(path)
    except FileNotFoundError as e:
        return f"Error: {e}"
    except ValueError as e:
        return f"Error: {e}"
```

**Apply to Kyutai MCP:**
```python
@mcp.tool()
async def speak_text(text: str, voice_id: str = "default") -> dict:
    try:
        if len(text) > 4096:
            return {
                "status": "error",
                "error": f"Text too long ({len(text)}/4096 chars)"
            }
        result = await service.speak(text, voice_id)
        return result
    except Exception as e:
        logger.error(f"speak_text failed: {e}")
        return {"status": "error", "error": str(e)}
```

---

## File Structure Summary

**Source Files (Phase 1):**
- `src/kyutai_mcp/main.py` — Entry point, arg parsing
- `src/kyutai_mcp/server.py` — FastMCP setup, tool registration (7 tools)
- `src/kyutai_mcp/config.py` — Configuration loading, validation
- `src/kyutai_mcp/services/base.py` — Abstract KyutaiService
- `src/kyutai_mcp/services/pocket_tts.py` — Pocket TTS implementation
- `src/kyutai_mcp/services/stt_api.py` — STT API implementation (Phase 2)
- `src/kyutai_mcp/services/tts_api.py` — TTS API implementation (Phase 2)
- `src/kyutai_mcp/services/moshi.py` — Moshi implementation (Phase 3)
- `src/kyutai_mcp/services/health.py` — Health monitoring
- `src/kyutai_mcp/utils/audio.py` — Audio file handling
- `src/kyutai_mcp/utils/cache.py` — Caching layer
- `src/kyutai_mcp/utils/errors.py` — Error definitions

**Config & Deployment:**
- `config.yaml` — Default configuration
- `Dockerfile` — Single image with all dependencies
- `docker-compose.yml` — 3-service stack (Phase 2+)

**Tests:**
- `tests/test_pocket_tts.py` — Unit tests for Pocket TTS
- `tests/test_mcp_tools.py` — Integration tests for all tools
- `tests/test_integration.py` — End-to-end tests with Obsidian

---

## Success Criteria for Implementation

✅ **Phase 1 MVP:**
- [ ] speak_text tool works with Pocket TTS
- [ ] list_models returns accurate inventory
- [ ] get_model_status returns health data
- [ ] Docker image builds and runs without errors
- [ ] Integration tests pass (3/3)
- [ ] Documentation complete

✅ **Phase 2 Production:**
- [ ] transcribe_audio tool works with STT API
- [ ] set_voice tool enables voice cloning
- [ ] configure_service allows runtime updates
- [ ] 3-container Docker stack works
- [ ] Health monitoring active
- [ ] Performance benchmarks meet SLA (p95 latency < 1s)

✅ **Phase 3 Advanced:**
- [ ] full_duplex_conversation tool enables Moshi dialogue
- [ ] WebSocket streaming works end-to-end
- [ ] Interrupt handling (pause, cancel) implemented
- [ ] Obsidian plugin UI updated for voice dialogue
- [ ] Load testing: 8+ concurrent conversations on GPU

---

**End of Architecture Document**

Next steps: Hand off to Phase 3 Implementation team with detailed tool APIs, data schemas, and service examples ready for coding.

## Related

- [[kyutai-api-specification|Kyutai API Specification]] — the upstream API research this architecture builds upon; documents Pocket TTS, Delayed Streams STT/TTS, Moshi, and Unmute APIs
- [[kyutai-obsidian-plugin-architecture|Kyutai Obsidian Plugin Architecture]] — the TypeScript plugin layer that calls this MCP server via HTTP; defines the UI components and workflows
- [[2026-02-10-kyutai-mcp-obsidian-plugin-plan|Kyutai MCP + Obsidian Plugin Plan]] — the compound engineering plan authorizing and scoping this architecture document
- [[cloud-vault-mcp|Cloud Vault MCP]] — the existing MCP server (FastMCP, port 8360) whose patterns (service-oriented architecture, health checks, Docker composition) are directly reused in this design
- [[2026-02-10-kyutai-token-waste-postmortem|Kyutai Token Waste Postmortem]] — lessons from Phase 1 that influenced the architecture decisions here (why FastMCP over TypeScript, why phased rollout)
- [[mcp-model-context-protocol]]
- [[api-design]]
- [[agent-architecture]]
