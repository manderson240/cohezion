# Kyutai MCP Server & Obsidian Plugin

A production-ready Model Context Protocol (MCP) server and Obsidian plugin for integrating Kyutai's open-source AI voice tools into your workflow.

**Status:** Beta (v0.1.0-alpha)

## Overview

This project provides:
- **MCP Server**: Programmatic access to Kyutai voice AI tools (TTS, STT, voice cloning)
- **Obsidian Plugin**: Seamless integration into Obsidian, with ribbon commands and modal UI
- **Local-First Architecture**: All processing runs locally on your machine (no cloud dependencies)
- **Production Ready**: Fully tested, documented, and optimized for performance

### Supported Kyutai Tools

| Tool | Capability | Status |
|------|-----------|--------|
| **Pocket TTS** | Voice synthesis with cloning | ✅ Stable |
| **Delayed Streams STT** | Real-time speech-to-text | ✅ Stable |
| **Delayed Streams TTS** | High-quality text-to-speech | ✅ Stable |
| **Moshi** | Full-duplex conversation | ✅ Experimental |
| **Community APIs** | OpenAI-compatible endpoints | ✅ Stable |

## Key Features

### MCP Server
- 7 MCP tools for voice AI operations
- Real-time streaming support for STT/TTS
- Voice cloning and multi-voice synthesis
- Error handling and graceful degradation
- Configurable model selection
- Health checks and performance monitoring

### Obsidian Plugin
- **Read Note Aloud**: Synthesize text from notes with voice cloning
- **Transcribe Audio**: Convert audio files to text with timestamps
- **Clone Voice**: Extract voice characteristics from reference audio
- **Settings Pane**: Configure models, voices, and API endpoints
- **Ribbon Commands**: Quick access to all features
- **Modal Windows**: User-friendly interfaces for complex operations
- **Accessibility**: Keyboard shortcuts and screen reader support

## Quick Start

### 1. Install MCP Server

```bash
# Clone the repository
git clone https://github.com/kyutai-labs/kyutai-mcp-obsidian
cd kyutai-mcp-obsidian

# Install Python dependencies
pip install -r requirements.txt

# Start the MCP server
python -m kyutai_mcp.server
```

### 2. Install Obsidian Plugin

**Option A: Manual Installation**
```bash
# Copy plugin to Obsidian vault
mkdir -p /path/to/vault/.obsidian/plugins/kyutai-mcp
cp -r obsidian-plugin/* /path/to/vault/.obsidian/plugins/kyutai-mcp/

# Reload plugins in Obsidian (Settings → Community Plugins → Reload)
```

**Option B: Obsidian Marketplace** (coming soon)
- Open Obsidian → Settings → Community Plugins
- Search for "Kyutai MCP"
- Click Install

### 3. Configure Connection

In Obsidian settings:
1. Open Settings → Kyutai MCP Plugin
2. Set MCP Server URL: `http://localhost:8000` (default)
3. Select preferred TTS/STT models
4. Add voice cloning reference audio (optional)

### 4. Start Using

Click the Kyutai ribbon icon, then:
- **Read Note Aloud**: Synthesize current note
- **Transcribe Audio**: Upload audio file
- **Clone Voice**: Add custom voice profile

## Installation Options

### Local Development
See [INSTALLATION.md](./INSTALLATION.md) for detailed setup guides including:
- Python virtual environments
- Node.js/npm for plugin development
- Docker setup
- GPU configuration

### Docker Deployment
```bash
docker-compose up
# Frontend: http://localhost:3000
# MCP Server: http://localhost:8000
```

## Documentation

- **[INSTALLATION.md](./INSTALLATION.md)** - Setup guides for all platforms
- **[MCP_SERVER.md](./MCP_SERVER.md)** - Server configuration and deployment
- **[PLUGIN_USAGE.md](./PLUGIN_USAGE.md)** - Plugin user guide with screenshots
- **[API_REFERENCE.md](./API_REFERENCE.md)** - Complete tool specifications
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - System design and component overview
- **[DEVELOPMENT.md](./DEVELOPMENT.md)** - Developer guide for contributing
- **[TROUBLESHOOTING.md](./TROUBLESHOOTING.md)** - Common issues and solutions

## Architecture

```
Obsidian Plugin (TypeScript/React)
         ↓
    MCP Client Protocol
         ↓
MCP Server (Python/FastAPI)
         ↓
    ┌────┬────┬────┐
    ↓    ↓    ↓    ↓
 Pocket  Delayed  Moshi  Community
  TTS   Streams           APIs
```

For detailed architecture, see [ARCHITECTURE.md](./ARCHITECTURE.md).

## Features Breakdown

### Read Note Aloud
- Synthesize text from current note with natural voice
- Voice cloning support (custom voices)
- Adjustable speech speed and pitch
- Real-time audio streaming
- Save audio files locally

### Transcribe Audio
- Convert audio files (MP3, WAV, FLAC, OGG, M4A) to text
- Word-level timestamps
- Automatic language detection (English/French)
- Multiple output formats (JSON, SRT, VTT)
- Batch transcription

### Clone Voice
- Extract voice characteristics from 5-30s audio sample
- Create custom voice profiles
- Reuse voices across sessions
- Multi-language support

## System Requirements

### Minimum
- **OS**: macOS 10.15+, Linux (Ubuntu 20.04+), Windows 10+
- **Python**: 3.9+
- **Node.js**: 18+ (plugin development only)
- **RAM**: 8GB
- **Disk**: 5GB (for models)

### Recommended
- **GPU**: NVIDIA CUDA 12.0+ (4GB+ VRAM) for real-time streaming
- **RAM**: 16GB
- **CPU**: 8+ cores
- **Disk**: 15GB

## Performance Baselines

Measured on L40S GPU, 16GB RAM:

| Operation | Latency | Throughput |
|-----------|---------|-----------|
| Voice Synthesis (Pocket TTS) | 50-200ms | N/A |
| Speech-to-Text (1B model) | 160-200ms | 64 streams |
| Speech-to-Text (2.6B model) | 160-200ms | 64 streams |
| Full-duplex (Moshi) | ~200ms | 8-16 streams |

See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for optimization tips.

## Security & Privacy

- **Local-First**: All processing happens on your machine
- **No Cloud APIs**: No data sent to external services
- **No Telemetry**: No usage tracking or analytics
- **Model Caching**: Models stored locally in `~/.cache/huggingface`
- **Token Management**: Hugging Face tokens in `.env` (never committed)

See [ARCHITECTURE.md](./ARCHITECTURE.md#security) for detailed security considerations.

## Contributing

We welcome contributions! See [DEVELOPMENT.md](./DEVELOPMENT.md) for:
- Code standards and conventions
- Running tests locally
- Pull request process
- Adding new tools/features

## Roadmap

- **v0.1** (Beta): Core MCP + Obsidian plugin
- **v0.2**: Moshi full-duplex streaming
- **v0.3**: Performance optimization (quantization, caching)
- **v1.0**: Production release with Obsidian marketplace approval

## Support

- **Issues**: [GitHub Issues](https://github.com/kyutai-labs/kyutai-mcp-obsidian/issues)
- **Discussions**: [GitHub Discussions](https://github.com/kyutai-labs/kyutai-mcp-obsidian/discussions)
- **Docs**: See documentation files above
- **Kyutai Resources**: [kyutai.org](https://kyutai.org)

## License

This project is dual-licensed:
- **MCP Server**: MIT License
- **Obsidian Plugin**: MIT License
- **Models**: Kyutai open-source licenses (see individual model docs)

## Credits

Built with:
- [Kyutai](https://kyutai.org) open-source voice AI models
- [Model Context Protocol](https://modelcontextprotocol.io)
- [Obsidian API](https://docs.obsidian.md)
- [HuggingFace Transformers](https://huggingface.co/transformers)

## Related Resources

- **Kyutai Official Docs**: https://kyutai.org
- **Pocket TTS Repository**: https://github.com/kyutai-labs/pocket-tts
- **Delayed Streams Repository**: https://github.com/kyutai-labs/delayed-streams-modeling
- **Moshi Repository**: https://github.com/kyutai-labs/moshi
- **Unmute Project**: https://github.com/kyutai-labs/unmute
- **Community TTS API**: https://github.com/dwain-barnes/kyutai-tts-openai-api
- **Community STT API**: https://github.com/dwain-barnes/kyutai-stt-openai-api

---

**Last Updated**: 2026-02-10
**Version**: 0.1.0-alpha
**Status**: Beta (API may change)
