import { Modal, App, Notice } from 'obsidian';
import * as THREE from 'three';
import { GraphData, PaperNode } from '../types/Paper';
import { ForceLayout } from '../physics/ForceLayout';
import { ThreeRenderer } from '../rendering/ThreeRenderer';
// TODO: Uncomment when UIManager is ready
// import { UIManager } from '../ui/UIManager';

/**
 * Camera controls for the 3D graph
 * Supports orbit, zoom, pan, and reset
 */
class GraphControls {
  private position = new THREE.Vector3();
  private target = new THREE.Vector3(0, 0, 0);
  private distance = 400;
  private theta = Math.PI * 0.5;
  private phi = Math.PI * 0.5;

  private isDragging = false;
  private previousMousePosition = { x: 0, y: 0 };

  private minDistance = 100;
  private maxDistance = 1500;

  constructor(
    private camera: THREE.PerspectiveCamera,
    private canvas: HTMLCanvasElement,
    private onUpdate?: () => void
  ) {
    this.setupEventListeners();
    this.updateCamera();
  }

  /**
   * Setup mouse and keyboard event listeners
   */
  private setupEventListeners(): void {
    // Mouse down
    this.canvas.addEventListener('mousedown', (e) => {
      if (e.button === 2) {
        // Right click for orbit
        this.isDragging = true;
        this.previousMousePosition = { x: e.clientX, y: e.clientY };
      }
    });

    // Mouse move
    this.canvas.addEventListener('mousemove', (e) => {
      if (this.isDragging) {
        const deltaX = e.clientX - this.previousMousePosition.x;
        const deltaY = e.clientY - this.previousMousePosition.y;

        this.theta -= deltaX * 0.01;
        this.phi -= deltaY * 0.01;

        this.phi = Math.max(0.1, Math.min(Math.PI - 0.1, this.phi));

        this.updateCamera();
        this.onUpdate?.();
      }
    });

    // Mouse up
    this.canvas.addEventListener('mouseup', () => {
      this.isDragging = false;
    });

    // Mouse leave
    this.canvas.addEventListener('mouseleave', () => {
      this.isDragging = false;
    });

    // Scroll for zoom
    this.canvas.addEventListener('wheel', (e) => {
      e.preventDefault();
      this.distance += e.deltaY * 0.5;
      this.distance = Math.max(this.minDistance, Math.min(this.maxDistance, this.distance));
      this.updateCamera();
      this.onUpdate?.();
    });

    // Keyboard controls
    window.addEventListener('keydown', (e) => {
      if (e.code === 'Space') {
        // Space to reset view
        this.reset();
        this.onUpdate?.();
      }
    });

    // Context menu prevention for right-click
    this.canvas.addEventListener('contextmenu', (e) => {
      e.preventDefault();
    });
  }

  /**
   * Update camera position based on spherical coordinates
   */
  private updateCamera(): void {
    this.position.x = this.target.x + this.distance * Math.sin(this.phi) * Math.cos(this.theta);
    this.position.y = this.target.y + this.distance * Math.cos(this.phi);
    this.position.z = this.target.z + this.distance * Math.sin(this.phi) * Math.sin(this.theta);

    this.camera.position.copy(this.position);
    this.camera.lookAt(this.target);
  }

  /**
   * Reset view to default
   */
  reset(): void {
    this.distance = 400;
    this.theta = Math.PI * 0.5;
    this.phi = Math.PI * 0.5;
    this.updateCamera();
  }

  /**
   * Set camera target
   */
  setTarget(target: THREE.Vector3): void {
    this.target.copy(target);
    this.updateCamera();
  }

  /**
   * Update method for external use
   */
  update(): void {
    this.updateCamera();
  }
}

/**
 * Main 3D Graph visualization modal
 * Renders 84 papers with force-directed layout and interactive controls
 */
export class Graph3D extends Modal {
  private graphData: GraphData | null = null;
  private renderer: ThreeRenderer | null = null;
  private layout: ForceLayout | null = null;
  private controls: GraphControls | null = null;

  private selectedPaper: PaperNode | null = null;
  private hoveredPaper: PaperNode | null = null;

  private isLoading = false;
  private frameCount = 0;
  private fps = 0;

  constructor(app: App) {
    super(app);
    this.modalEl.addClass('graph-3d-modal');
  }

  /**
   * Load graph data before showing
   */
  async loadGraphData(graphData: GraphData): Promise<void> {
    this.graphData = graphData;
    console.log(`Loaded graph with ${graphData.nodes.length} nodes and ${graphData.edges.length} edges`);
  }

  /**
   * Initialize the modal UI
   */
  onOpen(): void {
    const { contentEl, titleEl } = this;
    contentEl.empty();
    titleEl.setText('3D Paper Graph Visualization');

    // Create container for Three.js canvas
    const container = contentEl.createEl('div', { cls: 'graph-3d-container' });
    container.style.width = '100%';
    container.style.height = '100%';
    container.style.position = 'relative';

    // Initialize renderer
    const width = contentEl.clientWidth || window.innerWidth * 0.8;
    const height = contentEl.clientHeight || window.innerHeight * 0.8;

    this.renderer = new ThreeRenderer(container, width, height);

    // Load and position nodes
    if (this.graphData) {
      this.initializeGraph();
    }

    // Add UI overlay for info
    this.addUIOverlay(contentEl);

    // Setup interaction
    this.setupInteraction();
  }

  /**
   * Initialize graph rendering
   */
  private async initializeGraph(): Promise<void> {
    if (!this.graphData || !this.renderer) return;

    this.isLoading = true;
    new Notice('Computing layout...');

    // Run force-directed layout
    this.layout = new ForceLayout(this.graphData);
    const positions = await this.layout.positionNodes(2000);

    // Add nodes to scene
    this.renderer.addNodes(this.graphData, positions);

    // Add edges (top-5 per node)
    this.renderer.addEdges(this.graphData.edges, positions, 5);

    // Fit camera to view all nodes
    this.renderer.fitCamera(positions);

    // Start render loop
    this.renderer.startRenderLoop(this.controls);

    // Setup camera controls
    this.setupControls();

    this.isLoading = false;
    new Notice('3D Graph Ready!');

    console.log('Graph initialized and rendering');
  }

  /**
   * Setup camera controls
   */
  private setupControls(): void {
    if (!this.renderer) return;

    const canvas = this.renderer['canvas'] || document.querySelector('canvas');
    this.controls = new GraphControls(
      this.renderer['camera'],
      canvas as HTMLCanvasElement,
      () => {
        // Re-render on control changes
        if (this.renderer) {
          this.renderer['renderer'].render(this.renderer['scene'], this.renderer['camera']);
        }
      }
    );
  }

  /**
   * Setup mouse interaction (picking, highlighting)
   */
  private setupInteraction(): void {
    if (!this.renderer) return;

    const canvas = this.renderer['canvas'] || document.querySelector('canvas');

    canvas?.addEventListener('click', (e) => {
      const intersects = this.renderer!.getIntersectedObjects(e.clientX, e.clientY);

      if (intersects.length > 0) {
        const intersected = intersects[0].object as any;
        const paperId = intersected.paperId;

        if (paperId) {
          this.selectPaper(intersected.paperNode);
        }
      }
    });

    canvas?.addEventListener('mousemove', (e) => {
      const intersects = this.renderer!.getIntersectedObjects(e.clientX, e.clientY);

      // Clear previous hover
      if (this.hoveredPaper) {
        this.renderer!.highlightNode(this.hoveredPaper.id, false);
      }

      if (intersects.length > 0) {
        const intersected = intersects[0].object as any;
        if (intersected.paperNode) {
          this.hoveredPaper = intersected.paperNode;
          this.renderer!.highlightNode(this.hoveredPaper.id, true);
        }
      }
    });
  }

  /**
   * Select a paper and display info
   */
  private selectPaper(paper: PaperNode): void {
    if (this.selectedPaper?.id === paper.id) {
      // Deselect if clicking same paper
      if (this.renderer) {
        this.renderer.highlightNode(paper.id, false);
      }
      this.selectedPaper = null;
    } else {
      // Clear previous selection
      if (this.selectedPaper && this.renderer) {
        this.renderer.highlightNode(this.selectedPaper.id, false);
      }

      // Select new paper
      this.selectedPaper = paper;
      if (this.renderer) {
        this.renderer.highlightNode(paper.id, true);
      }

      // Show info
      this.showPaperInfo(paper);
    }
  }

  /**
   * Display selected paper information
   */
  private showPaperInfo(paper: PaperNode): void {
    const infoPanel = document.querySelector('.paper-info-panel') as HTMLElement;
    if (!infoPanel) return;

    let html = `
      <h3>${paper.title}</h3>
      <p><strong>ID:</strong> ${paper.id}</p>
    `;

    if (paper.authors) {
      html += `<p><strong>Authors:</strong> ${paper.authors.join(', ')}</p>`;
    }

    if (paper.year) {
      html += `<p><strong>Year:</strong> ${paper.year}</p>`;
    }

    html += `
      <h4>Dimensions</h4>
      <ul>
        <li>Connectivity: ${(paper.dimensions.connectivity * 100).toFixed(1)}%</li>
        <li>Conceptual Depth: ${(paper.dimensions.conceptual_depth * 100).toFixed(1)}%</li>
        <li>Temporal: ${(paper.dimensions.temporal * 100).toFixed(1)}%</li>
        <li>Completion: ${paper.dimensions.completion.toFixed(1)}%</li>
        <li>Recency: ${(paper.dimensions.recency * 100).toFixed(1)}%</li>
      </ul>
    `;

    infoPanel.innerHTML = html;
  }

  /**
   * Add UI overlay for info panel and stats
   */
  private addUIOverlay(container: HTMLElement): void {
    // Info panel
    const infoPanel = container.createEl('div', { cls: 'paper-info-panel' });
    infoPanel.style.position = 'absolute';
    infoPanel.style.top = '10px';
    infoPanel.style.right = '10px';
    infoPanel.style.width = '300px';
    infoPanel.style.background = 'rgba(0,0,0,0.8)';
    infoPanel.style.color = '#fff';
    infoPanel.style.padding = '15px';
    infoPanel.style.borderRadius = '5px';
    infoPanel.style.fontSize = '12px';
    infoPanel.style.maxHeight = '50vh';
    infoPanel.style.overflowY = 'auto';
    infoPanel.style.fontFamily = 'monospace';
    infoPanel.innerHTML = `
      <p>Click to select a paper</p>
      <p>Hover to highlight</p>
      <p>Right-drag to orbit</p>
      <p>Scroll to zoom</p>
      <p>Space to reset</p>
    `;

    // FPS counter
    const fpsCounter = container.createEl('div', { cls: 'fps-counter' });
    fpsCounter.style.position = 'absolute';
    fpsCounter.style.bottom = '10px';
    fpsCounter.style.left = '10px';
    fpsCounter.style.background = 'rgba(0,0,0,0.8)';
    fpsCounter.style.color = '#0f0';
    fpsCounter.style.padding = '10px';
    fpsCounter.style.borderRadius = '5px';
    fpsCounter.style.fontSize = '12px';
    fpsCounter.style.fontFamily = 'monospace';
    fpsCounter.innerHTML = 'FPS: 0';

    // Update FPS counter
    let lastTime = performance.now();
    const updateFPS = () => {
      const now = performance.now();
      const delta = now - lastTime;
      this.frameCount++;

      if (delta >= 1000) {
        this.fps = Math.round((this.frameCount * 1000) / delta);
        fpsCounter.innerHTML = `FPS: ${this.fps}`;
        this.frameCount = 0;
        lastTime = now;
      }

      requestAnimationFrame(updateFPS);
    };

    updateFPS();
  }

  /**
   * Clean up on modal close
   */
  onClose(): void {
    if (this.renderer) {
      this.renderer.dispose();
      this.renderer = null;
    }

    if (this.layout) {
      this.layout.stop();
      this.layout = null;
    }

    console.log('Graph3D modal closed');
  }
}
