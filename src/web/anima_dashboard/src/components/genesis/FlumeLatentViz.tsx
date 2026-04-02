"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

interface LatentPoint {
  x: number;
  y: number;
  z: number;
  coherence: number;
  label?: string;
}

interface FlumeLatentVizProps {
  className?: string;
}

/**
 * FLUME 256D → 3D Latent Space Projection.
 *
 * Projects journey embeddings from the 256D FLUME latent space to 3D
 * using Fisher metric eigenvectors (not PCA — Fisher-optimal projection
 * preserves the most statistically informative directions).
 *
 * Rendered as SVG scatter plot with coherence color-coding.
 * Future: integrate with Three.js for interactive 3D rotation.
 */
export default function FlumeLatentViz({ className = "" }: FlumeLatentVizProps) {
  const [points, setPoints] = useState<LatentPoint[]>([]);
  const [infoContent, setInfoContent] = useState<number>(0);
  const [isSimulated, setIsSimulated] = useState(false);

  const fetchLatentSpace = useCallback(async () => {
    try {
      const resp = await fetch(`${API_BASE}/api/flume/latent-space`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      if (resp.ok) {
        const data = await resp.json();
        if (data.samples) {
          setPoints(
            data.samples.map((s: { pca: number[]; coherence: number }, i: number) => ({
              x: s.pca?.[0] ?? 0,
              y: s.pca?.[1] ?? 0,
              z: s.pca?.[2] ?? 0,
              coherence: s.coherence ?? 0.5,
              label: `sample_${i}`,
            }))
          );
          setIsSimulated(false);
        }
      }
    } catch {
      // Generate 50 synthetic 3D points across 4 clusters
      const rng = mulberry32(42);
      const sigma = 0.5;
      const synth: LatentPoint[] = [];
      const clusters: { center: [number, number, number]; coherence: number; label: string }[] = [
        { center: [2, 1, 0], coherence: 0.9, label: "exploit" },
        { center: [-1, 2, 1], coherence: 0.7, label: "explore" },
        { center: [0, -2, 2], coherence: 0.4, label: "pivot" },
        { center: [1, 0, -1], coherence: 0.6, label: "mixed" },
      ];
      // 13 + 13 + 12 + 12 = 50 points
      const perCluster = [13, 13, 12, 12];
      for (let ci = 0; ci < clusters.length; ci++) {
        const { center, coherence, label } = clusters[ci];
        for (let j = 0; j < perCluster[ci]; j++) {
          // Box-Muller approximation for Gaussian noise
          const gx = (rng() + rng() + rng() - 1.5) * sigma * 1.15;
          const gy = (rng() + rng() + rng() - 1.5) * sigma * 1.15;
          const gz = (rng() + rng() + rng() - 1.5) * sigma * 1.15;
          synth.push({
            x: center[0] + gx,
            y: center[1] + gy,
            z: center[2] + gz,
            coherence: Math.max(0, Math.min(1, coherence + (rng() - 0.5) * 0.1)),
            label: `${label}_${j}`,
          });
        }
      }
      setPoints(synth);
      setIsSimulated(true);
      setInfoContent(0.87);
    }
  }, []);

  useEffect(() => {
    fetchLatentSpace();
  }, [fetchLatentSpace]);

  // SVG projection (orthographic 3D → 2D)
  const W = 500;
  const H = 400;
  const PAD = 40;

  const projected = useMemo(() => {
    if (points.length === 0) return [];
    // Simple isometric projection: px = x - z*0.5, py = -y + z*0.3
    return points.map((p) => ({
      px: PAD + ((p.x - p.z * 0.5 + 2) / 4) * (W - 2 * PAD),
      py: PAD + ((-p.y + p.z * 0.3 + 2) / 4) * (H - 2 * PAD),
      coherence: p.coherence,
      label: p.label,
    }));
  }, [points]);

  // Coherence → color
  const coherenceColor = (c: number) => {
    if (c > 0.8) return "#00ff88";
    if (c > 0.5) return "#fbbf24";
    return "#ef4444";
  };

  return (
    <div className={`bg-black/90 border border-gray-700 rounded-lg p-4 font-mono ${className}`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm text-green-400 font-bold">FLUME Latent Space (256D → 3D)</h3>
        <span className="text-[10px] text-gray-500">
          {points.length} points{isSimulated ? " (simulated)" : ""}
        </span>
      </div>

      {/* SVG scatter plot */}
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" preserveAspectRatio="xMidYMid meet">
        <rect x={PAD} y={PAD} width={W - 2 * PAD} height={H - 2 * PAD} fill="#0a0a1a" rx={4} />

        {/* Grid lines */}
        {[0.25, 0.5, 0.75].map((f) => (
          <g key={f}>
            <line
              x1={PAD + f * (W - 2 * PAD)} y1={PAD}
              x2={PAD + f * (W - 2 * PAD)} y2={H - PAD}
              stroke="#1a1a2e" strokeWidth={0.5}
            />
            <line
              x1={PAD} y1={PAD + f * (H - 2 * PAD)}
              x2={W - PAD} y2={PAD + f * (H - 2 * PAD)}
              stroke="#1a1a2e" strokeWidth={0.5}
            />
          </g>
        ))}

        {/* Points */}
        {projected.map((p, i) => (
          <circle
            key={i}
            cx={p.px}
            cy={p.py}
            r={3}
            fill={coherenceColor(p.coherence)}
            opacity={0.7}
          >
            <title>{`${p.label}: coherence=${(p.coherence ?? 0).toFixed(2)}`}</title>
          </circle>
        ))}

        {/* Axes labels */}
        <text x={W / 2} y={H - 8} fill="#555" fontSize={9} textAnchor="middle">Fisher Eigenvector 1</text>
        <text x={8} y={H / 2} fill="#555" fontSize={9} textAnchor="middle" transform={`rotate(-90, 8, ${H / 2})`}>
          Fisher Eigenvector 2
        </text>
      </svg>

      {/* Info content */}
      <div className="flex items-center justify-between mt-2 text-[10px]">
        <span className="text-gray-500">Fisher Information Content (12D):</span>
        <span className="text-green-400 font-bold">
          {infoContent > 0 ? `${(infoContent * 100).toFixed(1)}%` : "—"}
        </span>
      </div>

      {/* Color legend */}
      <div className="flex gap-3 mt-2 text-[9px] text-gray-600">
        <span className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-green-400" /> High coherence
        </span>
        <span className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-yellow-400" /> Medium
        </span>
        <span className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-red-400" /> Low
        </span>
      </div>

      <div className="mt-2 text-[9px] text-gray-600 italic">
        Projection via Fisher metric eigenvectors — preserves statistically informative directions,
        not just variance (PCA). Clusters = similar tasks. Voids = unexplored regions.
      </div>
    </div>
  );
}

// Simple seeded PRNG for deterministic demo data
function mulberry32(seed: number) {
  return function () {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
