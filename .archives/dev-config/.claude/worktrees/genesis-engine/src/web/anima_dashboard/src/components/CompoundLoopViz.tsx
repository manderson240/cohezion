"use client";

const PHASES = ["EXPANDING", "PLANNING", "EXECUTING", "REFLECTING", "REFINING"];
const PHASE_ANGLE = (2 * Math.PI) / PHASES.length;

/**
 * Compound Engineering Loop visualization (FR18).
 * Five-phase ring with animated indicator.
 */
export default function CompoundLoopViz({ currentPhase = 2 }: { currentPhase?: number }) {
  const cx = 150;
  const cy = 150;
  const r = 110;

  return (
    <div className="flex flex-col items-center">
      <svg width="300" height="300" viewBox="0 0 300 300">
        {/* Background ring */}
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="white" strokeOpacity={0.05} strokeWidth={2} />

        {/* Phase nodes */}
        {PHASES.map((phase, i) => {
          const angle = -Math.PI / 2 + i * PHASE_ANGLE;
          const x = cx + r * Math.cos(angle);
          const y = cy + r * Math.sin(angle);
          const isActive = i === currentPhase;

          return (
            <g key={phase}>
              {/* Connection to next */}
              {i < PHASES.length - 1 && (() => {
                const nextAngle = -Math.PI / 2 + (i + 1) * PHASE_ANGLE;
                const nx = cx + r * Math.cos(nextAngle);
                const ny = cy + r * Math.sin(nextAngle);
                return <line x1={x} y1={y} x2={nx} y2={ny} stroke="white" strokeOpacity={0.1} strokeWidth={1} />;
              })()}
              {/* Closing connection */}
              {i === PHASES.length - 1 && (() => {
                const firstAngle = -Math.PI / 2;
                const fx = cx + r * Math.cos(firstAngle);
                const fy = cy + r * Math.sin(firstAngle);
                return <line x1={x} y1={y} x2={fx} y2={fy} stroke="white" strokeOpacity={0.1} strokeWidth={1} />;
              })()}

              {/* Node circle */}
              <circle
                cx={x}
                cy={y}
                r={isActive ? 20 : 14}
                fill={isActive ? "var(--hiho-glow-color, #00ff00)" : "transparent"}
                fillOpacity={isActive ? 0.15 : 0}
                stroke={isActive ? "var(--hiho-glow-color, #00ff00)" : "white"}
                strokeOpacity={isActive ? 0.8 : 0.2}
                strokeWidth={isActive ? 2 : 1}
              >
                {isActive && (
                  <animate attributeName="r" values="18;22;18" dur="var(--hiho-pulse-speed, 8s)" repeatCount="indefinite" />
                )}
              </circle>

              {/* Label */}
              <text
                x={x}
                y={y + (y < cy ? -25 : 30)}
                textAnchor="middle"
                fill={isActive ? "var(--hiho-glow-color, #00ff00)" : "#666"}
                fontSize="9"
                fontFamily="monospace"
                fontWeight={isActive ? "bold" : "normal"}
                letterSpacing="0.1em"
              >
                {phase}
              </text>
            </g>
          );
        })}

        {/* Center label */}
        <text x={cx} y={cy - 5} textAnchor="middle" fill="white" fontSize="11" fontFamily="monospace" fontWeight="bold" opacity={0.6}>
          COMPOUND
        </text>
        <text x={cx} y={cy + 12} textAnchor="middle" fill="white" fontSize="9" fontFamily="monospace" opacity={0.3}>
          LOOP
        </text>
      </svg>
    </div>
  );
}
