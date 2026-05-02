/**
 * Type definitions for Kyutai Obsidian Plugin
 */

// Settings
export interface KyutaiPluginSettings {
  // General
  enabled: boolean;
  defaultTier: 'basic' | 'enhanced' | 'advanced';
  language: string;

  // TTS Settings
  tts: {
    model: 'pocket-tts' | 'tts-1.6b-en_fr';
    defaultVoice: string;
    speed: number;
    pitch: number;
    responseFormat: 'mp3' | 'wav' | 'flac';
  };

  // STT Settings
  stt: {
    model: 'stt-1b-en_fr' | 'stt-2.6b-en';
    language: string;
    includeTimestamps: boolean;
    autoCapitalize: boolean;
    confidenceThreshold: number;
    responseFormat: 'json' | 'text' | 'srt';
  };

  // Voice Management
  voices: Voice[];

  // API Configuration
  api: {
    serverUrl: string;
    useGpu: boolean;
    gpuModel: 'cuda' | 'metal' | 'auto';
    timeoutSeconds: number;
    retryAttempts: number;
    retryDelayMs: number;
  };

  // Cache Settings
  cache: {
    enabled: boolean;
    maxSizeMB: number;
    autoCleanup: boolean;
    retentionDays: number;
  };

  // UI Behavior
  ui: {
    showStatusBar: boolean;
    showProgressNotifications: boolean;
    insertResultsAsCodeBlocks: boolean;
    autoPlayResults: boolean;
    darkModeUI: boolean;
  };

  // Accessibility
  accessibility: {
    screenReaderMode: boolean;
    highContrast: boolean;
    largeText: boolean;
    reduceAnimations: boolean;
  };

  // Experimental
  experimental: {
    enableMoshi: boolean;
    enableHibiki: boolean;
    enableLocalLLaMA: boolean;
  };
}

// Voice Management
export interface Voice {
  id: string;
  name: string;
  type: 'builtin' | 'cloned';
  language?: string;
  gender?: 'male' | 'female' | 'neutral';
  referencePath?: string;
  createdAt: number;
}

// MCP API Responses
export interface TtsGenerateResponse {
  audio_path: string;
  duration: number;
  word_count: number;
  metadata?: Record<string, any>;
}

export interface SttTranscribeResponse {
  text: string;
  segments: TranscriptionSegment[];
  language: string;
  confidence: number;
  duration: number;
}

export interface TranscriptionSegment {
  id: number;
  seek: number;
  start: number;
  end: number;
  text: string;
  tokens: number[];
  temperature: number;
  avg_logprob: number;
  compression_ratio: number;
  no_speech_prob: number;
  words?: WordLevel[];
}

export interface WordLevel {
  word: string;
  start: number;
  end: number;
  confidence: number;
}

export interface VoicePreviewResponse {
  audio_path: string;
  duration: number;
}

export interface ModelStatusResponse {
  models: ModelInfo[];
  gpu_available: boolean;
  vram_usage_gb: number;
  timestamp: number;
}

export interface ModelInfo {
  name: string;
  status: 'loaded' | 'ready' | 'error';
  type: 'tts' | 'stt' | 'translation' | 'conversation';
  vram_used_mb: number;
}

// UI State
export interface PluginState {
  isLoading: boolean;
  currentModal: any; // Modal instance
  activeTask: {
    type: 'tts' | 'stt' | 'translate' | 'clone' | null;
    startTime: number;
    progress: number;
  };
  lastUsedVoice: string;
  lastUsedModel: {
    tts: string;
    stt: string;
  };
  mcpConnected: boolean;
  gpuAvailable: boolean;
  modelsLoaded: string[];
  notifications: Notification[];
}

export interface Notification {
  id: string;
  type: 'info' | 'warning' | 'error';
  message: string;
  duration: number;
}

// Cache
export interface CacheEntry {
  key: string;
  type: 'audio' | 'text' | 'voice';
  value: string;
  createdAt: number;
  accessedAt: number;
  metadata: Record<string, any>;
}

// Modal Props
export interface AudioInputModalProps {
  onConfirm: (audioPath: string) => void;
  onCancel: () => void;
  maxFileSizeMB?: number;
  allowRecording?: boolean;
  supportedFormats?: string[];
}

export type ResultType = 'audio' | 'text' | 'bilingual';

export interface AudioResult {
  audioPath: string;
  duration: number;
  voiceId: string;
  model: string;
}

export interface TextResult {
  text: string;
  language: string;
  confidence: number;
  segments: TranscriptionSegment[];
}

export interface BillingualResult {
  sourceText: string;
  targetText: string;
  sourceLanguage: string;
  targetLanguage: string;
  sourceAudio: string;
  targetAudio: string;
}

export interface ResultDisplayModalProps {
  resultType: ResultType;
  content: AudioResult | TextResult | BillingualResult;
  onInsert: (content: string) => void;
  onDownload: (path: string) => void;
}

// Error Handling
export interface ErrorModalProps {
  title: string;
  message: string;
  severity: 'info' | 'warning' | 'error' | 'fatal';
  details?: string;
  actions?: Array<{
    label: string;
    callback: () => void;
  }>;
}

// Default Settings
export const DEFAULT_SETTINGS: KyutaiPluginSettings = {
  enabled: true,
  defaultTier: 'basic',
  language: 'en',
  tts: {
    model: 'pocket-tts',
    defaultVoice: 'default',
    speed: 1.0,
    pitch: 100,
    responseFormat: 'mp3',
  },
  stt: {
    model: 'stt-1b-en_fr',
    language: 'en',
    includeTimestamps: true,
    autoCapitalize: true,
    confidenceThreshold: 0.7,
    responseFormat: 'json',
  },
  voices: [],
  api: {
    serverUrl: 'http://localhost:8000',
    useGpu: false,
    gpuModel: 'auto',
    timeoutSeconds: 30,
    retryAttempts: 3,
    retryDelayMs: 1000,
  },
  cache: {
    enabled: true,
    maxSizeMB: 500,
    autoCleanup: true,
    retentionDays: 30,
  },
  ui: {
    showStatusBar: true,
    showProgressNotifications: true,
    insertResultsAsCodeBlocks: true,
    autoPlayResults: false,
    darkModeUI: true,
  },
  accessibility: {
    screenReaderMode: false,
    highContrast: false,
    largeText: false,
    reduceAnimations: false,
  },
  experimental: {
    enableMoshi: false,
    enableHibiki: false,
    enableLocalLLaMA: false,
  },
};
