# Kyutai MCP + Obsidian Plugin - Installation Guide

Complete installation instructions for all platforms.

## System Requirements

### Minimum Requirements
- **RAM**: 2GB
- **Storage**: 500MB
- **Python**: 3.10+ (for MCP server)
- **Node.js**: 18+ (for plugin development)
- **Obsidian**: 0.15.0+

### Supported Operating Systems
- Windows 10/11
- macOS 10.15+
- Linux (Ubuntu 20.04+, Debian 11+, Fedora 35+)
- WSL2 (Windows Subsystem for Linux 2)
- Docker (Linux containers)

---

## Part 1: MCP Server Installation

The MCP server handles the voice AI functionality. You can install it locally or via Docker.

### Option A: Local Installation (Recommended for Development)

#### 1. Install Python 3.10+

**macOS**:
```bash
brew install python@3.10
```

**Ubuntu/Debian**:
```bash
sudo apt update
sudo apt install python3.10 python3.10-venv
```

**Windows**:
- Download from [python.org](https://www.python.org/downloads/)
- Install with "Add Python to PATH" checked

**Verify Installation**:
```bash
python3 --version  # Should be 3.10 or higher
pip3 --version
```

#### 2. Create Virtual Environment

**macOS/Linux**:
```bash
python3.10 -m venv kyutai-env
source kyutai-env/bin/activate
```

**Windows (PowerShell)**:
```powershell
python -m venv kyutai-env
.\kyutai-env\Scripts\Activate.ps1
```

**Windows (Command Prompt)**:
```cmd
python -m venv kyutai-env
kyutai-env\Scripts\activate.bat
```

#### 3. Install MCP Server Package

```bash
pip install kyutai-mcp-server
```

**Verify Installation**:
```bash
kyutai-mcp --help
```

#### 4. Configure Server

**Create configuration file** (`~/.kyutai/config.yaml`):

```yaml
# Kyutai MCP Server Configuration

server:
  host: "0.0.0.0"
  port: 8000
  debug: false
  log_level: "INFO"

services:
  # Phase 1 MVP - Pocket TTS
  pocket_tts:
    enabled: true
    timeout: 30
    max_workers: 4

  # Phase 2 - Hibiki TTS (disabled in Phase 1)
  hibiki:
    enabled: false
    model: "hibiki-v1"

  # Phase 3 - Moshi Speech (disabled in Phase 1)
  moshi:
    enabled: false
    model: "moshi-v1"

cache:
  enabled: true
  ttl: 3600
  max_size: 100

logging:
  format: "json"
  output: "file"
  file: "~/.kyutai/server.log"
```

**Copy to config location**:
```bash
mkdir -p ~/.kyutai
cp config.yaml ~/.kyutai/
```

#### 5. Start Server

```bash
kyutai-mcp start
```

**Expected Output**:
```
2026-02-10T10:30:00 | INFO | Kyutai MCP Server started on http://0.0.0.0:8000
2026-02-10T10:30:00 | INFO | Registered 7 tools: speak_text, transcribe_audio, ...
2026-02-10T10:30:00 | INFO | Health check: OK
```

**Verify Server Running**:
```bash
curl http://localhost:8000/health
# Response: {"status": "healthy", "tools": 7}
```

#### 6. (Optional) Install GPU Support

For faster audio processing:

**NVIDIA GPUs**:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install pocket-tts[gpu]
```

**AMD GPUs**:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm5.7
```

---

### Option B: Docker Installation (Recommended for Production)

#### 1. Install Docker

**macOS/Windows**:
- Download [Docker Desktop](https://www.docker.com/products/docker-desktop)
- Install and start Docker

**Ubuntu/Linux**:
```bash
sudo apt update
sudo apt install docker.io docker-compose
sudo usermod -aG docker $USER  # Add user to docker group
newgrp docker
```

**Verify Installation**:
```bash
docker --version
docker run hello-world
```

#### 2. Build Docker Image

```bash
cd kyutai-mcp-server
docker build -t kyutai-mcp:0.1.0 .
```

#### 3. Run Container with Docker Compose

**Create `docker-compose.yml`**:

```yaml
version: '3.8'

services:
  kyutai-mcp:
    image: kyutai-mcp:0.1.0
    ports:
      - "8000:8000"
    environment:
      - KYUTAI_LOG_LEVEL=INFO
      - KYUTAI_DEBUG=false
    volumes:
      - ./config.yaml:/app/config.yaml:ro
      - kyutai-cache:/app/cache
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  kyutai-cache:
```

**Start Services**:
```bash
docker-compose up -d
```

**Verify Container Running**:
```bash
docker-compose ps
# Should show kyutai-mcp service running

curl http://localhost:8000/health
# Response: {"status": "healthy"}
```

**View Logs**:
```bash
docker-compose logs -f kyutai-mcp
```

**Stop Services**:
```bash
docker-compose down
```

---

## Part 2: Obsidian Plugin Installation

### Option A: Community Marketplace (Recommended)

#### 1. Open Obsidian Settings

1. Open your Obsidian vault
2. Click **Settings** (bottom-left gear icon)
3. Select **Community Plugins** from left sidebar

#### 2. Find and Install Plugin

1. Click **Browse** button
2. Search for "Kyutai Voice AI"
3. Click the result
4. Click **Install**
5. Click **Enable** to activate

#### 3. Grant Permissions

When prompted, grant the plugin access to:
- Read notes
- Modify notes
- Record audio
- Network access

#### 4. Configure Settings

1. In Settings, select **Kyutai Voice AI** from plugin list
2. Configure:
   - **MCP Server URL**: `http://localhost:8000` (default)
   - **Timeout**: 30 seconds (default)
   - **Voice**: Your preferred voice
   - **Language**: Your preferred language
3. Click **Test Connection** to verify connectivity

---

### Option B: Manual Installation (Development)

#### 1. Prepare Plugin Files

**Download or clone** the plugin repository:
```bash
git clone https://github.com/kyutai/obsidian-plugin
cd obsidian-plugin
```

#### 2. Install Dependencies

```bash
npm install
```

#### 3. Build Plugin

```bash
npm run build
```

**Output**: Creates `main.js` bundle

#### 4. Install in Obsidian

1. Open Obsidian Settings → Community Plugins
2. Enable "Safe mode: OFF" (if needed)
3. Select "Third-party plugins"
4. Click "Browse" → Manual Install
5. Navigate to plugin directory and select `manifest.json`
6. Click **Enable** plugin

#### 5. Configure Plugin

See Option A, Step 4 above.

---

## Part 3: Verify Installation

### Test MCP Server

```bash
# 1. Check server health
curl http://localhost:8000/health

# 2. List available models
curl http://localhost:8000/models

# 3. Test TTS (speak_text)
curl -X POST http://localhost:8000/tools/speak_text \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello from Kyutai",
    "voice": "default",
    "speed": 1.0
  }'
```

### Test Obsidian Plugin

1. **Verify Plugin Loaded**:
   - Open Obsidian console (Ctrl+Shift+I)
   - Look for "Kyutai plugin loaded" message
   - Should show zero errors

2. **Test Ribbon Command**:
   - Create a new note
   - Type: "Hello, this is a test"
   - Click Kyutai ribbon icon
   - Click "Read Note Aloud"
   - Should play audio

3. **Test Settings**:
   - Open Settings → Kyutai Voice AI
   - Click "Test Connection"
   - Should show "✓ Connected to MCP server"

---

## Troubleshooting

### MCP Server Won't Start

**Problem**: `command not found: kyutai-mcp`

**Solution**:
```bash
# Verify installation
pip show kyutai-mcp-server

# Reinstall if needed
pip install --force-reinstall kyutai-mcp-server

# Try full path
~/.kyutai-env/bin/kyutai-mcp start
```

**Problem**: `Address already in use` on port 8000

**Solution**:
```bash
# Find process using port 8000
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill process
kill -9 <PID>  # macOS/Linux
taskkill /PID <PID> /F  # Windows

# Or use different port
kyutai-mcp start --port 8001
```

### Plugin Won't Connect to Server

**Problem**: "Cannot connect to MCP server" error

**Checklist**:
1. ✅ MCP server is running (`curl http://localhost:8000/health`)
2. ✅ Server URL correct in plugin settings
3. ✅ Firewall allows localhost connections
4. ✅ No proxy/VPN blocking connections

**Solution**:
```bash
# 1. Restart server
kyutai-mcp restart

# 2. Check server logs
tail -f ~/.kyutai/server.log

# 3. Disable and re-enable plugin
# Settings → Community Plugins → Kyutai Voice AI → Disable → Enable
```

### Plugin Commands Not Working

**Problem**: Ribbon commands don't appear or don't work

**Solution**:
1. Open Obsidian console (Ctrl+Shift+I)
2. Check for JavaScript errors
3. Verify plugin enabled in Community Plugins
4. Try restarting Obsidian
5. Check plugin compatibility (Obsidian 0.15.0+)

### Audio Playback Issues

**Problem**: Audio doesn't play or sounds distorted

**Solution**:
1. Check browser audio permission (granted in Obsidian)
2. Test system audio: `afplay /System/Library/Sounds/Ping.aiff` (macOS)
3. Check volume levels
4. Try different voice or speed setting
5. Check MCP server logs for errors

---

## Next Steps

After installation:

1. **Read the Quick Start**: See [QUICKSTART.md](mcp-server/QUICKSTART.md)
2. **Explore Settings**: Configure voice, language, and preferences
3. **Try Workflows**: Use Read Note Aloud, Transcribe Audio, Model Status
4. **Check Documentation**: See [API_REFERENCE.md](docs/API_REFERENCE.md)
5. **Report Issues**: GitHub Issues for bugs or feature requests

---

## Advanced Configuration

### Environment Variables

Override config via environment variables:

```bash
export KYUTAI_SERVER_PORT=9000
export KYUTAI_LOG_LEVEL=DEBUG
export KYUTAI_CACHE_ENABLED=false
kyutai-mcp start
```

### Custom Configuration

Create `~/.kyutai/config.yaml` with custom settings:

```yaml
server:
  host: "127.0.0.1"  # Localhost only
  port: 9000
  debug: true  # Enable debug mode

services:
  pocket_tts:
    timeout: 60  # Longer timeout for large texts
    max_workers: 8

cache:
  ttl: 7200  # 2 hours
  max_size: 500  # 500 MB
```

### Development Mode

For plugin development:

```bash
cd obsidian-plugin
npm run dev
# Watch for changes and rebuild

# In separate terminal
npm test  # Run tests
npm run lint  # Check code style
```

---

## Getting Help

- **Documentation**: [User Guide](README.md), [Troubleshooting](docs/TROUBLESHOOTING.md)
- **Issues**: [GitHub Issues](https://github.com/kyutai/obsidian-plugin/issues)
- **Discussions**: [GitHub Discussions](https://github.com/kyutai/obsidian-plugin/discussions)
- **Community**: [Obsidian Forum](https://forum.obsidian.md/)

---

**Last Updated**: 2026-02-10
**Version**: 0.1.0-alpha

