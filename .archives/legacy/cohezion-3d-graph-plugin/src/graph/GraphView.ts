/**
 * GraphView - 3D Graph Rendering with Three.js
 */

import * as THREE from 'three';
import { CameraController } from './CameraController';
import { DimensionMapper } from './DimensionMapper';
import { GraphData, GraphNode, GraphEdge, ProjectionConfig, PROJECTION_PRESETS, ProjectionPreset } from '../types';
import { App } from 'obsidian';

export class GraphView {
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private renderer: THREE.WebGLRenderer;
  private controls: CameraController;
  private graphData: GraphData;
  private app: App;

  private nodeObjects: Map<string, THREE.Mesh> = new Map();
  private edgeObjects: THREE.Line[] = [];
  private dimensionMapper: DimensionMapper;
  private animationSpeed: number = 1.0;

  private raycaster: THREE.Raycaster;
  private mouse: THREE.Vector2;
  private hoveredNode: THREE.Mesh | null = null;
  private tooltipElement: HTMLElement | null = null;

  constructor(container: HTMLElement, graphData: GraphData, app: App, defaultProjection: ProjectionPreset = 'temporal', animationSpeed: number = 1.0) {
    this.graphData = graphData;
    this.app = app;
    this.animationSpeed = animationSpeed;

    // Initialize dimension mapper
    this.dimensionMapper = new DimensionMapper(defaultProjection);
    
    // Initialize raycaster for mouse interaction
    this.raycaster = new THREE.Raycaster();
    this.mouse = new THREE.Vector2();
    
    // Create scene
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x1e1e1e);
    
    // Create camera
    this.camera = new THREE.PerspectiveCamera(
      75,
      container.clientWidth / container.clientHeight,
      0.1,
      1000
    );
    this.camera.position.set(50, 50, 50);
    this.camera.lookAt(0, 0, 0);
    
    // Create renderer
    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setSize(container.clientWidth, container.clientHeight);
    this.renderer.setPixelRatio(window.devicePixelRatio);
    container.appendChild(this.renderer.domElement);
    
    // Add camera controls
    this.controls = new CameraController(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.05;
    
    // Add lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    this.scene.add(ambientLight);
    
    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(10, 10, 10);
    this.scene.add(directionalLight);
    
    // Add grid helper
    const gridHelper = new THREE.GridHelper(100, 10, 0x444444, 0x222222);
    this.scene.add(gridHelper);
    
    // Create tooltip element
    this.createTooltipElement(container);
    
    // Add event listeners
    this.renderer.domElement.addEventListener('mousemove', this.onMouseMove.bind(this));
    this.renderer.domElement.addEventListener('click', this.onMouseClick.bind(this));
    window.addEventListener('resize', this.onWindowResize.bind(this));
    
    // Initial render
    this.renderGraph(this.currentProjection);
    this.animate();
  }
  
  /**
   * Create nodes and edges from graph data
   */
  renderGraph(projection: ProjectionPreset) {
    console.log(`[GraphView] Rendering ${this.graphData.nodes.length} nodes with projection: ${projection}`);

    const startTime = performance.now();

    // Clear existing geometry
    this.clearGraph();

    // Create nodes using dimension mapper
    this.createNodes(projection);

    // Create edges
    this.createEdges();

    const endTime = performance.now();
    console.log(`[GraphView] Rendered graph in ${(endTime - startTime).toFixed(2)}ms`);
  }
  
  /**
   * Create 3D mesh objects for nodes
   */
  private createNodes(projection: ProjectionPreset) {
    const geometry = new THREE.SphereGeometry(1, 16, 16);

    this.graphData.nodes.forEach((node: GraphNode) => {
      // Calculate position using dimension mapper
      const position = this.dimensionMapper.calculatePosition(node, projection);

      // Create material based on node type and conceptual depth
      const color = this.getNodeColor(node);
      const material = new THREE.MeshStandardMaterial({
        color: color,
        emissive: color,
        emissiveIntensity: 0.2,
      });

      // Create mesh
      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.set(position.x, position.y, position.z);

      // Scale based on completion
      const scale = 0.5 + (node.completion || 0) * 1.5;
      mesh.scale.set(scale, scale, scale);

      // Store node data in userData for interaction
      mesh.userData = { node };

      this.scene.add(mesh);
      this.nodeObjects.set(node.id, mesh);
    });
  }
  
  
  /**
   * Get node color based on conceptual depth and type
   */
  private getNodeColor(node: GraphNode): THREE.Color {
    // Use suggested color if available
    if (node.suggested_color) {
      return new THREE.Color(node.suggested_color);
    }
    
    // Fallback: gradient from red (theory) to blue (applied)
    const depth = node.conceptual_depth || 0.5;
    const r = depth;
    const g = 0.4;
    const b = 1 - depth;
    
    return new THREE.Color(r, g, b);
  }
  
  /**
   * Create lines for edges
   */
  private createEdges() {
    const material = new THREE.LineBasicMaterial({
      color: 0x444444,
      opacity: 0.3,
      transparent: true,
    });
    
    this.graphData.edges.forEach((edge: GraphEdge) => {
      const sourceNode = this.nodeObjects.get(edge.source);
      const targetNode = this.nodeObjects.get(edge.target);
      
      if (sourceNode && targetNode) {
        const points = [
          sourceNode.position,
          targetNode.position,
        ];
        
        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        const line = new THREE.Line(geometry, material);
        
        this.scene.add(line);
        this.edgeObjects.push(line);
      }
    });
  }
  
  /**
   * Clear all graph objects from scene
   */
  private clearGraph() {
    // Remove nodes
    this.nodeObjects.forEach((mesh) => {
      this.scene.remove(mesh);
      mesh.geometry.dispose();
      (mesh.material as THREE.Material).dispose();
    });
    this.nodeObjects.clear();
    
    // Remove edges
    this.edgeObjects.forEach((line) => {
      this.scene.remove(line);
      line.geometry.dispose();
      (line.material as THREE.Material).dispose();
    });
    this.edgeObjects = [];
  }
  
  /**
   * Create tooltip element for node hover
   */
  private createTooltipElement(container: HTMLElement) {
    this.tooltipElement = document.createElement('div');
    this.tooltipElement.style.position = 'absolute';
    this.tooltipElement.style.padding = '8px';
    this.tooltipElement.style.background = 'rgba(0, 0, 0, 0.8)';
    this.tooltipElement.style.color = '#fff';
    this.tooltipElement.style.borderRadius = '4px';
    this.tooltipElement.style.pointerEvents = 'none';
    this.tooltipElement.style.display = 'none';
    this.tooltipElement.style.zIndex = '1000';
    this.tooltipElement.style.fontSize = '12px';
    this.tooltipElement.style.maxWidth = '300px';
    container.appendChild(this.tooltipElement);
  }
  
  /**
   * Handle mouse move for hover effects
   */
  private onMouseMove(event: MouseEvent) {
    const rect = this.renderer.domElement.getBoundingClientRect();
    this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    
    // Raycast to find intersected nodes
    this.raycaster.setFromCamera(this.mouse, this.camera);
    const intersects = this.raycaster.intersectObjects(Array.from(this.nodeObjects.values()));
    
    if (intersects.length > 0) {
      const intersected = intersects[0].object as THREE.Mesh;
      
      if (this.hoveredNode !== intersected) {
        // Unhighlight previous node
        if (this.hoveredNode) {
          (this.hoveredNode.material as THREE.MeshStandardMaterial).emissiveIntensity = 0.2;
        }
        
        // Highlight new node
        this.hoveredNode = intersected;
        (intersected.material as THREE.MeshStandardMaterial).emissiveIntensity = 0.6;
        
        // Show tooltip
        const node = intersected.userData.node as GraphNode;
        this.showTooltip(node, event.clientX, event.clientY);
      }
    } else {
      // No intersection - hide tooltip
      if (this.hoveredNode) {
        (this.hoveredNode.material as THREE.MeshStandardMaterial).emissiveIntensity = 0.2;
        this.hoveredNode = null;
      }
      this.hideTooltip();
    }
  }
  
  /**
   * Handle mouse click to open note
   */
  private onMouseClick(event: MouseEvent) {
    if (this.hoveredNode) {
      const node = this.hoveredNode.userData.node as GraphNode;
      console.log(`[GraphView] Opening note: ${node.file_path}`);
      
      // Open note in Obsidian
      this.app.workspace.openLinkText(node.file_path, '', false);
    }
  }
  
  /**
   * Show tooltip with node information
   */
  private showTooltip(node: GraphNode, x: number, y: number) {
    if (!this.tooltipElement) return;
    
    this.tooltipElement.innerHTML = `
      <strong>${node.label}</strong><br/>
      Type: ${node.type}<br/>
      Connectivity: ${node.connectivity.toFixed(2)}<br/>
      Cross-Domain: ${node.cross_domain.toFixed(2)}<br/>
      Completion: ${(node.completion * 100).toFixed(0)}%<br/>
      Conceptual Depth: ${node.conceptual_depth.toFixed(2)}<br/>
      Links: ${node.wiki_links_count}
    `;
    
    this.tooltipElement.style.left = `${x + 10}px`;
    this.tooltipElement.style.top = `${y + 10}px`;
    this.tooltipElement.style.display = 'block';
  }
  
  /**
   * Hide tooltip
   */
  private hideTooltip() {
    if (this.tooltipElement) {
      this.tooltipElement.style.display = 'none';
    }
  }
  
  /**
   * Handle window resize
   */
  private onWindowResize() {
    const container = this.renderer.domElement.parentElement;
    if (!container) return;
    
    this.camera.aspect = container.clientWidth / container.clientHeight;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(container.clientWidth, container.clientHeight);
  }
  
  /**
   * Animation loop
   */
  private animate() {
    requestAnimationFrame(this.animate.bind(this));

    // Update camera controls
    this.controls.update();

    // Update projection transition animation if in progress
    if (this.dimensionMapper.isTransitionAnimating()) {
      this.dimensionMapper.updateTransition(this.nodeObjects, this.animationSpeed);
    }

    // Render scene
    this.renderer.render(this.scene, this.camera);
  }

  /**
   * Switch projection with animated transition
   */
  switchProjection(projection: ProjectionPreset) {
    console.log(`[GraphView] Switching to projection: ${projection}`);

    // Prepare animated transition
    this.dimensionMapper.prepareTransition(
      this.graphData.nodes,
      this.nodeObjects,
      projection
    );
  }
  
  /**
   * Cleanup resources
   */
  dispose() {
    this.clearGraph();
    this.controls.dispose();
    this.renderer.dispose();
    
    if (this.tooltipElement && this.tooltipElement.parentElement) {
      this.tooltipElement.parentElement.removeChild(this.tooltipElement);
    }
    
    this.renderer.domElement.removeEventListener('mousemove', this.onMouseMove.bind(this));
    this.renderer.domElement.removeEventListener('click', this.onMouseClick.bind(this));
    window.removeEventListener('resize', this.onWindowResize.bind(this));
  }
}
