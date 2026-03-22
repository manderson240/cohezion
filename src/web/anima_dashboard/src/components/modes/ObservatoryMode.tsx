"use client";

import { useState, useCallback } from "react";
import dynamic from "next/dynamic";
import { useUniverse } from "@/context/UniverseProvider";
import OuroborosControlRoom from "@/components/OuroborosControlRoom";
import SnapshotGallery from "@/components/SnapshotGallery";
import ReEntryNarrative from "@/components/ReEntryNarrative";
import ProvenanceTag from "@/components/ProvenanceTag";
import PersistenceDiagram from "@/components/PersistenceDiagram";

// Dynamic import with SSR disabled — prevents Three.js/R3F hydration errors and WebGL console noise
const TensorBeamVisualizer = dynamic(
  () => import("@/components/TensorBeamVisualizer"),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-[600px] bg-black/90 rounded-xl flex items-center justify-center">
        <span className="text-emerald-500/50 font-mono text-xs tracking-widest animate-pulse">
          INITIALIZING TENSOR BEAM...
        </span>
      </div>
    ),
  }
);

/**
 * KNOWER mode — Observatory.
 * Wraps existing visualization components, feeding them from the shared
 * UniverseProvider context (SSE stream) instead of per-component polling.
 */
export default function ObservatoryMode() {
  const { state, report, perturb, fetchReport } = useUniverse();
  const [localReport, setLocalReport] = useState(report);
  const [reportLoading, setReportLoading] = useState(false);

  const coherence = state?.coherence ?? 0.5;
  const caGrid = state?.ca_grid ?? [];
  const caGridDensity =
    caGrid.length > 0 ? caGrid.reduce((s, v) => s + v, 0) / caGrid.length : 0;
  const evoCount = state?.evo_states.length ?? 0;

  const handleFetchReport = useCallback(async () => {
    setReportLoading(true);
    try {
      const r = await fetchReport();
      if (r) setLocalReport(r);
    } finally {
      setReportLoading(false);
    }
  }, [fetchReport]);

  // Use SSE report if available, else local fetch
  const displayReport = report ?? localReport;

  return (
    <div className="grid grid-cols-1 xl:grid-cols-12 gap-8">
      {/* Re-Entry Narrative — shows once per session on first Observatory visit */}
      <div className="xl:col-span-12">
        <ReEntryNarrative />
      </div>

      {/* Left Column: Visualizations */}
      <div className="xl:col-span-8 flex flex-col gap-8">
        <section>
          <h2 className="text-xl font-bold mb-4 font-mono text-gray-300">
            {"// SPATIAL MANIFOLD"}
          </h2>
          <TensorBeamVisualizer
            coherence={coherence}
            caGridDensity={caGridDensity}
            evoCount={evoCount}
          />
        </section>

        <section>
          <SnapshotGallery
            caGrid={caGrid}
            coherence={coherence}
            tick={state?.tick}
          />
        </section>

        {/* Persistent Homology Overlay (FR22) */}
        {displayReport?.topology && (
          <section>
            <PersistenceDiagram topology={displayReport.topology} />
          </section>
        )}
      </div>

      {/* Right Column: Telemetry + Controls */}
      <div className="xl:col-span-4 flex flex-col gap-8">
        <OuroborosControlRoom />

        {/* Mycelium Telemetry */}
        <div className="bg-white/[0.02] backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-2xl relative overflow-hidden group">
          <h3 className="text-lg font-bold mb-6 font-mono text-cyan-400 flex items-center gap-2">
            <span className="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-ping mr-1" />
            MYCELIUM TELEMETRY
          </h3>
          <div className="space-y-5">
            {[
              { label: "Active EVOs", value: String(evoCount), source: "EVOInitializationFactory.create_evo()" },
              { label: "Mean Coherence", value: coherence.toFixed(4), source: "HIHOStabilizationEngine.apply_hiho_loop()" },
              {
                label: "CA Fabric Density",
                value: `${(caGridDensity * 100).toFixed(1)}%`,
                color: "text-emerald-400",
                source: "CellularAutomataEngine.evolve()",
              },
              {
                label: "Simulation Tick",
                value: String(state?.tick ?? 0),
                color: "text-amber-400",
                source: "UniverseStateService.tick()",
              },
            ].map((item) => (
              <div
                key={item.label}
                className="flex justify-between items-center border-b border-white/5 pb-3"
              >
                <span className="text-sm text-gray-400 font-mono">
                  {item.label}
                </span>
                <ProvenanceTag source={item.source}>
                  <span
                    className={`font-bold font-mono ${item.color ?? "text-white"}`}
                  >
                    {item.value}
                  </span>
                </ProvenanceTag>
              </div>
            ))}
          </div>

          {/* Perturbation Controls */}
          <div className="mt-6">
            <div className="text-[10px] text-gray-500 font-mono tracking-widest mb-3">
              PERTURBATION INJECTORS
            </div>
            <div className="grid grid-cols-2 gap-2">
              {[
                {
                  label: "SPIKE +0.3",
                  kind: "coherence_spike",
                  mag: 0.3,
                  color: "amber",
                },
                {
                  label: "COLLAPSE -0.3",
                  kind: "coherence_collapse",
                  mag: 0.3,
                  color: "red",
                },
                {
                  label: "CHARGE +0.5",
                  kind: "charge_injection",
                  mag: 0.5,
                  color: "blue",
                },
                {
                  label: "CA RESET",
                  kind: "ca_reset",
                  mag: 0.0,
                  color: "emerald",
                },
              ].map((btn) => (
                <button
                  key={btn.kind}
                  onClick={() => perturb(btn.kind, btn.mag)}
                  className={`py-2 px-3 bg-${btn.color}-500/10 hover:bg-${btn.color}-500/20 border border-${btn.color}-500/20 rounded-lg text-[10px] font-mono font-bold text-${btn.color}-400 transition-all tracking-wider`}
                >
                  {btn.label}
                </button>
              ))}
            </div>
          </div>

          {/* Synthesis Report */}
          <button
            onClick={handleFetchReport}
            disabled={reportLoading}
            className="mt-4 w-full py-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs tracking-widest font-mono font-bold text-gray-300 disabled:opacity-50"
          >
            {reportLoading ? "FETCHING..." : "FETCH SYNTHESIS REPORT"}
          </button>

          {displayReport && (
            <div className="mt-6 p-5 bg-[#050505]/90 rounded-xl border border-cyan-500/20 font-mono text-[11px]">
              <div className="flex justify-between items-center mb-4">
                <span
                  className={`text-sm font-bold tracking-widest ${
                    displayReport.hiho_status.stability === "stable"
                      ? "text-emerald-400"
                      : displayReport.hiho_status.stability === "warning"
                        ? "text-amber-400"
                        : "text-red-400"
                  }`}
                >
                  HIHO {displayReport.hiho_status.stability.toUpperCase()}
                </span>
              </div>
              <div className="text-cyan-300/80">{displayReport.summary}</div>
              <div className="grid grid-cols-2 gap-3 mt-3">
                {displayReport.evo_health.map((evo) => (
                  <div
                    key={evo.id}
                    className="p-2 bg-black/40 rounded border border-white/5"
                  >
                    <div className="text-gray-400">EVO-{evo.id}</div>
                    <div
                      className={`font-bold ${
                        evo.charge_status === "nominal"
                          ? "text-emerald-400"
                          : evo.charge_status === "decaying"
                            ? "text-amber-400"
                            : "text-red-400"
                      }`}
                    >
                      {evo.charge_status.toUpperCase()}{" "}
                      {evo.charge_density.toFixed(3)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
