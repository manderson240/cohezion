# Obsidian Plugin User Guide

Complete guide to using the Kyutai MCP Obsidian plugin for voice AI features.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Ribbon Commands](#ribbon-commands)
3. [Read Note Aloud](#read-note-aloud)
4. [Transcribe Audio](#transcribe-audio)
5. [Clone Voice](#clone-voice)
6. [Settings & Configuration](#settings--configuration)
7. [Keyboard Shortcuts](#keyboard-shortcuts)
8. [Tips & Tricks](#tips--tricks)
9. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Initial Setup

After installing the plugin (see [INSTALLATION.md](./INSTALLATION.md)):

1. **Verify MCP Server is running:**
   - Terminal: `python -m kyutai_mcp.server`
   - Or: `docker-compose up kyutai-mcp`

2. **Open Obsidian Settings:**
   - Settings → Community Plugins → Kyutai MCP
   - Click "Options" (gear icon)

3. **Configure Connection:**
   - MCP Server URL: `http://localhost:8000` (default)
   - Click "Test Connection"
   - Should show: ✓ Connected

4. **Verify Models:**
   - TTS Model: `pocket-tts` (or your preference)
   - STT Model: `stt-1b-en_fr` (or your preference)
   - Click "Load Models"

5. **Ready to use!**
   - Look for the Kyutai icon in the ribbon (left sidebar)
   - Click to access features

### Plugin Interface Overview

```
Obsidian Vault
│
├─ Ribbon (left sidebar)
│  └─ Kyutai Icon 🎤 ← Click here to open menu
│
├─ Plugin Menu
│  ├─ 📖 Read Note Aloud
│  ├─ 📝 Transcribe Audio
│  ├─ 🎙️ Clone Voice
│  └─ ⚙️ Settings
│
└─ Modal Windows (for detailed features)
   ├─ Voice Synthesis Panel
   ├─ Audio Transcription Panel
   └─ Voice Cloning Panel
```

---

## Ribbon Commands

The ribbon icon provides quick access to all features:

### Ribbon Icon Locations

**By Default:**
- Left sidebar, below other icons
- Click the 🎤 (microphone) icon

**Right-click options:**
- Customize position
- Pin to top
- Hide temporarily

### Opening Features from Ribbon

**Click ribbon icon:**
```
Kyutai MCP Menu
├─ 📖 Read Note Aloud (Ctrl+Shift+V)
├─ 📝 Transcribe Audio (Ctrl+Shift+T)
├─ 🎙️ Clone Voice (Ctrl+Shift+C)
└─ ⚙️ Settings
```

**Or use keyboard shortcuts directly** (see [Keyboard Shortcuts](#keyboard-shortcuts))

---

## Read Note Aloud

Convert note text to speech with natural voice and voice cloning support.

### Quick Start

1. **Open a note** in Obsidian
2. **Click ribbon icon** → "Read Note Aloud" (or `Ctrl+Shift+V`)
3. **Choose options:**
   - ✅ Voice: `default` or custom voice
   - ✅ Speed: `1.0` (normal, adjustable 0.5-2.0)
   - ✅ Pitch: `1.0` (normal, adjustable 0.5-2.0)
4. **Click "Synthesize"**
5. **Audio plays immediately** and saves to vault

### Interface

```
┌─────────────────────────────────────┐
│ 📖 Read Note Aloud                  │
├─────────────────────────────────────┤
│ Note: "My First Note"               │
│ [Select different note...]          │
│                                     │
│ Voice: [default ▼]                  │
│ [+ Add custom voice]                │
│                                     │
│ Speed: [━━◯━━━] 1.0x                │
│ Pitch:  [━━◯━━━] 1.0x                │
│                                     │
│ Format: [WAV ▼]                     │
│ Save to: Audio Files/               │
│ ☑ Auto-play when done               │
│ ☑ Save audio file                   │
│                                     │
│ [Synthesize] [Cancel]               │
└─────────────────────────────────────┘
```

### Options Explained

**Voice**
- `default`: Built-in voice
- `custom_voice`: Upload reference audio
- Click "➕ Add Voice" to create new voice profile

**Speed**
- `0.5`: Slow (50% speed)
- `1.0`: Normal
- `2.0`: Fast (2x speed)

**Pitch**
- `0.5`: Lower pitch
- `1.0`: Normal
- `2.0`: Higher pitch

**Format**
- `WAV`: Higher quality, larger file (2-5MB per minute)
- `MP3`: Compressed, standard (100-300KB per minute)
- `OGG`: Compressed, smaller (50-150KB per minute)

**Save Options**
- ✅ Auto-play: Play audio immediately
- ✅ Save file: Store in vault for reuse
- Save location: Choose folder for audio files

### Voice Cloning

Create custom voices from reference audio:

1. **Click "➕ Add Voice"**
2. **Name the voice:** "My Voice"
3. **Upload reference audio:**
   - 5-30 seconds recommended
   - WAV, MP3, or M4A format
   - Clear speech, minimal background noise
4. **Click "Test Voice"** to preview
5. **Click "Create"** to save

**Result:**
- Voice stored in vault: `Voice Profiles/my_voice.voiceprofile`
- Appears in "Voice" dropdown for future use
- Reusable across all notes

### Workflow Examples

**Example 1: Podcast from Notes**
1. Open note with article outline
2. Read aloud with custom voice
3. Save as MP3 to `Podcasts/` folder
4. Edit filename: `Episode_01_Title.mp3`
5. Share with others

**Example 2: Language Learning**
1. Create note with vocabulary
2. Read with slower speed (0.75x)
3. Listen repeatedly to hear pronunciation
4. Save WAV for offline learning

**Example 3: Accessibility**
1. Enable auto-play
2. Press `Ctrl+Shift+V` while reading notes
3. Listen hands-free while doing other tasks
4. Adjust speed/pitch for comfort

---

## Transcribe Audio

Convert audio files to text with word-level timestamps.

### Quick Start

1. **Click ribbon icon** → "Transcribe Audio" (or `Ctrl+Shift+T`)
2. **Upload audio file** (drag & drop or browse)
3. **Choose STT model:**
   - `stt-1b-en_fr`: English & French, fast
   - `stt-2.6b`: English only, more accurate
4. **Click "Transcribe"**
5. **View results** with timestamps
6. **Paste into note** or save as attachment

### Interface

```
┌──────────────────────────────────────┐
│ 📝 Transcribe Audio                  │
├──────────────────────────────────────┤
│ Audio File: [drag & drop here] ↕     │
│ file_name.mp3                        │
│ 45 seconds • 3.2 MB                  │
│                                      │
│ Model: [stt-1b-en_fr ▼]              │
│ Language: [Auto ▼]                   │
│                                      │
│ Output Format:                       │
│ ○ Full Text                          │
│ ○ Text with Timestamps               │
│ ● SRT (Subtitle File)                │
│ ○ JSON (Detailed)                    │
│                                      │
│ [Transcribe] [Cancel]                │
└──────────────────────────────────────┘
```

### Models

**STT 1B** (Recommended)
- Languages: English, French
- Speed: ~1-2 seconds per minute of audio
- Accuracy: Good for most use cases
- File size: 1.2GB

**STT 2.6B** (Premium)
- Languages: English only
- Speed: Slower, more accurate
- Accuracy: Excellent for technical content
- File size: 5GB

### Output Formats

**Full Text**
```
The quick brown fox jumps over the lazy dog
```

**Text with Timestamps**
```
[0:00-1:23] The quick brown fox
[1:23-2:45] jumps over the lazy dog
```

**SRT Format** (for video subtitles)
```
1
00:00:00,000 --> 00:01:23,000
The quick brown fox

2
00:01:23,000 --> 00:02:45,000
jumps over the lazy dog
```

**JSON Format** (detailed, for processing)
```json
{
  "text": "The quick brown fox jumps over the lazy dog",
  "segments": [
    {
      "id": 0,
      "start": 0.0,
      "end": 1.23,
      "text": "The quick brown fox"
    },
    {
      "id": 1,
      "start": 1.23,
      "end": 2.45,
      "text": "jumps over the lazy dog"
    }
  ],
  "language": "en"
}
```

### Supported Audio Formats

| Format | Quality | File Size | Support |
|--------|---------|-----------|---------|
| WAV | Lossless | Large | ✅ Full |
| MP3 | 128-320 kbps | Medium | ✅ Full |
| FLAC | Lossless | Large | ✅ Full |
| OGG | 128-320 kbps | Small | ✅ Full |
| M4A | 128-256 kbps | Small | ✅ Full |
| WEBM | 128-256 kbps | Small | ⚠️ Limited |

### Workflow Examples

**Example 1: Meeting Notes**
1. Record meeting with voice recorder
2. Transcribe with `stt-1b` model
3. Output as SRT to get timestamps
4. Create meeting note with timestamps
5. Link audio file as attachment

**Example 2: Lecture Transcription**
1. Download lecture recording
2. Transcribe with `stt-2.6b` for accuracy
3. Use SRT format to match video timing
4. Create study notes with timestamped content

**Example 3: Content Analysis**
1. Record ideas/brainstorm session
2. Transcribe to JSON format
3. Parse JSON in another tool
4. Extract key concepts automatically

---

## Clone Voice

Create and manage custom voice profiles for voice synthesis.

### Create Voice Profile

**Method 1: From Plugin Settings**

1. Settings → Kyutai MCP → "Manage Voices"
2. Click "➕ New Voice"
3. Enter name: "Character Voice"
4. Upload reference audio (5-30s)
5. Click "Preview" to hear
6. Click "Save"

**Method 2: From Read Note Aloud**

1. Open "Read Note Aloud" modal
2. Click "➕ Add Voice"
3. Follow same steps as Method 1

### Voice Profile Requirements

**Audio Quality:**
- Duration: 5-30 seconds
- Format: WAV, MP3, M4A
- Sample rate: 16kHz or 24kHz
- Channels: Mono or Stereo

**Content:**
- Clear speech
- Minimal background noise
- Natural speech patterns
- Single speaker

**NOT recommended:**
- Robotic/synthesized voice
- Heavy accents (may reduce quality)
- Music or singing
- Multiple speakers
- Noisy environments

### Voice Profile Management

**View all profiles:**
- Settings → Kyutai MCP → "Manage Voices"
- Shows: Name, Duration, Created date, Preview button

**Preview voice:**
1. Click "🔊 Preview" next to voice
2. Plays a test phrase
3. Hear how it sounds before using

**Use voice:**
1. Open "Read Note Aloud"
2. Select voice from dropdown
3. Synthesize text with that voice
4. Voice remains consistent

**Delete voice:**
1. Settings → Kyutai MCP → "Manage Voices"
2. Click "🗑️" next to voice
3. Confirm deletion

### Voice Profile Storage

Profiles stored in vault:
```
Obsidian Vault
└─ Voice Profiles/
   ├─ default.voiceprofile
   ├─ my_voice.voiceprofile
   └─ character.voiceprofile
```

Each `.voiceprofile` file contains:
- Voice characteristics (embeddings)
- Metadata (name, created date)
- Source audio reference

### Advanced: Edit Voice Profile

Edit profile directly (advanced users):

**File location:** `Voice Profiles/my_voice.voiceprofile`

**Format:**
```yaml
---
name: "My Voice"
created: 2026-02-10
duration_seconds: 15
language: "en"
---
# Audio embeddings and metadata (binary)
```

---

## Settings & Configuration

### Plugin Settings Panel

**Access:** Settings → Community Plugins → Kyutai MCP → Options (⚙️)

### Connection Settings

**MCP Server URL**
- Default: `http://localhost:8000`
- For remote server: `http://gpu-server.local:8000`
- Include protocol (`http://` or `https://`)

**Test Connection:**
- Button to verify connection
- Shows: ✓ Connected or ✗ Failed
- Displays server version and available models

### Model Selection

**TTS (Text-to-Speech) Model**
- `pocket-tts`: Recommended, fast, local
- `moshi`: Advanced, slower, higher quality
- `community-api`: If running community OpenAI-compatible API

**STT (Speech-to-Text) Model**
- `stt-1b-en_fr`: Recommended, English & French
- `stt-2.6b`: English only, more accurate
- `community-api`: If running community API

**Load Models Button:**
- Forces reload of selected models
- Useful if models crash or become unresponsive
- Takes 10-30 seconds

### Audio Settings

**Default Voice**
- `default`: Built-in voice
- Custom voice profiles (if created)

**Auto-play on Synthesize**
- ✅ Enabled: Play audio immediately after synthesis
- ☐ Disabled: Only save to file, don't play

**Save Audio Files**
- ✅ Enabled: Store all synthesized audio in vault
- ☐ Disabled: Play audio but don't save

**Audio Output Folder**
- Default: `Audio Files/`
- Can change to any folder in vault
- Folder is auto-created if doesn't exist

### Performance Settings

**Chunk Size** (advanced)
- Default: `8192`
- Larger = fewer requests, higher latency
- Smaller = more requests, lower latency

**Request Timeout** (advanced)
- Default: `300` seconds (5 minutes)
- Increase for very large transcriptions
- Decrease to fail faster on network issues

**Enable Streaming** (advanced)
- ✅ Enabled: Real-time transcription (more responsive)
- ☐ Disabled: Batch transcription (may be slower)

### Voice Profile Management

**Manage Voices Button:**
- Opens voice profile manager
- Create new profiles
- Preview existing profiles
- Delete unused profiles

**Voice Profile Folder:**
- Default: `Voice Profiles/`
- All voice data stored here
- Can backup or share profiles

### Debug Settings (Advanced)

**Enable Debug Logging**
- ✅ Enabled: Log all API calls and errors to console
- Useful for troubleshooting
- Check Obsidian console: `Ctrl+Shift+I` → Console tab

**Show Detailed Errors**
- ✅ Enabled: Display full error messages
- ☐ Disabled: Show simplified error messages

---

## Keyboard Shortcuts

### Default Shortcuts

| Shortcut | Action | Platform |
|----------|--------|----------|
| `Ctrl+Shift+V` | Read Note Aloud | Windows/Linux |
| `Cmd+Shift+V` | Read Note Aloud | macOS |
| `Ctrl+Shift+T` | Transcribe Audio | Windows/Linux |
| `Cmd+Shift+T` | Transcribe Audio | macOS |
| `Ctrl+Shift+C` | Clone Voice | Windows/Linux |
| `Cmd+Shift+C` | Clone Voice | macOS |

### Customize Shortcuts

1. Settings → Hotkeys
2. Search "Kyutai"
3. Click current shortcut to change
4. Press new key combination
5. Close settings

### Suggested Shortcuts

| Action | Shortcut | Rationale |
|--------|----------|-----------|
| Read Aloud | `Ctrl+Alt+V` | Alt + V for Voice |
| Transcribe | `Ctrl+Alt+T` | Alt + T for Transcribe |
| Quick Voice | `Ctrl+Alt+C` | Alt + C for Clone |

---

## Tips & Tricks

### Performance Optimization

**Faster synthesis:**
1. Use `pocket-tts` model (fastest)
2. Lower sample rate in settings (if available)
3. Disable auto-save if not needed
4. Use smaller text chunks (1000 chars max)

**Better transcription accuracy:**
1. Use `stt-2.6b` model
2. Provide clear audio (minimal background noise)
3. Use SRT format output (more accurate alignment)
4. Pre-filter audio if possible (remove music, noise)

### Workflow Automation

**Create batch transcriptions:**
1. Save multiple audio files to vault
2. Create script to process all files:
   ```bash
   for file in *.mp3; do
     # Call plugin via MCP API
   done
   ```
3. Results saved to vault automatically

**Link audio to notes:**
1. Transcribe audio file
2. Copy-paste transcript into note
3. Link audio file: `[[audio_filename.mp3]]`
4. Play from note directly

### Voice Profile Best Practices

**For consistent narration:**
1. Create voice profile from quiet recording
2. Use same voice for all notes
3. Maintains consistency across notes

**For multi-character content:**
1. Create separate voice profiles
2. Synthesize each character separately
3. Use video editor to combine
4. Create audiobook with multiple voices

**For language learning:**
1. Create profile from native speaker
2. Synthesize vocabulary repeatedly
3. Use slow speed (0.75x) for learning
4. Listen to natural pronunciation

### Integration with Other Tools

**Export to other applications:**
1. Save audio in standard format (MP3, WAV)
2. Open in audio editor (Audacity, etc.)
3. Edit, combine, or enhance
4. Re-import if needed

**Use transcripts in external tools:**
1. Export as JSON format
2. Process in Python/Node.js scripts
3. Extract entities, summarize, etc.
4. Import results back to vault

---

## Troubleshooting

### Connection Issues

**Problem: "Cannot connect to MCP Server"**

**Solution:**
1. Verify MCP server is running: `curl http://localhost:8000/health`
2. Check URL in plugin settings (default: `http://localhost:8000`)
3. Verify firewall allows localhost:8000
4. Restart both MCP server and Obsidian

**Problem: "Connection timeout"**

**Solution:**
1. Check server is responding: `curl -v http://localhost:8000/health`
2. Increase timeout in settings (↑ Request Timeout)
3. Check server logs for errors
4. Try restarting server with more workers: `MCP_WORKERS=8`

### Synthesis Issues

**Problem: "No voice output, only silence"**

**Solution:**
1. Check system volume is not muted
2. Verify "Auto-play" is enabled in settings
3. Check if audio file was created (in Audio Files folder)
4. Try different voice profile
5. Check server logs: `tail -f logs/kyutai-mcp.log`

**Problem: "Voice sounds robotic or unnatural"**

**Solution:**
1. Try different voice profile
2. Reduce speed to 0.75x-0.9x
3. Adjust pitch slightly
4. Use longer text (models better with more context)
5. Create better voice profile (clearer reference audio)

**Problem: "Synthesis is very slow (>5 seconds)"**

**Solution:**
1. Check if GPU is being used: `nvidia-smi` (if NVIDIA)
2. Enable GPU in MCP server settings: `USE_GPU=true`
3. Reduce text length per request
4. Check CPU usage (should be <20% if GPU working)
5. Restart server to clear memory

### Transcription Issues

**Problem: "Transcription accuracy is poor"**

**Solution:**
1. Use `stt-2.6b` model (more accurate but slower)
2. Improve audio quality (remove background noise)
3. Use clean audio format (WAV or FLAC if possible)
4. Check language selection matches audio language
5. Try shorter audio clips (under 1 minute) for testing

**Problem: "Transcription takes too long"**

**Solution:**
1. Use `stt-1b` model (faster but less accurate)
2. Reduce sample rate (if available in settings)
3. Check if GPU is available: `nvidia-smi`
4. Enable GPU in MCP server settings
5. Increase server workers: `MCP_WORKERS=8`

**Problem: "Transcription returns empty or wrong language"**

**Solution:**
1. Verify audio file is not corrupted
2. Try converting to different format (MP3 → WAV)
3. Check audio plays on system (not just plugin)
4. Verify language matches model capability:
   - `stt-1b`: English & French only
   - `stt-2.6b`: English only
5. Try with different audio file to isolate problem

### Voice Cloning Issues

**Problem: "Cannot create voice profile"**

**Solution:**
1. Check audio file is valid (play in media player first)
2. Audio should be 5-30 seconds
3. Use standard format (WAV, MP3, M4A)
4. Check disk space (need ~100MB free)
5. Verify voice storage location is writable

**Problem: "Voice profile doesn't sound like original"**

**Solution:**
1. Create profile with longer reference audio (15+ seconds)
2. Use quieter, clearer recording
3. Ensure only one speaker in audio
4. Try different reference audio sample
5. Test preview before using in notes

### Plugin Not Loading

**Problem: "Plugin appears as disabled in settings"**

**Solution:**
1. Check Obsidian console for errors: `Ctrl+Shift+I`
2. Verify plugin manifest.json is valid
3. Reinstall plugin:
   - Delete `.obsidian/plugins/kyutai-mcp/`
   - Re-extract plugin files
   - Reload in Obsidian
4. Check plugin version matches Obsidian version (v1.4.0+)

**Problem: "Ribbon icon doesn't appear"**

**Solution:**
1. Plugin may be disabled - enable in Community Plugins
2. Reload plugins: `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (macOS)
3. Check icon position (may be in different location)
4. Restart Obsidian completely
5. Check plugin console for errors

### Performance Issues

**Problem: "Obsidian becomes unresponsive during transcription"**

**Solution:**
1. Use streaming mode (real-time transcription)
2. Process shorter audio files (under 1 minute)
3. Run MCP server on separate machine
4. Increase Obsidian available memory
5. Close other resource-heavy applications

**Problem: "GPU memory errors during synthesis"**

**Solution:**
1. Reduce model complexity (use `pocket-tts` instead of `moshi`)
2. Reduce batch size in settings
3. Stop other GPU-intensive applications
4. Check VRAM: `nvidia-smi` (should have >2GB free)
5. Restart MCP server to clear memory

---

## Getting Help

- **Plugin Issues**: [GitHub Issues](https://github.com/kyutai-labs/kyutai-mcp-obsidian/issues)
- **MCP Server Issues**: [MCP Server Documentation](./MCP_SERVER.md)
- **General Kyutai Help**: [kyutai.org](https://kyutai.org)

---

**Last Updated**: 2026-02-10
**Version**: 0.1.0-alpha
