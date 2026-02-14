import { App, Modal } from 'obsidian';
import { DecisionExplorer } from './DecisionExplorer';
import { SurrealDBClient } from '../services/SurrealDBClient';
import { VaultBridge } from '../services/VaultBridge';

/**
 * Modal wrapper for Decision Explorer (Phase 5)
 *
 * Displays Decision Explorer in an Obsidian modal dialog.
 * Handles initialization of SurrealDB client and Vault Bridge.
 */
export class DecisionExplorerModal extends Modal {
  private explorer: DecisionExplorer | null = null;
  private paperFilter: string | null = null;

  constructor(app: App, paperFilter?: string) {
    super(app);
    if (paperFilter) {
      this.paperFilter = paperFilter;
    }
  }

  /**
   * Initialize and display the Decision Explorer
   */
  async onOpen(): Promise<void> {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.addClass('decision-explorer-modal');

    try {
      // Initialize services
      const surrealClient = new SurrealDBClient();
      const vaultBridge = new VaultBridge(this.app.vault);

      // Create explorer
      this.explorer = new DecisionExplorer(this.app, surrealClient, vaultBridge);

      // Load decisions
      await this.explorer.loadDecisions();

      // If paper filter provided, filter decisions
      if (this.paperFilter) {
        const relatedDecisions = await vaultBridge.findDecisionsForPaper(this.paperFilter);
        console.log(`Found ${relatedDecisions.length} decisions for paper: ${this.paperFilter}`);
      }

      // Render the explorer panel
      this.explorer.loadPanel(contentEl);
    } catch (error) {
      console.error('Error initializing Decision Explorer Modal:', error);
      contentEl.createDiv().setText(`Error: ${error}`);
    }
  }

  /**
   * Clean up on close
   */
  onClose(): void {
    const { contentEl } = this;
    contentEl.empty();
  }
}
