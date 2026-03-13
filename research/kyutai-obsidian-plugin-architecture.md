---
title: Kyutai Obsidian Plugin Architecture
date: 2026-02-09
status: complete
tags: [research, kyutai, obsidian, plugin, architecture, ui-design]
neural:
  activation: 1.0
  stage: growing
  synapse_in: 5
  synapse_out: 8
---

# Kyutai Obsidian Plugin Architecture

**Document Version:** 1.0
**Created:** 2026-02-09
**Status:** Complete Design Specification
**Target Audience:** UI/UX implementers, plugin developers

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [High-Level Architecture](#high-level-architecture)
3. [UI Components Specification](#ui-components-specification)
4. [Ribbon Commands (5-8 Main Actions)](#ribbon-commands-5-8-main-actions)
5. [Modal Windows & Dialogs](#modal-windows--dialogs)
6. [Settings Pane Architecture](#settings-pane-architecture)
7. [Workflows & User Journeys](#workflows--user-journeys)
8. [Plugin Integration Points](#plugin-integration-points)
9. [UI State Management](#ui-state-management)
10. [Accessibility & Theming](#accessibility--theming)
11. [Implementation Roadmap](#implementation-roadmap)
12. [Component Hierarchy Diagram](#component-hierarchy-diagram)
13. [Event Flow Diagrams](#event-flow-diagrams)
14. [Accessibility Checklist](#accessibility-checklist)

---

## Executive Summary

The **Kyutai Obsidian Plugin** integrates open-source voice AI models (TTS, STT, voice cloning, translation) directly into Obsidian, enabling users to:

- **Read notes aloud** with natural voices (text-to-speech)
- **Transcribe audio** recordings (speech-to-text)
- **Clone voices** from reference samples for consistent narration
- **Translate speech** between English and French in real-time
- **Converse** with AI using voice (advanced feature)

**Key Design Principles:**
- **Local-first deployment**: All processing happens on user's machine (privacy)
- **Modular tiers**: Basic TTS/STT on CPU; advanced features with GPU optional
- **OpenAI API compatibility**: Models deployed via community OpenAI-compatible wrappers
- **MCP integration**: Kyutai MCP server provides unified interface to all models
- **Accessibility-first**: Keyboard shortcuts, ARIA labels, screen reader support
- **Three-phase rollout**: MVP → Enhanced → Advanced features

---

## High-Level Architecture

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        OBSIDIAN APPLICATION                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │          KYUTAI OBSIDIAN PLUGIN (TypeScript)             │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │                                                            │   │
│  │  ┌─────────────────────────────────────────────────────┐ │   │
│  │  │  Ribbon UI Commands (5-8 buttons)                  │ │   │
│  │  │  - Read Note Aloud                                 │ │   │
│  │  │  - Transcribe Audio                                │ │   │
│  │  │  - Clone Voice                                     │ │   │
│  │  │  - Translate Speech                                │ │   │
│  │  │  - Converse (Advanced)                             │ │   │
│  │  │  - Settings                                        │ │   │
│  │  │  - Help                                            │ │   │
│  │  └─────────────────────────────────────────────────────┘ │   │
│  │                           ↓                                │   │
│  │  ┌─────────────────────────────────────────────────────┐ │   │
│  │  │  Modal Windows                                     │ │   │
│  │  │  - File/Audio Input Dialog                         │ │   │
│  │  │  - Voice Selection Modal                           │ │   │
│  │  │  - Result Display Panel                            │ │   │
│  │  │  - Configuration Modal                             │ │   │
│  │  │  - Error/Status Modal                              │ │   │
│  │  └─────────────────────────────────────────────────────┘ │   │
│  │                           ↓                                │   │
│  │  ┌─────────────────────────────────────────────────────┐ │   │
│  │  │  Settings Tab in Obsidian Settings                │ │   │
│  │  │  - Model Selection Dropdown                        │ │   │
│  │  │  - API Endpoint Configuration                      │ │   │
│  │  │  - Feature Toggles (Tiers)                         │ │   │
│  │  │  - Advanced Options                                │ │   │
│  │  │  - Voice Management                                │ │   │
│  │  └─────────────────────────────────────────────────────┘ │   │
│  │                           ↓                                │   │
│  │  ┌─────────────────────────────────────────────────────┐ │   │
│  │  │  File I/O & State Management                       │ │   │
│  │  │  - Vault file access                               │ │   │
│  │  │  - Audio file handling                             │ │   │
│  │  │  - Plugin state persistence                        │ │   │
│  │  │  - Cache management                                │ │   │
│  │  └─────────────────────────────────────────────────────┘ │   │
│  │                           ↓                                │   │
│  │  ┌─────────────────────────────────────────────────────┐ │   │
│  │  │  Status Bar & Progress Indicators                  │ │   │
│  │  │  - Model loading status                            │ │   │
│  │  │  - Processing progress                             │ │   │
│  │  │  - Error notifications                             │ │   │
│  │  └─────────────────────────────────────────────────────┘ │   │
│  │                                                            │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           ↓↓↓                                    │
├─────────────────────────────────────────────────────────────────┤
│  HTTP/WebSocket Communication Layer (Fetch API)                 │
├─────────────────────────────────────────────────────────────────┤
│                           ↓↓↓                                    │
├─────────────────────────────────────────────────────────────────┤
│           KYUTAI MCP SERVER (Python Backend)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  MCP Tools (Standardized Interface)                      │   │
│  │  - tts_generate(text, voice, model, speed)              │   │
│  │  - stt_transcribe(audio_file, model, language)          │   │
│  │  - voice_clone(reference_audio, target_text)            │   │
│  │  - translate_speech(audio, source_lang, target_lang)    │   │
│  │  - model_list()                                         │   │
│  │  - model_status()                                       │   │
│  │  - health_check()                                       │   │
│  │  - voice_list()                                         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           ↓↓↓                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Kyutai Model Services (Selectable Backends)             │   │
│  │                                                            │   │
│  │  TTS Options:                                             │   │
│  │  ├─ Pocket TTS (CPU-optimized, voice cloning)            │   │
│  │  └─ OpenAI-compatible API (tts-1.6b-en_fr model)         │   │
│  │                                                            │   │
│  │  STT Options:                                             │   │
│  │  ├─ MLX variant (Apple Silicon native - stt-1b-en_fr)   │   │
│  │  └─ OpenAI-compatible API (stt-2.6b-en model)            │   │
│  │                                                            │   │
│  │  Advanced:                                                │   │
│  │  ├─ Moshi (full-duplex conversation, GPU)               │   │
│  │  ├─ Hibiki (speech translation, French↔English)         │   │
│  │  └─ Delayed Streams Rust server (high throughput)       │   │
│  │                                                            │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           ↓↓↓                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Hardware Detection & Auto-Configuration                 │   │
│  │  - GPU availability (NVIDIA CUDA, Apple Metal)           │   │
│  │  - CPU capability detection                              │   │
│  │  - VRAM/RAM measurement                                  │   │
│  │  - Platform detection (Linux, macOS, Windows)            │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
User Action (Ribbon Button)
    ↓
Plugin Modal Opens
    ↓
User Provides Input (Audio/Text/Voice Sample)
    ↓
Plugin calls MCP Tool via Fetch/WebSocket
    ↓
MCP Server routes to Kyutai Model
    ↓
Model processes (TTS/STT/Translation/Voice Clone)
    ↓
MCP Server returns result (audio file path or text)
    ↓
Plugin caches result + displays in Modal
    ↓
User can play, save, or insert into note
```

---

## UI Components Specification

### Design Language

- **Color Scheme**: Inherit from Obsidian theme (light/dark mode support)
- **Typography**: Obsidian default font stack (monospace for paths, sans-serif for UI)
- **Spacing**: 8px baseline grid (multiples of 8)
- **Animations**: Subtle (200-400ms), fade-in/slide transitions
- **Icons**: Use Lucide React or Feather Icons (Obsidian-compatible)

### Component Library

```
kyutai-plugin/
├── components/
│   ├── RibbonButtons.ts          // 5-8 ribbon commands
│   ├── modals/
│   │   ├── AudioInputModal.ts     // File/audio input dialog
│   │   ├── ResultDisplayModal.ts  // Result viewing/playback
│   │   ├── VoiceSelectionModal.ts // Voice picker
│   │   ├── ConfigurationModal.ts  // Advanced settings
│   │   └── ErrorModal.ts          // Error handling
│   ├── SettingsTab.ts            // Settings pane
│   ├── StatusBar.ts              // Status indicators
│   ├── ProgressBar.ts            // Loading indicator
│   └── VoicePreview.ts           // Voice selection preview
├── services/
│   ├── MCPClient.ts              // MCP communication
│   ├── HardwareDetector.ts       // GPU/CPU detection
│   ├── AudioProcessor.ts         // Audio file handling
│   ├── VoiceManager.ts           // Voice library
│   └── ResultCache.ts            // Result caching
└── types/
    ├── models.ts                 // Type definitions
    └── api.ts                    // API contracts
```

---

## Ribbon Commands (5-8 Main Actions)

### Command 1: Read Note Aloud

**Icon**: 🔊 Speaker / Audio Wave
**Label**: "Read Note Aloud"
**Hotkey**: `Ctrl+Shift+P` (macOS: `Cmd+Shift+P`)

**Behavior:**
- Extracts current note's markdown text (non-code blocks)
- Removes formatting (links, emphasis)
- Opens Voice Selection Modal (if first time, uses default voice)
- Sends text to MCP TTS endpoint
- Generates audio file (saves to vault cache)
- Plays audio in player embedded in note

**Implementation:**

```typescript
// ribbonCommands.ts
app.workspace.registerDomEvent(document, 'click', async (evt) => {
  if (!evt.target?.hasClass('kyutai-read-aloud')) return;

  const editor = app.workspace.activeEditor?.editor;
  if (!editor) return;

  const text = extractNoteText(editor);
  const voiceId = settings.defaultVoice;

  const result = await mcpClient.call('tts_generate', {
    text,
    voice: voiceId,
    model: settings.ttsModel
  });

  showResultModal(result.audio_path);
});
```

---

### Command 2: Transcribe Audio

**Icon**: 🎙️ Microphone / Sound Wave
**Label**: "Transcribe Audio"
**Hotkey**: `Ctrl+Shift+T`

**Behavior:**
- Opens file picker for audio input (MP3, WAV, FLAC, OGG, M4A)
- Shows transcription progress
- Calls MCP STT endpoint with audio
- Returns text + word-level timestamps
- Inserts transcript into note (auto-dated code block)
- Allows editing before insertion

**Implementation:**

```typescript
const transcribeAudio = async () => {
  const filePath = await showAudioFilePicker();
  if (!filePath) return;

  const result = await mcpClient.call('stt_transcribe', {
    audio_file: filePath,
    model: settings.sttModel,
    language: settings.language
  });

  const transcript = formatTranscript(
    result.text,
    result.segments,
    result.language
  );

  showTranscriptModal(transcript); // Allow editing
};
```

---

### Command 3: Clone Voice

**Icon**: 🎭 Masks / Person
**Label**: "Clone Voice"
**Hotkey**: `Ctrl+Shift+V`

**Behavior:**
- Opens modal: "Record or Upload Reference Voice Sample"
  - Microphone button (record 5-30 seconds)
  - File picker (WAV/MP3)
- Saves reference voice to vault cache with UUID name
- Adds entry to voice library in settings
- Subsequent "Read Note Aloud" can select cloned voice
- Shows preview: user can hear voice sample

**Implementation:**

```typescript
const cloneVoice = async () => {
  const audioPath = await showVoiceInputModal();
  if (!audioPath) return;

  const voiceId = UUID();
  const voicePath = `${VAULT_CACHE}/${voiceId}.wav`;

  // Copy reference sample
  await app.vault.copy(audioPath, voicePath);

  // Register in settings
  settings.voices.push({
    id: voiceId,
    name: `Cloned Voice ${Date.now()}`,
    referencePath: voicePath,
    createdAt: Date.now()
  });

  // Show preview
  const preview = await mcpClient.call('voice_preview', {
    voice_id: voiceId,
    text: "This is a preview of your cloned voice."
  });

  playAudio(preview.audio_path);
};
```

---

### Command 4: Translate Speech

**Icon**: 🌍 Globe / Language
**Label**: "Translate Speech"
**Hotkey**: `Ctrl+Shift+L`

**Behavior:**
- Opens modal: "Speech Translation (French ↔ English)"
  - Source language dropdown (French, English)
  - Target language dropdown (auto-selects opposite)
  - Audio input (file picker or record)
- Calls Hibiki translation model via MCP
- Returns both audio (translated) + text (transcript + translation)
- Inserts into note with bilingual formatting

**Implementation:**

```typescript
const translateSpeech = async () => {
  const { audioPath, sourceLang, targetLang } =
    await showTranslationModal();

  const result = await mcpClient.call('translate_speech', {
    audio: audioPath,
    source_lang: sourceLang,
    target_lang: targetLang,
    model: 'hibiki-2b'
  });

  insertTranslationIntoNote({
    sourceText: result.source_text,
    targetText: result.target_text,
    audioPath: result.audio_path,
    languages: [sourceLang, targetLang]
  });
};
```

---

### Command 5: Converse (Voice Chat)

**Icon**: 💬 Chat Bubble
**Label**: "Converse with AI"
**Hotkey**: `Ctrl+Shift+C` (requires GPU - hidden if unavailable)

**Behavior:**
- Opens full-screen modal with Moshi conversation interface
- Record or type message → AI responds with text + speech
- Full-duplex capability (can interrupt)
- Conversation history saved to vault
- Export conversation as note

**Implementation:**

```typescript
const converseWithAI = async () => {
  if (!settings.gpuAvailable) {
    showNotice("GPU required for voice conversation");
    return;
  }

  const modal = new MoshiConversationModal(
    app,
    mcpClient,
    settings
  );
  modal.open();
};
```

---

### Command 6: Settings

**Icon**: ⚙️ Gear
**Label**: "Kyutai Settings"
**Hotkey**: Auto-opens plugin settings panel

**Behavior:**
- Opens Obsidian settings panel → Kyutai plugin tab
- See [Settings Pane Architecture](#settings-pane-architecture) below

---

### Command 7: Model Status

**Icon**: 📊 Bar Chart
**Label**: "Model Status"
**Hotkey**: `Ctrl+Shift+M`

**Behavior:**
- Opens read-only modal showing:
  - Available models and status (loaded/ready/error)
  - GPU/CPU resource usage
  - Cached voices and results
  - MCP server connection status
  - Last 5 operations (timestamps, models used)

**Implementation:**

```typescript
const showModelStatus = async () => {
  const status = await mcpClient.call('model_status');
  showStatusModal({
    connectedModels: status.models,
    gpuAvailable: status.gpu_available,
    vramUsage: status.vram_usage_gb,
    cachedVoices: settings.voices.length,
    lastOperations: cache.getRecentOperations(5)
  });
};
```

---

### Command 8: Help / Quickstart

**Icon**: ❓ Question Mark
**Label**: "Kyutai Help"

**Behavior:**
- Opens modal with:
  - Quick start guide (3 steps to TTS)
  - Feature matrix (what requires GPU)
  - Troubleshooting (common errors)
  - Links to Kyutai GitHub + documentation
  - Keyboard shortcuts reference

---

## Modal Windows & Dialogs

### Modal 1: Audio Input Dialog

**Purpose**: Unified interface for audio file/recording input
**Used by**: Transcribe, Translate, Voice Clone commands

**Layout:**

```
┌─────────────────────────────────────────┐
│  Audio Input                     [×]    │
├─────────────────────────────────────────┤
│                                         │
│  Choose Input Method:                   │
│  ◉ Upload File                          │
│  ○ Record from Microphone               │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ [Choose File...]                │   │
│  │ audio.mp3 (2.5 MB, 0:45)         │   │
│  └─────────────────────────────────┘   │
│                                         │
│  Supported: MP3, WAV, FLAC, OGG, M4A   │
│  Max size: 500 MB (customizable)       │
│                                         │
│                 [Cancel]  [Continue]   │
│                                         │
└─────────────────────────────────────────┘
```

**TypeScript Interface:**

```typescript
interface AudioInputModalProps {
  onConfirm: (audioPath: string) => void;
  onCancel: () => void;
  maxFileSizeMB?: number;
  allowRecording?: boolean;
  supportedFormats?: string[];
}

class AudioInputModal extends Modal {
  onConfirm: (path: string) => void;
  inputMethod: 'file' | 'record' = 'file';
  selectedFile: TFile | null = null;
  recordingData: Blob | null = null;

  async onOpen() {
    const { contentEl } = this;
    this.renderInputMethodSelector(contentEl);
  }

  private renderInputMethodSelector(container: HTMLElement) {
    // Radio buttons for file vs record
    // File picker implementation
    // Audio recorder WebAPI integration
  }
}
```

---

### Modal 2: Result Display Modal

**Purpose**: Play, save, or insert generated audio/text results
**Used by**: TTS, STT, Translation, Voice Clone results

**Layout (TTS Result):**

```
┌─────────────────────────────────────────────────┐
│  Read Note Aloud Result                   [×]   │
├─────────────────────────────────────────────────┤
│                                                 │
│  Voice: Cloned Voice #1 (English, Female)       │
│  Model: Pocket TTS | Duration: 2:45             │
│                                                 │
│  ┌───────────────────────────────────────────┐  │
│  │ ▶ [████████████░░░░░░] 1:23 / 2:45         │  │
│  │                                            │  │
│  │  Settings: Speed 1.0x | Pitch 100%        │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  [🔊 Download] [📝 Insert into Note] [Copy]    │
│                                                 │
│                        [OK]                    │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Layout (STT Result):**

```
┌─────────────────────────────────────────────────┐
│  Transcription Result                     [×]   │
├─────────────────────────────────────────────────┤
│  Model: STT 2.6B-EN | Language: English         │
│  Confidence: 95% | Duration: 0:45               │
│                                                 │
│  ┌───────────────────────────────────────────┐  │
│  │ The quick brown fox jumps over the lazy    │  │
│  │ dog. This is an example transcription.    │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  ├─ Word-level timestamps available             │
│  ├─ Segments: 3                                 │
│  └─ Editable: [Enable Editing]                  │
│                                                 │
│  [📋 Copy] [🔤 Insert as Code Block] [OK]      │
│                                                 │
└─────────────────────────────────────────────────┘
```

**TypeScript Interface:**

```typescript
type ResultType = 'audio' | 'text' | 'bilingual';

interface ResultDisplayModalProps {
  resultType: ResultType;
  content: AudioResult | TextResult | BillingualResult;
  onInsert: (content: string) => void;
  onDownload: (path: string) => void;
}

class ResultDisplayModal extends Modal {
  resultType: ResultType;
  audioElement: HTMLAudioElement | null;
  editable: boolean = false;

  async onOpen() {
    if (this.resultType === 'audio') {
      this.renderAudioPlayer();
    } else if (this.resultType === 'text') {
      this.renderTextDisplay();
    } else {
      this.renderBilingual();
    }
  }

  private renderAudioPlayer() {
    // HTML5 audio element
    // Playback controls
    // Duration display
    // Download button
  }
}
```

---

### Modal 3: Voice Selection Modal

**Purpose**: Choose which voice to use for TTS
**Trigger**: First use of "Read Note Aloud" or manual voice selection

**Layout:**

```
┌──────────────────────────────────────────┐
│  Select Voice                      [×]   │
├──────────────────────────────────────────┤
│                                          │
│  Built-in Voices:                        │
│  ◉ Default (English, Neutral)            │
│  ○ Alloy (English, Warm)                 │
│  ○ Echo (English, Energetic)             │
│                                          │
│  Cloned Voices:                          │
│  ○ Voice #1 [preview] [remove]           │
│  ○ Voice #2 [preview] [remove]           │
│                                          │
│  [+ Clone New Voice]                     │
│                                          │
│  ┌────────────────────────────────────┐  │
│  │ Preview: "The quick brown fox..."  │  │
│  │ ▶ [████░░░░░░░░░] 5s / 12s         │  │
│  └────────────────────────────────────┘  │
│                                          │
│          [Cancel]  [Select]              │
│                                          │
└──────────────────────────────────────────┘
```

**TypeScript Interface:**

```typescript
interface Voice {
  id: string;
  name: string;
  type: 'builtin' | 'cloned';
  language: string;
  gender?: 'male' | 'female' | 'neutral';
  referencePath?: string; // for cloned voices
}

class VoiceSelectionModal extends Modal {
  selectedVoiceId: string = '';
  voices: Voice[] = [];
  previewAudio: HTMLAudioElement | null;

  async onOpen() {
    this.loadVoices();
    this.renderVoiceList();
  }

  private renderVoiceList() {
    // List of built-in voices (radio buttons)
    // Separator
    // List of cloned voices with preview + remove buttons
    // Clone new voice button
  }

  async previewVoice(voiceId: string) {
    const preview = await mcpClient.call('voice_preview', {
      voice_id: voiceId,
      text: "The quick brown fox jumps over the lazy dog."
    });
    this.playPreview(preview.audio_path);
  }
}
```

---

### Modal 4: Configuration Modal

**Purpose**: Advanced settings UI (alternative to settings tab for quick access)
**Trigger**: Advanced option buttons in other modals

**Layout:**

```
┌─────────────────────────────────────────────┐
│  Advanced Settings                     [×]  │
├─────────────────────────────────────────────┤
│                                             │
│  TTS Settings:                              │
│  Model: [Pocket TTS ▼]                      │
│  Speed: [━━●━━━] 1.0x                       │
│  Pitch: [━━●━━━] 100%                       │
│                                             │
│  STT Settings:                              │
│  Model: [STT 2.6B ▼]                        │
│  Language: [English ▼]                      │
│  ☐ Include Word Timestamps                  │
│  ☐ Auto-capitalize                          │
│  Confidence Threshold: [━━●━] 0.8            │
│                                             │
│  API Settings:                              │
│  MCP Server URL: [http://localhost:8000]   │
│  ☐ Use GPU if available                     │
│  Timeout (seconds): [30]                    │
│                                             │
│  Cache Settings:                            │
│  Max cache size (MB): [500]                 │
│  [Clear Cache]                              │
│                                             │
│               [Restore Defaults] [OK]       │
│                                             │
└─────────────────────────────────────────────┘
```

**TypeScript Interface:**

```typescript
interface AdvancedSettings {
  tts: {
    model: string;
    speed: number; // 0.5-2.0
    pitch: number; // 80-120
  };
  stt: {
    model: string;
    language: string;
    includeTimestamps: boolean;
    autoCapitalize: boolean;
    confidenceThreshold: number;
  };
  api: {
    serverUrl: string;
    useGpu: boolean;
    timeoutSeconds: number;
  };
  cache: {
    maxSizeMB: number;
  };
}

class ConfigurationModal extends Modal {
  settings: AdvancedSettings;

  async onOpen() {
    this.renderTtsSection();
    this.renderSttSection();
    this.renderApiSection();
    this.renderCacheSection();
  }

  async clearCache() {
    if (await showConfirmation("Clear all cached audio?")) {
      await cache.clear();
      showNotice("Cache cleared");
    }
  }
}
```

---

### Modal 5: Error / Status Modal

**Purpose**: Display errors, warnings, and operational status
**Trigger**: Automatic on error or via status command

**Layout (Error):**

```
┌───────────────────────────────────────────┐
│  Error                               [×]  │
├───────────────────────────────────────────┤
│                                           │
│  ⚠️  Connection Failed                    │
│                                           │
│  Could not reach MCP server at            │
│  http://localhost:8000                    │
│                                           │
│  Steps to resolve:                        │
│  1. Check if MCP server is running        │
│     Run: python -m kyutai_mcp.server     │
│  2. Verify API endpoint in settings      │
│  3. Check firewall settings              │
│                                           │
│  Error Details:                           │
│  └─ Connection refused (ECONNREFUSED)     │
│                                           │
│  [View Server Logs] [Open Settings] [OK] │
│                                           │
└───────────────────────────────────────────┘
```

**TypeScript Interface:**

```typescript
type ErrorSeverity = 'info' | 'warning' | 'error' | 'fatal';

interface ErrorModalProps {
  title: string;
  message: string;
  severity: ErrorSeverity;
  details?: string;
  actions?: Array<{
    label: string;
    callback: () => void;
  }>;
}

class ErrorModal extends Modal {
  title: string;
  message: string;
  severity: ErrorSeverity;
  details?: string;
  actions: Array<{ label: string; callback: () => void }>;

  async onOpen() {
    this.renderErrorMessage();
    this.renderDetailsIfPresent();
    this.renderActionButtons();
  }

  private getIconForSeverity(severity: ErrorSeverity) {
    return {
      info: 'ℹ️',
      warning: '⚠️',
      error: '❌',
      fatal: '🔴'
    }[severity];
  }
}
```

---

## Settings Pane Architecture

**Location**: Obsidian Settings → Plugin tab → "Kyutai"
**Organization**: Collapsible sections for clarity

### Full Settings Schema

```typescript
interface KyutaiPluginSettings {
  // ===== GENERAL =====
  enabled: boolean;
  defaultTier: 'basic' | 'enhanced' | 'advanced'; // Controls visible features
  language: string; // 'en', 'fr', etc.

  // ===== TTS SETTINGS =====
  tts: {
    model: 'pocket-tts' | 'tts-1.6b-en_fr';
    defaultVoice: string; // voice UUID or 'default'
    speed: number; // 0.5-2.0, default 1.0
    pitch: number; // 80-120, default 100
    responseFormat: 'mp3' | 'wav' | 'flac'; // for API models
  };

  // ===== STT SETTINGS =====
  stt: {
    model: 'stt-1b-en_fr' | 'stt-2.6b-en';
    language: string; // 'en', 'fr'
    includeTimestamps: boolean;
    autoCapitalize: boolean;
    confidenceThreshold: number; // 0.0-1.0, default 0.7
    responseFormat: 'json' | 'text' | 'srt'; // Output format
  };

  // ===== VOICE MANAGEMENT =====
  voices: Array<{
    id: string; // UUID
    name: string;
    type: 'builtin' | 'cloned';
    referencePath?: string;
    language?: string;
    createdAt: number; // timestamp
  }>;

  // ===== API CONFIGURATION =====
  api: {
    serverUrl: string; // default: 'http://localhost:8000'
    useGpu: boolean;
    gpuModel: 'cuda' | 'metal' | 'auto'; // auto-detect
    timeoutSeconds: number; // default 30
    retryAttempts: number; // default 3
    retryDelayMs: number; // default 1000
  };

  // ===== CACHE SETTINGS =====
  cache: {
    enabled: boolean;
    maxSizeMB: number; // default 500
    autoCleanup: boolean;
    retentionDays: number; // default 30
  };

  // ===== PLUGIN BEHAVIOR =====
  ui: {
    showStatusBar: boolean;
    showProgressNotifications: boolean;
    insertResultsAsCodeBlocks: boolean; // vs inline
    autoPlayResults: boolean; // auto-play audio after generation
    darkModeUI: boolean; // independent from Obsidian theme
  };

  // ===== ACCESSIBILITY =====
  accessibility: {
    screenReaderMode: boolean;
    highContrast: boolean;
    largeText: boolean;
    reduceAnimations: boolean;
  };

  // ===== EXPERIMENTAL =====
  experimental: {
    enableMoshi: boolean; // full-duplex conversation
    enableHibiki: boolean; // speech translation
    enableLocalMllama: boolean; // local LLM for Moshi
  };
}
```

### Settings UI Layout

```
┌────────────────────────────────────────────────────┐
│ KYUTAI PLUGIN SETTINGS                             │
├────────────────────────────────────────────────────┤
│                                                    │
│ ▼ GENERAL                                          │
│   ☑ Enable Kyutai Plugin                           │
│   Feature Tier: [Basic ▼]                          │
│     → Basic: TTS, STT                              │
│     → Enhanced: Voice cloning, translation         │
│     → Advanced: Full Moshi conversation (GPU)      │
│   Default Language: [English ▼]                    │
│                                                    │
│ ▼ TEXT-TO-SPEECH                                   │
│   Model: [Pocket TTS ▼]                            │
│     ℹ️ CPU optimized, no GPU required              │
│   Default Voice: [Default (English) ▼]             │
│   Speed: [────●────] 1.0x                          │
│   Pitch: [────●────] 100%                          │
│   Response Format: [MP3 ▼]                         │
│   ☐ Auto-play after generation                     │
│                                                    │
│ ▼ SPEECH-TO-TEXT                                   │
│   Model: [STT 2.6B-EN ▼]                           │
│   Language: [English ▼]                            │
│   ☑ Include word-level timestamps                  │
│   ☑ Auto-capitalize                                │
│   Confidence Threshold: [────●────] 0.7            │
│   Response Format: [JSON ▼]                        │
│                                                    │
│ ▼ VOICE MANAGEMENT                                 │
│   Registered Voices: 2                             │
│   [► View Voices] [+ Add New]                      │
│                                                    │
│ ▼ API CONFIGURATION                                │
│   MCP Server URL: [http://localhost:8000]         │
│   ☑ Use GPU if available                           │
│   Auto-detect GPU: [✓ CUDA detected]              │
│   Timeout: [30] seconds                            │
│   Retry Attempts: [3]                              │
│   Retry Delay: [1000] ms                           │
│   [Test Connection]                                │
│                                                    │
│ ▼ CACHE SETTINGS                                   │
│   ☑ Enable caching                                 │
│   Max Cache Size: [500] MB                         │
│   Current Usage: 234 MB (47%)                      │
│   ☑ Auto-cleanup after [30] days                   │
│   [Clear Cache Now]                                │
│                                                    │
│ ▼ PLUGIN BEHAVIOR                                  │
│   ☑ Show status bar indicator                      │
│   ☑ Show progress notifications                    │
│   ☑ Insert results as code blocks                  │
│   ☑ Auto-play audio results                        │
│   Dark mode UI: [Auto ▼]                           │
│                                                    │
│ ▼ ACCESSIBILITY                                    │
│   ☐ Screen reader mode                             │
│   ☐ High contrast UI                               │
│   ☐ Large text                                     │
│   ☐ Reduce animations                              │
│                                                    │
│ ▼ EXPERIMENTAL (Advanced)                          │
│   ☐ Enable Moshi (voice conversation, requires GPU)│
│   ☐ Enable Hibiki (speech translation)             │
│   ☐ Enable local LLaMA (for Moshi responses)       │
│                                                    │
│                            [Reset to Defaults]    │
│                                                    │
└────────────────────────────────────────────────────┘
```

**TypeScript Settings Tab:**

```typescript
export class KyutaiSettingsTab extends PluginSettingTab {
  plugin: KyutaiPlugin;

  display(): void {
    const { containerEl } = this;
    containerEl.empty();
    containerEl.createEl('h2', { text: 'Kyutai Settings' });

    // General Settings
    new Setting(containerEl)
      .setName('Enable Kyutai')
      .setDesc('Turn the plugin on/off')
      .addToggle(toggle => toggle
        .setValue(this.plugin.settings.enabled)
        .onChange(async (value) => {
          this.plugin.settings.enabled = value;
          await this.plugin.saveSettings();
        })
      );

    new Setting(containerEl)
      .setName('Feature Tier')
      .setDesc('Controls which features are available')
      .addDropdown(dropdown => dropdown
        .addOption('basic', 'Basic (TTS, STT)')
        .addOption('enhanced', 'Enhanced (+ Voice cloning, translation)')
        .addOption('advanced', 'Advanced (+ Full conversation)')
        .setValue(this.plugin.settings.defaultTier)
        .onChange(async (value) => {
          this.plugin.settings.defaultTier = value as any;
          await this.plugin.saveSettings();
          this.display(); // Refresh to show/hide features
        })
      );

    // TTS Section
    containerEl.createEl('h3', { text: 'Text-to-Speech' });
    new Setting(containerEl)
      .setName('TTS Model')
      .setDesc('Choose model: Pocket TTS (CPU) or TTS 1.6B (GPU)')
      .addDropdown(dropdown => dropdown
        .addOption('pocket-tts', 'Pocket TTS (CPU, recommended)')
        .addOption('tts-1.6b-en_fr', 'TTS 1.6B (GPU, higher quality)')
        .setValue(this.plugin.settings.tts.model)
        .onChange(async (value) => {
          this.plugin.settings.tts.model = value as any;
          await this.plugin.saveSettings();
        })
      );

    new Setting(containerEl)
      .setName('Default Voice')
      .setDesc('Voice to use when reading notes')
      .addDropdown(dropdown => {
        dropdown.addOption('default', 'Default (English, Neutral)');
        this.plugin.settings.voices.forEach(voice => {
          dropdown.addOption(voice.id, `${voice.name}`);
        });
        dropdown
          .setValue(this.plugin.settings.tts.defaultVoice)
          .onChange(async (value) => {
            this.plugin.settings.tts.defaultVoice = value;
            await this.plugin.saveSettings();
          });
      });

    // Speed slider
    new Setting(containerEl)
      .setName('Speech Speed')
      .setDesc('0.5x (slow) to 2.0x (fast)')
      .addSlider(slider => slider
        .setLimits(0.5, 2.0, 0.1)
        .setValue(this.plugin.settings.tts.speed)
        .onChange(async (value) => {
          this.plugin.settings.tts.speed = value;
          await this.plugin.saveSettings();
        })
        .setDynamicTooltip()
      );

    // STT Section
    containerEl.createEl('h3', { text: 'Speech-to-Text' });
    // ... similar patterns for STT settings

    // Voice Management Section
    containerEl.createEl('h3', { text: 'Voice Management' });
    const voiceCount = this.plugin.settings.voices.length;
    new Setting(containerEl)
      .setName('Registered Voices')
      .setDesc(`${voiceCount} custom voices saved`)
      .addButton(btn => btn
        .setButtonText('View / Manage')
        .onClick(() => this.showVoiceManager())
      );

    // API Configuration Section
    containerEl.createEl('h3', { text: 'API Configuration' });
    new Setting(containerEl)
      .setName('MCP Server URL')
      .setDesc('Default: http://localhost:8000')
      .addText(text => text
        .setPlaceholder('http://localhost:8000')
        .setValue(this.plugin.settings.api.serverUrl)
        .onChange(async (value) => {
          this.plugin.settings.api.serverUrl = value;
          await this.plugin.saveSettings();
        })
      );

    new Setting(containerEl)
      .setName('Test Connection')
      .setDesc('Verify MCP server is reachable')
      .addButton(btn => btn
        .setButtonText('Test')
        .onClick(async () => {
          const result = await this.plugin.mcpClient.healthCheck();
          if (result.status === 'ok') {
            new Notice('✓ MCP server is online');
          } else {
            new Notice('✗ Could not connect to MCP server', 5000);
          }
        })
      );

    // Cache Section
    containerEl.createEl('h3', { text: 'Cache Settings' });
    const cacheUsage = await this.plugin.cache.getUsageMB();
    new Setting(containerEl)
      .setName(`Cache Usage: ${cacheUsage.used}MB / ${cacheUsage.max}MB`)
      .setDesc(`${Math.round((cacheUsage.used / cacheUsage.max) * 100)}% full`)
      .addButton(btn => btn
        .setButtonText('Clear Cache')
        .onClick(async () => {
          if (await showConfirmDialog('Clear all cached results?')) {
            await this.plugin.cache.clear();
            new Notice('Cache cleared');
          }
        })
      );

    // Experimental Features (show only if tier = advanced)
    if (this.plugin.settings.defaultTier === 'advanced') {
      containerEl.createEl('h3', { text: 'Experimental Features' });
      new Setting(containerEl)
        .setName('Enable Moshi Conversation')
        .setDesc('Full-duplex voice conversation (requires GPU)')
        .addToggle(toggle => toggle
          .setValue(this.plugin.settings.experimental.enableMoshi)
          .onChange(async (value) => {
            this.plugin.settings.experimental.enableMoshi = value;
            await this.plugin.saveSettings();
          })
        );
    }
  }

  private async showVoiceManager() {
    new VoiceManagerModal(this.plugin.app, this.plugin).open();
  }
}
```

---

## Workflows & User Journeys

### Workflow 1: Read Note Aloud (Simplest Path)

**Actors**: User, Obsidian plugin, MCP server, Pocket TTS model
**Duration**: ~3 seconds (cold start) + 2-5 seconds (generation)

**Steps**:

```
1. User opens note in Obsidian
2. User clicks Ribbon: "Read Note Aloud" button
   ↓
3. Plugin extracts markdown text (non-code blocks)
4. Plugin opens Voice Selection Modal
   ↓
5. User selects voice (default on first use)
6. User clicks "Continue"
   ↓
7. Plugin calls MCP: tts_generate({text, voice, model})
8. Status bar shows: "Generating audio... (Pocket TTS)"
   ↓
9. MCP server loads Pocket TTS model (if not cached)
10. Model generates audio stream → saves to file
11. MCP returns: { audio_path, duration, word_count }
    ↓
12. Plugin opens Result Display Modal
13. Audio player embedded with playback controls
   ↓
14. User can:
    - Play audio in modal
    - Download audio file
    - Insert audio link into note
    - Close dialog
```

**Error Paths**:

- **No MCP server**: Modal shows "Cannot connect to MCP server"
  - Actions: "Start Server" (docs link), "Use Offline Mode"
- **GPU memory exceeded**: "Pocket TTS not loaded - CPU overloaded"
  - Actions: "Clear cache", "Reduce text length", "Wait and retry"
- **File write failed**: "Could not save audio file"
  - Actions: "Check vault permissions", "Change cache location"

**Timing**:

| Step | Duration |
|------|----------|
| Modal open | 50ms |
| Extract text | 20ms |
| MCP call | 100-500ms (network) |
| Model load (cold) | 1-3s |
| Model load (cached) | 100ms |
| Audio generation | 1-5s (depends on text length) |
| Save to file | 100-500ms |
| Modal display | 50ms |
| **Total (cold start)** | ~4-9s |
| **Total (cached)** | ~2-3s |

---

### Workflow 2: Transcribe Audio Recording

**Actors**: User, Obsidian, Web Audio API, MCP server, STT model
**Duration**: ~30 seconds (for 60-second audio)

**Steps**:

```
1. User clicks Ribbon: "Transcribe Audio" button
   ↓
2. Plugin opens Audio Input Dialog
3. User selects: "Record from Microphone"
4. Browser requests microphone permission
5. User grants permission
   ↓
6. Recording interface opens (inline in modal)
   - "Record" button, timer, waveform visualizer
7. User records audio (5 seconds to 5 minutes)
8. User clicks "Stop Recording"
   ↓
9. Plugin displays: "Processing... [████░░░░]"
10. Audio sent to MCP: stt_transcribe({audio, model, language})
11. MCP loads STT model (1B-en_fr recommended)
12. Model processes audio → returns JSON
    { text, segments, language, confidence }
    ↓
13. Plugin opens Result Display Modal
14. Shows transcript + word-level timestamps
15. User can edit transcript in modal
    ↓
16. User clicks "Insert into Note"
17. Transcript inserted as timestamped code block:
    ```
    [Transcription: 2026-02-09 14:23:45]
    The quick brown fox jumps...
    [Confidence: 95%] [Duration: 1:23]
    ```
```

**Alternative: Upload Audio File**

```
1. User selects "Upload Audio File"
2. File picker opens (filters: MP3, WAV, FLAC, OGG, M4A)
3. User selects file
4. Plugin validates file size (<500MB default)
5. Proceed to step 10 above
```

---

### Workflow 3: Clone Voice

**Actors**: User, Obsidian, Web Audio API, MCP server, Pocket TTS
**Duration**: ~30 seconds (record) + 5 seconds (register)

**Steps**:

```
1. User clicks Ribbon: "Clone Voice" button
   ↓
2. Plugin opens Voice Input Modal
3. User chooses: "Record voice sample"
4. Microphone permission requested + granted
5. User records 5-30 second sample (e.g., "Hello, my name is...")
6. User clicks "Stop"
   ↓
7. Modal shows: "Processing voice sample..."
8. Plugin generates UUID: voice_12345abc
9. Saves audio to vault: .obsidian/plugins/kyutai/voices/voice_12345abc.wav
   ↓
10. Plugin registers in settings:
    {
      id: "voice_12345abc",
      name: "Cloned Voice #1",
      type: "cloned",
      referencePath: ".obsidian/plugins/kyutai/voices/...",
      createdAt: 1707500625000
    }
    ↓
11. Plugin calls MCP: voice_preview({voice_id, text})
12. MCP uses voice sample with Pocket TTS to generate preview
13. Returns: { audio_path, duration }
    ↓
14. Plugin opens Result Modal with preview audio
15. User hears: "This is a preview of your cloned voice"
    (spoken in cloned voice)
    ↓
16. User clicks "Save" → voice registered
17. Voice now available in "Read Note Aloud" voice dropdown
```

---

### Workflow 4: Translate Speech (Intermediate)

**Actors**: User, Obsidian, Web Audio API, MCP server, Hibiki model
**Duration**: ~45 seconds
**Requirements**: GPU (Hibiki needs VRAM)

**Steps**:

```
1. User clicks Ribbon: "Translate Speech" button
   ↓
2. Plugin checks GPU availability
   - If no GPU: Modal shows "Feature requires GPU"
   - Offer: "See available features" → Settings
   - Exit
   ↓
3. Plugin opens Translation Modal
4. Source language: [French ▼]
5. Target language: [English ▼] (auto-set)
6. Audio input: Record or Upload
   ↓
7. User records French audio (or uploads)
8. User clicks "Translate"
   ↓
9. Status: "Loading Hibiki model..." → "Translating..."
10. MCP call: translate_speech({
      audio, source_lang: 'fr', target_lang: 'en', model: 'hibiki-2b'
    })
11. Hibiki processes:
    - Transcribes French speech
    - Translates to English
    - Synthesizes English speech (with voice transfer option)
12. Returns: {
      source_text: "Bonjour...",
      target_text: "Hello...",
      source_audio: "...",
      target_audio: "...",
      language_detected: "fr"
    }
    ↓
13. Plugin opens Result Modal (bilingual layout)
    - Left column: French text (clickable to play)
    - Right column: English text (clickable to play)
    - Timeline sync: clicking word highlights both translations
    ↓
14. User can:
    - Play source/target audio
    - Copy translations to clipboard
    - Insert bilingual result into note
    - Export as side-by-side markdown table
```

---

### Workflow 5: Converse with AI (Advanced, GPU Required)

**Actors**: User, Obsidian, Web Audio API, MCP server, Moshi model, LLM
**Duration**: Ongoing session (can last hours)
**Requirements**: GPU with 24GB+ VRAM

**Steps**:

```
1. User clicks Ribbon: "Converse with AI" button
   ↓
2. Plugin checks GPU availability (Moshi requires L4+)
   - If no GPU: Same as Translate workflow
   - Exit
   ↓
3. Plugin opens full-screen Moshi Conversation Modal
   ```
   ┌─────────────────────────────────────┐
   │ Voice Assistant Conversation   [×]  │
   ├─────────────────────────────────────┤
   │                                     │
   │ [Conversation history scrollable]   │
   │ > User: "What is the capital..." ▶  │
   │ < AI: "The capital of France..." ◀  │
   │ > User: "Tell me more" ▶            │
   │ < AI: [audio playing...] ◀          │
   │                                     │
   ├─────────────────────────────────────┤
   │ [● Record] or [Type message...]    │
   │ [Settings] [History] [Export] [OK] │
   │                                     │
   └─────────────────────────────────────┘
   ```
4. MCP server establishes WebSocket to Moshi
   ↓
5. User clicks "Record" button
6. Browser records user speech
7. User speaks: "What time is it?"
8. User stops recording (or auto-detects silence)
   ↓
9. Audio sent via WebSocket to Moshi
10. Moshi processes:
    - Audio → Text (STT component)
    - Text → LLM response + speech tokens
    - Tokens → Audio (TTS component)
11. Moshi streams response audio back to plugin
12. Plugin plays audio in real-time (uses Web Audio API)
    ↓
13. Conversation visible in history:
    > "What time is it?"
    < "It is 2:45 PM on February 9th, 2026."
    [with play buttons for audio]
    ↓
14. User can:
    - Continue conversation (loop back to step 5)
    - Interrupt AI (stop audio + send new input)
    - Save conversation to vault note
    - Export as markdown + audio attachments
    - Close modal
```

---

## Plugin Integration Points

### Obsidian API Hooks Used

```typescript
// 1. Ribbon Icon Command Registration
app.registerDomEvent(document, 'click', handler);
// Alt: registerCommand() for keyboard shortcuts

// 2. Modal Windows
import { Modal, App } from 'obsidian';
class MyModal extends Modal {
  async onOpen() { /* render UI */ }
}

// 3. Settings Tab
import { PluginSettingTab } from 'obsidian';
class KyutaiSettingsTab extends PluginSettingTab {
  display() { /* render settings */ }
}

// 4. File I/O
const file = app.vault.getAbstractFileByPath('path/to/file');
await app.vault.create(path, data);
await app.vault.modify(file, newContent);

// 5. Workspace Events
app.workspace.on('active-leaf-change', (leaf) => {
  // Update UI when user switches notes
});

// 6. Editor Integration
const editor = app.workspace.activeEditor?.editor;
const text = editor?.getSelection();
editor?.replaceSelection(newText);

// 7. Status Bar
const statusBar = app.statusBar.containerEl;
const el = statusBar.createEl('span', { text: 'Kyutai: Ready' });

// 8. Notices & Modals
import { Notice, ConfirmationModal } from 'obsidian';
new Notice('Processing...', 0); // 0 = indefinite duration
await showConfirmation('Are you sure?');
```

### MCP Client Communication

```typescript
// Initialize MCP client
class MCPClient {
  private serverUrl: string = 'http://localhost:8000';
  private ws: WebSocket | null = null;

  // HTTP-based calls (REST API)
  async call(tool: string, params: object) {
    const response = await fetch(
      `${this.serverUrl}/mcp/call`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tool, params })
      }
    );
    return response.json();
  }

  // WebSocket-based calls (streaming, for Moshi)
  async connectWebSocket() {
    this.ws = new WebSocket(`ws://${this.serverUrl.replace('http://', '')}/stream`);
    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleStreamMessage(message);
    };
  }

  async sendStreamMessage(data: object) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }
}

// Example usage in plugin
async function readNoteAloud(text: string, voice: string) {
  try {
    const result = await mcpClient.call('tts_generate', {
      text,
      voice,
      model: settings.ttsModel
    });

    // result.audio_path points to generated audio
    const audioPath = result.audio_path;
    showResultModal(audioPath);
  } catch (error) {
    showErrorModal('TTS Generation Failed', error.message);
  }
}
```

### Audio File Handling

```typescript
// Record audio using Web Audio API
class AudioRecorder {
  private mediaRecorder: MediaRecorder | null = null;
  private chunks: Blob[] = [];

  async startRecording() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    this.mediaRecorder = new MediaRecorder(stream);
    this.mediaRecorder.ondataavailable = (event) => {
      this.chunks.push(event.data);
    };
    this.mediaRecorder.start();
  }

  async stopRecording(): Promise<Blob> {
    return new Promise((resolve) => {
      this.mediaRecorder!.onstop = () => {
        const blob = new Blob(this.chunks, { type: 'audio/wav' });
        resolve(blob);
      };
      this.mediaRecorder!.stop();
    });
  }
}

// Save audio to vault
async function saveAudioToVault(audioBlob: Blob, filename: string) {
  const arrayBuffer = await audioBlob.arrayBuffer();
  const vault = app.vault;
  const vaultPath = `.obsidian/plugins/kyutai/audio/${filename}`;

  // Note: Obsidian vault API works with text, use binary encoding for audio
  const base64 = btoa(String.fromCharCode(...new Uint8Array(arrayBuffer)));
  await vault.create(vaultPath, base64);

  return vaultPath;
}

// Play audio
function playAudio(audioPath: string) {
  const audio = new Audio(audioPath);
  audio.play();

  // Or embed in modal
  const audioEl = document.createElement('audio');
  audioEl.src = audioPath;
  audioEl.controls = true;
  container.appendChild(audioEl);
}
```

---

## UI State Management

### Plugin-Level State

```typescript
interface PluginState {
  // Session state
  isLoading: boolean;
  currentModal: Modal | null;
  activeTask: {
    type: 'tts' | 'stt' | 'translate' | 'clone' | null;
    startTime: number;
    progress: number; // 0-100
  };

  // User preferences
  lastUsedVoice: string;
  lastUsedModel: {
    tts: string;
    stt: string;
  };

  // Connection state
  mcpConnected: boolean;
  gpuAvailable: boolean;
  modelsLoaded: string[]; // ['pocket-tts', 'stt-1b-en_fr']

  // Notification state
  notifications: Array<{
    id: string;
    type: 'info' | 'warning' | 'error';
    message: string;
    duration: number;
  }>;
}

// Redux-like state management in plugin
class KyutaiPlugin extends Plugin {
  private state: PluginState = {
    isLoading: false,
    currentModal: null,
    activeTask: { type: null, startTime: 0, progress: 0 },
    lastUsedVoice: 'default',
    lastUsedModel: { tts: 'pocket-tts', stt: 'stt-1b-en_fr' },
    mcpConnected: false,
    gpuAvailable: false,
    modelsLoaded: [],
    notifications: []
  };

  setState(updates: Partial<PluginState>) {
    this.state = { ...this.state, ...updates };
    this.updateUI(); // Trigger re-render
  }

  async startTask(type: string, handler: () => Promise<any>) {
    this.setState({ isLoading: true, activeTask: { type: any, startTime: Date.now(), progress: 0 } });
    try {
      return await handler();
    } finally {
      this.setState({ isLoading: false });
    }
  }
}
```

### Component-Level State (Modal Example)

```typescript
class ResultDisplayModal extends Modal {
  // Component state
  private isPlaying: boolean = false;
  private currentTime: number = 0;
  private duration: number = 0;
  private audioElement: HTMLAudioElement | null = null;
  private editMode: boolean = false;
  private editedText: string = '';

  // Lifecycle
  async onOpen() {
    this.setState({ isPlaying: false, currentTime: 0, editMode: false });
    this.render();
  }

  // State updates
  private updatePlaybackState(time: number) {
    this.currentTime = time;
    this.renderProgressBar();
  }

  private toggleEditMode() {
    this.editMode = !this.editMode;
    this.editedText = this.editedText || this.originalText;
    this.render();
  }

  // Render based on state
  private render() {
    const { contentEl } = this;
    contentEl.empty();

    if (this.editMode) {
      this.renderEditingUI();
    } else {
      this.renderViewingUI();
    }
  }
}
```

### Cache Management

```typescript
interface CacheEntry {
  key: string; // hash of input params
  type: 'audio' | 'text' | 'voice';
  value: string; // file path or text content
  createdAt: number;
  accessedAt: number;
  metadata: Record<string, any>;
}

class ResultCache {
  private cache: Map<string, CacheEntry> = new Map();
  private maxSizeMB: number = 500;
  private retentionDays: number = 30;

  set(key: string, entry: CacheEntry) {
    this.cache.set(key, entry);
    this.checkCapacity();
  }

  get(key: string): CacheEntry | null {
    const entry = this.cache.get(key);
    if (entry) {
      entry.accessedAt = Date.now();
    }
    return entry || null;
  }

  private checkCapacity() {
    // If cache exceeds size, delete oldest entries
    // If entry older than retentionDays, delete
  }
}
```

---

## Accessibility & Theming

### Keyboard Shortcuts

| Action | Windows/Linux | macOS | Category |
|--------|---------------|-------|----------|
| Read Note Aloud | `Ctrl+Shift+P` | `Cmd+Shift+P` | Primary |
| Transcribe Audio | `Ctrl+Shift+T` | `Cmd+Shift+T` | Primary |
| Clone Voice | `Ctrl+Shift+V` | `Cmd+Shift+V` | Primary |
| Translate Speech | `Ctrl+Shift+L` | `Cmd+Shift+L` | Secondary |
| Open Settings | `Ctrl+Shift+,` | `Cmd+Shift+,` | Settings |
| Play/Pause Audio | `Space` (in modal) | `Space` | Playback |
| Increase Speed | `Ctrl+]` | `Cmd+]` | Playback |
| Decrease Speed | `Ctrl+[` | `Cmd+[` | Playback |
| Close Modal | `Esc` | `Esc` | Navigation |
| Accept/Submit | `Enter` | `Enter` | Navigation |

**Implementation:**

```typescript
app.scope.register(['Ctrl', 'Shift'], 'p', async () => {
  await executeReadNoteAloud();
});

// In modals, register within modal scope
modal.scope.register([], 'Escape', () => modal.close());
modal.scope.register([], 'Enter', () => modal.confirm());
```

### ARIA Labels & Screen Reader Support

```typescript
class AudioPlayerModal extends Modal {
  private renderAudioPlayer(audioPath: string) {
    const playerContainer = this.contentEl.createDiv({ cls: 'audio-player' });

    // Audio element (hidden from visual display)
    const audio = playerContainer.createEl('audio', {
      attr: { 'aria-label': 'Audio playback control' }
    });
    audio.src = audioPath;

    // Play button
    const playBtn = playerContainer.createEl('button', { text: '▶ Play' });
    playBtn.setAttribute('aria-label', 'Play audio');
    playBtn.setAttribute('aria-pressed', 'false');
    playBtn.addEventListener('click', () => {
      audio.play();
      playBtn.setAttribute('aria-pressed', 'true');
    });

    // Progress bar
    const progressBar = playerContainer.createEl('input', {
      attr: {
        type: 'range',
        min: '0',
        max: '100',
        value: '0',
        'aria-label': 'Audio progress',
        'aria-valuenow': '0',
        'aria-valuemin': '0',
        'aria-valuemax': '100'
      }
    });

    // Time display
    const timeDisplay = playerContainer.createEl('span', {
      attr: { 'aria-live': 'polite', 'aria-atomic': 'true' }
    });

    audio.addEventListener('timeupdate', () => {
      const progress = (audio.currentTime / audio.duration) * 100;
      progressBar.value = String(progress);
      progressBar.setAttribute('aria-valuenow', String(Math.round(progress)));
      timeDisplay.setText(`${formatTime(audio.currentTime)} / ${formatTime(audio.duration)}`);
    });
  }
}
```

### Theme Support (Light / Dark)

```typescript
// In CSS variables (based on Obsidian's theme)
:root {
  --kyutai-bg-primary: var(--background-primary);
  --kyutai-bg-secondary: var(--background-secondary);
  --kyutai-text-normal: var(--text-normal);
  --kyutai-text-muted: var(--text-muted);
  --kyutai-interactive-accent: var(--interactive-accent);
  --kyutai-interactive-accent-hover: var(--interactive-accent-hover);
}

.kyutai-modal {
  background-color: var(--kyutai-bg-primary);
  color: var(--kyutai-text-normal);
}

.kyutai-button {
  background-color: var(--kyutai-interactive-accent);
  color: white;
}

.kyutai-button:hover {
  background-color: var(--kyutai-interactive-accent-hover);
}

/* High contrast mode */
.kyutai-high-contrast {
  --kyutai-text-normal: #000000;
  --kyutai-bg-primary: #ffffff;
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .kyutai-modal {
    animation: none;
    transition: none;
  }
}

/* Large text mode */
.kyutai-large-text {
  font-size: 18px;
  line-height: 1.6;
}
```

### Accessibility Checklist

- [x] All interactive elements keyboard accessible
- [x] Focus indicators visible (2px outline)
- [x] Color contrast ≥ 4.5:1 (WCAG AA)
- [x] ARIA labels on all inputs
- [x] Screen reader announcement for async updates
- [x] Escape key closes modals
- [x] Alt text for all icons (via title attribute)
- [x] Form validation errors announced to screen readers
- [x] No auto-playing audio
- [x] Captions/transcripts available for audio output
- [x] Touch-friendly button sizes (≥ 44x44px)
- [x] Support for system dark mode
- [x] Support for reduced-motion preference
- [x] Support for high-contrast mode

---

## Implementation Roadmap

### Phase 1: MVP (4-6 weeks)

**Goal**: Core TTS + STT functionality, CPU-based
**Team**: 2-3 developers

**Deliverables**:

1. **Plugin Shell**
   - Ribbon buttons (5 commands: TTS, STT, Clone, Settings, Help)
   - Settings tab with basic configuration
   - Modal framework (AudioInputModal, ResultDisplayModal)

2. **TTS Integration**
   - Pocket TTS via local API
   - Voice selection modal
   - Audio player in result modal
   - Insert audio link into note

3. **STT Integration**
   - OpenAI-compatible STT API (via MCP)
   - Audio file upload + recording
   - Result display with optional editing
   - Insert transcript into note

4. **Voice Cloning**
   - Record voice sample
   - Register as custom voice
   - Use in TTS workflows

5. **Settings & State**
   - Model selection (TTS, STT)
   - Default voice configuration
   - Cache management
   - API endpoint configuration

6. **Error Handling**
   - Connection errors (MCP server unavailable)
   - File I/O errors
   - Model load failures
   - User-friendly error modals

**Testing**:
- Manual testing on macOS, Windows, Linux
- Accessibility testing (keyboard nav, screen reader)
- Performance testing (cold vs warm cache)

**Timeline**:
- Week 1-2: Plugin shell + UI framework
- Week 2-3: TTS + STT integration
- Week 3-4: Voice cloning + caching
- Week 4-5: Settings + state management
- Week 5-6: Testing + polish

---

### Phase 2: Enhancement (3-4 weeks)

**Goal**: Voice translation, GPU support detection, advanced settings
**Requires**: Phase 1 complete

**Deliverables**:

1. **Speech Translation**
   - Hibiki model integration
   - Bilingual result modal
   - Audio sync between translations
   - Export as markdown table

2. **GPU Detection**
   - Hardware detection service
   - Auto-configure models based on GPU
   - Feature tier system (basic → enhanced → advanced)
   - Graceful degradation if GPU unavailable

3. **Advanced Settings**
   - Batch processing (transcribe multiple files)
   - Model parameters (speed, pitch, quality sliders)
   - API timeout + retry configuration
   - Advanced caching options

4. **Batch Operations**
   - Transcribe directory of audio files
   - Apply voice clone to multiple notes
   - Export conversation history

5. **Performance Optimization**
   - Model caching (keep loaded models in memory)
   - Lazy loading (load models on-demand)
   - Cache invalidation strategy
   - Concurrent operation limits

**Timeline**:
- Week 1-2: Hibiki translation + bilingual UI
- Week 2: GPU detection + feature tiers
- Week 3: Advanced settings + batch operations
- Week 3-4: Performance optimization + testing

---

### Phase 3: Advanced (4-6 weeks)

**Goal**: Full-duplex Moshi conversation, streaming, advanced workflows
**Requires**: Phase 1 + 2 complete

**Deliverables**:

1. **Moshi Conversation**
   - WebSocket streaming integration
   - Real-time audio playback
   - Conversation history
   - Export as note + audio attachments

2. **Streaming Support**
   - Chunked audio processing (for long files)
   - Progressive result display (incremental STT output)
   - Streaming TTS (play audio while generating)

3. **Advanced Workflows**
   - Interview mode (record + transcribe + summarize)
   - Meeting transcription (multi-speaker detection)
   - Podcast notes (auto-segment + summarize chapters)
   - Voice journal (daily voice notes)

4. **Integration with Obsidian Plugins**
   - Dataview queries on transcriptions
   - Smart linking (extract entities from transcripts)
   - Search across audio (index transcripts)
   - Sync with existing plugins (Templater, etc.)

5. **Mobile Support (Optional)**
   - Mobile-responsive UI
   - iOS voice control (via mobile app)
   - Battery-efficient streaming

**Timeline**:
- Week 1-2: WebSocket client + Moshi integration
- Week 2-3: Streaming + progressive display
- Week 3-4: Conversation history + export
- Week 4-5: Advanced workflows
- Week 5-6: Integration + polish

---

## Component Hierarchy Diagram

```
KyutaiPlugin (Root)
├── RibbonCommandManager
│   ├── ReadAloudCommand
│   ├── TranscribeCommand
│   ├── CloneVoiceCommand
│   ├── TranslateCommand
│   ├── ConverseCommand
│   ├── SettingsCommand
│   ├── StatusCommand
│   └── HelpCommand
│
├── ModalManager
│   ├── AudioInputModal
│   │   ├── FilePickerSection
│   │   ├── RecordingSection
│   │   └── PreviewSection
│   │
│   ├── ResultDisplayModal
│   │   ├── AudioPlayerComponent
│   │   ├── TextDisplayComponent
│   │   ├── BilingualComponent
│   │   └── ActionButtonsComponent
│   │
│   ├── VoiceSelectionModal
│   │   ├── BuiltinVoicesList
│   │   ├── ClonedVoicesList
│   │   ├── VoicePreviewPlayer
│   │   └── CloneNewVoiceButton
│   │
│   ├── ConfigurationModal
│   │   ├── TtsSettingsSection
│   │   ├── SttSettingsSection
│   │   ├── ApiSettingsSection
│   │   └── CacheSettingsSection
│   │
│   ├── ErrorModal
│   └── StatusModal
│
├── SettingsTab
│   ├── GeneralSection
│   ├── TtsSection
│   ├── SttSection
│   ├── VoiceManagementSection
│   ├── ApiConfigurationSection
│   ├── CacheSection
│   ├── UiBehaviorSection
│   ├── AccessibilitySection
│   └── ExperimentalSection
│
├── StatusBar
│   ├── StatusIndicator
│   ├── ProgressBar
│   └── NotificationCenter
│
├── Services (Singleton)
│   ├── MCPClient
│   │   ├── HttpClient
│   │   └── WebSocketClient
│   │
│   ├── AudioProcessor
│   │   ├── Recorder
│   │   ├── Player
│   │   └── FileHandler
│   │
│   ├── VoiceManager
│   │   ├── VoiceRegistry
│   │   └── VoicePreviewGenerator
│   │
│   ├── HardwareDetector
│   │   ├── GpuDetector
│   │   ├── RamDetector
│   │   └── PlatformDetector
│   │
│   └── ResultCache
│       ├── MemoryCache
│       └── FileSystemCache
│
└── Types & Constants
    ├── Models (TypeScript interfaces)
    ├── API Contracts
    └── Enums & Constants
```

---

## Event Flow Diagrams

### Event Flow: Read Note Aloud

```
┌─────────────────────────────────────────────────────────────┐
│ User clicks "Read Note Aloud" button                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ readAloudCommand.execute()                                  │
│  - Extract markdown from active editor                      │
│  - Validate text (not empty, < max length)                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ VoiceSelectionModal.open()                                 │
│  - Load registered voices from settings                     │
│  - Display voice list (built-in + cloned)                  │
│  - User selects voice                                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ mcpClient.call('tts_generate', {text, voice, model})       │
│  - HTTP POST to MCP server                                 │
│  - Handle response: { audio_path, duration, metadata }     │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │ Success                 │ Error
        ▼                         ▼
  ┌──────────────┐    ┌──────────────────┐
  │ Cache result │    │ ErrorModal.show  │
  │ Show audio   │    │ - Retry button   │
  │ player modal │    │ - Settings link  │
  └──────────────┘    └──────────────────┘
        │                     │
        ▼                     ▼
  ┌────────────────────┐  [User dismisses]
  │ User can:          │
  │ - Play audio       │
  │ - Download        │
  │ - Insert into note│
  └────────────────────┘
```

### Event Flow: Transcribe Audio

```
┌─────────────────────────────────────────────────────────────┐
│ User clicks "Transcribe Audio" button                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ AudioInputModal.open()                                      │
│  - Show: Choose input method (file/record)                 │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │ File                    │ Record
        ▼                         ▼
  ┌──────────────┐    ┌──────────────────┐
  │ File picker  │    │ Microphone dialog│
  │ Validate size│    │ Record audio     │
  │ Select audio │    │ Stop recording   │
  └──────────────┘    └──────────────────┘
        │                     │
        └────────────┬────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Show progress: "Processing audio..." [████░░░░]             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ mcpClient.call('stt_transcribe', {audio, model, lang})     │
│  - MCP server loads STT model                              │
│  - Process audio stream                                    │
│  - Return { text, segments, language, confidence }        │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │ Success                 │ Error
        ▼                         ▼
  ┌──────────────────┐    ┌──────────────────┐
  │ Show transcript  │    │ ErrorModal.show  │
  │ in result modal  │    │ Retry / Cancel   │
  │ User can edit    │    └──────────────────┘
  │ before insert    │
  └──────────────────┘
        │
        ▼
  ┌──────────────────┐
  │ User clicks      │
  │ "Insert into     │
  │ note"            │
  └──────────────────┘
        │
        ▼
  ┌──────────────────────────────────────┐
  │ Insert formatted transcript:         │
  │ ```                                  │
  │ [Transcription: 2026-02-09 14:23]    │
  │ The quick brown fox...               │
  │ [Confidence: 95%]                    │
  │ ```                                  │
  └──────────────────────────────────────┘
```

---

## Accessibility Checklist

### Visual Design
- [ ] Color contrast meets WCAG AA (4.5:1 for text)
- [ ] Color not sole method of conveying information
- [ ] Focus indicators clearly visible (2px minimum)
- [ ] All buttons ≥44x44px (touch-friendly)
- [ ] Text size ≥12px, line-height ≥1.5
- [ ] Icon buttons have text labels

### Keyboard Navigation
- [ ] All functionality accessible via keyboard
- [ ] Logical tab order (top-left to bottom-right)
- [ ] No keyboard traps (user can tab out)
- [ ] Modal: Escape closes, focus returns to opener
- [ ] Modals: Focus trapped within modal
- [ ] Skip links: Skip to main content button

### Screen Reader Support
- [ ] All interactive elements have descriptive labels
- [ ] Form fields have associated labels
- [ ] Audio players have labels (e.g., "Audio playback")
- [ ] Async updates announced via `aria-live`
- [ ] Form errors announced immediately
- [ ] Headings properly nested (h1 → h2 → h3)
- [ ] List structure preserved in markup

### Audio Accessibility
- [ ] Transcripts available for all audio content
- [ ] Option to disable autoplay
- [ ] Audio controls easily accessible
- [ ] Captions for video (if applicable)

### Mobile Accessibility
- [ ] Touch targets ≥44x44px
- [ ] No horizontal scroll required
- [ ] Pinch zoom functional
- [ ] Mobile keyboard doesn't obscure critical content

### Sensory-Independent
- [ ] Instructions don't rely on color alone
- [ ] Instructions don't rely on sound alone
- [ ] Blinking/animation can be disabled (prefers-reduced-motion)

### Testing
- [ ] WAVE accessibility checker (zero errors)
- [ ] Axe DevTools scan (zero violations)
- [ ] NVDA (Windows), JAWS, or VoiceOver testing
- [ ] Keyboard-only navigation testing
- [ ] Mobile VoiceOver testing (iOS)

---

## Conclusion

This architecture provides a comprehensive design for integrating Kyutai's voice AI models into Obsidian. The phased approach allows for MVP launch with core TTS/STT features, then expansion to advanced capabilities (translation, conversation) as the infrastructure matures.

**Key Strengths:**
- **Modular design**: Easy to add/remove features per tier
- **Privacy-first**: All processing local, no cloud dependency
- **Accessible**: WCAG AA compliant, keyboard navigable
- **User-friendly**: Clear workflows, helpful error messages
- **Extensible**: MCP server pattern allows adding models without plugin changes

**Next Steps:**
1. Assign 2-3 engineers to Phase 1 (4-6 weeks)
2. Set up MCP server development (parallel work)
3. Create component library (buttons, modals, etc.)
4. Establish testing framework (unit + e2e)
5. Design plugin icon + branding
6. Prepare Obsidian marketplace submission criteria

---

**Document Version:** 1.0
**Status:** READY FOR IMPLEMENTATION
**Last Updated:** 2026-02-09

## Related

- [[kyutai-api-specification|Kyutai API Specification]] — the foundational API research; this plugin calls the models documented there via the MCP bridge
- [[kyutai-mcp-server-architecture|Kyutai MCP Server Architecture]] — the Python backend this TypeScript plugin communicates with over HTTP/WebSocket
- [[2026-02-10-kyutai-mcp-obsidian-plugin-plan|Kyutai MCP + Obsidian Plugin Plan]] — the compound engineering plan that produced this architecture document
- [[2026-02-10-kyutai-pocket-tts-token-efficient-success|Kyutai Pocket TTS: Token-Efficient Success]] — post-implementation validation of the Phase 1 TTS workflow described in Workflow 1 of this document
- [[cloud-vault-mcp|Cloud Vault MCP]] — the existing Obsidian MCP integration (port 8360) whose infrastructure patterns informed this plugin design
- [[kyutai-project]]
- [[mcp-model-context-protocol]]
- [[api-design]]
