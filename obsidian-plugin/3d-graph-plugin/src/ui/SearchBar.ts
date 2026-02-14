import { GraphData, PaperNode } from '../types/Paper';

/**
 * SearchBar - Full-text search for papers in the graph
 * Supports title, keywords, and author search
 */
export class SearchBar {
  private containerEl: HTMLElement | null = null;
  private inputEl: HTMLInputElement | null = null;
  private resultsEl: HTMLElement | null = null;
  private matchedPapers: PaperNode[] = [];
  private currentMatchIndex: number = 0;

  private onResultsChange: ((papers: PaperNode[]) => void) | null = null;
  private onPaperSelected: ((paper: PaperNode) => void) | null = null;

  constructor(
    private parentEl: HTMLElement,
    private graphData: GraphData
  ) {}

  /**
   * Create the search bar HTML structure
   */
  create(): void {
    if (this.containerEl) return;

    this.containerEl = this.parentEl.createDiv('search-bar-container');

    const inputWrapper = this.containerEl.createDiv('search-input-wrapper');

    this.inputEl = inputWrapper.createEl('input', {
      type: 'text',
      placeholder: 'Search papers by title, keywords, authors...',
      cls: 'search-input',
    });

    const clearBtn = inputWrapper.createEl('button', {
      text: '✕',
      cls: 'search-clear-btn',
    });
    clearBtn.addEventListener('click', () => this.clear());

    // Results counter
    const counterEl = this.containerEl.createDiv('search-counter');
    counterEl.innerHTML = '<span class="search-match-text">No results</span>';

    // Results dropdown
    this.resultsEl = this.containerEl.createDiv('search-results search-results-hidden');

    // Event listeners
    this.inputEl.addEventListener('input', (e) => {
      this.handleSearch((e.target as HTMLInputElement).value);
    });

    this.inputEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        this.selectFirstMatch();
      } else if (e.key === 'Escape') {
        this.clear();
      }
    });

    // Close results on click outside
    document.addEventListener('click', (e) => {
      if (!this.containerEl?.contains(e.target as Node)) {
        this.hideResults();
      }
    });
  }

  /**
   * Handle search input
   */
  private handleSearch(query: string): void {
    if (!this.inputEl || !this.resultsEl) return;

    if (query.length < 2) {
      this.matchedPapers = [];
      this.hideResults();
      this.updateCounter();
      return;
    }

    const lowerQuery = query.toLowerCase();
    const startTime = performance.now();

    // Search across title, keywords, and authors
    this.matchedPapers = this.graphData.nodes.filter((paper) => {
      const titleMatch = paper.title.toLowerCase().includes(lowerQuery);
      const authorsMatch =
        paper.authors &&
        paper.authors.some((author) => author.toLowerCase().includes(lowerQuery));

      return titleMatch || authorsMatch;
    });

    const duration = performance.now() - startTime;
    console.log(`Search completed in ${duration.toFixed(2)}ms, found ${this.matchedPapers.length} matches`);

    this.currentMatchIndex = 0;
    this.updateCounter();
    this.renderResults();

    if (this.onResultsChange) {
      this.onResultsChange(this.matchedPapers);
    }
  }

  /**
   * Render search results dropdown
   */
  private renderResults(): void {
    if (!this.resultsEl) return;

    this.resultsEl.empty();

    if (this.matchedPapers.length === 0) {
      this.resultsEl.addClass('search-results-hidden');
      return;
    }

    this.resultsEl.removeClass('search-results-hidden');

    // Limit to top 10 results
    const displayPapers = this.matchedPapers.slice(0, 10);

    displayPapers.forEach((paper, index) => {
      const resultItem = this.resultsEl!.createDiv('search-result-item');
      if (index === this.currentMatchIndex) {
        resultItem.addClass('search-result-selected');
      }

      resultItem.createEl('div', { text: paper.title, cls: 'search-result-title' });

      if (paper.year || paper.authors) {
        const meta = resultItem.createDiv('search-result-meta');
        if (paper.authors && paper.authors.length > 0) {
          meta.createEl('span', { text: paper.authors.join(', '), cls: 'search-result-authors' });
        }
        if (paper.year) {
          meta.createEl('span', { text: paper.year.toString(), cls: 'search-result-year' });
        }
      }

      resultItem.addEventListener('click', () => {
        this.currentMatchIndex = index;
        this.selectMatch(paper);
      });
    });

    if (this.matchedPapers.length > 10) {
      this.resultsEl.createDiv('search-results-more', (div) => {
        div.createEl('span', {
          text: `+${this.matchedPapers.length - 10} more results`,
        });
      });
    }
  }

  /**
   * Update match counter text
   */
  private updateCounter(): void {
    const counterEl = this.containerEl?.querySelector('.search-match-text') as HTMLElement;
    if (!counterEl) return;

    if (this.matchedPapers.length === 0) {
      counterEl.textContent = 'No results';
    } else {
      counterEl.textContent = `${this.currentMatchIndex + 1} of ${this.matchedPapers.length}`;
    }
  }

  /**
   * Select the first matching paper
   */
  private selectFirstMatch(): void {
    if (this.matchedPapers.length > 0) {
      this.selectMatch(this.matchedPapers[0]);
    }
  }

  /**
   * Select a specific paper result
   */
  private selectMatch(paper: PaperNode): void {
    if (this.onPaperSelected) {
      this.onPaperSelected(paper);
    }
  }

  /**
   * Hide results dropdown
   */
  private hideResults(): void {
    if (this.resultsEl) {
      this.resultsEl.addClass('search-results-hidden');
    }
  }

  /**
   * Clear search
   */
  clear(): void {
    if (this.inputEl) {
      this.inputEl.value = '';
    }
    this.matchedPapers = [];
    this.currentMatchIndex = 0;
    this.hideResults();
    this.updateCounter();

    if (this.onResultsChange) {
      this.onResultsChange([]);
    }
  }

  /**
   * Set callback for results change
   */
  onResultsChanged(callback: (papers: PaperNode[]) => void): void {
    this.onResultsChange = callback;
  }

  /**
   * Set callback for paper selection
   */
  onPaperClicked(callback: (paper: PaperNode) => void): void {
    this.onPaperSelected = callback;
  }

  /**
   * Get current search results
   */
  getMatchedPapers(): PaperNode[] {
    return this.matchedPapers;
  }

  /**
   * Destroy the search bar
   */
  destroy(): void {
    if (this.containerEl) {
      this.containerEl.remove();
      this.containerEl = null;
    }
  }
}
