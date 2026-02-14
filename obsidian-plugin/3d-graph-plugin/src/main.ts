import { Plugin, PluginSettingTab, App, Setting, Modal, Notice } from 'obsidian';
import { GraphData, PaperNode, Dimension } from './types/Paper';
import { Graph3D } from './visualizations/3DGraph';
import { Decision, DecisionCascade } from './types/Decision';
import { SurrealDBClient } from './services/SurrealDBClient';
import { VaultBridge } from './services/VaultBridge';

/**
 * Settings interface for the 3D Graph plugin
 * Persisted to disk and loaded on plugin startup
 */
interface GraphPluginSettings {
  /** Node size scaling: 'small' (0.5x-1.0x), 'medium' (0.75x-1.5x), 'large' (1.0x-2.0x) */
  nodeScaling: 'small' | 'medium' | 'large';

  /** Label visibility: 'on' (always), 'hover' (on mouse over), 'off' (never) */
  labelVisibility: 'on' | 'hover' | 'off';

  /** Physics simulation speed: 'slow' (stable), 'normal' (balanced), 'fast' (quick) */
  physicsSpeed: 'slow' | 'normal' | 'fast';

  /** Color palette: 'default', 'colorblind', 'bw' */
  colorPalette: string;

  /** Performance mode: 'high' (>30 FPS, full quality), 'low' (<30 FPS, battery friendly) */
  performanceMode: 'high' | 'low';

  /** Phase 5 Settings: Decision visualization */
  showDecisionNodes: boolean;
  showCascadeOverlay: boolean;
  cascadeDepth: number; // 1-5
  confidenceThreshold: number; // 0.0-1.0
}

/** Default plugin settings - used on first install */
const DEFAULT_SETTINGS: GraphPluginSettings = {
  nodeScaling: 'medium',
  labelVisibility: 'hover',
  physicsSpeed: 'normal',
  colorPalette: 'default',
  performanceMode: 'high',
  showDecisionNodes: true,
  showCascadeOverlay: false,
  cascadeDepth: 3,
  confidenceThreshold: 0.6,
};

/**
 * Main plugin class for 3D Graph Visualization in Obsidian
 * Handles plugin lifecycle, settings management, and UI registration
 *
 * @example
 * // Users can:
 * // 1. Click ribbon icon to open 3D graph
 * // 2. Use command palette (Ctrl+P > "Open 3D Graph")
 * // 3. Customize settings in Settings tab
 */
export default class GraphPlugin extends Plugin {
  /** Current plugin settings (persisted across sessions) */
  settings: GraphPluginSettings;

  /**
   * Called when plugin is loaded by Obsidian
   * Sets up ribbon icons, commands, and settings tabs
   */
  async onload(): Promise<void> {
    await this.loadSettings();

    // Register ribbon icon in left sidebar - 3D Graph
    this.addRibbonIcon('network', '3D Graph', () => {
      this.openGraph3D();
    });

    // Register ribbon icon - Decision Explorer (NEW in Phase 5)
    this.addRibbonIcon('lightbulb', 'Decision Explorer', () => {
      this.openDecisionExplorer();
    });

    // Register command for command palette - 3D Graph
    this.addCommand({
      id: 'open-3d-graph',
      name: 'Open 3D Graph',
      callback: () => {
        this.openGraph3D();
      },
    });

    // Register command - Decision Explorer (NEW in Phase 5)
    this.addCommand({
      id: 'open-decision-explorer',
      name: 'Open Decision Explorer',
      hotkeys: [
        {
          modifiers: ['Ctrl', 'Shift'],
          key: 'd',
        },
      ],
      callback: () => {
        this.openDecisionExplorer();
      },
    });

    // Register ribbon icon - Decision Health Dashboard (NEW in Phase 7)
    this.addRibbonIcon('heart-pulse', 'Decision Health Dashboard', () => {
      this.openDecisionHealthDashboard();
    });

    // Register ribbon icon - Cascade Timeline (NEW in Phase 7)
    this.addRibbonIcon('git-branch', 'Cascade Timeline', () => {
      this.openCascadeTimeline();
    });

    // Register command - Decision Health Dashboard (NEW in Phase 7)
    this.addCommand({
      id: 'open-decision-health-dashboard',
      name: 'Open Decision Health Dashboard',
      hotkeys: [
        {
          modifiers: ['Ctrl', 'Shift'],
          key: 'h',
        },
      ],
      callback: () => {
        this.openDecisionHealthDashboard();
      },
    });

    // Register command - Cascade Timeline (NEW in Phase 7)
    this.addCommand({
      id: 'open-cascade-timeline',
      name: 'Open Cascade Timeline',
      callback: () => {
        this.openCascadeTimeline();
      },
    });

    // Register settings tab in plugin settings
    this.addSettingTab(new GraphSettingTab(this.app, this));

    console.log('3D Graph Plugin loaded (Phase 7: Health Dashboard + Cascade Timeline integrated)');
  }

  /**
   * Open the 3D graph modal with graph data
   * Loads graph data and displays it in a new modal window
   *
   * @private
   * @returns {Promise<void>}
   * @throws Will show notice if graph fails to load
   */
  private async openGraph3D(): Promise<void> {
    try {
      // Create sample graph data for demonstration
      const graphData = this.generateSampleGraphData();

      const modal = new Graph3D(this.app);
      await modal.loadGraphData(graphData);
      modal.open();
    } catch (error) {
      console.error('Failed to open 3D graph:', error);
      new Notice('Error opening 3D graph. Check console for details.');
    }
  }

  /**
   * Open the Decision Explorer modal
   * Displays decision search, reasoning chains, cascades, and contradictions
   *
   * NEW in Phase 5: Integrated with 3D Graph for unified decision intelligence
   *
   * @param {string} paperFilter Optional paper title to filter decisions by
   * @private
   * @returns {Promise<void>}
   */
  private async openDecisionExplorer(paperFilter?: string): Promise<void> {
    try {
      // Import DecisionExplorerModal dynamically to avoid circular dependencies
      const { DecisionExplorerModal } = await import('./ui/DecisionExplorerModal');

      const modal = new DecisionExplorerModal(this.app, paperFilter);
      modal.open();
      const msg = paperFilter
        ? `Decision Explorer opened (filtered for "${paperFilter}")`
        : 'Decision Explorer opened. Search for decisions or view reasoning chains.';
      new Notice(msg);
    } catch (error) {
      console.error('Failed to open Decision Explorer:', error);
      new Notice('Error opening Decision Explorer. Check console for details.');
    }
  }

  /**
   * Open the Decision Health Dashboard modal
   * Displays 6 interactive metrics for decision health and velocity
   *
   * NEW in Phase 7: Real-time dashboard with confidence distribution,
   * reasoning breakdown, contradiction trends, quality ranking,
   * impact distribution, and decision velocity
   *
   * @private
   * @returns {Promise<void>}
   */
  private async openDecisionHealthDashboard(): Promise<void> {
    try {
      const { DecisionHealthDashboard } = await import('./ui/DecisionHealthDashboard');
      const surrealClient = new SurrealDBClient();
      const vaultBridge = new VaultBridge(this.app.vault);

      // Load decisions from vault
      const decisionsMap = await vaultBridge.loadAllDecisions();
      const decisions: Decision[] = Array.from(decisionsMap.values());

      const modal = new DecisionHealthDashboard(this.app, decisions, surrealClient);
      modal.open();
      new Notice(`Decision Health Dashboard opened (${decisions.length} decisions loaded)`);
    } catch (error) {
      console.error('Failed to open Decision Health Dashboard:', error);
      new Notice('Error opening Decision Health Dashboard. Check console for details.');
    }
  }

  /**
   * Open the Cascade Timeline modal
   * Displays temporal impacts of decisions with cascading effects
   *
   * NEW in Phase 7: Chronological timeline with color-coded cascade impacts
   *
   * @private
   * @returns {Promise<void>}
   */
  private async openCascadeTimeline(): Promise<void> {
    try {
      const { CascadeTimeline } = await import('./ui/CascadeTimeline');
      const surrealClient = new SurrealDBClient();
      const vaultBridge = new VaultBridge(this.app.vault);

      // Load decisions from vault
      const decisionsMap = await vaultBridge.loadAllDecisions();
      const decisions: Decision[] = Array.from(decisionsMap.values());

      // Load cascades from SurrealDB
      let cascades: DecisionCascade[] = [];
      try {
        const cascadesResult = await surrealClient.executeQuery(
          'SELECT * FROM decision_cascades LIMIT 500;'
        );
        if (Array.isArray(cascadesResult)) {
          cascades = cascadesResult.map((row: any) => ({
            source_decision_id: row.source_decision_id,
            target_decision_id: row.target_decision_id,
            dependency_type: row.dependency_type || 'influences',
            impact_level: row.impact_level || 'minor',
            description: row.description || '',
          }));
        }
      } catch (e) {
        console.log('Cascade data not yet available in SurrealDB, showing decisions only');
      }

      const modal = new CascadeTimeline(this.app, decisions, cascades);
      modal.open();
      new Notice(`Cascade Timeline opened (${decisions.length} decisions, ${cascades.length} cascades)`);
    } catch (error) {
      console.error('Failed to open Cascade Timeline:', error);
      new Notice('Error opening Cascade Timeline. Check console for details.');
    }
  }

  /**
   * Generate sample graph data (84 papers) for testing
   * Creates synthetic papers with random dimensions and connections
   *
   * @private
   * @returns {GraphData} Complete graph with 84 nodes and ~250 edges
   * @note TODO: Replace with actual DataLoader that reads from vault
   */
  private generateSampleGraphData(): GraphData {
    const papers: PaperNode[] = [];

    // Generate 84 sample papers
    for (let i = 0; i < 84; i++) {
      const paper: PaperNode = {
        id: `paper-${i}`,
        title: `Paper ${i + 1}: Research on AI and Knowledge Graphs`,
        path: `/papers/paper-${i}.md`,
        authors: [`Author ${i}`, `CoAuthor ${i}`],
        year: 2020 + Math.floor(i / 10),
        dimensions: {
          connectivity: Math.random(),
          conceptual_depth: Math.random(),
          temporal: Math.random(),
          cross_domain: (i % 15) + 1,
          completion: Math.random() * 100,
          recency: Math.random(),
          semantic_similarity: Math.random() * 0.5,
          similar_papers: [],
        },
      };
      papers.push(paper);
    }

    // Generate edges (connections)
    const edges = [];
    for (let i = 0; i < papers.length; i++) {
      // Each paper connects to 3-5 random others
      const connectionCount = 3 + Math.floor(Math.random() * 3);
      for (let j = 0; j < connectionCount; j++) {
        const target = Math.floor(Math.random() * papers.length);
        if (target !== i) {
          edges.push({
            source: papers[i].id,
            target: papers[target].id,
            similarity: Math.random() * 0.5 + 0.5,
          });
        }
      }
    }

    return {
      nodes: papers,
      edges: edges,
      metadata: {
        totalPapers: papers.length,
        totalEdges: edges.length,
        avgConnectivity: 0.5,
        domainDistribution: {},
        loadedAt: Date.now(),
      },
    };
  }

  /**
   * Called when plugin is unloaded by Obsidian
   * Clean up resources and listeners
   */
  onunload(): void {
    console.log('3D Graph Plugin unloaded');
  }

  /**
   * Load plugin settings from Obsidian's data.json
   * Falls back to DEFAULT_SETTINGS if no saved settings exist
   *
   * @returns {Promise<void>}
   */
  async loadSettings(): Promise<void> {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  /**
   * Save plugin settings to Obsidian's data.json
   * Called automatically when user changes settings
   *
   * @returns {Promise<void>}
   */
  async saveSettings(): Promise<void> {
    await this.saveData(this.settings);
  }
}

/**
 * Settings tab for the 3D Graph plugin
 * Renders UI controls in Obsidian's Settings panel
 *
 * Users can adjust:
 * - Node size scaling (small/medium/large)
 * - Label visibility (on/hover/off)
 * - Physics speed (slow/normal/fast)
 * - Performance mode (high/low)
 */
class GraphSettingTab extends PluginSettingTab {
  /** Reference to parent plugin instance */
  plugin: GraphPlugin;

  /**
   * Create settings tab
   *
   * @param {App} app Obsidian app instance
   * @param {GraphPlugin} plugin Parent plugin instance
   */
  constructor(app: App, plugin: GraphPlugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  /**
   * Render the settings UI in the settings panel
   * Called when settings tab is opened, or when plugin loads
   *
   * Creates controls for:
   * - Node Size Scaling dropdown
   * - Label Visibility dropdown
   * - Physics Speed dropdown
   * - Performance Mode dropdown
   *
   * Each control auto-saves changes to plugin.settings
   */
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

    // Phase 5: Decision Visualization Settings
    containerEl.createEl('h3', { text: 'Decision Intelligence (Phase 5)' });

    new Setting(containerEl)
      .setName('Show Decision Nodes')
      .setDesc('Display decision nodes in 3D graph alongside papers')
      .addToggle((toggle) =>
        toggle
          .setValue(this.plugin.settings.showDecisionNodes)
          .onChange(async (value) => {
            this.plugin.settings.showDecisionNodes = value;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName('Show Cascade Overlay')
      .setDesc('Display decision cascade relationships on 3D graph')
      .addToggle((toggle) =>
        toggle
          .setValue(this.plugin.settings.showCascadeOverlay)
          .onChange(async (value) => {
            this.plugin.settings.showCascadeOverlay = value;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName('Cascade Depth')
      .setDesc('How many levels of cascading effects to show (1-5)')
      .addSlider((slider) =>
        slider
          .setLimits(1, 5, 1)
          .setValue(this.plugin.settings.cascadeDepth)
          .onChange(async (value) => {
            this.plugin.settings.cascadeDepth = value;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName('Confidence Threshold')
      .setDesc('Only show decisions above this confidence level (0-1)')
      .addSlider((slider) =>
        slider
          .setLimits(0, 1, 0.1)
          .setValue(this.plugin.settings.confidenceThreshold)
          .setDynamicTooltip()
          .onChange(async (value) => {
            this.plugin.settings.confidenceThreshold = value;
            await this.plugin.saveSettings();
          })
      );
  }
}
