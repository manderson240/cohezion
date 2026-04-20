/**
 * Settings UI
 */

import { App, PluginSettingTab, Setting } from 'obsidian';
import HyperdimPlugin from '../main';
import { ProjectionPreset, PROJECTION_PRESETS } from '../types';

export class HyperdimSettingsTab extends PluginSettingTab {
  plugin: HyperdimPlugin;

  constructor(app: App, plugin: HyperdimPlugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  display(): void {
    const { containerEl } = this;
    containerEl.empty();

    containerEl.createEl('h2', { text: 'Hyperdimensional Compound Visualization Settings' });

    // API Settings
    containerEl.createEl('h3', { text: 'API Configuration' });

    new Setting(containerEl)
      .setName('Cloud Vault MCP URL')
      .setDesc('URL of the Cloud Vault MCP server')
      .addText((text) =>
        text
          .setPlaceholder('http://localhost:8360')
          .setValue(this.plugin.settings.api.cloudVaultMcpUrl)
          .onChange(async (value) => {
            this.plugin.settings.api.cloudVaultMcpUrl = value;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName('Enable Real-Time Sync')
      .setDesc('Sync graph data in real-time (requires MCP server)')
      .addToggle((toggle) =>
        toggle
          .setValue(this.plugin.settings.api.enableRealTimeSync)
          .onChange(async (value) => {
            this.plugin.settings.api.enableRealTimeSync = value;
            await this.plugin.saveSettings();
          })
      );

    // Visualization Settings
    containerEl.createEl('h3', { text: 'Visualization' });

    new Setting(containerEl)
      .setName('Default Projection')
      .setDesc('Initial dimensional projection when opening graph')
      .addDropdown((dropdown) => {
        Object.entries(PROJECTION_PRESETS).forEach(([key, config]) => {
          dropdown.addOption(key, config.name);
        });
        dropdown
          .setValue(this.plugin.settings.visualization.defaultProjection)
          .onChange(async (value) => {
            this.plugin.settings.visualization.defaultProjection = value as ProjectionPreset;
            await this.plugin.saveSettings();
          });
      });

    new Setting(containerEl)
      .setName('Node Size')
      .setDesc('Base size for graph nodes')
      .addSlider((slider) =>
        slider
          .setLimits(1, 10, 0.5)
          .setValue(this.plugin.settings.visualization.nodeSize)
          .setDynamicTooltip()
          .onChange(async (value) => {
            this.plugin.settings.visualization.nodeSize = value;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName('Edge Opacity')
      .setDesc('Transparency of graph edges')
      .addSlider((slider) =>
        slider
          .setLimits(0.1, 1.0, 0.1)
          .setValue(this.plugin.settings.visualization.edgeOpacity)
          .setDynamicTooltip()
          .onChange(async (value) => {
            this.plugin.settings.visualization.edgeOpacity = value;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName('Animation Speed')
      .setDesc('Speed of projection transitions')
      .addSlider((slider) =>
        slider
          .setLimits(0.5, 2.0, 0.1)
          .setValue(this.plugin.settings.visualization.animationSpeed)
          .setDynamicTooltip()
          .onChange(async (value) => {
            this.plugin.settings.visualization.animationSpeed = value;
            await this.plugin.saveSettings();
          })
      );

    // Performance Settings
    containerEl.createEl('h3', { text: 'Performance' });

    new Setting(containerEl)
      .setName('Max Nodes')
      .setDesc('Maximum number of nodes to render')
      .addText((text) =>
        text
          .setPlaceholder('500')
          .setValue(String(this.plugin.settings.performance.maxNodes))
          .onChange(async (value) => {
            const num = parseInt(value, 10);
            if (!isNaN(num) && num > 0) {
              this.plugin.settings.performance.maxNodes = num;
              await this.plugin.saveSettings();
            }
          })
      );

    new Setting(containerEl)
      .setName('Enable LOD')
      .setDesc('Level of Detail optimization (reduces quality at distance)')
      .addToggle((toggle) =>
        toggle
          .setValue(this.plugin.settings.performance.enableLOD)
          .onChange(async (value) => {
            this.plugin.settings.performance.enableLOD = value;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName('Render Quality')
      .setDesc('Graphics quality (higher = better visuals, lower = better performance)')
      .addDropdown((dropdown) =>
        dropdown
          .addOption('low', 'Low')
          .addOption('medium', 'Medium')
          .addOption('high', 'High')
          .setValue(this.plugin.settings.performance.renderQuality)
          .onChange(async (value) => {
            this.plugin.settings.performance.renderQuality = value as 'low' | 'medium' | 'high';
            await this.plugin.saveSettings();
          })
      );
  }
}
