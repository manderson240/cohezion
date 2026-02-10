# Kyutai MCP Server - Quick Start Guide

Get the MCP server running in 5 minutes.

## Installation

### Option 1: Local (Python)

```bash
# Clone/navigate to project
cd /home/mike-anderson/vaults/cohezion-vault/mcp-server

# Install dependencies
pip install -r requirements.txt
pip install pocket-tts

# Create config directory
mkdir -p ~/.kyutai-mcp
cp config.yaml.example ~/.kyutai-mcp/config.yaml

# Run server
python -m kyutai_mcp.main --host 127.0.0.1 --port 8361
```

**Result:** Server running at `http://127.0.0.1:8361`

### Option 2: Docker Compose

```bash
# From project directory
docker compose up -d kyutai-mcp

# Check logs
docker compose logs -f kyutai-mcp

# Verify health
curl http://127.0.0.1:8361/health
```

**Result:** Server running in container at `http://127.0.0.1:8361`

## Test It

### Health Check
```bash
curl http://127.0.0.1:8361/health
```

### List Models
```bash
curl http://127.0.0.1:8361/tools/list_models
```

### Generate Speech
```bash
curl -X POST http://127.0.0.1:8361/tools/speak_text \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello from Kyutai!",
    "voice_id": "default",
    "output_format": "wav"
  }'
```

### Check Model Status
```bash
curl http://127.0.0.1:8361/tools/get_model_status
```

## Configuration

Edit `~/.kyutai-mcp/config.yaml`:

```yaml
server:
  host: 127.0.0.1
  port: 8361
  log_level: info

pocket_tts:
  enabled: true

# For Phase 2, enable APIs:
apis:
  tts:
    enabled: false
    url: "http://localhost:8000/v1"
  stt:
    enabled: false
    url: "http://localhost:8080/v1"
```

## Stop Server

**Local:** `Ctrl+C`

**Docker:** `docker compose down`

## Troubleshooting

### Port 8361 Already in Use
```bash
lsof -i :8361
kill -9 <PID>
```

### Pocket TTS Not Installed
```bash
pip install pocket-tts
```

### Audio Directory Not Found
```bash
mkdir -p /tmp/kyutai-audio
```

## Next Steps

1. **For Obsidian:** Integrate via the plugin interface (Phase 3)
2. **For Testing:** Run `pytest tests/`
3. **For Phase 2:** See `README.md` for STT/TTS API setup

## Documentation

- **Full Guide:** `README.md`
- **Architecture:** `../research/kyutai-mcp-server-architecture.md`
- **API Specs:** `README.md` (Usage Examples section)

## Project Files

```
/home/mike-anderson/vaults/cohezion-vault/mcp-server/
├── src/kyutai_mcp/          # Source code
├── tests/                    # Tests
├── Dockerfile               # Docker image
├── docker-compose.yml       # Docker Compose
├── config.yaml.example      # Config template
├── requirements.txt         # Python deps
├── README.md                # Full documentation
└── QUICKSTART.md           # This file
```

---

**Next:** Read `README.md` for comprehensive documentation and examples.
