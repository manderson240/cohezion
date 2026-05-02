/**
 * Hyperdimensional Compound Visualization - Type Definitions
 */

import { App } from 'obsidian';

// ============================================================================
// Plugin Settings
// ============================================================================

export interface HyperdimPluginSettings {
  api: {
    cloudVaultMcpUrl: string;
    enableRealTimeSync: boolean;
  };
  visualization: {
    nodeSize: number;
    edgeOpacity: number;
    animationSpeed: number;
    defaultProjection: ProjectionPreset;
  };
  performance: {
    maxNodes: number;
    enableLOD: boolean;
    renderQuality: 'low' | 'medium' | 'high';
  };
}

export const DEFAULT_SETTINGS: HyperdimPluginSettings = {
  api: {
    cloudVaultMcpUrl: 'http://localhost:8360',
    enableRealTimeSync: false,
  },
  visualization: {
    nodeSize: 5.0,
    edgeOpacity: 0.3,
    animationSpeed: 1.0,
    defaultProjection: 'temporal',
  },
  performance: {
    maxNodes: 500,
    enableLOD: true,
    renderQuality: 'high',
  },
};

// ============================================================================
// Graph Data Types
// ============================================================================

export interface GraphNode {
  id: string;
  label: string;
  file_path: string;
  type: 'paper' | 'concept' | 'decision' | 'experiment' | 'pattern' | 'lesson';

  // 12D dimensions
  connectivity: number;           // 0-1
  cross_domain: number;           // 0-1
  completion: number;             // 0-1
  temporal: number;               // 0-1
  recency: number;                // 0-1
  conceptual_depth: number;       // 0-1 (1=theory, 0=applied)

  // Future dimensions (placeholders)
  agent_visits?: number;          // Agent tracking
  capability_score?: number;      // Capability measurement
  innovation_potential?: number;  // Universe simulation
  knowledge_gap?: number;         // Gap analysis
  impact_score?: number;          // Impact measurement
  semantic_density?: number;      // Semantic richness

  // Visual properties
  tags: string[];
  date: string;
  wiki_links_count: number;
  is_bridging: boolean;
  is_orphaned: boolean;
  theory_leaning: boolean;
  suggested_color: string;
  suggested_size: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  weight: number;
  type: 'wiki_link' | 'semantic_similarity' | 'agent_journey';
}

export interface GraphData {
  meta: {
    export_date: string;
    source: string;
    nodes_count: number;
    edges_count: number;
    phase: string;
  };
  dimensions: Record<string, string>;
  visual_mappings: Record<string, string>;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// ============================================================================
// Projection Types
// ============================================================================

export type ProjectionPreset =
  | 'temporal'           // Temporal × Connectivity × Cross-Domain
  | 'semantic'           // Semantic × Conceptual Depth × Recency
  | 'theory_applied'     // Theory-Applied × Completion × Impact
  | 'custom';

export interface ProjectionConfig {
  name: string;
  description: string;
  xAxis: keyof GraphNode;
  yAxis: keyof GraphNode;
  zAxis: keyof GraphNode;
  xLabel: string;
  yLabel: string;
  zLabel: string;
}

export const PROJECTION_PRESETS: Record<ProjectionPreset, ProjectionConfig> = {
  temporal: {
    name: 'Temporal Evolution',
    description: 'View knowledge evolution over time and cross-domain connections',
    xAxis: 'temporal',
    yAxis: 'connectivity',
    zAxis: 'cross_domain',
    xLabel: 'Publication Date',
    yLabel: 'Hub Centrality',
    zLabel: 'Domain Diversity',
  },
  semantic: {
    name: 'Semantic Landscape',
    description: 'Explore conceptual depth and semantic relationships',
    xAxis: 'conceptual_depth',
    yAxis: 'recency',
    zAxis: 'connectivity',
    xLabel: 'Theory ← → Applied',
    yLabel: 'Recency',
    zLabel: 'Connectivity',
  },
  theory_applied: {
    name: 'Theory-Applied Balance',
    description: 'Visualize theoretical vs. applied knowledge with completion status',
    xAxis: 'conceptual_depth',
    yAxis: 'completion',
    zAxis: 'connectivity',
    xLabel: 'Theory ← → Applied',
    yLabel: 'Completion',
    zLabel: 'Impact',
  },
  custom: {
    name: 'Custom Projection',
    description: 'Define your own dimensional mapping',
    xAxis: 'connectivity',
    yAxis: 'cross_domain',
    zAxis: 'completion',
    xLabel: 'X Axis',
    yLabel: 'Y Axis',
    zLabel: 'Z Axis',
  },
};

// ============================================================================
// Agent Tracking Types (Phase 2)
// ============================================================================

export interface AgentJourney {
  agent_id: string;
  timestamp: string;
  note_path: string;
  action: 'read' | 'edit' | 'create' | 'link';
  duration_ms: number;
}

// ============================================================================
// Capability Metrics Types (Phase 3)
// ============================================================================

export interface CapabilityMetrics {
  total_turns: number;
  success_rate: number;
  avg_response_time_ms: number;
  knowledge_coverage: number;
  tool_usage_efficiency: number;
}

// ============================================================================
// Simulation Types (Phase 4)
// ============================================================================

export interface SimulationConfig {
  type: 'decision_fork' | 'task_optimization' | 'knowledge_gap';
  parameters: Record<string, any>;
  max_iterations: number;
}

export interface SimulationResult {
  config: SimulationConfig;
  iterations: number;
  outcome: Record<string, any>;
  metrics: Record<string, number>;
}
