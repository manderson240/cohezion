/**
 * Decision Node Renderer for 3D Graph
 *
 * Renders decision nodes in 3D space with visual encoding:
 * - Color: reasoning_type (research=blue, pattern=green, intuition=purple, etc.)
 * - Size: confidence_score (0.5x-2.0x scale)
 * - Glow: high-confidence decisions (>0.8) get stronger glow effect
 *
 * Phase 2: Paper Integration - Task 4
 */

import * as THREE from 'three';
import { Decision } from '../types/Decision';

export interface DecisionNodeData {
  id: string;
  decision: Decision;
  position: { x: number; y: number; z: number };
  color: number;
  size: number;
  opacity: number;
  glowIntensity: number;
}

export class DecisionNodeRenderer {
  static decisionToNodeData(
    decision: Decision,
    position: { x: number; y: number; z: number }
  ): DecisionNodeData {
    return {
      id: decision.id,
      decision,
      position,
      color: this.getColorByReasoningType(decision.reasoning_type),
      size: this.getSizeByConfidence(decision.confidence_score),
      opacity: this.getOpacityByConfidence(decision.confidence_score),
      glowIntensity: Math.max(0, decision.confidence_score - 0.5),
    };
  }

  private static getColorByReasoningType(type: string): number {
    const colors: Record<string, number> = {
      research: 240,
      pattern: 120,
      intuition: 280,
      convention: 30,
      hybrid: 60,
    };
    return colors[type] || 240;
  }

  private static getSizeByConfidence(confidence: number): number {
    return 0.5 + confidence * 1.5;
  }

  private static getOpacityByConfidence(confidence: number): number {
    return 0.3 + confidence * 0.7;
  }

  private static hslToRgb(h: number, s: number, l: number): { r: number; g: number; b: number } {
    let r, g, b;
    if (s === 0) {
      r = g = b = l;
    } else {
      const hue2rgb = (p: number, q: number, t: number) => {
        if (t < 0) t += 1;
        if (t > 1) t -= 1;
        if (t < 1 / 6) return p + (q - p) * 6 * t;
        if (t < 1 / 2) return q;
        if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
        return p;
      };
      const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
      const p = 2 * l - q;
      r = hue2rgb(p, q, h + 1 / 3);
      g = hue2rgb(p, q, h);
      b = hue2rgb(p, q, h - 1 / 3);
    }
    return {
      r: Math.round(r * 255),
      g: Math.round(g * 255),
      b: Math.round(b * 255),
    };
  }

  private static rgbToHex(r: number, g: number, b: number): number {
    return (r << 16) | (g << 8) | b;
  }

  static createNodeMesh(nodeData: DecisionNodeData): THREE.Mesh | null {
    const geometry = new THREE.SphereGeometry(8, 16, 16);
    const rgb = this.hslToRgb(nodeData.color / 360, 0.6, 0.5);
    const hexColor = this.rgbToHex(rgb.r, rgb.g, rgb.b);

    const material = new THREE.MeshStandardMaterial({
      color: hexColor,
      emissive: nodeData.glowIntensity > 0.5 ? hexColor : 0x000000,
      emissiveIntensity: nodeData.glowIntensity,
      metalness: 0.3,
      roughness: 0.4,
      transparent: nodeData.opacity < 1.0,
      opacity: nodeData.opacity,
    });

    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.set(nodeData.position.x, nodeData.position.y, nodeData.position.z);
    mesh.scale.set(nodeData.size, nodeData.size, nodeData.size);

    // Store decision metadata using THREE's userData property
    interface DecisionUserData {
      type: 'decision';
      decisionId: string;
      decision: Decision;
    }
    (mesh.userData as unknown as DecisionUserData) = {
      type: 'decision',
      decisionId: nodeData.id,
      decision: nodeData.decision,
    };

    return mesh;
  }

  static fadeInNode(mesh: THREE.Mesh, duration: number = 300): Promise<void> {
    return new Promise((resolve) => {
      const startTime = performance.now();
      const material = mesh.material as THREE.MeshStandardMaterial;
      const startOpacity = material.opacity || 0;

      const animate = (currentTime: number) => {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        material.opacity = startOpacity + (1 - startOpacity) * progress;
        if (progress < 1) {
          requestAnimationFrame(animate);
        } else {
          resolve();
        }
      };
      requestAnimationFrame(animate);
    });
  }
}
