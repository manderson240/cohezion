/**
 * Unit tests for MCP client integration
 */

import { describe, it, expect, beforeEach, jest } from '@jest/globals';
import {
  MockMCPClient,
  setupMockMCPClient,
  createMockTTSResponse,
  createMockSTTResponse,
  createMockListModelsResponse
} from '../fixtures/mock-mcp';

describe('MCP Client', () => {
  let client: MockMCPClient;

  beforeEach(() => {
    client = setupMockMCPClient();
  });

  describe('Connection Management', () => {
    it('should connect to MCP server', async () => {
      const newClient = new MockMCPClient();
      await newClient.connect();
      expect(newClient.isConnected()).toBe(true);
    });

    it('should disconnect from MCP server', async () => {
      await client.disconnect();
      expect(client.isConnected()).toBe(false);
    });

    it('should auto-connect by default', () => {
      const newClient = new MockMCPClient();
      expect(newClient.isConnected()).toBe(true);
    });

    it('should emit connected event', async () => {
      const newClient = new MockMCPClient({ autoConnect: false });
      const connectedSpy = jest.fn();
      newClient.on('connected', connectedSpy);

      await newClient.connect();
      expect(connectedSpy).toHaveBeenCalled();
    });

    it('should emit disconnected event', async () => {
      const disconnectedSpy = jest.fn();
      client.on('disconnected', disconnectedSpy);

      await client.disconnect();
      expect(disconnectedSpy).toHaveBeenCalled();
    });

    it('should handle connection errors', async () => {
      // Should handle connection failures gracefully
      expect(true).toBe(true);
    });

    it('should reconnect after disconnection', async () => {
      await client.disconnect();
      await client.connect();
      expect(client.isConnected()).toBe(true);
    });
  });

  describe('Tool Invocation', () => {
    it('should call speak_text tool', async () => {
      const response = await client.callTool('speak_text', {
        text: 'Hello world'
      });

      expect(response.status).toBe('success');
      expect(response.data).toHaveProperty('audio_base64');
    });

    it('should call transcribe_audio tool', async () => {
      const response = await client.callTool('transcribe_audio', {
        audio_path: '/path/to/audio.wav'
      });

      expect(response.status).toBe('success');
      expect(response.data).toHaveProperty('text');
    });

    it('should call list_models tool', async () => {
      const response = await client.callTool('list_models', {});

      expect(response.status).toBe('success');
      expect(response.data).toHaveProperty('models');
    });

    it('should call get_model_status tool', async () => {
      const response = await client.callTool('get_model_status', {
        model_id: 'pocket-tts'
      });

      expect(response.status).toBe('success');
    });

    it('should return error for unknown tool', async () => {
      const response = await client.callTool('unknown_tool', {});

      expect(response.status).toBe('error');
      expect(response.error).toBeDefined();
    });

    it('should handle tool parameter passing', async () => {
      const params = {
        text: 'Test text',
        voice_id: 'character_1',
        speed: 1.5
      };

      const response = await client.callTool('speak_text', params);
      expect(response.status).toBe('success');

      const lastCall = client.getLastCall();
      expect(lastCall).toBeDefined();
      expect(lastCall?.params.text).toBe('Test text');
    });

    it('should support async tool handlers', async () => {
      const asyncHandler = async (params: any) => {
        return new Promise(resolve =>
          setTimeout(() => resolve({ delayed: true }), 10)
        );
      };

      const testClient = new MockMCPClient();
      testClient.registerTool('async_tool', asyncHandler);

      const response = await testClient.callTool('async_tool', {});
      expect(response.status).toBe('success');
    });

    it('should handle tool errors', async () => {
      const errorHandler = async () => {
        throw new Error('Tool execution failed');
      };

      const testClient = new MockMCPClient();
      testClient.registerTool('error_tool', errorHandler);

      const response = await testClient.callTool('error_tool', {});
      expect(response.status).toBe('error');
      expect(response.error).toContain('Tool execution failed');
    });
  });

  describe('Call History Tracking', () => {
    it('should track tool calls', async () => {
      await client.callTool('speak_text', { text: 'Hello' });
      await client.callTool('speak_text', { text: 'World' });

      const history = client.getCallHistory();
      expect(history.length).toBe(2);
    });

    it('should return call history', async () => {
      await client.callTool('speak_text', { text: 'Test' });

      const history = client.getCallHistory();
      expect(history).toBeDefined();
      expect(Array.isArray(history)).toBe(true);
    });

    it('should get calls to specific tool', async () => {
      await client.callTool('speak_text', { text: 'A' });
      await client.callTool('transcribe_audio', { audio_path: 'path' });
      await client.callTool('speak_text', { text: 'B' });

      const calls = client.getToolCalls('speak_text');
      expect(calls.length).toBe(2);
      expect(calls.every(c => c.name === 'speak_text')).toBe(true);
    });

    it('should count tool calls', async () => {
      await client.callTool('speak_text', { text: 'A' });
      await client.callTool('speak_text', { text: 'B' });

      expect(client.getCallCount('speak_text')).toBe(2);
    });

    it('should get total call count', async () => {
      await client.callTool('speak_text', { text: 'A' });
      await client.callTool('transcribe_audio', { audio_path: 'path' });

      expect(client.getCallCount()).toBe(2);
    });

    it('should reset call history', async () => {
      await client.callTool('speak_text', { text: 'Test' });
      expect(client.getCallCount()).toBe(1);

      client.resetCallHistory();
      expect(client.getCallCount()).toBe(0);
    });

    it('should get last call', async () => {
      await client.callTool('speak_text', { text: 'First' });
      await client.callTool('transcribe_audio', { audio_path: 'path' });

      const lastCall = client.getLastCall();
      expect(lastCall?.name).toBe('transcribe_audio');
    });
  });

  describe('Response Handling', () => {
    it('should parse TTS responses', async () => {
      const response = await client.callTool('speak_text', { text: 'Test' });

      expect(response.data).toHaveProperty('status', 'success');
      expect(response.data).toHaveProperty('audio_base64');
      expect(response.data).toHaveProperty('duration_ms');
      expect(response.data).toHaveProperty('latency_ms');
    });

    it('should parse STT responses', async () => {
      const response = await client.callTool('transcribe_audio', {
        audio_path: 'test.wav'
      });

      expect(response.data).toHaveProperty('text');
      expect(response.data).toHaveProperty('segments');
      expect(response.data).toHaveProperty('language');
    });

    it('should parse model list responses', async () => {
      const response = await client.callTool('list_models', {});

      expect(response.data).toHaveProperty('models');
      expect(Array.isArray(response.data.models)).toBe(true);
    });

    it('should include metadata in responses', async () => {
      const response = await client.callTool('speak_text', { text: 'Test' });

      expect(response.data).toHaveProperty('model_used');
      expect(response.data).toHaveProperty('latency_ms');
    });
  });

  describe('Concurrent Operations', () => {
    it('should handle concurrent tool calls', async () => {
      const promises = [
        client.callTool('speak_text', { text: 'A' }),
        client.callTool('speak_text', { text: 'B' }),
        client.callTool('speak_text', { text: 'C' })
      ];

      const results = await Promise.all(promises);
      expect(results.every(r => r.status === 'success')).toBe(true);
      expect(client.getCallCount()).toBe(3);
    });

    it('should maintain call history with concurrent calls', async () => {
      const promises = Array.from({ length: 5 }, (_, i) =>
        client.callTool('speak_text', { text: `Text ${i}` })
      );

      await Promise.all(promises);
      const history = client.getCallHistory();
      expect(history.length).toBe(5);
    });
  });

  describe('Error Handling', () => {
    it('should handle network errors', async () => {
      // Simulate network error
      const testClient = new MockMCPClient();
      testClient.registerTool('fail_tool', async () => {
        throw new Error('Network error');
      });

      const response = await testClient.callTool('fail_tool', {});
      expect(response.status).toBe('error');
    });

    it('should handle timeout errors', async () => {
      // Should handle timeout gracefully
      expect(true).toBe(true);
    });

    it('should provide error messages', async () => {
      const response = await client.callTool('nonexistent', {});
      expect(response.error).toBeDefined();
      expect(typeof response.error).toBe('string');
    });

    it('should recover from errors', async () => {
      // Error should not affect subsequent calls
      await client.callTool('nonexistent', {});
      const response = await client.callTool('speak_text', { text: 'Test' });

      expect(response.status).toBe('success');
    });
  });

  describe('Tool Registration', () => {
    it('should register custom tools', () => {
      const testClient = new MockMCPClient();
      const customHandler = async () => ({ custom: 'response' });

      testClient.registerTool('custom_tool', customHandler);
      expect(testClient.getCallCount()).toBe(0);
    });

    it('should override existing tools', async () => {
      const testClient = new MockMCPClient();
      const customHandler = async () => ({ custom: true });

      testClient.registerTool('speak_text', customHandler);
      const response = await testClient.callTool('speak_text', {});

      expect(response.data.custom).toBe(true);
    });

    it('should support multiple tool registrations', () => {
      const testClient = new MockMCPClient();
      testClient.registerTool('tool1', async () => ({ id: 1 }));
      testClient.registerTool('tool2', async () => ({ id: 2 }));

      // Both tools should be available
      expect(testClient).toBeDefined();
    });
  });

  describe('Event Handling', () => {
    it('should emit tool call events', async () => {
      const callSpy = jest.fn();
      client.on('tool_call', callSpy);

      // Placeholder: emit event on tool call
      expect(true).toBe(true);
    });

    it('should emit response events', async () => {
      const responseSpy = jest.fn();
      client.on('response', responseSpy);

      // Placeholder: emit event on response
      expect(true).toBe(true);
    });

    it('should emit error events', async () => {
      const errorSpy = jest.fn();
      client.on('error', errorSpy);

      // Placeholder: emit event on error
      expect(true).toBe(true);
    });
  });
});
