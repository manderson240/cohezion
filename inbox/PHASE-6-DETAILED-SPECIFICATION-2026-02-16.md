---
title: "Phase 6 Detailed Design Specification"
date: 2026-02-16
status: approved
type: design-specification
phase: 6
estimated_loc: 600
estimated_tests: 30
target_coverage: 80%
tags: [phase-6, visualization, 3d-graph, animations, dashboard, design-spec]
---

# Phase 6 Detailed Design Specification

## Overview

**Phase 6** delivers advanced 3D decision graph visualization with real-time cascade analysis, confidence heatmaps, and interactive timeline exploration.

- **Duration**: 2 weeks (2026-03-09 to 2026-03-22)
- **Deliverables**: 600+ LOC, 30+ tests, 80%+ coverage
- **Teams**: data-graph-specialist (3D rendering), observability-specialist (streaming), integration-engineer (API integration)
- **Technologies**: Three.js, Babylon.js, D3.js, WebGL, Server-Sent Events (SSE)

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    VISUALIZATION CLIENT                     │
├──────────────────────┬──────────────────────────────────────┤
│  3D Graph Renderer   │  Timeline & Controls                 │
│  (WebGL, Three.js)   │  (D3.js, React)                      │
└──────────────────────┼──────────────────────────────────────┘
                       │ WebSocket/SSE
┌──────────────────────┴──────────────────────────────────────┐
│                   STREAMING SERVER                          │
├──────────────────────┬──────────────────────────────────────┤
│  Server-Sent Events  │  Real-time Graph Updates            │
│  (SSE connections)   │  (WebSocket fallback)               │
└──────────────────────┼──────────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────────┐
│                   VISUALIZATION ENGINE                      │
├──────────────────┬─────────────────┬──────────────────┬─────┤
│ Layout Algorithm │ Confidence      │ Cascade          │ Anim│
│ (Sugiyama)       │ Heatmap Overlay │ Propagation      │ Sys │
└──────────────────┼─────────────────┼──────────────────┼─────┘
                   │
┌───────────────────┴──────────────────────────────────────────┐
│                   DATA LAYER                                 │
├───────────────────┬──────────────────┬──────────────────────┤
│ Decision Graph    │ Confidence Data  │ Score History      │
│ (from Phase 4A)   │ (from Phase 5)   │ (from Phase 5)     │
└───────────────────┴──────────────────┴──────────────────────┘
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **3D Rendering** | Three.js 0.160+ | WebGL-based 3D graph |
| **GPU Optimization** | Babylon.js (alt) | Hardware acceleration |
| **2D Overlay** | D3.js 7.0+ | Timeline, legend, controls |
| **Real-time Updates** | SSE / WebSocket | Live graph streaming |
| **State Management** | Zustand | Visualization state |
| **Layout Algorithm** | Sugiyama (hierarchical) | Graph positioning |
| **Collision Detection** | Cannon.js (optional) | Physics-based layout |
| **Performance** | OffscreenCanvas | Worker-thread rendering |

---

## 6.1: 3D Graph Rendering Engine

### Graph Representation

**Data Structure (From Phase 4A decision graph):**

```typescript
interface DecisionNode {
  id: string;
  title: string;
  description: string;
  status: 'pending' | 'active' | 'resolved' | 'archived';
  confidence: number;  // From Phase 5 ML scoring
  uncertainty: number;
  priority: 'low' | 'medium' | 'high';
  created_at: Date;
  updated_at: Date;
}

interface DecisionEdge {
  source: string;  // decision id
  target: string;  // decision id
  relationship: 'depends_on' | 'blocks' | 'enables' | 'conflicts';
  strength: number; // 0-1, impact magnitude
  impact_type: 'positive' | 'negative' | 'neutral';
}

interface DecisionGraph {
  nodes: DecisionNode[];
  edges: DecisionEdge[];
  lastUpdated: Date;
  version: number;
}
```

### Three.js Scene Setup

**Core Visualization Component (3DGraphRenderer.tsx):**

```typescript
import * as THREE from 'three';
import { DecisionNode, DecisionEdge, DecisionGraph } from './types';

class ThreeDGraphRenderer {
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private renderer: THREE.WebGLRenderer;
  private graph: DecisionGraph;
  private nodeObjects: Map<string, THREE.Mesh> = new Map();
  private edgeObjects: Map<string, THREE.Line> = new Map();
  private animationFrame: number | null = null;

  constructor(container: HTMLElement) {
    // Scene setup
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x0a0e27);
    this.scene.fog = new THREE.FogExp2(0x0a0e27, 0.0008);

    // Camera setup
    const width = container.clientWidth;
    const height = container.clientHeight;
    this.camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
    this.camera.position.set(0, 0, 100);

    // Renderer setup
    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setSize(width, height);
    this.renderer.setPixelRatio(window.devicePixelRatio);
    container.appendChild(this.renderer.domElement);

    // Lighting
    this.setupLighting();

    // Event listeners
    window.addEventListener('resize', () => this.onWindowResize());
    this.animationFrame = requestAnimationFrame(() => this.animate());
  }

  private setupLighting() {
    // Ambient light
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    this.scene.add(ambientLight);

    // Directional light (decision importance)
    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(50, 50, 50);
    directionalLight.castShadow = true;
    this.scene.add(directionalLight);

    // Point lights at key nodes
    const pointLight = new THREE.PointLight(0x00ff88, 0.5);
    pointLight.position.set(0, 0, 50);
    this.scene.add(pointLight);
  }

  async loadGraph(graph: DecisionGraph) {
    this.graph = graph;

    // Clear existing objects
    this.nodeObjects.forEach(mesh => this.scene.remove(mesh));
    this.edgeObjects.forEach(line => this.scene.remove(line));
    this.nodeObjects.clear();
    this.edgeObjects.clear();

    // Calculate layout
    const layout = await this.calculateLayout(graph);

    // Create node meshes
    for (const node of graph.nodes) {
      const mesh = this.createNodeMesh(node, layout[node.id]);
      this.scene.add(mesh);
      this.nodeObjects.set(node.id, mesh);
    }

    // Create edge lines
    for (const edge of graph.edges) {
      const line = this.createEdgeLine(edge, layout);
      this.scene.add(line);
      this.edgeObjects.set(`${edge.source}-${edge.target}`, line);
    }

    // Auto-fit camera
    this.fitCameraToGraph();
  }

  private createNodeMesh(node: DecisionNode, position: THREE.Vector3): THREE.Mesh {
    // Node sphere with confidence-based color
    const geometry = new THREE.SphereGeometry(5, 32, 32);
    const color = this.confidenceToColor(node.confidence);
    const material = new THREE.MeshStandardMaterial({
      color: color,
      emissive: color,
      emissiveIntensity: 0.5,
      roughness: 0.4,
      metalness: 0.6
    });

    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.copy(position);
    mesh.userData = { nodeId: node.id, node: node };

    // Size by priority
    const priorityScale = {
      'low': 1.0,
      'medium': 1.5,
      'high': 2.0
    };
    mesh.scale.setScalar(priorityScale[node.priority]);

    // Outline for selection
    const outlineGeometry = new THREE.SphereGeometry(5.5, 32, 32);
    const outlineMaterial = new THREE.LineBasicMaterial({
      color: 0xffffff,
      linewidth: 2
    });
    const outlineWireframe = new THREE.LineSegments(outlineGeometry, outlineMaterial);
    mesh.add(outlineWireframe);

    return mesh;
  }

  private createEdgeLine(edge: DecisionEdge, layout: Record<string, THREE.Vector3>): THREE.Line {
    const points = [
      layout[edge.source],
      layout[edge.target]
    ];

    const geometry = new THREE.BufferGeometry().setFromPoints(points);

    // Color and width by impact type
    const colorMap = {
      'positive': 0x00ff88,
      'negative': 0xff4444,
      'neutral': 0x888888
    };

    const widthMap = {
      'positive': 2,
      'negative': 3,
      'neutral': 1
    };

    const material = new THREE.LineBasicMaterial({
      color: colorMap[edge.impact_type],
      linewidth: widthMap[edge.impact_type],
      transparent: true,
      opacity: 0.6
    });

    const line = new THREE.Line(geometry, material);
    line.userData = { edge: edge };

    return line;
  }

  private confidenceToColor(confidence: number): THREE.Color {
    // Red (0.0) → Yellow (0.5) → Green (1.0)
    if (confidence < 0.5) {
      // Red to Yellow
      const t = confidence * 2; // 0 to 1
      return new THREE.Color(1.0, t, 0.0);
    } else {
      // Yellow to Green
      const t = (confidence - 0.5) * 2; // 0 to 1
      return new THREE.Color(1.0 - t, 1.0, 0.0);
    }
  }

  private async calculateLayout(graph: DecisionGraph): Promise<Record<string, THREE.Vector3>> {
    // Sugiyama (hierarchical) layout algorithm
    // Returns map of node id -> position

    return new Promise(resolve => {
      // Implement Sugiyama algorithm or use existing library
      const layout: Record<string, THREE.Vector3> = {};

      // Simplified: arrange in layers based on dependencies
      const layers = this.calculateLayers(graph);
      let zOffset = 0;

      for (const layer of layers) {
        const layerWidth = layer.length * 20;
        let xOffset = -layerWidth / 2;

        for (const nodeId of layer) {
          layout[nodeId] = new THREE.Vector3(xOffset, 0, zOffset);
          xOffset += 20;
        }

        zOffset -= 40;
      }

      resolve(layout);
    });
  }

  private calculateLayers(graph: DecisionGraph): string[][] {
    // Topological sort to arrange in layers
    const inDegree = new Map<string, number>();
    const adjacency = new Map<string, string[]>();

    graph.nodes.forEach(n => {
      inDegree.set(n.id, 0);
      adjacency.set(n.id, []);
    });

    graph.edges.forEach(e => {
      inDegree.set(e.target, (inDegree.get(e.target) || 0) + 1);
      adjacency.get(e.source)!.push(e.target);
    });

    const layers: string[][] = [];
    const queue = [...graph.nodes]
      .filter(n => inDegree.get(n.id) === 0)
      .map(n => n.id);

    while (queue.length > 0) {
      const layer: string[] = [];
      const nextQueue: string[] = [];

      for (const node of queue) {
        layer.push(node);
        for (const neighbor of adjacency.get(node) || []) {
          inDegree.set(neighbor, (inDegree.get(neighbor) || 1) - 1);
          if (inDegree.get(neighbor) === 0) {
            nextQueue.push(neighbor);
          }
        }
      }

      if (layer.length > 0) {
        layers.push(layer);
      }
      queue.length = 0;
      queue.push(...nextQueue);
    }

    return layers;
  }

  private fitCameraToGraph() {
    const box = new THREE.Box3();
    this.nodeObjects.forEach(mesh => box.expandByObject(mesh));

    const size = box.getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z);
    const fov = this.camera.fov * (Math.PI / 180);
    let cameraZ = maxDim / 2 / Math.tan(fov / 2);

    this.camera.position.z = cameraZ;
    this.camera.lookAt(box.getCenter(new THREE.Vector3()));
  }

  private animate() {
    this.renderer.render(this.scene, this.camera);
    this.animationFrame = requestAnimationFrame(() => this.animate());
  }

  private onWindowResize() {
    const width = this.renderer.domElement.parentElement!.clientWidth;
    const height = this.renderer.domElement.parentElement!.clientHeight;
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height);
  }

  dispose() {
    if (this.animationFrame) {
      cancelAnimationFrame(this.animationFrame);
    }
    this.renderer.dispose();
  }
}

export default ThreeDGraphRenderer;
```

---

## 6.2: Confidence Heatmap Overlay

### Heatmap Design

**Visualization Concept:**
- Nodes colored by confidence (Red=low → Green=high)
- Edges colored by impact type (Green=positive, Red=negative)
- Glow intensity by uncertainty (high uncertainty = dimmer glow)
- Animation shows confidence changes over time

**Heatmap Component (ConfidenceHeatmap.ts):**

```typescript
class ConfidenceHeatmap {
  private heatmapTexture: THREE.CanvasTexture | null = null;
  private confidenceData: Map<string, number>;
  private uncertaintyData: Map<string, number>;

  constructor() {
    this.confidenceData = new Map();
    this.uncertaintyData = new Map();
  }

  updateConfidence(nodeId: string, confidence: number, uncertainty: number) {
    this.confidenceData.set(nodeId, confidence);
    this.uncertaintyData.set(nodeId, uncertainty);
  }

  generateHeatmapTexture(width: number = 256, height: number = 256): THREE.CanvasTexture {
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d')!;

    // Red → Yellow → Green gradient
    const gradient = ctx.createLinearGradient(0, 0, width, 0);
    gradient.addColorStop(0.0, '#ff0000');  // Red (0.0 confidence)
    gradient.addColorStop(0.33, '#ffff00'); // Yellow (0.33)
    gradient.addColorStop(0.66, '#7fff00'); // Chartreuse (0.66)
    gradient.addColorStop(1.0, '#00ff00'); // Green (1.0)

    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, width, height);

    this.heatmapTexture = new THREE.CanvasTexture(canvas);
    return this.heatmapTexture;
  }

  applyHeatmapToNode(mesh: THREE.Mesh, nodeId: string) {
    const confidence = this.confidenceData.get(nodeId) || 0.5;
    const uncertainty = this.uncertaintyData.get(nodeId) || 0.1;

    // Material color
    const material = mesh.material as THREE.MeshStandardMaterial;
    material.color.setHSL(
      (1 - confidence) * 0.33,  // Hue: red→yellow→green
      0.8,
      0.5
    );

    // Emissive glow based on confidence
    material.emissiveIntensity = 0.3 + (confidence * 0.7);

    // Glow diminishes with uncertainty
    material.opacity = 1.0 - (uncertainty * 0.3);

    // Roughness decreases with confidence (high confidence = smooth/shiny)
    material.roughness = 0.8 - (confidence * 0.4);
  }

  applyHeatmapToEdge(line: THREE.Line, edge: DecisionEdge) {
    const material = line.material as THREE.LineBasicMaterial;

    // Color by impact type
    const colorMap = {
      'positive': 0x00ff88,
      'negative': 0xff4444,
      'neutral': 0x888888
    };

    material.color.setHex(colorMap[edge.impact_type]);

    // Opacity by strength
    material.opacity = 0.3 + (edge.strength * 0.7);

    // Line width by impact magnitude (simulated via material)
    const widthMap = {
      'positive': 2,
      'negative': 3,
      'neutral': 1
    };
    material.linewidth = widthMap[edge.impact_type];
  }

  // Animate confidence changes
  animateConfidenceChange(mesh: THREE.Mesh, nodeId: string,
                         oldConfidence: number, newConfidence: number,
                         duration: number = 1000) {
    const startTime = Date.now();
    const animate = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1.0);

      const current = oldConfidence + (newConfidence - oldConfidence) * progress;
      const material = mesh.material as THREE.MeshStandardMaterial;

      material.color.setHSL(
        (1 - current) * 0.33,
        0.8,
        0.5
      );
      material.emissiveIntensity = 0.3 + (current * 0.7);

      if (progress < 1.0) {
        requestAnimationFrame(animate);
      }
    };
    animate();
  }
}

export default ConfidenceHeatmap;
```

---

## 6.3: Cascade Animation System

### Wave Propagation Visualization

**Cascade Algorithm:**

When a decision changes, show impact propagating through the dependency graph:

```typescript
class CascadeAnimationSystem {
  private animatingNodes: Set<string> = new Set();
  private renderer: ThreeDGraphRenderer;
  private graph: DecisionGraph;

  constructor(renderer: ThreeDGraphRenderer, graph: DecisionGraph) {
    this.renderer = renderer;
    this.graph = graph;
  }

  async animateCascade(startNodeId: string, impactMap: Record<string, number>) {
    // BFS from start node, animate in waves
    const visited = new Set<string>();
    const queue: Array<{ nodeId: string; distance: number }> = [
      { nodeId: startNodeId, distance: 0 }
    ];

    const waveDelay = 200;  // ms between waves
    const nodeDuration = 800; // ms per node animation

    while (queue.length > 0) {
      const { nodeId, distance } = queue.shift()!;

      if (visited.has(nodeId)) continue;
      visited.add(nodeId);

      // Delay animation based on distance
      await new Promise(resolve => setTimeout(resolve, distance * waveDelay));

      // Highlight this node
      this.animateNodeImpact(nodeId, impactMap[nodeId] || 0, nodeDuration);

      // Queue dependent nodes
      const dependencies = this.graph.edges
        .filter(e => e.source === nodeId)
        .map(e => e.target);

      for (const depId of dependencies) {
        if (!visited.has(depId)) {
          queue.push({ nodeId: depId, distance: distance + 1 });
        }
      }
    }
  }

  private animateNodeImpact(nodeId: string, impact: number, duration: number) {
    const startTime = Date.now();
    const pulseIntensity = Math.abs(impact);

    const animate = () => {
      const elapsed = Date.now() - startTime;
      if (elapsed > duration) return;

      const progress = elapsed / duration;
      const pulse = Math.sin(progress * Math.PI) * pulseIntensity;

      // Scale the node up and down
      const mesh = this.renderer.nodeObjects.get(nodeId);
      if (mesh) {
        const material = mesh.material as THREE.MeshStandardMaterial;
        material.emissiveIntensity = 0.3 + pulse;

        if (progress < 1.0) {
          requestAnimationFrame(animate);
        }
      }
    };

    animate();
  }

  // Animate edge flow (arrow traveling along edge)
  animateEdgeFlow(sourceId: string, targetId: string, duration: number = 1000) {
    const startTime = Date.now();

    const animate = () => {
      const elapsed = Date.now() - startTime;
      if (elapsed > duration) return;

      const progress = elapsed / duration;

      // Create animated particle traveling along edge
      // (Implementation: use Line with dashed material)

      requestAnimationFrame(animate);
    };

    animate();
  }
}

export default CascadeAnimationSystem;
```

---

## 6.4: Interactive Timeline & Scrubber

### Timeline Component (D3.js)

**Timeline UI (DecisionTimeline.tsx):**

```typescript
import * as d3 from 'd3';

class DecisionTimeline {
  private svg: d3.Selection<SVGSVGElement, unknown, HTMLElement, any>;
  private scale: d3.ScaleTime<number, number>;
  private selectedDate: Date | null = null;
  private onDateSelect: ((date: Date) => void) | null = null;

  constructor(container: HTMLElement) {
    const width = container.clientWidth;
    const height = 100;

    this.svg = d3.select(container)
      .append('svg')
      .attr('width', width)
      .attr('height', height);

    this.scale = d3.scaleTime()
      .domain([new Date(Date.now() - 90 * 24 * 60 * 60 * 1000), new Date()])
      .range([50, width - 50]);
  }

  loadData(decisions: DecisionData[]) {
    // Group decisions by date
    const dateMap = new Map<string, DecisionData[]>();

    decisions.forEach(d => {
      const dateKey = d3.timeFormat('%Y-%m-%d')(new Date(d.updated_at));
      if (!dateMap.has(dateKey)) {
        dateMap.set(dateKey, []);
      }
      dateMap.get(dateKey)!.push(d);
    });

    // Create timeline bars
    const dates = Array.from(dateMap.entries())
      .sort((a, b) => new Date(a[0]).getTime() - new Date(b[0]).getTime());

    this.svg.selectAll('.timeline-bar')
      .data(dates, d => d[0])
      .enter()
      .append('rect')
      .attr('class', 'timeline-bar')
      .attr('x', d => this.scale(new Date(d[0])))
      .attr('y', 40)
      .attr('width', 3)
      .attr('height', d => Math.min(d[1].length * 3, 40))
      .attr('fill', '#00ff88')
      .attr('opacity', 0.7)
      .on('click', (event, d) => {
        this.selectedDate = new Date(d[0]);
        if (this.onDateSelect) {
          this.onDateSelect(this.selectedDate);
        }
        this.highlightDate(new Date(d[0]));
      });

    // Add time axis
    const xAxis = d3.axisBottom(this.scale).tickFormat(d3.timeFormat('%m-%d'));
    this.svg.append('g')
      .attr('transform', 'translate(0, 80)')
      .call(xAxis);
  }

  private highlightDate(date: Date) {
    this.svg.selectAll('.timeline-bar')
      .attr('opacity', d => {
        const barDate = new Date(d[0]);
        return barDate.toDateString() === date.toDateString() ? 1.0 : 0.4;
      });
  }

  onDateSelected(callback: (date: Date) => void) {
    this.onDateSelect = callback;
  }
}

export default DecisionTimeline;
```

---

## 6.5: Real-time Streaming Architecture

### Server-Sent Events (SSE) Streaming

**FastAPI SSE Endpoint:**

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import json
import asyncio

@app.get("/api/v1/graph/stream")
async def stream_graph_updates(decision_id: Optional[str] = None):
    """
    Stream real-time graph updates via Server-Sent Events.
    """
    async def event_generator():
        try:
            while True:
                # Get latest graph state
                graph = db.get_decision_graph()

                # Check for new scores
                new_scores = db.get_score_updates_since(last_check)

                for decision_id, new_score in new_scores.items():
                    event_data = {
                        'type': 'score_update',
                        'decision_id': decision_id,
                        'confidence': new_score['final_confidence'],
                        'uncertainty': new_score['uncertainty'],
                        'timestamp': datetime.now().isoformat()
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"

                # Check for graph changes (new decisions, dependencies)
                graph_changes = db.get_graph_changes_since(last_check)
                if graph_changes:
                    event_data = {
                        'type': 'graph_update',
                        'added_nodes': graph_changes['added_nodes'],
                        'added_edges': graph_changes['added_edges'],
                        'timestamp': datetime.now().isoformat()
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"

                # Heartbeat every 5 seconds
                await asyncio.sleep(5)

        except asyncio.CancelledError:
            pass

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**Client-side Event Handler (useGraphStream.ts):**

```typescript
import { useEffect, useRef } from 'react';
import { useVisualizationStore } from './store/visualizationStore';

export function useGraphStream() {
  const eventSourceRef = useRef<EventSource | null>(null);
  const updateGraph = useVisualizationStore(s => s.updateGraph);
  const updateScore = useVisualizationStore(s => s.updateScore);

  useEffect(() => {
    // Connect to SSE endpoint
    eventSourceRef.current = new EventSource('/api/v1/graph/stream');

    eventSourceRef.current.addEventListener('message', (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'score_update') {
        // Update score and trigger animation
        updateScore(data.decision_id, {
          confidence: data.confidence,
          uncertainty: data.uncertainty
        });
      } else if (data.type === 'graph_update') {
        // Add new nodes/edges
        updateGraph(data.added_nodes, data.added_edges);
      }
    });

    eventSourceRef.current.addEventListener('error', () => {
      eventSourceRef.current?.close();
      // Reconnect after delay
      setTimeout(() => {
        eventSourceRef.current = new EventSource('/api/v1/graph/stream');
      }, 3000);
    });

    return () => {
      eventSourceRef.current?.close();
    };
  }, [updateGraph, updateScore]);
}
```

---

## 6.6: Visualization State Management (Zustand)

**Store (visualizationStore.ts):**

```typescript
import { create } from 'zustand';

interface VisualizationState {
  // Graph state
  graph: DecisionGraph | null;
  selectedNodes: Set<string>;
  hoveredNode: string | null;
  filterConfidenceMin: number;

  // Display options
  showHeatmap: boolean;
  showEdgeLabels: boolean;
  showTimeline: boolean;
  animationSpeed: number; // 0.5x to 2x

  // Actions
  setGraph: (graph: DecisionGraph) => void;
  selectNode: (nodeId: string) => void;
  deselectNode: (nodeId: string) => void;
  clearSelection: () => void;
  setHoveredNode: (nodeId: string | null) => void;
  setFilterConfidenceMin: (min: number) => void;
  updateScore: (nodeId: string, score: ScoreData) => void;
  toggleHeatmap: () => void;
  toggleEdgeLabels: () => void;
  setAnimationSpeed: (speed: number) => void;
  animateCascade: (startNodeId: string, impactMap: Record<string, number>) => void;
}

export const useVisualizationStore = create<VisualizationState>((set, get) => ({
  graph: null,
  selectedNodes: new Set(),
  hoveredNode: null,
  filterConfidenceMin: 0.0,
  showHeatmap: true,
  showEdgeLabels: false,
  showTimeline: true,
  animationSpeed: 1.0,

  setGraph: (graph) => set({ graph }),

  selectNode: (nodeId) => set(state => {
    const newSelected = new Set(state.selectedNodes);
    newSelected.add(nodeId);
    return { selectedNodes: newSelected };
  }),

  deselectNode: (nodeId) => set(state => {
    const newSelected = new Set(state.selectedNodes);
    newSelected.delete(nodeId);
    return { selectedNodes: newSelected };
  }),

  clearSelection: () => set({ selectedNodes: new Set() }),

  setHoveredNode: (nodeId) => set({ hoveredNode: nodeId }),

  setFilterConfidenceMin: (min) => set({ filterConfidenceMin: min }),

  updateScore: (nodeId, score) => set(state => {
    if (!state.graph) return state;
    const updatedGraph = {
      ...state.graph,
      nodes: state.graph.nodes.map(n =>
        n.id === nodeId
          ? { ...n, confidence: score.confidence, uncertainty: score.uncertainty }
          : n
      )
    };
    return { graph: updatedGraph };
  }),

  toggleHeatmap: () => set(state => ({ showHeatmap: !state.showHeatmap })),
  toggleEdgeLabels: () => set(state => ({ showEdgeLabels: !state.showEdgeLabels })),

  setAnimationSpeed: (speed) => set({ animationSpeed: Math.max(0.5, Math.min(2.0, speed)) }),

  animateCascade: (startNodeId, impactMap) => {
    // Trigger cascade animation (implementation in CascadeAnimationSystem)
    // This is typically called from visualization component
  }
}));
```

---

## 6.7: Interactive Controls

**Visualization Controls Component (VisualizationControls.tsx):**

```typescript
export function VisualizationControls() {
  const {
    showHeatmap, toggleHeatmap,
    showEdgeLabels, toggleEdgeLabels,
    showTimeline,
    filterConfidenceMin, setFilterConfidenceMin,
    animationSpeed, setAnimationSpeed
  } = useVisualizationStore();

  return (
    <div className="visualization-controls">
      <h3>Controls</h3>

      {/* Toggle heatmap */}
      <label>
        <input
          type="checkbox"
          checked={showHeatmap}
          onChange={toggleHeatmap}
        />
        Confidence Heatmap
      </label>

      {/* Toggle edge labels */}
      <label>
        <input
          type="checkbox"
          checked={showEdgeLabels}
          onChange={toggleEdgeLabels}
        />
        Edge Labels
      </label>

      {/* Confidence filter */}
      <div>
        <label>Min Confidence: {filterConfidenceMin.toFixed(2)}</label>
        <input
          type="range"
          min="0"
          max="1"
          step="0.05"
          value={filterConfidenceMin}
          onChange={(e) => setFilterConfidenceMin(parseFloat(e.target.value))}
        />
      </div>

      {/* Animation speed */}
      <div>
        <label>Animation Speed: {animationSpeed.toFixed(1)}x</label>
        <input
          type="range"
          min="0.5"
          max="2.0"
          step="0.1"
          value={animationSpeed}
          onChange={(e) => setAnimationSpeed(parseFloat(e.target.value))}
        />
      </div>

      {/* Interaction help */}
      <div className="help-text">
        <p>Click nodes to select / drag to pan / scroll to zoom</p>
        <p>Hover over nodes for details / click to show cascade</p>
      </div>
    </div>
  );
}
```

---

## Testing Strategy

### Unit Tests (12+ tests)

```typescript
// tests/unit/heatmap.test.ts
describe('ConfidenceHeatmap', () => {
  it('should generate color gradient texture', () => {
    const heatmap = new ConfidenceHeatmap();
    const texture = heatmap.generateHeatmapTexture(256, 256);
    expect(texture).toBeDefined();
  });

  it('should apply correct color for confidence levels', () => {
    const heatmap = new ConfidenceHeatmap();
    expect(heatmap.confidenceToColor(0.0)).toEqual('#ff0000'); // Red
    expect(heatmap.confidenceToColor(0.5)).toEqual('#ffff00'); // Yellow
    expect(heatmap.confidenceToColor(1.0)).toEqual('#00ff00'); // Green
  });
});

// tests/unit/layout.test.ts
describe('Layout Algorithm', () => {
  it('should calculate topological layers correctly', () => {
    const graph = createTestGraph();
    const layers = calculateLayers(graph);
    expect(layers.length).toBeGreaterThan(0);
    // Verify topological ordering
  });
});
```

### Integration Tests (10+ tests)

```typescript
// tests/integration/streaming.test.ts
describe('SSE Streaming', () => {
  it('should stream graph updates via SSE', async () => {
    const response = await fetch('/api/v1/graph/stream');
    const reader = response.body?.getReader();
    const data = await reader?.read();
    expect(data?.value).toBeDefined();
  });
});

// tests/integration/rendering.test.ts
describe('3D Rendering', () => {
  it('should load and render graph', async () => {
    const container = document.createElement('div');
    const renderer = new ThreeDGraphRenderer(container);
    await renderer.loadGraph(testGraph);
    expect(renderer.nodeObjects.size).toBe(testGraph.nodes.length);
  });
});
```

### E2E Tests (8+ tests)

```typescript
// tests/e2e/visualization.test.ts
describe('Visualization E2E', () => {
  it('should load graph and update in real-time', async () => {
    // Load page
    await page.goto('http://localhost:3000/visualization');

    // Verify 3D graph rendered
    const canvas = await page.$('canvas');
    expect(canvas).toBeDefined();

    // Wait for real-time update
    await page.waitForTimeout(1000);

    // Update a score
    await fetch('/api/v1/scores/decision_1', {
      method: 'POST',
      body: JSON.stringify({ force_refresh: true })
    });

    // Verify animation occurred
    const animationClass = await page.locator('[data-node-id="decision_1"]')
      .evaluate(el => el.className);
    expect(animationClass).toContain('animating');
  });
});
```

---

## Performance Targets

| Metric | Target | Method |
|--------|--------|--------|
| Initial graph load | <2s | 3D scene initialization |
| Real-time updates | <100ms | SSE processing |
| Zoom/pan interaction | 60fps | GPU rendering |
| Node animation | 60fps | requestAnimationFrame |
| Large graph (1000 nodes) | <5s | Level-of-detail rendering |

---

## Success Criteria

- ✅ 3D graph renders correctly with 100+ nodes
- ✅ Confidence heatmap shows colors: Red→Green by confidence
- ✅ Cascade animation shows impact propagation visually
- ✅ Timeline scrubber allows historical filtering
- ✅ Real-time updates via SSE < 100ms latency
- ✅ 30+ tests passing, 80%+ coverage
- ✅ Interactive controls (zoom, pan, select, filter)
- ✅ No memory leaks on long-running streams
- ✅ Works on Chrome, Firefox, Safari

---

## Team Assignments

| Role | Team Member | Focus |
|------|-------------|-------|
| 3D Rendering | data-graph-specialist | Three.js scene, layout, nodes/edges |
| Heatmap & Animation | data-graph-specialist | Color mapping, cascade animation |
| Streaming | observability-specialist | SSE endpoints, real-time updates |
| Timeline UI | data-graph-specialist | D3.js timeline, scrubber controls |
| State Management | all | Zustand store, event handling |
| Testing | all | Unit, integration, e2e tests |

---

## Deliverables Checklist

- [ ] ThreeDGraphRenderer (3D graph visualization)
- [ ] ConfidenceHeatmap overlay system
- [ ] CascadeAnimationSystem
- [ ] DecisionTimeline (D3.js component)
- [ ] useGraphStream hook (SSE integration)
- [ ] VisualizationControls (UI controls)
- [ ] visualizationStore (Zustand state)
- [ ] 30+ unit/integration/e2e tests
- [ ] Performance benchmarks
- [ ] User guide & interactive documentation

---

**Status**: 🔵 SPECIFICATION COMPLETE - Ready for Implementation

**Next Steps**:
1. Implement 3D renderer (Step 1)
2. Add heatmap system (Step 2)
3. Build cascade animations (Step 3)
4. Add timeline controls (Step 4)
5. Integrate real-time streaming (Step 5)
