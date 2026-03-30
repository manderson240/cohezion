"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";

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
  const [mode, setMode] = useState<"api" | "local">("api");
  const fallbackTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const generateLocalLandscape = useCallback((): LandscapeData => {
    const n = 150;
    const a = 1.0;
    const b = 1.0;
    const Tc = 10.0;
    const temps = Array.from({ length: n }, (_, i) => 0.001 + (i / (n - 1)) * 200);
    const freeEnergies = temps.map((T) => {
      // Landau: F = a*(T-Tc)*phi^2 + b*phi^4, phi = sqrt(a*(Tc-T)/(2b)) for T<Tc
      if (T < Tc) {
        const phi = Math.sqrt(a * (Tc - T) / (2 * b));
        return a * (T - Tc) * phi * phi + b * phi ** 4;
      }
      return 0;
    });
    const susceptibilities = temps.map((T) => {
      const delta = Math.abs(T - Tc);
      return delta > 0.001 ? 1 / (2 * a * delta) : 500;
    });
    return {
      temperatures: temps,
      free_energies: freeEnergies,
      susceptibilities,
      critical_temperatures: [100, 10, 1, 0.1, 0.01],
    };
  }, []);

  const fetchLandscape = useCallback(async () => {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 2000);
      const resp = await fetch(
        `${API_BASE}/api/genesis/cosmogony/free-energy-landscape?n_points=150`,
        { signal: controller.signal }
      );
      clearTimeout(timeout);
      if (resp.ok) {
        setData(await resp.json());
        setMode("api");
        return;
      }
    } catch {
      // Fall through to local computation
    }
    setData(generateLocalLandscape());
    setMode("local");
  }, [generateLocalLandscape]);

  useEffect(() => {
    // 2-second fallback timer
    fallbackTimer.current = setTimeout(() => {
      if (!data) {
        setData(generateLocalLandscape());
        setMode("local");
      }
    }, 2000);

    fetchLandscape();
    return () => {
      if (fallbackTimer.current) clearTimeout(fallbackTimer.current);
    };
  }, [fetchLandscape, generateLocalLandscape, data]);

  if (!data) {
    return (
      <div className={`bg-black/90 border border-gray-700 rounded-lg p-4 ${className}`}>
        <div className="text-gray-500 text-xs font-mono animate-pulse">Connecting to API... (local fallback in 2s)</div>
      </div>
    );
  }

  // --- Free Energy F(phi) curve for current temperature (SVG) ---
  const LANDAU_A = 1.0;
  const LANDAU_B = 1.0;
  const LANDAU_TC = 10.0;
  const phiRange = 20; // -phiRange/2 to +phiRange/2
  const nPhi = 100;
  const fPhiPoints: { phi: number; F: number }[] = [];
  for (let i = 0; i <= nPhi; i++) {
    const phi = -phiRange / 2 + (i / nPhi) * phiRange;
    const F = LANDAU_A * (currentTemperature - LANDAU_TC) * phi * phi + LANDAU_B * phi ** 4;
    fPhiPoints.push({ phi, F });
  }
  // Scale for F(phi) SVG
  const fPhiW = 300;
  const fPhiH = 180;
  const fPhiPad = 30;
  const minPhi = -phiRange / 2;
  const maxPhi = phiRange / 2;
  const minFPhi = Math.min(...fPhiPoints.map((p) => p.F));
  const maxFPhi = Math.max(...fPhiPoints.map((p) => p.F));
  const rangeFPhi = maxFPhi - minFPhi || 1;
  const toPhiX = (p: number) => fPhiPad + ((p - minPhi) / (maxPhi - minPhi)) * (fPhiW - 2 * fPhiPad);
  const toPhiY = (f: number) => fPhiPad + (1 - (f - minFPhi) / rangeFPhi) * (fPhiH - 2 * fPhiPad);
  const fPhiPath = fPhiPoints
    .map((p, i) => `${i === 0 ? "M" : "L"} ${toPhiX(p.phi).toFixed(1)} ${toPhiY(p.F).toFixed(1)}`)
    .join(" ");

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
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm text-green-400 font-bold">Landau Free Energy F(T)</h3>
        {mode === "local" && (
          <span className="text-[9px] px-2 py-0.5 bg-amber-500/20 text-amber-400 rounded border border-amber-500/30">
            Local Computation
          </span>
        )}
      </div>

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

      {/* F(phi) quartic curve for current temperature */}
      <div className="mt-4 pt-3 border-t border-gray-800">
        <h4 className="text-[11px] text-cyan-400 font-bold mb-2">
          F(phi) at T = {currentTemperature.toFixed(2)} — HIHO Well
        </h4>
        <svg viewBox={`0 0 ${fPhiW} ${fPhiH}`} className="w-full max-w-[400px]" preserveAspectRatio="xMidYMid meet">
          <rect x={fPhiPad} y={fPhiPad} width={fPhiW - 2 * fPhiPad} height={fPhiH - 2 * fPhiPad} fill="#0a0a1a" rx={4} />
          {/* Zero line */}
          <line
            x1={fPhiPad} y1={toPhiY(0)} x2={fPhiW - fPhiPad} y2={toPhiY(0)}
            stroke="#333" strokeWidth={0.5} strokeDasharray="4,4"
          />
          {/* F(phi) curve */}
          <path d={fPhiPath} fill="none" stroke="#10b981" strokeWidth={2} />
          {/* phi=0 vertical marker */}
          <line
            x1={toPhiX(0)} y1={fPhiPad} x2={toPhiX(0)} y2={fPhiH - fPhiPad}
            stroke="#555" strokeWidth={0.5} strokeDasharray="2,2"
          />
          {/* Axes labels */}
          <text x={fPhiW / 2} y={fPhiH - 4} fill="#666" fontSize={9} textAnchor="middle">phi (order parameter)</text>
          <text x={8} y={fPhiH / 2} fill="#666" fontSize={9} textAnchor="middle" transform={`rotate(-90, 8, ${fPhiH / 2})`}>F(phi)</text>
          {/* HIHO annotation */}
          {currentTemperature < LANDAU_TC && (
            <text x={fPhiW / 2} y={fPhiPad + 12} fill="#10b981" fontSize={8} textAnchor="middle">
              Double well: symmetry broken (T &lt; Tc={LANDAU_TC})
            </text>
          )}
          {currentTemperature >= LANDAU_TC && (
            <text x={fPhiW / 2} y={fPhiPad + 12} fill="#fbbf24" fontSize={8} textAnchor="middle">
              Single well: symmetric phase (T &gt;= Tc={LANDAU_TC})
            </text>
          )}
        </svg>
      </div>
    </div>
  );
}
