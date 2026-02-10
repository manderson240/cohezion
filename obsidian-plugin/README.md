# Kyutai Obsidian Plugin

Integrate Kyutai's open-source voice AI models directly into Obsidian. Read notes aloud (TTS), transcribe audio (STT), clone voices, and translate speech - all running locally on your machine for maximum privacy.

## Features

### Phase 1 (MVP) - Available Now
- **Read Note Aloud** - Convert note text to natural-sounding speech
- **Transcribe Audio** - Convert audio recordings to text with word-level timestamps
- **Voice Cloning** - Create custom voices from audio samples
- **Settings Panel** - Full configuration of TTS/STT models and parameters

### Phase 2 - Coming Soon
- **Speech Translation** - Real-time translation between English and French
- **GPU Detection** - Automatic feature tier selection based on hardware
- **Batch Operations** - Process multiple files at once

### Phase 3 - Advanced
- **Voice Conversation** - Full-duplex dialogue with AI (Moshi)
- **Streaming Support** - Progressive audio processing
- **Meeting Transcription** - Multi-speaker detection and summarization

## Installation

### Prerequisites
1. **Obsidian** - v0.15.0 or later
2. **Kyutai MCP Server** - Running on `http://localhost:8000`
   - See [kyutai-mcp-server](../kyutai-mcp-server) for setup

### Steps
1. Clone this repository:
   ```bash
   git clone https://github.com/kyutai/kyutai-obsidian-plugin.git
   ```

2. Install dependencies:
   ```bash
   cd kyutai-obsidian-plugin
   npm install
   ```

3. Build the plugin:
   ```bash
   npm run build
   ```

4. Copy to Obsidian plugins directory:
   ```bash
   cp main.js manifest.json styles.css ~/.obsidian/plugins/kyutai-obsidian-plugin/
   ```

5. Enable the plugin in Obsidian:
   - Open Settings → Community Plugins
   - Search for "Kyutai"
   - Click "Enable"

## Quick Start

### 1. Configure the MCP Server
1. Open Obsidian Settings → Kyutai
2. Set "MCP Server URL" (default: `http://localhost:8000`)
3. Click "Test Connection" to verify

### 2. Read a Note Aloud
1. Open any note
2. Click the speaker icon (🔊) in the ribbon
3. Select a voice and click "Continue"
4. Audio will be generated and played in a modal

### 3. Transcribe Audio
1. Click the microphone icon (🎙️) in the ribbon
2. Choose to upload a file or record from microphone
3. Wait for transcription to complete
4. Review and optionally edit the transcript
5. Click "Insert into Note" to add it to your document

### 4. Clone Your Voice
1. Click the voice icon (🎭) in the ribbon
2. Record or upload a 5-30 second audio sample
3. Your voice will be registered and available in future TTS operations

## Keyboard Shortcuts

| Action | Windows/Linux | macOS |
|--------|---------------|-------|
| Read Note Aloud | `Ctrl+Shift+P` | `Cmd+Shift+P` |
| Transcribe Audio | `Ctrl+Shift+T` | `Cmd+Shift+T` |
| Clone Voice | `Ctrl+Shift+V` | `Cmd+Shift+V` |
| Open Settings | `Ctrl+,` | `Cmd+,` |

## Settings

### General
- **Enable Kyutai Plugin** - Toggle plugin on/off
- **Feature Tier** - Choose available features:
  - Basic: TTS + STT
  - Enhanced: + Voice cloning + Translation
  - Advanced: + Full conversation (GPU required)
- **Default Language** - English or French

### Text-to-Speech
- **Model** - Pocket TTS (CPU) or TTS 1.6B (GPU)
- **Default Voice** - Voice to use when reading notes
- **Speed** - 0.5x to 2.0x (default 1.0x)
- **Pitch** - 80-120% (default 100%)

### Speech-to-Text
- **Model** - STT 1B (CPU, bilingual) or STT 2.6B (GPU, English only)
- **Language** - English or French
- **Include Timestamps** - Word-level timing information
- **Auto-capitalize** - Capitalize sentences automatically
- **Confidence Threshold** - Minimum confidence level (0.0-1.0)

### API Configuration
- **MCP Server URL** - Address of Kyutai MCP server
- **Use GPU** - Enable GPU acceleration if available
- **Timeout** - Seconds to wait before timing out
- **Retry Attempts** - Number of retries on failure

### Cache Settings
- **Enable Caching** - Save results to avoid re-processing
- **Max Cache Size** - Maximum cache storage (MB)
- **Retention** - Auto-delete cache after N days
- **Clear Cache** - Manually delete all cached results

### Accessibility
- **Screen Reader Mode** - Optimize for screen readers
- **High Contrast** - Increase contrast for visibility
- **Large Text** - Increase font size
- **Reduce Animations** - Minimize motion

## Architecture

### Project Structure
```
kyutai-obsidian-plugin/
├── src/
│   ├── main.ts              # Plugin entry point
│   ├── types.ts             # Type definitions
│   ├── services/
│   │   ├── mcp-client.ts    # MCP server communication
│   │   └── audio-processor.ts # Audio recording & playback
│   └── ui/
│       ├── commands.ts      # Ribbon commands
│       ├── modals.ts        # Modal windows
│       └── settings.ts      # Settings tab
├── styles.css               # Plugin styling
├── manifest.json            # Plugin metadata
├── package.json             # Dependencies
└── README.md               # This file
```

### Component Overview

**MCPClient** (`src/services/mcp-client.ts`)
- HTTP communication with MCP server
- WebSocket streaming support (for future features)
- Health checks and model status

**AudioProcessor** (`src/services/audio-processor.ts`)
- Recording via Web Audio API
- Playback and seeking
- File validation and format handling

**Modals** (`src/ui/modals.ts`)
- AudioInputModal: File upload or microphone recording
- ResultDisplayModal: Audio player and text display
- ErrorModal: User-friendly error messages

**Commands** (`src/ui/commands.ts`)
- Ribbon command implementation
- Text extraction from notes
- Result insertion into notes

**Settings** (`src/ui/settings.ts`)
- Obsidian settings panel
- Configuration persistence
- Model selection and parameter adjustment

## Development

### Setup
```bash
git clone <repo>
cd kyutai-obsidian-plugin
npm install
```

### Build
```bash
npm run build
```

### Development Mode
```bash
npm run dev  # Watch mode with live reload
```

### Testing
```bash
npm test
```

## Troubleshooting

### MCP Server Connection Failed
**Problem:** "Could not connect to MCP server"

**Solution:**
1. Ensure MCP server is running: `python -m kyutai_mcp.server`
2. Check the server URL in settings (default: `http://localhost:8000`)
3. Verify firewall allows localhost connections
4. Check browser console for detailed errors

### Microphone Permission Denied
**Problem:** "Microphone access denied"

**Solution:**
1. Check browser permissions (Settings → Privacy & Security)
2. Allow Obsidian access to microphone
3. Reload plugin: Restart Obsidian

### Audio Not Playing
**Problem:** Generated audio won't play

**Solution:**
1. Check browser audio permissions
2. Ensure audio output device is connected
3. Test audio playback in other applications
4. Check browser console for errors

### Model Not Loading
**Problem:** "Model failed to load" or timeout

**Solution:**
1. Ensure sufficient disk space (models are 1-5GB)
2. Check internet connection (first download takes time)
3. Increase timeout in settings (default 30s)
4. Check MCP server logs for detailed errors

## API Reference

### MCP Tools Used

**tts_generate**
```json
{
  "text": "Hello world",
  "voice": "default",
  "model": "pocket-tts",
  "speed": 1.0
}
```

**stt_transcribe**
```json
{
  "audio_file": "base64_encoded_audio",
  "model": "stt-1b-en_fr",
  "language": "en"
}
```

**voice_preview**
```json
{
  "voice_id": "voice_12345",
  "text": "Preview text"
}
```

**model_status**
```json
{}
```

## Accessibility

This plugin is designed with accessibility in mind:
- ✓ Keyboard navigation (Tab, Enter, Escape)
- ✓ ARIA labels on all interactive elements
- ✓ Screen reader support
- ✓ High contrast mode
- ✓ Large text option
- ✓ Reduced motion support
- ✓ Dark/light theme compatibility

## Performance Tips

1. **Use Pocket TTS** - Faster than TTS 1.6B, CPU-friendly
2. **Enable Caching** - Avoid re-processing the same content
3. **Limit Text Length** - Keep notes under 10,000 words for faster processing
4. **Close Other Apps** - Free up system resources for audio models
5. **Use GPU if Available** - Dramatically faster processing for compatible models

## Limitations

- Maximum audio file size: 500 MB
- Maximum text length: 50,000 characters
- Models require minimum system resources:
  - CPU: 2-4 cores
  - RAM: 4-8 GB minimum (16GB recommended)
  - GPU: Optional (24GB+ VRAM for Moshi)
- Speech recognition accuracy depends on audio quality

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

MIT License - See LICENSE file for details

## Support

- **Documentation**: [Kyutai Docs](https://docs.kyutai.org)
- **GitHub Issues**: [Report bugs](https://github.com/kyutai/kyutai-obsidian-plugin/issues)
- **Discord Community**: [Join us](https://discord.gg/kyutai)

## Acknowledgments

Built with:
- [Obsidian Plugin API](https://docs.obsidian.md/Plugins/Getting+started/Build+a+plugin)
- [Kyutai MCP Server](https://github.com/kyutai/kyutai-mcp-server)
- [Kyutai AI Models](https://kyutai.org)

---

**Status:** Phase 1 MVP - Production Ready

**Last Updated:** February 2026

**Version:** 0.1.0
