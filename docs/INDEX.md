# Kyutai MCP Server & Obsidian Plugin - Documentation Index

**Quick Navigation for All Documentation**

## For Different Audiences

### 👤 End Users (Obsidian Plugin Users)
Start here if you're using the Obsidian plugin:
1. **[README.md](./README.md)** - Overview and features
2. **[INSTALLATION.md](./INSTALLATION.md)** - Setup guide
3. **[PLUGIN_USAGE.md](./PLUGIN_USAGE.md)** - How to use features
4. **[TROUBLESHOOTING.md](./TROUBLESHOOTING.md)** - Problem solving

### 👨‍💼 System Administrators (Server Deployment)
Start here if you're deploying the MCP server:
1. **[INSTALLATION.md](./INSTALLATION.md)** - Server setup
2. **[MCP_SERVER.md](./MCP_SERVER.md)** - Configuration & deployment
3. **[ARCHITECTURE.md](./ARCHITECTURE.md)** - System design
4. **[TROUBLESHOOTING.md](./TROUBLESHOOTING.md)** - Diagnostics

### 👨‍💻 Developers & Integrators
Start here if you're building with the MCP server:
1. **[API_REFERENCE.md](./API_REFERENCE.md)** - All MCP tools
2. **[MCP_SERVER.md](./MCP_SERVER.md)** - Configuration
3. **[ARCHITECTURE.md](./ARCHITECTURE.md)** - System design
4. **[DEVELOPMENT.md](./DEVELOPMENT.md)** - Contributing code

### 🏗️ Contributors & Maintainers
Start here if you're contributing to the project:
1. **[DEVELOPMENT.md](./DEVELOPMENT.md)** - Development setup
2. **[ARCHITECTURE.md](./ARCHITECTURE.md)** - System design
3. **[API_REFERENCE.md](./API_REFERENCE.md)** - Tool specifications
4. **[TROUBLESHOOTING.md](./TROUBLESHOOTING.md)** - Debugging

---

## Document Overview

### 📖 README.md
**Purpose:** Project overview and quick start
- ✅ What is Kyutai MCP + Obsidian plugin?
- ✅ Key features and use cases
- ✅ 3-step quick start
- ✅ System requirements
- ✅ Links to detailed docs
- **Read if:** You're new to the project

### 🔧 INSTALLATION.md
**Purpose:** Complete setup guide for all platforms
- ✅ System requirements (OS, Python, Node.js, Docker)
- ✅ MCP Server setup (Python venv, dependencies, models)
- ✅ Obsidian plugin installation (manual, npm, marketplace)
- ✅ Configuration (env vars, .yaml files)
- ✅ Verification procedures
- ✅ Docker setup and deployment
- ✅ Platform-specific notes (macOS, Linux, Windows, WSL2)
- ✅ Troubleshooting common install issues
- **Read if:** You're setting up for the first time

### 🚀 MCP_SERVER.md
**Purpose:** Server configuration, deployment, and operations
- ✅ Server overview and architecture
- ✅ Configuration options (all env vars and YAML settings)
- ✅ Starting the server (CLI, Python API, Docker, systemd)
- ✅ Model management (loading, caching, switching)
- ✅ Health checks and monitoring (Prometheus)
- ✅ Performance tuning (latency, throughput, memory)
- ✅ GPU configuration (CUDA, ROCm, MLX)
- ✅ Logging and debugging strategies
- ✅ Production deployment (checklist, architectures, reverse proxy)
- **Read if:** You're deploying or operating the server

### 📱 PLUGIN_USAGE.md
**Purpose:** Complete user guide for Obsidian plugin
- ✅ Getting started and initial setup
- ✅ All ribbon commands and features
- ✅ Read Note Aloud (text-to-speech with voice cloning)
- ✅ Transcribe Audio (speech-to-text with timestamps)
- ✅ Clone Voice (creating custom voice profiles)
- ✅ Settings and configuration options
- ✅ Keyboard shortcuts and customization
- ✅ Tips, tricks, and workflow examples
- ✅ Troubleshooting plugin-specific issues
- **Read if:** You're using the Obsidian plugin

### 🔌 API_REFERENCE.md
**Purpose:** Complete specification of all MCP tools
- ✅ Overview of 7 MCP tools
- ✅ Authentication and security
- ✅ Detailed specification of each tool:
  - synthesize_text (TTS)
  - transcribe_audio (STT)
  - clone_voice (voice profiling)
  - list_voices (voice catalog)
  - list_models (model metadata)
  - get_status (health metrics)
  - stream_audio (WebSocket streaming)
- ✅ Request/response examples for each tool
- ✅ Error codes and handling
- ✅ Rate limiting
- ✅ Client library examples (Python, JavaScript, cURL)
- **Read if:** You're integrating with the MCP server

### 🏗️ ARCHITECTURE.md
**Purpose:** System design and technical architecture
- ✅ System overview diagrams
- ✅ Component architecture (plugin + server)
- ✅ Data flow diagrams (TTS, STT, streaming)
- ✅ Model management (lifecycle, selection, memory)
- ✅ Audio pipeline (processing steps, streaming)
- ✅ Resource management (threading, memory, GPU)
- ✅ Security considerations (validation, auth, privacy)
- ✅ Error handling and recovery
- ✅ Performance characteristics (latency, throughput, memory)
- ✅ Deployment architectures (single machine, separate server, HA)
- ✅ Design patterns (factory, strategy, observer)
- **Read if:** You want to understand system design

### 👨‍💻 DEVELOPMENT.md
**Purpose:** Guide for developers and contributors
- ✅ Getting started (prerequisites, clone, setup)
- ✅ Project structure (both server and plugin)
- ✅ Development environment (VS Code, debugging)
- ✅ Code standards (PEP 8 for Python, ESLint for TypeScript)
- ✅ Running tests (pytest, Jest, fixtures)
- ✅ Building and packaging (wheel, npm, Docker)
- ✅ Adding new MCP tools (step-by-step example)
- ✅ Debugging techniques (logging, profiling)
- ✅ Pull request process and code review
- ✅ Performance optimization tips
- **Read if:** You're contributing code

### 🐛 TROUBLESHOOTING.md
**Purpose:** Problem diagnosis and solutions
- ✅ Server startup issues
- ✅ Server crashes and slowness
- ✅ Plugin loading and connection errors
- ✅ Model and inference problems
- ✅ Audio quality and output issues
- ✅ Performance troubleshooting
- ✅ GPU detection and memory issues
- ✅ Network and remote server issues
- ✅ Comprehensive diagnostic checklist
- ✅ 50+ specific problem scenarios with solutions
- **Read if:** Something isn't working

---

## Feature Quick Reference

### Text-to-Speech (Synthesis)
- **Doc:** [PLUGIN_USAGE.md § Read Note Aloud](./PLUGIN_USAGE.md#read-note-aloud)
- **API:** [API_REFERENCE.md § synthesize_text](./API_REFERENCE.md#1-synthesize_text)
- **Config:** [MCP_SERVER.md § Model Selection](./MCP_SERVER.md#model-selection-strategy)

### Speech-to-Text (Transcription)
- **Doc:** [PLUGIN_USAGE.md § Transcribe Audio](./PLUGIN_USAGE.md#transcribe-audio)
- **API:** [API_REFERENCE.md § transcribe_audio](./API_REFERENCE.md#2-transcribe_audio)
- **Models:** [INSTALLATION.md § Pre-download Models](./INSTALLATION.md#step-4-download-models)

### Voice Cloning
- **Doc:** [PLUGIN_USAGE.md § Clone Voice](./PLUGIN_USAGE.md#clone-voice)
- **API:** [API_REFERENCE.md § clone_voice](./API_REFERENCE.md#3-clone_voice)
- **Examples:** [PLUGIN_USAGE.md § Voice Profile Best Practices](./PLUGIN_USAGE.md#voice-profile-best-practices)

### Real-Time Streaming
- **API:** [API_REFERENCE.md § stream_audio](./API_REFERENCE.md#7-stream_audio)
- **Examples:** [API_REFERENCE.md § Python Example](./API_REFERENCE.md#python-example-asyncio)

---

## Common Tasks

### Setup
- **First time setup:** [INSTALLATION.md](./INSTALLATION.md)
- **Docker deployment:** [INSTALLATION.md § Docker Setup](./INSTALLATION.md#docker-setup)
- **Remote server:** [MCP_SERVER.md § Deployment Architectures](./MCP_SERVER.md#deployment-architectures)

### Configuration
- **Server settings:** [MCP_SERVER.md § Configuration Options](./MCP_SERVER.md#configuration-options)
- **Plugin settings:** [PLUGIN_USAGE.md § Settings & Configuration](./PLUGIN_USAGE.md#settings--configuration)
- **GPU setup:** [MCP_SERVER.md § GPU Configuration](./MCP_SERVER.md#gpu-configuration)

### Optimization
- **Better latency:** [MCP_SERVER.md § Optimize for Latency](./MCP_SERVER.md#optimize-for-latency)
- **More throughput:** [MCP_SERVER.md § Optimize for Throughput](./MCP_SERVER.md#optimize-for-throughput)
- **Less memory:** [MCP_SERVER.md § Optimize for Memory](./MCP_SERVER.md#optimize-for-memory)
- **Plugin performance:** [PLUGIN_USAGE.md § Performance Optimization](./PLUGIN_USAGE.md#performance-optimization)

### Integration
- **Custom client:** [API_REFERENCE.md § Client Libraries](./API_REFERENCE.md#client-libraries)
- **New MCP tools:** [DEVELOPMENT.md § Adding New Tools](./DEVELOPMENT.md#adding-new-tools)
- **Extend plugin:** [DEVELOPMENT.md § Development Environment](./DEVELOPMENT.md#development-environment)

### Troubleshooting
- **Server won't start:** [TROUBLESHOOTING.md § Server Won't Start](./TROUBLESHOOTING.md#server-wont-start)
- **Plugin connection:** [TROUBLESHOOTING.md § Connection Refused](./TROUBLESHOOTING.md#connection-refused)
- **No audio output:** [TROUBLESHOOTING.md § No Audio Output](./TROUBLESHOOTING.md#no-audio-output)
- **GPU issues:** [TROUBLESHOOTING.md § GPU Not Detected](./TROUBLESHOOTING.md#gpu-not-detected)
- **Slow performance:** [TROUBLESHOOTING.md § High Latency](./TROUBLESHOOTING.md#high-latency-5-seconds-per-request)

---

## Information by Format

### Configuration Examples
- **Environment variables:** [INSTALLATION.md § Configuration](./INSTALLATION.md#step-5-configure-environment)
- **YAML config:** [MCP_SERVER.md § YAML Configuration File](./MCP_SERVER.md#yaml-configuration-file)
- **Docker Compose:** [INSTALLATION.md § Docker Compose](./INSTALLATION.md#docker-compose-configuration)
- **Systemd service:** [MCP_SERVER.md § Systemd Service](./MCP_SERVER.md#systemd-service-linux)

### Code Examples
- **Python:** [API_REFERENCE.md § Python Examples](./API_REFERENCE.md#python)
- **JavaScript/TypeScript:** [API_REFERENCE.md § JavaScript](./API_REFERENCE.md#javascript)
- **cURL:** [API_REFERENCE.md § cURL](./API_REFERENCE.md#curl-bash)
- **Bash:** [DEVELOPMENT.md § Testing](./DEVELOPMENT.md#running-tests)

### Diagrams
- **System overview:** [ARCHITECTURE.md § System Overview](./ARCHITECTURE.md#system-overview)
- **Data flow:** [ARCHITECTURE.md § Data Flow](./ARCHITECTURE.md#data-flow)
- **Model selection:** [ARCHITECTURE.md § Model Selection Strategy](./ARCHITECTURE.md#model-selection-strategy)
- **Audio pipeline:** [ARCHITECTURE.md § Audio Pipeline](./ARCHITECTURE.md#audio-processing-steps)

---

## Document Statistics

| Document | Lines | Size | Focus |
|----------|-------|------|-------|
| README.md | 245 | 7.6K | Overview |
| INSTALLATION.md | 662 | 14K | Setup |
| MCP_SERVER.md | 935 | 21K | Server operations |
| PLUGIN_USAGE.md | 786 | 21K | User guide |
| API_REFERENCE.md | 1,090 | 22K | API spec |
| ARCHITECTURE.md | 898 | 30K | System design |
| DEVELOPMENT.md | 896 | 19K | Development |
| TROUBLESHOOTING.md | 980 | 20K | Problem solving |
| **TOTAL** | **6,492** | **155K** | Complete suite |

---

## Cross-References

### Internal Links
All documents are cross-linked. For example:
- README links to INSTALLATION for setup
- PLUGIN_USAGE links to TROUBLESHOOTING for common issues
- DEVELOPMENT links to ARCHITECTURE for system design
- TROUBLESHOOTING links to other docs for detailed info

### External Links
- **Kyutai Official:** https://kyutai.org
- **Obsidian Docs:** https://docs.obsidian.md
- **Model Context Protocol:** https://modelcontextprotocol.io
- **GitHub Issues:** https://github.com/kyutai-labs/kyutai-mcp-obsidian/issues

---

## Getting Help

1. **Check relevant doc** (see "For Different Audiences" above)
2. **Search doc for keyword:** Use browser Ctrl+F / Cmd+F
3. **Check Troubleshooting:** [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
4. **Run diagnostics:** [TROUBLESHOOTING.md § Diagnostic Checklist](./TROUBLESHOOTING.md#diagnostic-checklist)
5. **Report issue:** Collect info from diagnostics and file GitHub issue

---

**Last Updated:** 2026-02-10
**Version:** 0.1.0-alpha
**Total Documentation:** 8 complete guides
