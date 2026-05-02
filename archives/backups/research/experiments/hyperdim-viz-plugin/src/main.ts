/**
 * Hyperdimensional Compound Visualization Plugin - Main Entry Point
 */

import { Plugin, Notice, WorkspaceLeaf } from 'obsidian';
import { HyperdimPluginSettings, DEFAULT_SETTINGS } from './types';
import { MCPClient } from './services/mcp-client';
import { GraphViewModal } from './ui/modals';
import { HyperdimSettingsTab } from './ui/settings';

export default class HyperdimPlugin extends Plugin {
  settings: HyperdimPluginSettings = DEFAULT_SETTINGS;
  mcpClient: MCPClient;

  async onload() {
    console.log('[HyperdimPlugin] Loading...');

    // Load settings
    await this.loadSettings();

    // Initialize MCP client
    this.mcpClient = new MCPClient(this.settings.api.cloudVaultMcpUrl);

    // Verify MCP server connection
    try {
      const health = await this.mcpClient.healthCheck();
      if (health.status === 'ok') {
        console.log('[HyperdimPlugin] Cloud Vault MCP server connected');
      } else {
        console.warn('[HyperdimPlugin] MCP server error:', health.message);
        new Notice('Hyperdim Viz: MCP server unreachable. Check settings.', 5000);
      }
    } catch (error) {
      console.warn('[HyperdimPlugin] Failed to connect to MCP server:', error);
      new Notice(
        'Hyperdim Viz: Could not connect to Cloud Vault MCP. Ensure it is running on port 8360.',
        5000
      );
    }

    // Register ribbon icon - main graph view
    this.addRibbonIcon('graph', 'Open 12D Graph', async () => {
      await this.openGraphView();
    });

    // Register commands
    this.addCommand({
      id: 'open-12d-graph',
      name: 'Open 12D Graph Visualization',
      callback: async () => {
        await this.openGraphView();
      },
    });

    this.addCommand({
      id: 'switch-temporal-projection',
      name: 'Switch to Temporal Projection',
      callback: async () => {
        this.settings.visualization.defaultProjection = 'temporal';
        await this.saveSettings();
        new Notice('Switched to Temporal projection');
      },
    });

    this.addCommand({
      id: 'switch-semantic-projection',
      name: 'Switch to Semantic Projection',
      callback: async () => {
        this.settings.visualization.defaultProjection = 'semantic';
        await this.saveSettings();
        new Notice('Switched to Semantic projection');
      },
    });

    this.addCommand({
      id: 'switch-theory-applied-projection',
      name: 'Switch to Theory-Applied Projection',
      callback: async () => {
        this.settings.visualization.defaultProjection = 'theory_applied';
        await this.saveSettings();
        new Notice('Switched to Theory-Applied projection');
      },
    });

    // Register settings tab
    this.addSettingTab(new HyperdimSettingsTab(this.app, this));

    console.log('[HyperdimPlugin] Loaded successfully');
  }

  async openGraphView() {
    try {
      new Notice('Loading graph data...', 2000);
      const graphModal = new GraphViewModal(this.app, this.settings, this.mcpClient);
      graphModal.open();
    } catch (error) {
      console.error('[HyperdimPlugin] Failed to open graph view:', error);
      new Notice(`Failed to open graph view: ${error.message}`, 5000);
    }
  }

  onunload() {
    console.log('[HyperdimPlugin] Unloading...');
  }

  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings() {
    await this.saveData(this.settings);
  }
}
