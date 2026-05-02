/**
 * DimensionMapper - Maps 12D graph data to 3D projections
 * Implements multiple projection presets and smooth transitions
 */

import { GraphNode, ProjectionPreset, ProjectionConfig, PROJECTION_PRESETS } from '../types';
import * as THREE from 'three';

export class DimensionMapper {
  private currentProjection: ProjectionPreset;
  private animationProgress = 0;
  private isAnimating = false;
  
  private sourcePositions: Map<string, THREE.Vector3> = new Map();
  private targetPositions: Map<string, THREE.Vector3> = new Map();
  
  constructor(defaultProjection: ProjectionPreset = 'temporal') {
    this.currentProjection = defaultProjection;
  }
  
  /**
   * Calculate 3D position for a node based on projection preset
   */
  calculatePosition(node: GraphNode, projection: ProjectionPreset): THREE.Vector3 {
    const config = PROJECTION_PRESETS[projection];
    
    // Extract dimensional values
    const xValue = this.getDimensionValue(node, config.xAxis);
    const yValue = this.getDimensionValue(node, config.yAxis);
    const zValue = this.getDimensionValue(node, config.zAxis);
    
    // Scale to world coordinates (spread nodes across space)
    const scale = 50;
    return new THREE.Vector3(
      (xValue - 0.5) * scale,
      (yValue - 0.5) * scale,
      (zValue - 0.5) * scale
    );
  }
  
  /**
   * Get dimensional value from node, with fallback to 0.5
   */
  private getDimensionValue(node: GraphNode, dimension: keyof GraphNode): number {
    const value = node[dimension];
    
    if (typeof value === 'number') {
      return value;
    }
    
    // Fallback for undefined dimensions
    return 0.5;
  }
  
  /**
   * Prepare for animated transition to new projection
   */
  prepareTransition(
    nodes: GraphNode[],
    nodeObjects: Map<string, THREE.Mesh>,
    targetProjection: ProjectionPreset
  ) {
    // Store current positions as source
    this.sourcePositions.clear();
    nodeObjects.forEach((mesh, nodeId) => {
      this.sourcePositions.set(nodeId, mesh.position.clone());
    });
    
    // Calculate target positions
    this.targetPositions.clear();
    nodes.forEach((node) => {
      const targetPos = this.calculatePosition(node, targetProjection);
      this.targetPositions.set(node.id, targetPos);
    });
    
    this.currentProjection = targetProjection;
    this.animationProgress = 0;
    this.isAnimating = true;
  }
  
  /**
   * Update animation frame for projection transition
   * Returns true if animation is still in progress
   */
  updateTransition(nodeObjects: Map<string, THREE.Mesh>, animationSpeed: number = 1.0): boolean {
    if (!this.isAnimating) return false;
    
    this.animationProgress += 0.02 * animationSpeed;
    
    if (this.animationProgress >= 1.0) {
      this.animationProgress = 1.0;
      this.isAnimating = false;
    }
    
    // Ease-in-out interpolation
    const t = this.easeInOutCubic(this.animationProgress);
    
    // Interpolate all node positions
    nodeObjects.forEach((mesh, nodeId) => {
      const source = this.sourcePositions.get(nodeId);
      const target = this.targetPositions.get(nodeId);
      
      if (source && target) {
        mesh.position.lerpVectors(source, target, t);
      }
    });
    
    return this.isAnimating;
  }
  
  /**
   * Ease-in-out cubic easing function
   */
  private easeInOutCubic(t: number): number {
    return t < 0.5
      ? 4 * t * t * t
      : 1 - Math.pow(-2 * t + 2, 3) / 2;
  }
  
  /**
   * Get current projection
   */
  getCurrentProjection(): ProjectionPreset {
    return this.currentProjection;
  }
  
  /**
   * Check if animation is in progress
   */
  isTransitionAnimating(): boolean {
    return this.isAnimating;
  }
  
  /**
   * Get dimension info for current projection
   */
  getCurrentDimensionInfo(): ProjectionConfig {
    return PROJECTION_PRESETS[this.currentProjection];
  }
  
  /**
   * Get all available projections
   */
  getAvailableProjections(): Array<{ key: ProjectionPreset; config: ProjectionConfig }> {
    return Object.entries(PROJECTION_PRESETS).map(([key, config]) => ({
      key: key as ProjectionPreset,
      config,
    }));
  }
}
