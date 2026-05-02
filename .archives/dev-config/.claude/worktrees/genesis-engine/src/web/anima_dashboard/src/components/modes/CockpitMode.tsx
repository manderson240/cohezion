"use client";

import { useUniverse } from "@/context/UniverseProvider";
import CompoundLoopViz from "@/components/CompoundLoopViz";
import ArchitectureGraph from "@/components/ArchitectureGraph";

/**
 * DOER mode — Cockpit.
 * Compound loop visualization + live architecture graph.
 */
export default function CockpitMode() {
  const { state } = useUniverse();

  // Derive current phase from tick (cycles through 5 phases)
  const currentPhase = state ? (state.tick % 50 < 10 ? 0 : state.tick % 50 < 20 ? 1 : state.tick % 50 < 30 ? 2 : state.tick % 50 < 40 ? 3 : 4) : 2;

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div className="text-center">
        <h2
          className="text-3xl font-bold font-mono tracking-wider mb-2"
          style={{ color: "var(--hiho-glow-color, #00ff00)" }}
        >
          DOER
        </h2>
        <p className="text-gray-500 font-mono text-sm tracking-widest">
          COCKPIT MODE — Compound Engineering Loop
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Compound Loop */}
        <div className="bg-white/[0.02] backdrop-blur-xl border border-white/10 rounded-2xl p-6">
          <h3 className="text-sm font-bold font-mono tracking-widest text-gray-400 mb-4">
            COMPOUND LOOP
          </h3>
          <CompoundLoopViz currentPhase={currentPhase} />
          <div className="text-center mt-4 text-[11px] text-gray-600 font-mono">
            Coherence: {(state?.coherence ?? 0.5).toFixed(4)} | Tick: {state?.tick ?? 0}
          </div>
        </div>

        {/* Architecture Graph */}
        <div>
          <h3 className="text-sm font-bold font-mono tracking-widest text-gray-400 mb-4">
            ARCHITECTURE GRAPH
          </h3>
          <ArchitectureGraph />
        </div>
      </div>
    </div>
  );
}
