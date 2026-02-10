/**
 * Kyutai Obsidian Plugin - Main Entry Point
 */

import { Plugin, Notice } from 'obsidian';
import { KyutaiPluginSettings, DEFAULT_SETTINGS } from './types';
import { MCPClient } from './services/mcp-client';
import { RibbonCommandManager } from './ui/commands';
import { KyutaiSettingsTab } from './ui/settings';

export default class KyutaiPlugin extends Plugin {
  settings: KyutaiPluginSettings = DEFAULT_SETTINGS;
  mcpClient: MCPClient;
  private ribbonManager: RibbonCommandManager | null = null;

  async onload() {
    console.log('[Kyutai Plugin] Loading...');

    // Load settings
    await this.loadSettings();

    // Initialize MCP client
    this.mcpClient = new MCPClient(this.settings.api.serverUrl);

    // Verify MCP server connection
    try {
      const health = await this.mcpClient.healthCheck();
      if (health.status === 'ok') {
        console.log('[Kyutai Plugin] MCP server connected');
      } else {
        console.warn('[Kyutai Plugin] MCP server error:', health.message);
        new Notice('Kyutai: MCP server unreachable. Check settings.', 5000);
      }
    } catch (error) {
      console.warn('[Kyutai Plugin] Failed to connect to MCP server:', error);
      new Notice(
        'Kyutai: Could not connect to MCP server. Please ensure it is running.',
        5000
      );
    }

    // Register ribbon commands
    this.ribbonManager = new RibbonCommandManager(
      this.app,
      this.mcpClient,
      this.settings
    );
    this.ribbonManager.registerCommands(this);

    // Register settings tab
    this.addSettingTab(new KyutaiSettingsTab(this.app, this));

    // Register keyboard shortcuts
    this.registerKeyboardShortcuts();

    console.log('[Kyutai Plugin] Loaded successfully');
  }

  private registerKeyboardShortcuts(): void {
    // Read Note Aloud: Ctrl+Shift+P (Windows/Linux) or Cmd+Shift+P (macOS)
    this.registerCommand({
      id: 'kyutai-read-aloud',
      name: 'Read Note Aloud',
      hotkeys: [
        {
          modifiers: ['Ctrl', 'Shift'],
          key: 'p',
        },
        {
          modifiers: ['Cmd', 'Shift'],
          key: 'p',
        },
      ],
      callback: () => {
        // Trigger read aloud command via ribbon manager
        if (this.ribbonManager) {
          // Access private method via type assertion (not ideal but works)
          (this.ribbonManager as any).readNoteAloud();
        }
      },
    });

    // Transcribe Audio: Ctrl+Shift+T
    this.registerCommand({
      id: 'kyutai-transcribe',
      name: 'Transcribe Audio',
      hotkeys: [
        {
          modifiers: ['Ctrl', 'Shift'],
          key: 't',
        },
        {
          modifiers: ['Cmd', 'Shift'],
          key: 't',
        },
      ],
      callback: () => {
        if (this.ribbonManager) {
          (this.ribbonManager as any).transcribeAudio();
        }
      },
    });
  }

  onunload() {
    console.log('[Kyutai Plugin] Unloading...');
    this.mcpClient.disconnectWebSocket();
  }

  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings() {
    await this.saveData(this.settings);

    // Update MCP client server URL if changed
    this.mcpClient.setServerUrl(this.settings.api.serverUrl);
  }

  registerCommand(cmd: any) {
    this.addCommand(cmd);
  }
}
