/**
 * Paper Backlinks Panel
 *
 * Shows all decisions that reference a given paper.
 * Used when user clicks on a paper to see which decisions depend on it.
 *
 * Phase 2: Paper Integration
 */

import { App, Modal, Notice } from 'obsidian';
import { SurrealDBClient } from '../services/SurrealDBClient';

export interface PaperLink {
  decision_id: string;
  link_type: string;
  confidence: number;
  mentioned_in: string;
}

export class PaperBacklinksPanel extends Modal {
  private paperId: string;
  private surrealClient: SurrealDBClient;
  private links: PaperLink[] = [];

  constructor(
    app: App,
    paperId: string,
    surrealClient: SurrealDBClient
  ) {
    super(app);
    this.paperId = paperId;
    this.surrealClient = surrealClient;
    this.titleEl.textContent = `Decisions Referencing: ${paperId}`;
  }

  async onOpen(): Promise<void> {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.addClass('paper-backlinks-panel');

    contentEl.innerHTML = `
      <div style="padding: 20px;">
        <p>Loading decisions that reference this paper...</p>
      </div>
    `;

    await this.loadBacklinks();
    this.render();
  }

  /**
   * Load all decisions referencing this paper
   */
  private async loadBacklinks(): Promise<void> {
    try {
      const query = `
        SELECT decision_id, link_type, confidence, mentioned_in
        FROM paper_decision_links
        WHERE paper_id = $paperId
        ORDER BY confidence DESC
      `;
      const results = await this.surrealClient.executeQuery(query, {
        paperId: this.paperId,
      });

      if (results && Array.isArray(results)) {
        this.links = results;
      }
    } catch (error) {
      console.error('Error loading paper backlinks:', error);
      new Notice('Failed to load decisions for this paper');
    }
  }

  /**
   * Render the backlinks panel
   */
  private render(): void {
    const { contentEl } = this;
    contentEl.empty();

    const container = contentEl.createDiv('paper-backlinks-container');
    container.style.padding = '20px';

    if (this.links.length === 0) {
      const noLinks = container.createDiv();
      noLinks.textContent = 'No decisions reference this paper';
      noLinks.style.color = '#999';
      noLinks.style.textAlign = 'center';
      noLinks.style.padding = '40px 0';
      return;
    }

    // Header
    const header = container.createEl('h3');
    header.textContent = `${this.links.length} Decisions Reference This Paper`;
    header.style.marginBottom = '20px';

    // Links list
    const listDiv = container.createDiv('paper-backlinks-list');
    for (const link of this.links) {
      const linkItem = listDiv.createDiv('paper-backlinks-item');
      linkItem.style.padding = '12px';
      linkItem.style.marginBottom = '10px';
      linkItem.style.backgroundColor = '#f9f9f9';
      linkItem.style.border = '1px solid #ddd';
      linkItem.style.borderRadius = '4px';
      linkItem.style.cursor = 'pointer';

      // Decision ID
      const titleDiv = linkItem.createDiv();
      const titleSpan = titleDiv.createEl('strong');
      titleSpan.textContent = link.decision_id;
      titleSpan.style.color = '#3b82f6';

      // Link type badge
      const typeSpan = titleDiv.createEl('span');
      typeSpan.style.marginLeft = '10px';
      typeSpan.style.fontSize = '0.85em';
      typeSpan.style.backgroundColor = '#e0e0e0';
      typeSpan.style.color = '#333';
      typeSpan.style.padding = '2px 8px';
      typeSpan.style.borderRadius = '3px';
      typeSpan.textContent = link.link_type;

      // Confidence score
      const confDiv = titleDiv.createDiv();
      confDiv.style.marginTop = '4px';
      confDiv.style.fontSize = '0.85em';
      confDiv.style.color = '#666';
      confDiv.textContent = `Confidence: ${(link.confidence * 100).toFixed(0)}%`;

      // Excerpt
      if (link.mentioned_in) {
        const excerptDiv = linkItem.createDiv();
        excerptDiv.style.marginTop = '8px';
        excerptDiv.style.fontSize = '0.85em';
        excerptDiv.style.color = '#666';
        excerptDiv.style.fontStyle = 'italic';
        excerptDiv.style.backgroundColor = '#f0f0f0';
        excerptDiv.style.padding = '8px';
        excerptDiv.style.borderRadius = '2px';
        excerptDiv.style.maxHeight = '60px';
        excerptDiv.style.overflow = 'hidden';
        excerptDiv.textContent = `"${link.mentioned_in.substring(0, 100)}..."`;
      }

      linkItem.onmouseenter = () => {
        linkItem.style.backgroundColor = '#f0f8ff';
        linkItem.style.borderColor = '#3b82f6';
      };
      linkItem.onmouseleave = () => {
        linkItem.style.backgroundColor = '#f9f9f9';
        linkItem.style.borderColor = '#ddd';
      };
    }

    // Stats footer
    const stats = container.createDiv();
    stats.style.marginTop = '20px';
    stats.style.padding = '12px';
    stats.style.backgroundColor = '#f0f0f0';
    stats.style.borderRadius = '4px';
    stats.style.fontSize = '0.9em';
    stats.style.color = '#666';

    const linkTypes = new Set(this.links.map(l => l.link_type));
    const avgConfidence = (
      this.links.reduce((sum, l) => sum + l.confidence, 0) / this.links.length
    ).toFixed(2);

    stats.innerHTML = `
      <div><strong>Summary:</strong></div>
      <div style="margin-top: 8px;">
        • Link types: ${Array.from(linkTypes).join(', ')}<br/>
        • Average confidence: ${avgConfidence}
      </div>
    `;
  }
}
