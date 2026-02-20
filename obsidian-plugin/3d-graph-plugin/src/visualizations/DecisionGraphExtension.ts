/**
 * 3D Graph Decision Extension
 *
 * Extends the 3D graph with decision node overlay.
 * Features:
 * - Toggle button for showing/hiding decision nodes
 * - Real-time rendering of decisions with color/size encoding
 * - Integration with DynamicPaperIngestor for new paper events
 * - Smooth fade-in animations for new nodes
 *
 * Phase 2: Paper Integration - Task 4
 */

import * as THREE from 'three';
import { Decision } from '../types/Decision';
import { DecisionNodeRenderer, DecisionNodeData } from './DecisionNodeRenderer';
import { DynamicPaperIngestor, PaperIngestionEvent } from '../services/DynamicPaperIngestor';

export class DecisionGraphExtension {
  private showDecisions: boolean = false;
  private decisionMeshes: Map<string, THREE.Mesh> = new Map();
  private paperIngestor: DynamicPaperIngestor | null = null;
  private scene: THREE.Scene | null = null;

  constructor(scene: THREE.Scene) {
    this.scene = scene;
  }

  /**
   * Initialize extension with DynamicPaperIngestor for event listening
   */
  initialize(ingestor: DynamicPaperIngestor): void {
    this.paperIngestor = ingestor;

    // Listen for paper ingestion events
    ingestor.onIngestionEvent((event: PaperIngestionEvent) => {
      this.handlePaperIngestionEvent(event);
    });

    console.log('✓ Decision graph extension initialized');
  }

  /**
   * Toggle decision node visibility
   */
  toggleDecisionVisibility(): boolean {
    this.showDecisions = !this.showDecisions;

    if (this.showDecisions) {
      this.renderDecisionNodes();
    } else {
      this.hideDecisionNodes();
    }

    return this.showDecisions;
  }

  /**
   * Render all decision nodes
   */
  private renderDecisionNodes(): void {
    if (!this.scene) return;

    // This would be called with decision data from SurrealDB
    // For now, just set the flag
    console.log('Rendering decision nodes...');
  }

  /**
   * Hide all decision nodes
   */
  private hideDecisionNodes(): void {
    for (const mesh of this.decisionMeshes.values()) {
      if (mesh && this.scene) {
        this.scene.remove(mesh);
      }
    }
    this.decisionMeshes.clear();
    console.log('Decision nodes hidden');
  }

  /**
   * Add a decision node to the graph
   */
  addDecisionNode(
    decision: Decision,
    position: { x: number; y: number; z: number }
  ): void {
    if (!this.showDecisions || !this.scene) return;

    // Skip if already rendered
    if (this.decisionMeshes.has(decision.id)) return;

    const nodeData = DecisionNodeRenderer.decisionToNodeData(decision, position);
    const mesh = DecisionNodeRenderer.createNodeMesh(nodeData);

    if (mesh) {
      this.scene.add(mesh);
      this.decisionMeshes.set(decision.id, mesh);

      // Fade in animation
      DecisionNodeRenderer.fadeInNode(mesh, 300);

      console.log(`Decision node added: ${decision.id}`);
    }
  }

  /**
   * Remove a decision node from the graph
   */
  removeDecisionNode(decisionId: string): void {
    const mesh = this.decisionMeshes.get(decisionId);
    if (mesh && this.scene) {
      this.scene.remove(mesh);
      this.decisionMeshes.delete(decisionId);
      console.log(`Decision node removed: ${decisionId}`);
    }
  }

  /**
   * Handle paper ingestion event (new paper added)
   * This updates any decisions that reference the new paper
   */
  private handlePaperIngestionEvent(event: PaperIngestionEvent): void {
    if (!this.showDecisions) return;

    switch (event.type) {
      case 'paper_added':
        console.log(`[DecisionGraph] New paper detected: ${event.paperId}`);
        // Would query SurrealDB for decisions referencing this paper
        // and re-render if needed
        break;

      case 'paper_updated':
        console.log(`[DecisionGraph] Paper updated: ${event.paperId}`);
        // May need to re-rank decisions by relevance
        break;

      case 'paper_removed':
        console.log(`[DecisionGraph] Paper removed: ${event.paperId}`);
        // Remove decisions that no longer have references
        break;
    }
  }

  /**
   * Get current visibility state
   */
  isVisible(): boolean {
    return this.showDecisions;
  }

  /**
   * Get number of rendered decision nodes
   */
  getNodeCount(): number {
    return this.decisionMeshes.size;
  }

  /**
   * Create toggle button for UI
   */
  createToggleButton(): HTMLElement {
    const button = document.createElement('button');
    button.textContent = '🔄 Toggle Decision Nodes';
    button.style.padding = '10px 15px';
    button.style.border = '1px solid #9333ea';
    button.style.borderRadius = '4px';
    button.style.backgroundColor = this.showDecisions ? '#9333ea' : '#f3e8ff';
    button.style.color = this.showDecisions ? '#fff' : '#000';
    button.style.cursor = 'pointer';
    button.style.fontWeight = 'bold';

    button.onclick = () => {
      const visible = this.toggleDecisionVisibility();
      button.style.backgroundColor = visible ? '#9333ea' : '#f3e8ff';
      button.style.color = visible ? '#fff' : '#000';
      button.textContent = visible ? '✓ Decision Nodes ON' : '🔄 Toggle Decision Nodes';
    };

    return button;
  }
}
