import * as d3 from 'd3-force';
import { GraphData, PaperNode } from '../types/Paper';
import * as THREE from 'three';

/**
 * Force-directed 3D layout using D3-force
 * Maps 8 dimensions to 3D space for initial positioning
 */
export class ForceLayout {
  private simulation: d3.Simulation<PaperNode, undefined>;
  private converged = false;
  private maxIterations = 300;
  private currentIteration = 0;

  constructor(private graphData: GraphData) {
    this.simulation = d3.forceSimulation(this.graphData.nodes);
    this.setupForces();
  }

  /**
   * Configure forces for the simulation
   */
  private setupForces(): void {
    // Repulsive forces to spread nodes out
    this.simulation
      .force('charge', d3.forceManyBody().strength(-300).distanceMax(500))
      .force('collide', d3.forceCollide().radius((d: any) => Math.sqrt(d.dimensions.completion) * 1.5))
      .force('center', d3.forceCenter(0, 0));

    // Attractive forces for semantic neighbors (top-5 per paper)
    const links: any[] = [];
    const edgeMap = new Set<string>();

    for (const edge of this.graphData.edges) {
      const key = `${edge.source}-${edge.target}`;
      if (!edgeMap.has(key)) {
        links.push({
          source: edge.source,
          target: edge.target,
          strength: Math.pow(edge.similarity, 2),
        });
        edgeMap.add(key);
      }
    }

    this.simulation.force(
      'link',
      d3
        .forceLink(links)
        .id((d: any) => d.id)
        .strength((link: any) => link.strength * 0.5)
        .distance(100)
    );

    // Stop when converged or max iterations reached
    this.simulation.on('tick', () => {
      this.currentIteration++;
      if (this.simulation.alpha() < 0.001 || this.currentIteration >= this.maxIterations) {
        this.simulation.stop();
        this.converged = true;
      }
    });
  }

  /**
   * Apply 8-dimensional mapping to nodes for spatial distribution
   * X: connectivity (isolated → hubs)
   * Y: conceptual_depth (theory → applied)
   * Z: temporal (historical → recent)
   */
  private applyDimensionalMapping(): void {
    const padding = 100;

    for (const node of this.graphData.nodes) {
      if (!node.position) {
        node.position = { x: 0, y: 0, z: 0 };
      }

      // X-axis: connectivity (0-1 → -200 to 200)
      const xBase = (node.dimensions.connectivity - 0.5) * 400;

      // Y-axis: conceptual_depth (0-1 → -200 to 200)
      const yBase = (node.dimensions.conceptual_depth - 0.5) * 400;

      // Z-axis: temporal (0-1 → -300 to 0, front is recent)
      const zBase = (node.dimensions.temporal - 1) * 300;

      // Blend dimensional mapping with simulation positions
      const blend = 0.6;
      node.position.x = (xBase * (1 - blend) + (node.x || 0) * blend) + padding * Math.random() - padding / 2;
      node.position.y = (yBase * (1 - blend) + (node.y || 0) * blend) + padding * Math.random() - padding / 2;
      node.position.z = (zBase * (1 - blend) + (node.z || 0) * blend) + padding * Math.random() - padding / 2;
    }
  }

  /**
   * Run the simulation and return positioned nodes
   * @returns Promise<Map<string, THREE.Vector3>> with paper positions
   */
  async positionNodes(timeoutMs = 2000): Promise<Map<string, THREE.Vector3>> {
    return new Promise((resolve) => {
      // Apply initial dimensional mapping
      this.applyDimensionalMapping();

      // Run simulation with timeout
      const timeoutHandle = setTimeout(() => {
        this.simulation.stop();
        this.converged = true;
      }, timeoutMs);

      // Track when simulation finishes
      const checkConvergence = () => {
        if (this.converged) {
          clearTimeout(timeoutHandle);
          const positions = new Map<string, THREE.Vector3>();

          for (const node of this.graphData.nodes) {
            if (node.position) {
              positions.set(
                node.id,
                new THREE.Vector3(node.position.x, node.position.y, node.position.z)
              );
            }
          }

          resolve(positions);
        } else {
          requestAnimationFrame(checkConvergence);
        }
      };

      checkConvergence();
    });
  }

  /**
   * Get current simulation alpha (velocity, 0-1)
   */
  getAlpha(): number {
    return this.simulation.alpha();
  }

  /**
   * Manually advance simulation by N ticks
   */
  tick(iterations = 1): void {
    for (let i = 0; i < iterations; i++) {
      this.simulation.tick();
    }
  }

  /**
   * Stop the simulation
   */
  stop(): void {
    this.simulation.stop();
    this.converged = true;
  }
}
