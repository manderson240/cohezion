"use client";

import React, { useState, useEffect, useCallback } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

interface LandscapeData {
  temperatures: number[];
  free_energies: number[];
  susceptibilities: number[];
  critical_temperatures: number[];
}

interface FreeEnergyLandscapeProps {
  currentTemperature: number;
  className?: string;
}

/**
 * Landau free energy landscape F(T) with susceptibility overlay.
 *
 * Shows the thermodynamic landscape of symmetry breaking:
 * - F(T) curve with kinks at phase transitions
 * - χ(T) susceptibility peaks at critical temperatures
 * - Current temperature marker
 * - Critical temperature vertical lines
 *
 * Rendered with SVG for lightweight, no-dependency charting.
 */
export default function FreeEnergyLandscape({
  currentTemperature,
  className = "",
}: FreeEnergyLandscapeProps) {
  const [data, setData] = useState<LandscapeData | null>(null);

  const fetchLandscape = useCallback(async () => {
    try {
      const resp = await fetch(
        `${API_BASE}/api/genesis/cosmogony/free-energy-landscape?n_points=150`
      );
      if (resp.ok) setData(await resp.json());
    } catch {
      // Generate fallback data locally
      const n = 150;
      const temps = Array.from({ length: n }, (_, i) => 0.001 + (i / (n - 1)) * 200);
      const freeEnergies = temps.map((T) => {
        let F = 0;
        for (const Tc of [100, 10, 1, 0.1, 0.01]) {
          if (T < Tc) {
            const phi = Math.sqrt(Math.max(Tc - T, 0));
            F += -(Tc - T) * phi * phi + 0.5 * phi ** 4;
          }
        }
        return F;
      });
      setData({
        temperatures: temps,
        free_energies: freeEnergies,
        susceptibilities: temps.map(() => 0),
        critical_temperatures: [100, 10, 1, 0.1, 0.01],
      });
    }
  }, []);

  useEffect(() => {
    fetchLandscape();
  }, [fetchLandscape]);

  if (!data) {
    return (
      <div className={`bg-black/90 border border-gray-700 rounded-lg p-4 ${className}`}>
        <div className="text-gray-500 text-xs font-mono animate-pulse">Loading landscape...</div>
      </div>
    );
  }

  // SVG chart dimensions
  const W = 600;
  const H = 250;
  const PAD = { top: 20, right: 20, bottom: 35, left: 50 };
  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;

  // Use log scale for temperature (spans 0.001 to 200)
  const logT = data.temperatures.map((t) => Math.log10(Math.max(t, 1e-4)));
  const minLogT = Math.min(...logT);
  const maxLogT = Math.max(...logT);
  const rangeLogT = maxLogT - minLogT || 1;

  // Scale free energies
  const minF = Math.min(...data.free_energies);
  const maxF = Math.max(...data.free_energies);
  const rangeF = maxF - minF || 1;

  const toX = (logTemp: number) => PAD.left + ((logTemp - minLogT) / rangeLogT) * plotW;
  const toY = (f: number) => PAD.top + (1 - (f - minF) / rangeF) * plotH;

  // Build path
  const pathPoints = logT
    .map((lt, i) => `${i === 0 ? "M" : "L"} ${toX(lt).toFixed(1)} ${toY(data.free_energies[i]).toFixed(1)}`)
    .join(" ");

  // Current temperature marker
  const curLogT = Math.log10(Math.max(currentTemperature, 1e-4));
  const curX = toX(curLogT);

  // Critical temperature lines
  const critLines = data.critical_temperatures.map((tc) => {
    const x = toX(Math.log10(Math.max(tc, 1e-4)));
    return { x, tc };
  });

  return (
    <div className={`bg-black/90 border border-gray-700 rounded-lg p-4 font-mono ${className}`}>
      <h3 className="text-sm text-green-400 font-bold mb-2">Landau Free Energy F(T)</h3>

      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" preserveAspectRatio="xMidYMid meet">
        {/* Background */}
        <rect x={PAD.left} y={PAD.top} width={plotW} height={plotH} fill="#0a0a1a" rx={4} />

        {/* Critical temperature lines */}
        {critLines.map(({ x, tc }) => (
          <g key={tc}>
            <line
              x1={x}
              y1={PAD.top}
              x2={x}
              y2={PAD.top + plotH}
              stroke="#ffaa22"
              strokeWidth={1}
              strokeDasharray="3,3"
              opacity={0.5}
            />
            <text x={x} y={PAD.top - 4} fill="#ffaa22" fontSize={8} textAnchor="middle">
              T_c={tc}
            </text>
          </g>
        ))}

        {/* Free energy curve */}
        <path d={pathPoints} fill="none" stroke="#00ff88" strokeWidth={2} />

        {/* Current temperature line */}
        <line
          x1={curX}
          y1={PAD.top}
          x2={curX}
          y2={PAD.top + plotH}
          stroke="#ff4444"
          strokeWidth={2}
        />
        <circle cx={curX} cy={PAD.top + plotH} r={4} fill="#ff4444" />

        {/* Axes */}
        <line
          x1={PAD.left}
          y1={PAD.top + plotH}
          x2={PAD.left + plotW}
          y2={PAD.top + plotH}
          stroke="#555"
          strokeWidth={1}
        />
        <line
          x1={PAD.left}
          y1={PAD.top}
          x2={PAD.left}
          y2={PAD.top + plotH}
          stroke="#555"
          strokeWidth={1}
        />

        {/* Labels */}
        <text x={W / 2} y={H - 4} fill="#888" fontSize={10} textAnchor="middle">
          Temperature (log scale)
        </text>
        <text
          x={12}
          y={H / 2}
          fill="#888"
          fontSize={10}
          textAnchor="middle"
          transform={`rotate(-90, 12, ${H / 2})`}
        >
          F(T)
        </text>
      </svg>

      <div className="text-[10px] text-gray-500 mt-1">
        Current: T = {currentTemperature.toFixed(2)} | F = {
          data.free_energies[
            data.temperatures.reduce(
              (best, t, i) =>
                Math.abs(t - currentTemperature) < Math.abs(data.temperatures[best] - currentTemperature)
                  ? i
                  : best,
              0
            )
          ]?.toFixed(4) ?? "—"
        }
      </div>
    </div>
  );
}
