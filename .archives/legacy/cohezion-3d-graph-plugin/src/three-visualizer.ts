/**
 * Three.js 3D visualization engine for Cohezion knowledge graph
 * Maps 8 dimensions to visual properties
 */

import * as THREE from 'three';
import { forceSimulation, forceLink, forceManyBody, forceCenter } from 'd3-force';
import { Paper, PaperDimensions } from './data-loader';

export class ThreeVisualizer {
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private renderer: THREE.WebGLRenderer;
  private nodes: Map<string, THREE.Object3D> = new Map();
  private links: THREE.LineSegments[] = [];
  private simulation: any;
  private animationId: number | null = null;
  private nodePositions: Map<string, { x: number; y: number; z: number }> = new Map();

  constructor(container: HTMLElement) {
    // Scene setup
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x1a1a1a);

    // Camera setup
    this.camera = new THREE.PerspectiveCamera(
      75,
      container.clientWidth / container.clientHeight,
      0.1,
      10000
    );
    this.camera.position.z = 100;

    // Renderer setup
    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setSize(container.clientWidth, container.clientHeight);
    this.renderer.setPixelRatio(window.devicePixelRatio);
    container.appendChild(this.renderer.domElement);

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    this.scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.6);
    directionalLight.position.set(100, 100, 100);
    this.scene.add(directionalLight);

    // Window resize handling
    window.addEventListener('resize', () => this.onWindowResize(container));

    // Start animation loop
    this.animate();
  }

  /**
   * Create nodes and links from papers data
   */
  loadGraph(papers: Paper[], connections: Map<string, string[]>): void {
    console.log('Creating visualization for', papers.length, 'papers...');

    // Create node objects
    const nodeData: any[] = [];
    const nodeMap: Map<string, number> = new Map();

    papers.forEach((paper, index) => {
      nodeData.push({
        id: paper.filename,
        paper: paper,
      });
      nodeMap.set(paper.filename, index);

      // Create mesh for node
      const geometry = new THREE.SphereGeometry(1, 32, 32);
      const color = this.getDimensionColor(paper.dimensions);
      const material = new THREE.MeshStandardMaterial({ color });
      const mesh = new THREE.Mesh(geometry, material);
      mesh.userData = { paper, connections: connections.get(paper.filename) || [] };

      this.nodes.set(paper.filename, mesh);
      this.scene.add(mesh);
    });

    // Create links
    const linkData: any[] = [];
    const addedLinks = new Set<string>();

    for (const [source, targets] of connections) {
      for (const target of targets) {
        const linkId = [source, target].sort().join('-');
        if (!addedLinks.has(linkId)) {
          linkData.push({
            source: nodeMap.get(source),
            target: nodeMap.get(target),
          });
          addedLinks.add(linkId);
        }
      }
    }

    // Setup D3 force simulation
    this.simulation = forceSimulation(nodeData)
      .force('link', forceLink(linkData)
        .id((d: any) => d.id)
        .distance(30)
      )
      .force('charge', forceManyBody().strength(-300))
      .force('center', forceCenter(0, 0));

    // Create visual links
    const geometry = new THREE.BufferGeometry();
    const positions: number[] = [];

    linkData.forEach((link: any) => {
      const source = nodeData[link.source];
      const target = nodeData[link.target];
      positions.push(source.x, source.y, source.z);
      positions.push(target.x, target.y, target.z);
    });

    geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(positions), 3));
    const material = new THREE.LineBasicMaterial({ color: 0x4488ff, transparent: true, opacity: 0.6 });
    const lines = new THREE.LineSegments(geometry, material);
    this.scene.add(lines);
    this.links.push(lines);

    console.log(`✅ Created graph with ${papers.length} nodes and ${addedLinks.size} edges`);
  }

  /**
   * Map paper dimensions to RGB color
   */
  private getDimensionColor(dimensions: PaperDimensions): number {
    const r = Math.min(255, Math.round((dimensions.connectivity || 0) * 255));
    const g = Math.min(255, Math.round((dimensions.completion || 0) * 255));
    const b = Math.min(255, Math.round((dimensions.conceptual_depth || 0) * 255));
    return (r << 16) | (g << 8) | b;
  }

  /**
   * Animation loop
   */
  private animate = (): void => {
    this.animationId = requestAnimationFrame(this.animate);

    // Update node positions from physics simulation
    if (this.simulation) {
      this.simulation.nodes().forEach((node: any, index: number) => {
        const nodeArray = Array.from(this.nodes.values());
        if (index < nodeArray.length) {
          const mesh = nodeArray[index];
          mesh.position.set(node.x || 0, node.y || 0, node.z || 0);
        }
      });

      // Update link positions
      if (this.simulation.force('link')) {
        const links = this.simulation.force('link').links();
        const positions: number[] = [];

        links.forEach((link: any) => {
          const source = this.simulation.nodes()[link.source];
          const target = this.simulation.nodes()[link.target];
          positions.push(source.x, source.y, source.z);
          positions.push(target.x, target.y, target.z);
        });

        if (this.links.length > 0) {
          this.links[0].geometry.setAttribute('position',
            new THREE.BufferAttribute(new Float32Array(positions), 3)
          );
        }
      }
    }

    this.renderer.render(this.scene, this.camera);
  };

  /**
   * Handle window resize
   */
  private onWindowResize(container: HTMLElement): void {
    const width = container.clientWidth;
    const height = container.clientHeight;

    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height);
  }

  /**
   * Cleanup
   */
  dispose(): void {
    if (this.animationId !== null) {
      cancelAnimationFrame(this.animationId);
    }
    this.renderer.dispose();
  }
}

export default ThreeVisualizer;
