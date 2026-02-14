/**
 * Mock MCP client for Obsidian plugin testing
 */

import { EventEmitter } from 'events';

export interface MCPToolCall {
  name: string;
  params: Record<string, any>;
}

export interface MCPResponse {
  status: 'success' | 'error';
  data?: any;
  error?: string;
}

export class MockMCPClient extends EventEmitter {
  private tools: Map<string, Function> = new Map();
  private callHistory: MCPToolCall[] = [];
  private connected: boolean = false;

  constructor(private options?: { autoConnect?: boolean }) {
    super();
    if (options?.autoConnect !== false) {
      this.connect();
    }
  }

  /**
   * Connect to mock MCP server
   */
  async connect(): Promise<void> {
    this.connected = true;
    this.emit('connected');
  }

  /**
   * Disconnect from mock MCP server
   */
  async disconnect(): Promise<void> {
    this.connected = false;
    this.emit('disconnected');
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.connected;
  }

  /**
   * Register a mock tool
   */
  registerTool(name: string, handler: Function): void {
    this.tools.set(name, handler);
  }

  /**
   * Call a registered tool
   */
  async callTool(name: string, params: Record<string, any>): Promise<MCPResponse> {
    this.callHistory.push({ name, params });

    const handler = this.tools.get(name);
    if (!handler) {
      return {
        status: 'error',
        error: `Tool '${name}' not found`
      };
    }

    try {
      const result = await handler(params);
      return {
        status: 'success',
        data: result
      };
    } catch (error) {
      return {
        status: 'error',
        error: error instanceof Error ? error.message : String(error)
      };
    }
  }

  /**
   * Get call history
   */
  getCallHistory(): MCPToolCall[] {
    return [...this.callHistory];
  }

  /**
   * Get calls to specific tool
   */
  getToolCalls(toolName: string): MCPToolCall[] {
    return this.callHistory.filter(call => call.name === toolName);
  }

  /**
   * Get call count
   */
  getCallCount(toolName?: string): number {
    if (!toolName) {
      return this.callHistory.length;
    }
    return this.callHistory.filter(call => call.name === toolName).length;
  }

  /**
   * Reset call history
   */
  resetCallHistory(): void {
    this.callHistory = [];
  }

  /**
   * Get last call
   */
  getLastCall(): MCPToolCall | undefined {
    return this.callHistory[this.callHistory.length - 1];
  }
}

/**
 * Mock TTS response
 */
export function createMockTTSResponse(overrides?: Partial<any>): any {
  return {
    status: 'success',
    audio_base64: 'data:audio/wav;base64,UklGRiYAAABXQVZFZm10IBAAAAABAAEAQB...',
    duration_ms: 1000,
    model_used: 'pocket-tts',
    latency_ms: 50,
    ...overrides
  };
}

/**
 * Mock STT response
 */
export function createMockSTTResponse(overrides?: Partial<any>): any {
  return {
    status: 'success',
    text: 'This is a mock transcription',
    segments: [
      {
        id: 0,
        start: 0,
        end: 1.5,
        text: 'This is a mock'
      },
      {
        id: 1,
        start: 1.5,
        end: 2.5,
        text: 'transcription'
      }
    ],
    language: 'en',
    model_used: 'stt-1b-en_fr',
    latency_ms: 120,
    ...overrides
  };
}

/**
 * Mock list_models response
 */
export function createMockListModelsResponse(overrides?: Partial<any>): any {
  return {
    status: 'success',
    models: [
      {
        id: 'pocket-tts',
        name: 'Pocket TTS',
        category: 'tts',
        parameters: 100000000,
        languages: ['en', 'fr']
      },
      {
        id: 'stt-1b-en_fr',
        name: 'STT 1B English/French',
        category: 'stt',
        parameters: 1000000000,
        languages: ['en', 'fr']
      }
    ],
    ...overrides
  };
}

/**
 * Mock health check response
 */
export function createMockHealthResponse(overrides?: Partial<any>): any {
  return {
    status: 'healthy',
    models: {
      'pocket-tts': 'ready',
      'stt-1b-en_fr': 'ready'
    },
    uptime_seconds: 3600,
    timestamp: new Date().toISOString(),
    ...overrides
  };
}

/**
 * Setup mock MCP client with default tools
 */
export function setupMockMCPClient(): MockMCPClient {
  const client = new MockMCPClient();

  client.registerTool('speak_text', async (params) => {
    return createMockTTSResponse({
      text: params.text,
      voice_id: params.voice_id || 'default'
    });
  });

  client.registerTool('transcribe_audio', async (params) => {
    return createMockSTTResponse({
      audio_path: params.audio_path
    });
  });

  client.registerTool('list_models', async (params) => {
    return createMockListModelsResponse();
  });

  client.registerTool('get_model_status', async (params) => {
    return {
      status: 'success',
      model_id: params.model_id,
      model_status: 'ready',
      memory_mb: 1024,
      last_used: new Date().toISOString()
    };
  });

  return client;
}
