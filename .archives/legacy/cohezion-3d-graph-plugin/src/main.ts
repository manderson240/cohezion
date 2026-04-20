import {
  Plugin,
  PluginSettingTab,
  App,
  Setting,
  Notice,
  WorkspaceLeaf,
  ItemView,
} from 'obsidian';
import DataLoader, { SemanticData } from './data-loader';
import ThreeVisualizer from './three-visualizer';

const VIEW_TYPE_GRAPH = 'cohezion-3d-graph';

interface GraphSettings {
  renderDistance: number;
  nodeSize: number;
  linkStrength: number;
  physics: boolean;
}

const DEFAULT_SETTINGS: GraphSettings = {
  renderDistance: 200,
  nodeSize: 1,
  linkStrength: 1,
  physics: true,
};

class GraphView extends ItemView {
  private visualizer: ThreeVisualizer | null = null;
  private dataLoader: DataLoader = new DataLoader();
  private container: HTMLElement | null = null;
  private searchInput: HTMLInputElement | null = null;
  private statsPanel: HTMLElement | null = null;

  getViewType() {
    return VIEW_TYPE_GRAPH;
  }

  getDisplayText() {
    return 'Cohezion 3D Graph';
  }

  getIcon() {
    return 'network';
  }

  async onOpen() {
    const contentEl = this.containerEl.children[1] as HTMLElement;
    contentEl.empty();

    // Create layout
    const layout = contentEl.createDiv({ cls: 'cohezion-graph-layout' });

    // Create sidebar
    const sidebar = layout.createDiv({ cls: 'cohezion-sidebar' });
    sidebar.createEl('h3', { text: 'Search & Filter' });

    // Search input
    this.searchInput = sidebar.createEl('input', {
      type: 'text',
      cls: 'cohezion-search',
      placeholder: 'Search papers...',
    });
    this.searchInput.addEventListener('change', () => this.onSearch());

    // Stats panel
    this.statsPanel = sidebar.createDiv({ cls: 'cohezion-stats' });

    // Create visualization container
    this.container = layout.createDiv({ cls: 'cohezion-canvas' });

    // Load data and initialize visualization
    await this.initializeVisualization();

    // Handle window resize
    this.registerEvent(this.app.workspace.on('resize', () => {
      if (this.visualizer) {
        // Trigger resize handling in visualizer
      }
    }));
  }

  async initializeVisualization() {
    try {
      // Load semantic dimensions data
      const response = await fetch('/tmp/semantic_dimensions.json');
      const data: SemanticData = await response.json();

      // Load data
      await this.dataLoader.loadData(data);

      // Create visualizer
      if (this.container) {
        this.visualizer = new ThreeVisualizer(this.container);
        
        // Get papers and connections
        const papers = this.dataLoader.getPapers();
        const connections = new Map();
        
        papers.forEach(p => {
          const conns = this.dataLoader.getConnections(p.filename);
          connections.set(p.filename, conns);
        });

        // Load graph
        this.visualizer.loadGraph(papers, connections);

        // Update stats
        this.updateStats();

        new Notice(`✅ Loaded ${papers.length} papers with knowledge graph`);
      }
    } catch (error) {
      console.error('Failed to load visualization:', error);
      new Notice('❌ Failed to load knowledge graph');
    }
  }

  private onSearch() {
    if (!this.searchInput) return;

    const query = this.searchInput.value.toLowerCase();
    if (!query) return;

    const results = this.dataLoader.searchByKeyword(query);
    new Notice(`Found ${results.length} papers matching "${query}"`);
  }

  private updateStats() {
    if (!this.statsPanel) return;

    this.statsPanel.empty();
    const stats = this.dataLoader.getStats();

    this.statsPanel.createEl('h4', { text: 'Statistics' });
    this.statsPanel.createEl('p', { text: `Papers: ${stats.totalPapers}` });
    this.statsPanel.createEl('p', { text: `Connections: ${stats.totalConnections}` });

    const dimAvg = this.statsPanel.createEl('div', { cls: 'cohezion-dimensions' });
    dimAvg.createEl('h5', { text: 'Avg Dimensions' });

    Object.entries(stats.dimensionAverages).forEach(([key, value]) => {
      dimAvg.createEl('p', { text: `${key}: ${(value as number).toFixed(2)}` });
    });
  }

  async onClose() {
    if (this.visualizer) {
      this.visualizer.dispose();
    }
  }
}

export default class CohezionGraphPlugin extends Plugin {
  settings: GraphSettings = DEFAULT_SETTINGS;

  async onload() {
    console.log('Loading Cohezion 3D Graph Plugin');

    // Load settings
    await this.loadSettings();

    // Register view
    this.registerView(VIEW_TYPE_GRAPH, (leaf: WorkspaceLeaf) => new GraphView(leaf));

    // Add ribbon icon
    this.addRibbonIcon('network', 'Open 3D Graph', () => {
      this.activateView();
    });

    // Add settings tab
    this.addSettingTab(new GraphSettingTab(this.app, this));

    // Open view on load
    this.activateView();
  }

  async activateView() {
    const { workspace } = this.app;

    let leaf: WorkspaceLeaf | null = null;
    const leaves = workspace.getLeavesOfType(VIEW_TYPE_GRAPH);

    if (leaves.length > 0) {
      leaf = leaves[0];
    } else {
      leaf = workspace.getLeaf(false);
      await leaf.setViewState({ type: VIEW_TYPE_GRAPH });
    }

    workspace.revealLeaf(leaf);
  }

  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData('settings'));
  }

  async saveSettings() {
    await this.saveData('settings', this.settings);
  }
}

class GraphSettingTab extends PluginSettingTab {
  plugin: CohezionGraphPlugin;

  constructor(app: App, plugin: CohezionGraphPlugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  display(): void {
    const { containerEl } = this;
    containerEl.empty();

    containerEl.createEl('h2', { text: 'Cohezion 3D Graph Settings' });

    new Setting(containerEl)
      .setName('Physics Simulation')
      .setDesc('Enable/disable D3 force simulation')
      .addToggle(toggle =>
        toggle.setValue(this.plugin.settings.physics).onChange(async value => {
          this.plugin.settings.physics = value;
          await this.plugin.saveSettings();
        })
      );

    new Setting(containerEl)
      .setName('Node Size')
      .setDesc('Scale of paper nodes')
      .addSlider(slider =>
        slider
          .setMin(0.5)
          .setMax(3)
          .setStep(0.5)
          .setValue(this.plugin.settings.nodeSize)
          .onChange(async value => {
            this.plugin.settings.nodeSize = value;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName('Link Strength')
      .setDesc('Strength of connection forces')
      .addSlider(slider =>
        slider
          .setMin(0.5)
          .setMax(2)
          .setStep(0.1)
          .setValue(this.plugin.settings.linkStrength)
          .onChange(async value => {
            this.plugin.settings.linkStrength = value;
            await this.plugin.saveSettings();
          })
      );
  }
}
