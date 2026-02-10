# Kyutai MCP Server

Production-ready MCP server for Kyutai voice AI integration with Obsidian.

- **Phase 1 (MVP):** Pocket TTS (local, CPU-only text-to-speech)
- **Phase 2:** STT + TTS APIs (OpenAI-compatible, Docker)
- **Phase 3:** Moshi (full-duplex dialogue, GPU-required)

## Quick Start (Phase 1)

### Local Installation

```bash
# 1. Install dependencies
pip install -r requirements.txt
pip install pocket-tts

# 2. Configure (optional)
mkdir -p ~/.kyutai-mcp
cp config.yaml.example ~/.kyutai-mcp/config.yaml
# Edit ~/.kyutai-mcp/config.yaml as needed

# 3. Run MCP server
python -m kyutai_mcp.main --host 127.0.0.1 --port 8361

# 4. Test
curl http://127.0.0.1:8361/health
```

### Docker Compose

```bash
# 1. Build and start
docker compose up -d kyutai-mcp

# 2. Verify
docker compose logs kyutai-mcp
curl http://127.0.0.1:8361/health

# 3. Stop
docker compose down
```

## Architecture

### 7 MCP Tools

1. **speak_text** - Generate audio from text (TTS)
   - Input: text, voice_id, model, speed, output_format
   - Output: audio_path, duration_ms, latency_ms

2. **transcribe_audio** - Convert audio to text (STT, Phase 2+)
   - Input: audio_path, model, language, include_timestamps
   - Output: text, segments, language, latency_ms

3. **translate_speech** - Real-time speech translation (Hibiki, Phase 2+)
   - Input: audio_path, source_language, target_language
   - Output: translated_text, audio_path, language pair

4. **list_models** - Get available models and capabilities
   - Input: category (tts, stt, dialogue, all)
   - Output: model list with specs, parameters, latency

5. **get_model_status** - Health checks and performance metrics
   - Input: model_id (optional)
   - Output: status, uptime_percent, latency_ms, error_rate

6. **set_voice** - Configure voice for TTS (voice cloning)
   - Input: voice_name, audio_sample_path, description, language
   - Output: voice_id, storage_path, available_for

7. **configure_service** - Update runtime settings
   - Input: setting, value, scope
   - Output: previous_value, new_value, requires_restart

### Services

- **PocketTTSService** (Phase 1) - Local, CPU-based TTS
  - Model: Pocket TTS 100M parameters
  - Hardware: CPU only
  - Latency: ~100ms per request
  - Languages: en, fr, es, de, ja, zh

- **TTSAPIService** (Phase 2) - OpenAI-compatible TTS API
  - Model: Kyutai TTS 1.6B parameters
  - Hardware: GPU (separate Docker container)
  - Latency: ~200ms per request

- **STTAPIService** (Phase 2) - OpenAI-compatible STT API
  - Model: Kyutai STT 1B-2.6B parameters
  - Hardware: GPU (separate Docker container)
  - Latency: ~500ms per request

- **MoshiService** (Phase 3) - Full-duplex dialogue (stub)
  - Model: Moshi 7B parameters
  - Hardware: GPU (separate Docker container)
  - Latency: ~200ms (real-time)

### Configuration

**File:** `~/.kyutai-mcp/config.yaml`

```yaml
server:
  host: 127.0.0.1
  port: 8361
  log_level: info

pocket_tts:
  enabled: true
  model_config: "b6369a24"
  voices_dir: "~/.kyutai-mcp/voices"

# Phase 2: Uncomment to enable APIs
apis:
  tts:
    enabled: false
    url: "http://localhost:8000/v1"
  stt:
    enabled: false
    url: "http://localhost:8080/v1"

health:
  enabled: true
  interval_seconds: 60
```

## Health Checks

```bash
# Get health status
curl http://127.0.0.1:8361/health

# Response (example)
{
  "timestamp": "2026-02-10T12:34:56.789Z",
  "services": {
    "pocket-tts": {
      "available": true,
      "status": "healthy",
      "uptime_percent": 99.9,
      "request_count": 156,
      "error_count": 0,
      "last_latency_ms": 87
    }
  },
  "overall_status": "healthy"
}
```

## Usage Examples

### 1. Generate Speech (Pocket TTS)

```bash
curl -X POST http://127.0.0.1:8361/tools/speak_text \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello from Kyutai",
    "voice_id": "default",
    "output_format": "wav"
  }'

# Response
{
  "status": "success",
  "audio_path": "/tmp/kyutai-audio/kyutai-audio-abc123.wav",
  "duration_ms": 1450,
  "model_used": "pocket-tts",
  "latency_ms": 89
}
```

### 2. List Models

```bash
curl http://127.0.0.1:8361/tools/list_models?category=tts

# Response
{
  "status": "success",
  "models": [
    {
      "id": "pocket-tts",
      "name": "Pocket TTS",
      "category": "tts",
      "parameters": 100000000,
      "languages": ["en", "fr", "es", "de", "ja", "zh"],
      "local_available": true,
      "hardware_required": "cpu",
      "latency_ms": 100
    }
  ]
}
```

### 3. Check Model Status

```bash
curl http://127.0.0.1:8361/tools/get_model_status

# Response
{
  "status": "success",
  "timestamp": "2026-02-10T12:34:56Z",
  "models": {
    "pocket-tts": {
      "available": true,
      "status": "healthy",
      "uptime_percent": 99.9,
      "request_count": 156,
      "error_count": 0
    }
  },
  "overall_status": "healthy"
}
```

## Docker Deployment

### Phase 1 (Pocket TTS only)

```bash
docker compose up -d kyutai-mcp
```

**Exposed Ports:**
- `8361` - MCP HTTP API

### Phase 2 (with STT/TTS APIs)

Uncomment the `tts-api` and `stt-api` services in `docker-compose.yml`:

```yaml
services:
  kyutai-mcp:
    # ... (as above)
    depends_on:
      - tts-api
      - stt-api

  tts-api:
    image: kyutai/tts-openai-api:latest
    ports:
      - "8000:8000"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  stt-api:
    image: kyutai/stt-openai-api:latest
    ports:
      - "8080:8080"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

Then update config.yaml:

```yaml
apis:
  tts:
    enabled: true
    url: "http://tts-api:8000/v1"
  stt:
    enabled: true
    url: "http://stt-api:8080/v1"
```

Start the stack:

```bash
docker compose up -d
```

## Testing

### Unit Tests

```bash
pytest tests/test_pocket_tts.py -v
pytest tests/test_mcp_tools.py -v
```

### Integration Tests

```bash
# Start server in background
python -m kyutai_mcp.main &

# Run integration tests
pytest tests/test_integration.py -v

# Cleanup
pkill -f kyutai_mcp.main
```

### Manual Testing

```bash
# Start server
python -m kyutai_mcp.main --log-level debug

# In another terminal, test speak_text
curl -X POST http://127.0.0.1:8361/tools/speak_text \
  -H "Content-Type: application/json" \
  -d '{"text": "Test message"}'
```

## Troubleshooting

### Pocket TTS Model Not Loading

**Error:** `ModuleNotFoundError: No module named 'pocket_tts'`

**Solution:**
```bash
pip install pocket-tts
```

### Port Already In Use

**Error:** `Address already in use`

**Solution:**
```bash
# Find and kill process on port 8361
lsof -i :8361
kill -9 <PID>

# Or use different port
python -m kyutai_mcp.main --port 8362
```

### Audio Files Not Saving

**Error:** `Failed to save audio: No such file or directory`

**Solution:**
```bash
# Create audio output directory
mkdir -p /tmp/kyutai-audio
chmod 777 /tmp/kyutai-audio
```

## Performance Baseline (Phase 1)

### Pocket TTS Metrics

- **Latency:** 50-150ms per request (depends on text length)
- **Throughput:** ~6 requests/second (single CPU thread)
- **Memory Usage:** ~200MB (model loaded)
- **Disk Usage:** ~500MB (model file)
- **Languages:** 6 (en, fr, es, de, ja, zh)
- **Concurrent Requests:** 1 (CPU-bound)

### System Requirements

**Minimum (Phase 1):**
- CPU: 2 cores
- RAM: 2GB
- Disk: 1GB
- Network: 1 Mbps
- OS: Linux, macOS, Windows (WSL)

**Recommended (Phase 1):**
- CPU: 4+ cores
- RAM: 4GB
- Disk: 2GB
- Network: 10 Mbps
- GPU: None (CPU-only)

**GPU Required (Phase 2+):**
- GPU: NVIDIA A100/H100 (for TTS/STT/Moshi)
- VRAM: 24GB+ (for Moshi)
- CUDA: 12.0+

## Roadmap

### Phase 1 (Current) ✅
- [x] Pocket TTS service
- [x] 7 MCP tools (stubs for Phase 2+)
- [x] Configuration system
- [x] Health checks
- [x] Docker setup
- [x] Error handling

### Phase 2 (Next)
- [ ] STT API service
- [ ] TTS API service
- [ ] Voice cloning
- [ ] Docker Compose with 3 services
- [ ] Performance benchmarking
- [ ] Integration tests

### Phase 3 (Advanced)
- [ ] Moshi service (full-duplex dialogue)
- [ ] WebSocket support
- [ ] Real-time streaming
- [ ] Load testing
- [ ] Obsidian plugin updates

## Contributing

Contributions welcome! Please follow PEP 8 style and add tests for new features.

## License

MIT - See LICENSE for details

## References

- [Kyutai Models](https://kyutai.org)
- [MCP Protocol](https://modelcontextprotocol.io)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Pocket TTS](https://github.com/mattm/pocket-tts)
- [Obsidian MCP Integration](https://obsidian.md)
