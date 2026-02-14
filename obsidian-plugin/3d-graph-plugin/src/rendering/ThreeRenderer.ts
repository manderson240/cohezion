import * as THREE from 'three';
import { GraphData, PaperNode, GraphEdge } from '../types/Paper';

/**
 * Three.js WebGL renderer setup for 3D graph visualization
 * Manages scene, camera, lights, and rendering loop
 */
export class ThreeRenderer {
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private renderer: THREE.WebGLRenderer;
  private canvas: HTMLCanvasElement;
  private container: HTMLElement;

  private nodeGeometry: THREE.BufferGeometry;
  private nodeMaterial: THREE.MeshPhongMaterial;
  private lineMaterial: THREE.LineBasicMaterial;

  private nodeObjects: Map<string, THREE.Mesh> = new Map();
  private edgeLines: Map<string, THREE.LineSegments> = new Map();

  private raycaster: THREE.Raycaster;
  private mouse: THREE.Vector2;

  private animationFrameId: number | null = null;
  private isDisposed = false;

  constructor(container: HTMLElement, width: number, height: number) {
    this.container = container;

    // Scene setup
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x1a1a1a);
    this.scene.fog = new THREE.Fog(0x1a1a1a, 2000, 3500);

    // Camera setup (perspective, responsive)
    this.camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 10000);
    this.camera.position.set(0, 100, 200);
    this.camera.lookAt(0, 0, 0);

    // Renderer setup
    this.renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      preserveDrawingBuffer: true,
    });
    this.renderer.setSize(width, height);
    this.renderer.setPixelRatio(window.devicePixelRatio);
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFShadowMap;

    this.canvas = this.renderer.domElement;
    container.appendChild(this.canvas);

    // Lighting
    this.setupLights();

    // Raycasting for interaction
    this.raycaster = new THREE.Raycaster();
    this.mouse = new THREE.Vector2();

    // Create reusable materials
    this.nodeGeometry = new THREE.SphereGeometry(1, 32, 32);
    this.nodeMaterial = new THREE.MeshPhongMaterial({
      emissive: 0x111111,
      shininess: 100,
    });
    this.lineMaterial = new THREE.LineBasicMaterial({
      color: 0x888888,
      linewidth: 1,
      fog: true,
    });

    // Handle window resize
    window.addEventListener('resize', () => this.onWindowResize());

    console.log('ThreeRenderer initialized');
  }

  /**
   * Setup directional and ambient lighting for depth perception
   */
  private setupLights(): void {
    // Directional light (sun)
    const directional = new THREE.DirectionalLight(0xffffff, 0.8);
    directional.position.set(500, 500, 300);
    directional.castShadow = true;
    directional.shadow.mapSize.width = 2048;
    directional.shadow.mapSize.height = 2048;
    directional.shadow.camera.left = -1000;
    directional.shadow.camera.right = 1000;
    directional.shadow.camera.top = 1000;
    directional.shadow.camera.bottom = -1000;
    this.scene.add(directional);

    // Ambient light
    const ambient = new THREE.AmbientLight(0xffffff, 0.5);
    this.scene.add(ambient);

    // Hemisphere light for additional depth
    const hemisphere = new THREE.HemisphereLight(0x8899ff, 0xff8844, 0.3);
    this.scene.add(hemisphere);
  }

  /**
   * Add paper nodes to the scene
   */
  addNodes(graphData: GraphData, positions: Map<string, THREE.Vector3>, colorPalette?: string[]): void {
    const palette = colorPalette || this.generateColorPalette(10);

    for (const node of graphData.nodes) {
      const position = positions.get(node.id);
      if (!position) continue;

      // Calculate size based on completion (0.5x - 2.0x)
      const size = 0.5 + (node.dimensions.completion / 100) * 1.5;

      // Calculate opacity based on recency (30%-100%)
      const opacity = 0.3 + node.dimensions.recency * 0.7;

      // Get color from domain clustering (hue)
      const hueIndex = (node.dimensions.cross_domain - 1) % palette.length;
      const color = new THREE.Color(palette[hueIndex]);

      // Create mesh
      const mesh = new THREE.Mesh(this.nodeGeometry, this.nodeMaterial.clone());
      mesh.scale.set(size, size, size);
      mesh.position.copy(position);
      mesh.castShadow = true;
      mesh.receiveShadow = true;

      // Apply color and opacity
      (mesh.material as THREE.MeshPhongMaterial).color = color;
      (mesh.material as THREE.MeshPhongMaterial).transparent = true;
      (mesh.material as THREE.MeshPhongMaterial).opacity = opacity;

      // Store metadata for picking
      (mesh as any).paperId = node.id;
      (mesh as any).paperNode = node;

      this.scene.add(mesh);
      this.nodeObjects.set(node.id, mesh);
    }

    console.log(`Added ${graphData.nodes.length} nodes`);
  }

  /**
   * Add edges (semantic connections) to the scene
   */
  addEdges(
    edges: GraphEdge[],
    positions: Map<string, THREE.Vector3>,
    maxEdgesPerNode = 5,
    colorPalette?: string[]
  ): void {
    const palette = colorPalette || this.generateColorPalette(10);
    const nodeEdgeCount = new Map<string, number>();

    // Limit edges per node for clarity
    for (const edge of edges) {
      const sourceCount = nodeEdgeCount.get(edge.source) || 0;
      const targetCount = nodeEdgeCount.get(edge.target) || 0;

      if (sourceCount >= maxEdgesPerNode || targetCount >= maxEdgesPerNode) {
        continue; // Skip this edge to maintain limit
      }

      const sourcePos = positions.get(edge.source);
      const targetPos = positions.get(edge.target);

      if (!sourcePos || !targetPos) continue;

      // Create line geometry
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute('position', new THREE.BufferAttribute(
        new Float32Array([sourcePos.x, sourcePos.y, sourcePos.z, targetPos.x, targetPos.y, targetPos.z]),
        3
      ));

      // Width proportional to similarity
      const width = Math.max(1, edge.similarity * 3);

      // Color as average hue of endpoints
      const material = new THREE.LineBasicMaterial({
        color: 0x666666,
        linewidth: width,
        fog: true,
      });

      const line = new THREE.LineSegments(geometry, material);
      this.scene.add(line);

      // Track edge
      const edgeKey = `${edge.source}-${edge.target}`;
      this.edgeLines.set(edgeKey, line);

      // Increment counters
      nodeEdgeCount.set(edge.source, sourceCount + 1);
      nodeEdgeCount.set(edge.target, targetCount + 1);
    }

    console.log(`Added ${this.edgeLines.size} edges`);
  }

  /**
   * Auto-fit camera to show all nodes
   */
  fitCamera(positions: Map<string, THREE.Vector3>): void {
    if (positions.size === 0) return;

    const box = new THREE.Box3();
    for (const [, pos] of positions) {
      box.expandByPoint(pos);
    }

    const size = box.getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z);
    const fov = this.camera.fov * (Math.PI / 180); // Convert to radians
    let cameraZ = Math.abs(maxDim / 2 / Math.tan(fov / 2));

    cameraZ *= 1.5; // Add padding

    const center = box.getCenter(new THREE.Vector3());
    this.camera.position.set(center.x, center.y + maxDim * 0.3, center.z + cameraZ);
    this.camera.lookAt(center);
    this.camera.updateProjectionMatrix();
  }

  /**
   * Start the render loop
   */
  startRenderLoop(controls: any): void {
    const animate = () => {
      this.animationFrameId = requestAnimationFrame(animate);

      if (controls) {
        controls.update();
      }

      this.renderer.render(this.scene, this.camera);
    };

    animate();
  }

  /**
   * Stop the render loop
   */
  stopRenderLoop(): void {
    if (this.animationFrameId !== null) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }
  }

  /**
   * Get raycaster for picking
   */
  getRaycaster(): THREE.Raycaster {
    return this.raycaster;
  }

  /**
   * Get intersected objects at mouse position
   */
  getIntersectedObjects(clientX: number, clientY: number): THREE.Intersection[] {
    const rect = this.canvas.getBoundingClientRect();
    this.mouse.x = ((clientX - rect.left) / rect.width) * 2 - 1;
    this.mouse.y = -((clientY - rect.top) / rect.height) * 2 + 1;

    this.raycaster.setFromCamera(this.mouse, this.camera);
    return this.raycaster.intersectObjects(Array.from(this.nodeObjects.values()), false);
  }

  /**
   * Highlight a node with glow effect
   */
  highlightNode(paperId: string, enabled: boolean = true): void {
    const mesh = this.nodeObjects.get(paperId);
    if (!mesh) return;

    if (enabled) {
      const material = mesh.material as THREE.MeshPhongMaterial;
      material.emissive.setHex(0x4488ff);
      material.emissiveIntensity = 0.8;
    } else {
      const material = mesh.material as THREE.MeshPhongMaterial;
      material.emissive.setHex(0x111111);
      material.emissiveIntensity = 0;
    }
  }

  /**
   * Get a paper node by ID
   */
  getNodeObject(paperId: string): THREE.Mesh | undefined {
    return this.nodeObjects.get(paperId);
  }

  /**
   * Handle window resize
   */
  private onWindowResize(): void {
    const width = this.container.clientWidth;
    const height = this.container.clientHeight;

    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height);
  }

  /**
   * Generate a color palette for domain clustering
   */
  private generateColorPalette(count: number): string[] {
    const palette: string[] = [];
    for (let i = 0; i < count; i++) {
      const hue = (i / count) * 360;
      palette.push(`hsl(${hue}, 100%, 50%)`);
    }
    return palette;
  }

  /**
   * Dispose of resources
   */
  dispose(): void {
    if (this.isDisposed) return;

    this.stopRenderLoop();
    this.nodeGeometry.dispose();
    this.nodeMaterial.dispose();
    this.lineMaterial.dispose();

    for (const mesh of this.nodeObjects.values()) {
      (mesh.material as THREE.Material).dispose();
      mesh.geometry.dispose();
    }

    for (const line of this.edgeLines.values()) {
      (line.material as THREE.Material).dispose();
      line.geometry.dispose();
    }

    this.renderer.dispose();
    this.canvas.remove();
    this.isDisposed = true;

    console.log('ThreeRenderer disposed');
  }
}
