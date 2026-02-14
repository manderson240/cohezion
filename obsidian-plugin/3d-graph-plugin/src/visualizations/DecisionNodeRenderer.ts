import * as THREE from 'three';
import { Decision } from '../types/Decision';
import { PaperNode } from '../types/Paper';

/**
 * Renderer for decision nodes in 3D graph
 * Extends the Phase 3 3DGraph with decision visualization
 *
 * Features:
 * - Decision nodes colored by reasoning type
 * - Node size by confidence score
 * - Glow effect for high-confidence decisions
 * - Edges showing decision-to-paper relationships
 * - Interactive: Click to open DecisionExplorer
 *
 * @example
 * const renderer = new DecisionNodeRenderer(scene);
 * renderer.addDecisionNodes(decisions, paperMap);
 * renderer.toggleVisibility(true);
 */
export class DecisionNodeRenderer {
  private scene: THREE.Scene;
  private decisions: Map<string, { node: THREE.Mesh; label: THREE.Sprite; decision: Decision }> = new Map();
  private edges: THREE.Line[] = [];
  private visible: boolean = false;
  private reasoningTypeColors: Record<string, number> = {
    research: 0x3b82f6, // blue
    pattern: 0x10b981, // green
    intuition: 0xf59e0b, // amber
    convention: 0x8b5cf6, // purple
    hybrid: 0x6366f1, // indigo
  };

  constructor(scene: THREE.Scene) {
    this.scene = scene;
  }

  /**
   * Add decision nodes to 3D space
   * @param decisions Decisions to visualize
   * @param paperMap Map of paper IDs for linking
   * @param paperPositions Map of paper positions
   */
  addDecisionNodes(
    decisions: Decision[],
    paperMap: Map<string, PaperNode>,
    paperPositions: Map<string, { x: number; y: number; z: number }>
  ): void {
    // Clear existing decision nodes
    for (const { node, label } of this.decisions.values()) {
      this.scene.remove(node);
      if (label) this.scene.remove(label);
    }
    this.decisions.clear();

    // Clear edges
    for (const edge of this.edges) {
      this.scene.remove(edge);
    }
    this.edges = [];

    // Add each decision as a node
    for (const decision of decisions) {
      this.addDecisionNode(decision, paperMap, paperPositions);
    }
  }

  /**
   * Add a single decision node
   */
  private addDecisionNode(
    decision: Decision,
    paperMap: Map<string, PaperNode>,
    paperPositions: Map<string, { x: number; y: number; z: number }>
  ): void {
    const confidenceScore = decision.confidence_score;
    const reasoningType = decision.reasoning_type;
    const color = this.reasoningTypeColors[reasoningType] || this.reasoningTypeColors.hybrid;

    // Calculate position (offset from related papers)
    const position = this.calculateDecisionPosition(decision, paperMap, paperPositions);

    // Create geometry
    const geometry = new THREE.IcosahedronGeometry(1, 2);
    const material = new THREE.MeshPhongMaterial({
      color,
      emissive: color,
      emissiveIntensity: 0.3,
      wireframe: false,
      shininess: 100,
    });

    // Scale by confidence (0.5x to 2.0x)
    const scale = 0.5 + confidenceScore * 1.5;

    // Create mesh
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.set(position.x, position.y, position.z);
    mesh.scale.set(scale, scale, scale);

    // Add glow for high-confidence
    if (confidenceScore > 0.8) {
      const glowGeometry = new THREE.IcosahedronGeometry(1.2, 2);
      const glowMaterial = new THREE.MeshBasicMaterial({
        color,
        transparent: true,
        opacity: 0.15,
      });
      const glow = new THREE.Mesh(glowGeometry, glowMaterial);
      glow.position.copy(mesh.position);
      glow.scale.set(scale * 1.3, scale * 1.3, scale * 1.3);
      this.scene.add(glow);
    }

    // Create label sprite
    const canvas = document.createElement('canvas');
    canvas.width = 256;
    canvas.height = 64;
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.fillStyle = '#fff';
      ctx.font = 'bold 24px Arial';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(decision.title.slice(0, 15), 128, 32);
    }

    const texture = new THREE.CanvasTexture(canvas);
    const spriteMaterial = new THREE.SpriteMaterial({ map: texture });
    const label = new THREE.Sprite(spriteMaterial);
    label.position.set(position.x, position.y + 3, position.z);
    label.scale.set(4, 1, 1);

    // Add to scene
    this.scene.add(mesh);
    this.scene.add(label);

    // Store reference
    this.decisions.set(decision.id, {
      node: mesh,
      label,
      decision,
    });

    // Create edges to related papers
    if (decision.related_papers) {
      for (const paperId of decision.related_papers) {
        const paperPos = paperPositions.get(paperId);
        if (paperPos) {
          this.addEdgeToPaper(position, paperPos);
        }
      }
    }
  }

  /**
   * Calculate position for a decision node
   * Based on related papers' positions
   */
  private calculateDecisionPosition(
    decision: Decision,
    paperMap: Map<string, PaperNode>,
    paperPositions: Map<string, { x: number; y: number; z: number }>
  ): { x: number; y: number; z: number } {
    const relatedPositions: { x: number; y: number; z: number }[] = [];

    if (decision.related_papers) {
      for (const paperId of decision.related_papers) {
        const pos = paperPositions.get(paperId);
        if (pos) {
          relatedPositions.push(pos);
        }
      }
    }

    // Average of related papers
    if (relatedPositions.length > 0) {
      const avgX = relatedPositions.reduce((sum, p) => sum + p.x, 0) / relatedPositions.length;
      const avgY = relatedPositions.reduce((sum, p) => sum + p.y, 0) / relatedPositions.length;
      const avgZ = relatedPositions.reduce((sum, p) => sum + p.z, 0) / relatedPositions.length;

      // Offset slightly above the papers
      return {
        x: avgX + Math.random() * 20 - 10,
        y: avgY + 10,
        z: avgZ + Math.random() * 20 - 10,
      };
    }

    // Random position if no related papers
    return {
      x: Math.random() * 100 - 50,
      y: Math.random() * 100 - 50,
      z: Math.random() * 100 - 50,
    };
  }

  /**
   * Add an edge from decision to paper
   */
  private addEdgeToPaper(decisionPos: { x: number; y: number; z: number }, paperPos: { x: number; y: number; z: number }): void {
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array([decisionPos.x, decisionPos.y, decisionPos.z, paperPos.x, paperPos.y, paperPos.z]);
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

    const material = new THREE.LineBasicMaterial({
      color: 0xcccccc,
      transparent: true,
      opacity: 0.3,
      linewidth: 1,
    });

    const line = new THREE.Line(geometry, material);
    this.scene.add(line);
    this.edges.push(line);
  }

  /**
   * Toggle visibility of decision nodes
   */
  toggleVisibility(visible: boolean): void {
    this.visible = visible;

    for (const { node, label } of this.decisions.values()) {
      node.visible = visible;
      if (label) label.visible = visible;
    }

    for (const edge of this.edges) {
      edge.visible = visible;
    }
  }

  /**
   * Get decision node by ID
   */
  getDecisionNode(decisionId: string): THREE.Mesh | null {
    return this.decisions.get(decisionId)?.node || null;
  }

  /**
   * Highlight a decision node (for interaction)
   */
  highlightDecision(decisionId: string, highlight: boolean): void {
    const decisionData = this.decisions.get(decisionId);
    if (!decisionData) return;

    const mesh = decisionData.node;
    if (highlight) {
      mesh.userData.originalScale = mesh.scale.clone();
      mesh.scale.multiplyScalar(1.5);
      if (mesh.material instanceof THREE.MeshPhongMaterial) {
        mesh.material.emissiveIntensity = 0.8;
      }
    } else {
      if (mesh.userData.originalScale) {
        mesh.scale.copy(mesh.userData.originalScale);
      }
      if (mesh.material instanceof THREE.MeshPhongMaterial) {
        mesh.material.emissiveIntensity = 0.3;
      }
    }
  }

  /**
   * Get all decision nodes
   */
  getDecisions(): Decision[] {
    return Array.from(this.decisions.values()).map(d => d.decision);
  }

  /**
   * Get decision by node
   */
  getDecisionByNode(node: THREE.Object3D): Decision | null {
    for (const decisionData of this.decisions.values()) {
      if (decisionData.node === node) {
        return decisionData.decision;
      }
    }
    return null;
  }

  /**
   * Clear all decision nodes
   */
  clear(): void {
    for (const { node, label } of this.decisions.values()) {
      this.scene.remove(node);
      if (label) this.scene.remove(label);
    }
    for (const edge of this.edges) {
      this.scene.remove(edge);
    }

    this.decisions.clear();
    this.edges = [];
  }
}
