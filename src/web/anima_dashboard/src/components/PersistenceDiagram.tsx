"use client";

interface PersistencePairEntry {
  birth: number;
  death: number;
  dimension: number;
  persistence: number;
}

interface TopologyData {
  persistence_pairs: PersistencePairEntry[];
  entropy: number;
  n_clusters: number;
  n_loops: number;
}

/**
 * Persistence Diagram scatter plot (FR22).
 * Plots birth vs death for H0 (clusters) and H1 (loops) features.
 * Points far from the diagonal represent significant topological features.
 */
export default function PersistenceDiagram({ topology }: { topology: TopologyData | null }) {
  if (!topology || topology.persistence_pairs.length === 0) {
    return (
      <div className="text-center text-gray-600 font-mono text-xs py-4">
        Accumulating topology data...
      </div>
    );
  }

  const pairs = topology.persistence_pairs;
  // Find axis bounds (exclude sentinel 999 values)
  const finitePairs = pairs.filter((p) => p.death < 900);
  const maxVal = finitePairs.length > 0
    ? Math.max(...finitePairs.map((p) => Math.max(p.birth, p.death))) * 1.1
    : 1;

  const W = 280;
  const H = 280;
  const PAD = 40;
  const plotW = W - 2 * PAD;
  const plotH = H - 2 * PAD;

  const scaleX = (v: number) => PAD + (v / maxVal) * plotW;
  const scaleY = (v: number) => PAD + plotH - (v / maxVal) * plotH;

  return (
    <div className="bg-white/[0.02] backdrop-blur-xl border border-white/10 rounded-2xl p-4">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-[10px] font-bold font-mono tracking-widest text-gray-400">
          PERSISTENCE DIAGRAM
        </h4>
        <div className="flex gap-3 text-[9px] font-mono text-gray-500">
          <span>H0: {topology.n_clusters} clusters</span>
          <span>H1: {topology.n_loops} loops</span>
          <span>entropy: {(topology.entropy ?? 0).toFixed(3)}</span>
        </div>
      </div>

      <svg width="100%" viewBox={`0 0 ${W} ${H}`}>
        {/* Diagonal line (birth = death) */}
        <line
          x1={scaleX(0)} y1={scaleY(0)}
          x2={scaleX(maxVal)} y2={scaleY(maxVal)}
          stroke="white" strokeOpacity={0.1} strokeWidth={1}
          strokeDasharray="4,4"
        />

        {/* Axes */}
        <line x1={PAD} y1={PAD + plotH} x2={PAD + plotW} y2={PAD + plotH}
          stroke="white" strokeOpacity={0.15} strokeWidth={1} />
        <line x1={PAD} y1={PAD} x2={PAD} y2={PAD + plotH}
          stroke="white" strokeOpacity={0.15} strokeWidth={1} />

        {/* Axis labels */}
        <text x={PAD + plotW / 2} y={H - 4} textAnchor="middle"
          fill="#555" fontSize="8" fontFamily="monospace">birth</text>
        <text x={8} y={PAD + plotH / 2} textAnchor="middle"
          fill="#555" fontSize="8" fontFamily="monospace"
          transform={`rotate(-90, 8, ${PAD + plotH / 2})`}>death</text>

        {/* Points */}
        {finitePairs.map((p, i) => {
          const isH0 = p.dimension === 0;
          const color = isH0 ? "var(--hiho-glow-color, #00ff00)" : "#f093fb";
          const opacity = Math.min(0.3 + p.persistence * 2, 0.9);
          return (
            <circle
              key={i}
              cx={scaleX(p.birth)}
              cy={scaleY(p.death)}
              r={3 + p.persistence * 8}
              fill={color}
              fillOpacity={opacity * 0.4}
              stroke={color}
              strokeOpacity={opacity}
              strokeWidth={1}
            />
          );
        })}
      </svg>
    </div>
  );
}
