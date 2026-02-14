import { GraphData, PaperNode, GraphEdge } from '../types/Paper';
import { MetadataPanel } from './MetadataPanel';
import { SearchBar } from './SearchBar';
import { FilterControls } from './FilterControls';
import { Statistics } from './Statistics';
import { KeyboardControls } from './KeyboardControls';

/**
 * UIManager - Central orchestrator for all UI components
 * Manages search, filters, metadata panel, statistics, and keyboard controls
 */
export class UIManager {
  private metadataPanel: MetadataPanel;
  private searchBar: SearchBar;
  private filterControls: FilterControls;
  private statistics: Statistics;
  private keyboardControls: KeyboardControls;

  private containerEl: HTMLElement;
  private sidebarEl: HTMLElement;
  private visiblePapers: PaperNode[] = [];
  private visibleEdges: GraphEdge[] = [];

  private onPaperSelected: ((paper: PaperNode) => void) | null = null;
  private onPapersFiltered: ((papers: PaperNode[], edges: GraphEdge[]) => void) | null = null;

  constructor(
    private graphData: GraphData,
    parentEl: HTMLElement
  ) {
    this.containerEl = parentEl;
    this.visiblePapers = [...graphData.nodes];
    this.visibleEdges = [...graphData.edges];

    // Create sidebar for controls
    this.sidebarEl = this.containerEl.createDiv('graph-ui-sidebar');
  }

  /**
   * Initialize all UI components
   */
  initialize(): void {
    // Create sidebar sections
    const controlsSection = this.sidebarEl.createDiv('sidebar-section');

    // Initialize components
    this.searchBar = new SearchBar(controlsSection, this.graphData);
    this.searchBar.create();
    this.searchBar.onResultsChanged((papers) => this.handleSearchResults(papers));
    this.searchBar.onPaperClicked((paper) => this.selectPaper(paper));

    this.filterControls = new FilterControls(controlsSection, this.graphData);
    this.filterControls.create();
    this.filterControls.onFiltersChanged((filters, filteredPapers) =>
      this.handleFilterChange(filteredPapers)
    );

    this.statistics = new Statistics(controlsSection);
    this.statistics.create();

    // Initialize metadata panel (on the right)
    this.metadataPanel = new MetadataPanel(this.containerEl);
    this.metadataPanel.create();

    // Initialize keyboard controls
    this.keyboardControls = new KeyboardControls();
    this.setupKeyboardCallbacks();

    // Initial statistics update
    this.updateStatistics();
  }

  /**
   * Handle search results - highlight papers and filter view
   */
  private handleSearchResults(papers: PaperNode[]): void {
    if (papers.length === 0) {
      // Reset to show all papers
      this.visiblePapers = [...this.graphData.nodes];
      this.visibleEdges = [...this.graphData.edges];
    } else {
      // Show only searched papers
      this.visiblePapers = papers;
      const paperIds = new Set(papers.map((p) => p.id));
      this.visibleEdges = this.graphData.edges.filter(
        (e) => paperIds.has(e.source) && paperIds.has(e.target)
      );
    }

    this.updateStatistics();
    this.notifyPapersFiltered();
  }

  /**
   * Handle filter changes
   */
  private handleFilterChange(filteredPapers: PaperNode[]): void {
    // Apply current search on top of filters
    const searchResults = this.searchBar.getMatchedPapers();

    if (searchResults.length > 0) {
      const searchIds = new Set(searchResults.map((p) => p.id));
      this.visiblePapers = filteredPapers.filter((p) => searchIds.has(p.id));
    } else {
      this.visiblePapers = filteredPapers;
    }

    const paperIds = new Set(this.visiblePapers.map((p) => p.id));
    this.visibleEdges = this.graphData.edges.filter(
      (e) => paperIds.has(e.source) && paperIds.has(e.target)
    );

    this.updateStatistics();
    this.notifyPapersFiltered();
  }

  /**
   * Select a paper and show metadata
   */
  selectPaper(paper: PaperNode): void {
    this.metadataPanel.update(paper);

    if (this.onPaperSelected) {
      this.onPaperSelected(paper);
    }
  }

  /**
   * Update statistics display
   */
  private updateStatistics(): void {
    this.statistics.update(this.visiblePapers, this.visibleEdges.length);
  }

  /**
   * Setup keyboard event callbacks
   */
  private setupKeyboardCallbacks(): void {
    this.keyboardControls.onEscapePressed(() => {
      this.metadataPanel.hide();
      this.searchBar.clear();
    });

    this.keyboardControls.onHelpPressed(() => {
      this.showKeyboardHelp();
    });
  }

  /**
   * Show keyboard help modal
   */
  private showKeyboardHelp(): void {
    const helpText = `
3D Graph Controls:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Right Mouse Drag    Rotate camera
Mouse Wheel         Zoom in/out
+/-                 Zoom in/out
Space               Reset camera view
Escape              Close panels
?/H                 Show this help

Search & Filter:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Type in search      Find papers by title/author
Click filter        Apply dimension filters
Reset All           Clear all filters
Click paper         View detailed metadata
    `;

    alert(helpText);
  }

  /**
   * Notify that papers have been filtered
   */
  private notifyPapersFiltered(): void {
    if (this.onPapersFiltered) {
      this.onPapersFiltered(this.visiblePapers, this.visibleEdges);
    }
  }

  /**
   * Register callback for paper selection
   */
  onPaperSelected(callback: (paper: PaperNode) => void): void {
    this.onPaperSelected = callback;
  }

  /**
   * Register callback for papers filtered
   */
  onPapersFiltered(callback: (papers: PaperNode[], edges: GraphEdge[]) => void): void {
    this.onPapersFiltered = callback;
  }

  /**
   * Get currently visible papers
   */
  getVisiblePapers(): PaperNode[] {
    return this.visiblePapers;
  }

  /**
   * Get currently visible edges
   */
  getVisibleEdges(): GraphEdge[] {
    return this.visibleEdges;
  }

  /**
   * Clear all filters and search
   */
  clearAllFilters(): void {
    this.searchBar.clear();
    this.filterControls.reset();
    this.visiblePapers = [...this.graphData.nodes];
    this.visibleEdges = [...this.graphData.edges];
    this.updateStatistics();
    this.notifyPapersFiltered();
  }

  /**
   * Destroy all UI components
   */
  destroy(): void {
    this.metadataPanel.destroy();
    this.searchBar.destroy();
    this.filterControls.destroy();
    this.statistics.destroy();
    this.keyboardControls.destroy();

    if (this.sidebarEl) {
      this.sidebarEl.remove();
    }
  }
}
