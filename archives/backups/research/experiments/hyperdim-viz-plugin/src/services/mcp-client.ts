/**
 * MCP Client - Communication with Cloud Vault MCP Server
 */

import { GraphData } from '../types';
import { Notice } from 'obsidian';

export class MCPClient {
  private serverUrl: string;
  private ws: WebSocket | null = null;
  private requestId: number = 0;

  constructor(serverUrl: string = 'http://localhost:8360') {
    this.serverUrl = serverUrl;
  }

  /**
   * HTTP-based call to MCP server (for most tools)
   */
  async call<T>(tool: string, params: Record<string, any>): Promise<T> {
    try {
      const response = await fetch(`${this.serverUrl}/mcp/call`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ tool, params }),
      });

      if (!response.ok) {
        throw new Error(`MCP Server error: ${response.statusText}`);
      }

      const data = await response.json();
      if (data.error) {
        throw new Error(`MCP Error: ${data.error}`);
      }

      return data.result as T;
    } catch (error) {
      console.error(`[MCPClient] Error calling ${tool}:`, error);
      throw error;
    }
  }

  /**
   * Fetch graph data from vault
   */
  async fetchGraphData(): Promise<GraphData> {
    return this.call<GraphData>('get_graph_data', {});
  }

  /**
   * Get agent journey data (Phase 2)
   */
  async getAgentJourneys(agentId?: string): Promise<any[]> {
    return this.call<any[]>('get_agent_journeys', { agent_id: agentId });
  }

  /**
   * Get capability metrics (Phase 3)
   */
  async getCapabilityMetrics(): Promise<any> {
    return this.call<any>('get_capability_metrics', {});
  }

  /**
   * Health Check: Verify MCP server is running
   */
  async healthCheck(): Promise<{ status: 'ok' | 'error'; message?: string }> {
    try {
      const response = await fetch(`${this.serverUrl}/health`, {
        method: 'GET',
      });

      if (response.ok) {
        return { status: 'ok' };
      } else {
        return { status: 'error', message: 'Server returned non-200 status' };
      }
    } catch (error) {
      return { status: 'error', message: String(error) };
    }
  }

  /**
   * WebSocket connection for streaming (Moshi)
   */
  async connectWebSocket(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        const wsUrl = this.serverUrl.replace('http://', 'ws://').replace('https://', 'wss://');
        this.ws = new WebSocket(`${wsUrl}/stream`);

        this.ws.onopen = () => {
          console.log('[MCPClient] WebSocket connected');
          resolve();
        };

        this.ws.onerror = (error) => {
          console.error('[MCPClient] WebSocket error:', error);
          reject(new Error('Failed to connect to MCP WebSocket'));
        };

        this.ws.onmessage = (event) => {
          console.log('[MCPClient] WebSocket message:', event.data);
        };

        this.ws.onclose = () => {
          console.log('[MCPClient] WebSocket closed');
          this.ws = null;
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * Send message via WebSocket (streaming)
   */
  sendStreamMessage(data: Record<string, any>): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      throw new Error('WebSocket not connected');
    }
  }

  /**
   * Register WebSocket message handler
   */
  onStreamMessage(callback: (data: Record<string, any>) => void): void {
    if (this.ws) {
      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          callback(data);
        } catch (error) {
          console.error('[MCPClient] Failed to parse WebSocket message:', error);
        }
      };
    }
  }

  /**
   * Close WebSocket connection
   */
  disconnectWebSocket(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * Update server URL
   */
  setServerUrl(url: string): void {
    this.serverUrl = url;
  }

  /**
   * Get current server URL
   */
  getServerUrl(): string {
    return this.serverUrl;
  }
}
