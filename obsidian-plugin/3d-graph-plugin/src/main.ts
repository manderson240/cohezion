import { Plugin, PluginSettingTab, App, Setting, Modal, Notice } from 'obsidian';
import { GraphData, PaperNode, Dimension } from './types/Paper';

interface GraphPluginSettings {
  nodeScaling: 'small' | 'medium' | 'large';
  labelVisibility: 'on' | 'hover' | 'off';
  physicsSpeed: 'slow' | 'normal' | 'fast';
  colorPalette: string;
  performanceMode: 'high' | 'low';
}

const DEFAULT_SETTINGS: GraphPluginSettings = {
  nodeScaling: 'medium',
  labelVisibility: 'hover',
  physicsSpeed: 'normal',
  colorPalette: 'default',
  performanceMode: 'high',
};

export default class GraphPlugin extends Plugin {
  settings: GraphPluginSettings;

  async onload() {
    await this.loadSettings();

    // Add ribbon icon to open the 3D graph
    this.addRibbonIcon('network', '3D Graph', () => {
      new Notice('Opening 3D Graph Visualization...');
      // TODO: Open 3D graph modal
    });

    // Add command to open 3D graph
    this.addCommand({
      id: 'open-3d-graph',
      name: 'Open 3D Graph',
      callback: () => {
        new Notice('Opening 3D Graph...');
        // TODO: Open 3D graph modal
      },
    });

    // Add settings tab
    this.addSettingTab(new GraphSettingTab(this.app, this));

    console.log('3D Graph Plugin loaded');
  }

  onunload() {
    console.log('3D Graph Plugin unloaded');
  }

  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings() {
    await this.saveData(this.settings);
  }
}

class GraphSettingTab extends PluginSettingTab {
  plugin: GraphPlugin;

  constructor(app: App, plugin: GraphPlugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  display(): void {
    const { containerEl } = this;

    containerEl.empty();

    containerEl.createEl('h2', { text: '3D Graph Visualization Settings' });

    new Setting(containerEl)
      .setName('Node Size Scaling')
      .setDesc('Controls the scale range of visualization nodes')
      .addDropdown((dropdown) =>
        dropdown
          .addOption('small', 'Small (0.5x - 1.0x)')
          .addOption('medium', 'Medium (0.75x - 1.5x)')
          .addOption('large', 'Large (1.0x - 2.0x)')
          .setValue(this.plugin.settings.nodeScaling)
          .onChange(async (value: any) => {
            this.plugin.settings.nodeScaling = value;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName('Label Visibility')
      .setDesc('When to show paper titles')
      .addDropdown((dropdown) =>
        dropdown
          .addOption('on', 'Always On')
          .addOption('hover', 'On Hover')
          .addOption('off', 'Off')
          .setValue(this.plugin.settings.labelVisibility)
          .onChange(async (value: any) => {
            this.plugin.settings.labelVisibility = value;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName('Physics Simulation Speed')
      .setDesc('Controls force-directed layout simulation speed')
      .addDropdown((dropdown) =>
        dropdown
          .addOption('slow', 'Slow (more stable)')
          .addOption('normal', 'Normal (balanced)')
          .addOption('fast', 'Fast (less stable)')
          .setValue(this.plugin.settings.physicsSpeed)
          .onChange(async (value: any) => {
            this.plugin.settings.physicsSpeed = value;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName('Performance Mode')
      .setDesc('Adjust quality vs frame rate')
      .addDropdown((dropdown) =>
        dropdown
          .addOption('high', 'High Quality (>30 FPS)')
          .addOption('low', 'Low Power (<30 FPS, battery friendly)')
          .setValue(this.plugin.settings.performanceMode)
          .onChange(async (value: any) => {
            this.plugin.settings.performanceMode = value;
            await this.plugin.saveSettings();
          })
      );
  }
}
