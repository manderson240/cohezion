import { PaperNode } from '../types/Paper';

/**
 * MetadataPanel - Displays detailed information about a selected paper
 * Shows dimensions, similar papers, and vault link
 */
export class MetadataPanel {
  private containerEl: HTMLElement | null = null;
  private isVisible: boolean = false;
  private selectedPaper: PaperNode | null = null;

  constructor(private parentEl: HTMLElement) {}

  /**
   * Create the panel HTML structure
   */
  create(): void {
    if (this.containerEl) return;

    this.containerEl = this.parentEl.createDiv({
      cls: 'metadata-panel metadata-panel-hidden',
    });

    const header = this.containerEl.createDiv('metadata-header');
    header.createEl('h3', { text: 'Paper Details', cls: 'metadata-title' });

    const closeBtn = header.createEl('button', {
      text: '×',
      cls: 'metadata-close-btn',
    });
    closeBtn.addEventListener('click', () => this.hide());

    // Content areas
    this.containerEl.createDiv('metadata-content-wrapper', (wrapper) => {
      wrapper.createDiv('metadata-paper-title');
      wrapper.createDiv('metadata-dimensions');
      wrapper.createDiv('metadata-similar-papers');
      wrapper.createDiv('metadata-actions');
    });
  }

  /**
   * Update panel with paper information
   */
  update(paper: PaperNode): void {
    this.selectedPaper = paper;

    if (!this.containerEl) {
      this.create();
    }

    // Update title with vault link
    const titleEl = this.containerEl!.querySelector('.metadata-paper-title');
    if (titleEl) {
      titleEl.empty();
      const titleLink = titleEl.createEl('a', {
        text: paper.title,
        cls: 'metadata-paper-link',
      });
      titleLink.href = `obsidian://open?path=${encodeURIComponent(paper.path)}`;
      titleLink.title = 'Click to open in vault';

      if (paper.year) {
        titleEl.createEl('span', { text: ` (${paper.year})`, cls: 'metadata-year' });
      }
      if (paper.authors && paper.authors.length > 0) {
        titleEl.createEl('div', {
          text: `Authors: ${paper.authors.join(', ')}`,
          cls: 'metadata-authors',
        });
      }
    }

    // Update dimensions
    const dimensionsEl = this.containerEl!.querySelector('.metadata-dimensions');
    if (dimensionsEl) {
      this.renderDimensions(dimensionsEl as HTMLElement, paper);
    }

    // Update similar papers
    const similarEl = this.containerEl!.querySelector('.metadata-similar-papers');
    if (similarEl) {
      this.renderSimilarPapers(similarEl as HTMLElement, paper);
    }

    this.show();
  }

  /**
   * Render dimension information
   */
  private renderDimensions(containerEl: HTMLElement, paper: PaperNode): void {
    containerEl.empty();
    containerEl.createEl('h4', { text: 'Dimensions', cls: 'metadata-section-title' });

    const dimensionsList = containerEl.createEl('ul', { cls: 'metadata-dimensions-list' });
    const d = paper.dimensions;

    const dimensions = [
      { name: 'Connectivity', value: d.connectivity.toFixed(2), max: 1.0 },
      { name: 'Conceptual Depth', value: d.conceptual_depth.toFixed(2), max: 1.0 },
      { name: 'Temporal', value: d.temporal.toFixed(2), max: 1.0 },
      { name: 'Cross Domain', value: d.cross_domain.toFixed(0), max: 15 },
      { name: 'Completion', value: `${d.completion.toFixed(0)}%`, max: 100 },
      { name: 'Recency', value: d.recency.toFixed(2), max: 1.0 },
      { name: 'Semantic Similarity', value: d.semantic_similarity.toFixed(2), max: 1.0 },
    ];

    dimensions.forEach(({ name, value, max }) => {
      const li = dimensionsList.createEl('li', { cls: 'metadata-dimension-item' });
      li.createEl('span', { text: name, cls: 'metadata-dimension-name' });
      li.createEl('span', { text: value, cls: 'metadata-dimension-value' });

      // Simple progress bar for normalized dimensions
      const barContainer = li.createDiv('metadata-dimension-bar');
      const normalizedValue = (parseFloat(value) / max) * 100;
      barContainer.createDiv('metadata-dimension-fill', (bar) => {
        bar.style.width = `${Math.min(normalizedValue, 100)}%`;
      });
    });
  }

  /**
   * Render similar papers section
   */
  private renderSimilarPapers(containerEl: HTMLElement, paper: PaperNode): void {
    containerEl.empty();
    containerEl.createEl('h4', { text: 'Similar Papers (Top 5)', cls: 'metadata-section-title' });

    const similarPapers = paper.dimensions.similar_papers.slice(0, 5);

    if (similarPapers.length === 0) {
      containerEl.createEl('p', { text: 'No similar papers found', cls: 'metadata-empty' });
      return;
    }

    const list = containerEl.createEl('ul', { cls: 'metadata-similar-list' });
    similarPapers.forEach((similar) => {
      const li = list.createEl('li', { cls: 'metadata-similar-item' });
      li.createEl('span', { text: similar.title, cls: 'metadata-similar-title' });
      li.createEl('span', { text: similar.score.toFixed(3), cls: 'metadata-similar-score' });
    });
  }

  /**
   * Show the panel
   */
  show(): void {
    if (!this.containerEl) return;
    this.isVisible = true;
    this.containerEl.removeClass('metadata-panel-hidden');
  }

  /**
   * Hide the panel
   */
  hide(): void {
    if (!this.containerEl) return;
    this.isVisible = false;
    this.containerEl.addClass('metadata-panel-hidden');
    this.selectedPaper = null;
  }

  /**
   * Check if panel is visible
   */
  getIsVisible(): boolean {
    return this.isVisible;
  }

  /**
   * Get the selected paper
   */
  getSelectedPaper(): PaperNode | null {
    return this.selectedPaper;
  }

  /**
   * Destroy the panel
   */
  destroy(): void {
    if (this.containerEl) {
      this.containerEl.remove();
      this.containerEl = null;
    }
  }
}
