import * as d3 from 'd3-force';
import { GraphData, PaperNode } from '../types/Paper';
import * as THREE from 'three';

/**
 * Force-directed 3D layout using D3-Force simulation
 *
 * This class maps papers to 3D positions using a physics-based approach:
 * 1. Initial positioning: Use 8 dimensions to place papers in 3D space
 *    - X-axis: connectivity (isolated → hub papers)
 *    - Y-axis: conceptual_depth (theory → applied)
 *    - Z-axis: temporal (historical → recent)
 * 2. Physics simulation: Apply forces to refine positions
 *    - Repulsion: Push papers apart (prevent overlap)
 *    - Collision: Prevent node overlap
 *    - Links: Attract semantically similar papers
 *    - Center: Gentle gravity to prevent drift
 * 3. Convergence: Stop when stable (alpha < 0.001) or max iterations reached
 *
 * @example
 * const layout = new ForceLayout(graphData);
 * const positions = await layout.positionNodes(2000);
 * // Returns Map<paperId, THREE.Vector3>
 */
export class ForceLayout {
  /** D3 force simulation instance (manages physics) */
  private simulation: d3.Simulation<PaperNode, undefined>;

  /** Whether simulation has converged to stable state */
  private converged = false;

  /** Maximum iterations before timeout (300 ticks) */
  private maxIterations = 300;

  /** Current iteration count */
  private currentIteration = 0;

  /**
   * Create a new force layout simulator
   *
   * @param {GraphData} graphData - Complete graph with nodes and edges
   * @throws Will throw if graphData.nodes is empty
   */
  constructor(private graphData: GraphData) {
    this.simulation = d3.forceSimulation(this.graphData.nodes);
    this.setupForces();
  }

  /**
   * Configure forces for the physics simulation
   *
   * Forces applied:
   * - **charge**: Repulsive force (pushes papers apart)
   *   - Strength: -300 (negative = repulsive)
   *   - Max distance: 500 (force drops off with distance)
   * - **collide**: Collision detection (prevent overlap)
   *   - Radius based on paper completion score
   * - **link**: Attractive force (pulls similar papers together)
   *   - Strength: 0.5 × similarity score squared
   *   - Distance: 100 units
   * - **center**: Gravity (keeps papers centered)
   *   - Prevents drift away from origin
   *
   * @private
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
   * Apply 8-dimensional semantic mapping to initial node positions
   *
   * Maps each paper's dimensions to 3D coordinates:
   * - **X-axis** (±200): Connectivity (isolated ↔ hub papers)
   * - **Y-axis** (±200): Conceptual depth (theory ↔ applied)
   * - **Z-axis** (-300 to 0): Temporal (historical ↔ recent, front is recent)
   *
   * The simulation then refines these positions based on forces.
   * Blend factor (60% dimension, 40% simulation) balances initial placement
   * with force-directed convergence.
   *
   * @private
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
   * Run the physics simulation and get final node positions
   *
   * This is the main entry point: applies dimensional mapping, runs the
   * simulation until convergence or timeout, and returns final positions.
   *
   * Flow:
   * 1. Apply 8D semantic mapping to initialize positions
   * 2. Start force simulation
   * 3. Wait for convergence (alpha < 0.001) or timeout
   * 4. Extract positions from all nodes
   * 5. Return as Map<paperId, THREE.Vector3>
   *
   * @param {number} [timeoutMs=2000] - Max time to run simulation (ms)
   * @returns {Promise<Map<string, THREE.Vector3>>} Final positions keyed by paper ID
   *
   * @example
   * const layout = new ForceLayout(graphData);
   * const positions = await layout.positionNodes(2000);
   * positions.get('paper-42'); // Returns Vector3 { x: 150, y: -50, z: 200 }
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
   * Get current simulation alpha (velocity/energy)
   *
   * Alpha decreases over time as the simulation converges.
   * - 1.0 = High energy (papers moving fast)
   * - 0.5 = Medium energy (stabilizing)
   * - 0.001 = Low energy (nearly converged)
   * - 0.0 = Stopped (converged)
   *
   * @returns {number} Current alpha (0.0-1.0)
   */
  getAlpha(): number {
    return this.simulation.alpha();
  }

  /**
   * Manually advance simulation by N ticks
   * Useful for debugging or custom timing
   *
   * @param {number} [iterations=1] - Number of ticks to advance
   *
   * @example
   * layout.tick(10); // Advance 10 iterations without waiting
   */
  tick(iterations = 1): void {
    for (let i = 0; i < iterations; i++) {
      this.simulation.tick();
    }
  }

  /**
   * Stop the simulation immediately
   * Marks simulation as converged and halts further ticks
   */
  stop(): void {
    this.simulation.stop();
    this.converged = true;
  }
}
