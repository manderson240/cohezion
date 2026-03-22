"use client";

import { useState, useEffect } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

interface GraphNode {
  id: string;
  label: string;
  category: string;
  color: string;
  module_count: number;
}

interface GraphEdge {
  source: string;
  target: string;
}

/**
 * Architecture Graph visualization (Layer 6).
 * Force-directed layout of Cohezion packages and their import relationships.
 */
export default function ArchitectureGraph() {
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/architecture/graph`)
      .then((r) => (r.ok ? r.json() : { nodes: [], edges: [] }))
      .then((data) => {
        setNodes(data.nodes);
        setEdges(data.edges);
      })
      .catch(() => {});
  }, []);

  if (nodes.length === 0) {
    return (
      <div className="text-center text-gray-600 font-mono text-xs py-8">
        Loading architecture graph...
      </div>
    );
  }

  // Simple circular layout
  const cx = 300;
  const cy = 250;
  const r = 200;
  const positions = new Map<string, { x: number; y: number }>();
  nodes.forEach((node, i) => {
    const angle = -Math.PI / 2 + (i / nodes.length) * 2 * Math.PI;
    positions.set(node.id, {
      x: cx + r * Math.cos(angle),
      y: cy + r * Math.sin(angle),
    });
  });

  return (
    <div className="bg-white/[0.02] backdrop-blur-xl border border-white/10 rounded-2xl p-4 overflow-hidden">
      <svg width="100%" viewBox="0 0 600 500">
        {/* Edges */}
        {edges.map((edge, i) => {
          const from = positions.get(edge.source);
          const to = positions.get(edge.target);
          if (!from || !to) return null;
          const highlighted =
            hoveredNode === edge.source || hoveredNode === edge.target;
          return (
            <line
              key={i}
              x1={from.x}
              y1={from.y}
              x2={to.x}
              y2={to.y}
              stroke={highlighted ? "var(--hiho-glow-color, #00ff00)" : "white"}
              strokeOpacity={highlighted ? 0.4 : 0.06}
              strokeWidth={highlighted ? 1.5 : 0.5}
            />
          );
        })}

        {/* Nodes */}
        {nodes.map((node) => {
          const pos = positions.get(node.id)!;
          const hovered = hoveredNode === node.id;
          const nodeR = Math.min(8 + node.module_count * 0.5, 25);
          return (
            <g
              key={node.id}
              onMouseEnter={() => setHoveredNode(node.id)}
              onMouseLeave={() => setHoveredNode(null)}
              className="cursor-pointer"
            >
              <circle
                cx={pos.x}
                cy={pos.y}
                r={nodeR}
                fill={node.color}
                fillOpacity={hovered ? 0.4 : 0.15}
                stroke={node.color}
                strokeOpacity={hovered ? 0.8 : 0.3}
                strokeWidth={hovered ? 2 : 1}
              />
              <text
                x={pos.x}
                y={pos.y + nodeR + 14}
                textAnchor="middle"
                fill={hovered ? "white" : "#888"}
                fontSize="8"
                fontFamily="monospace"
                fontWeight={hovered ? "bold" : "normal"}
              >
                {node.label}
              </text>
              {hovered && (
                <text
                  x={pos.x}
                  y={pos.y + nodeR + 24}
                  textAnchor="middle"
                  fill="#666"
                  fontSize="7"
                  fontFamily="monospace"
                >
                  {node.module_count} modules
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
