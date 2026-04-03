"use client";

import { useState, useEffect, useRef } from "react";
import { useUniverse } from "@/context/UniverseProvider";

/**
 * Bottom narration bar showing template-generated narration from live metrics.
 * Tier 1 (template) always works — no model dependency.
 */
export default function AnimaNarrationBar() {
  const { state, report } = useUniverse();
  const [displayText, setDisplayText] = useState("");
  const prevTextRef = useRef("");

  // Compute narration from live data (empty string when no state yet)
  const narration = state
    ? (() => {
        const coherence = state.coherence;
        const caGrid = state.ca_grid;
        const caActive = caGrid.reduce((s, v) => s + v, 0);
        const caTotal = caGrid.length || 256;
        const evoCount = state.evo_states.length;
        const nominalCount = state.evo_states.filter((e) => e.charge_density > 0.8).length;
        const stability = report?.hiho_status.stability ?? (
          Math.abs(coherence - 0.5) < 0.1 ? "STABLE" : Math.abs(coherence - 0.5) < 0.3 ? "WARNING" : "CRITICAL"
        );
        return `HIHO ${typeof stability === "string" ? stability.toUpperCase() : stability}: ${(coherence ?? 0).toFixed(4)} coherence. CA Rule 30: ${caActive}/${caTotal} active. ${nominalCount}/${evoCount} EVOs nominal. [tick ${state.tick}]`;
      })()
    : "";

  // Typewriter effect — hooks called unconditionally (React rules of hooks)
  useEffect(() => {
    if (!narration || narration === prevTextRef.current) return;
    prevTextRef.current = narration;

    let i = 0;
    setDisplayText("");
    const timer = setInterval(() => {
      i++;
      setDisplayText(narration.slice(0, i));
      if (i >= narration.length) clearInterval(timer);
    }, 8);

    return () => clearInterval(timer);
  }, [narration]);

  // Pre-SSE placeholder
  if (!state) {
    return (
      <footer
        className="fixed bottom-0 left-0 right-0 px-6 py-3 bg-black/80 backdrop-blur-xl border-t z-40 font-mono text-[11px] text-gray-500 leading-relaxed"
        style={{ borderColor: "var(--hiho-glow-color, #00ff00)20" }}
      >
        <div className="max-w-[1920px] mx-auto flex items-center gap-3">
          <span className="w-2 h-2 rounded-full bg-gray-600 flex-shrink-0 animate-pulse" />
          <span className="truncate">Awaiting first universe tick...</span>
        </div>
      </footer>
    );
  }

  return (
    <footer
      className="fixed bottom-0 left-0 right-0 px-6 py-3 bg-black/80 backdrop-blur-xl border-t z-40 font-mono text-[11px] text-gray-400 leading-relaxed"
      style={{ borderColor: "var(--hiho-glow-color, #00ff00)20" }}
    >
      <div className="max-w-[1920px] mx-auto flex items-center gap-3">
        <span
          className="w-2 h-2 rounded-full flex-shrink-0"
          style={{
            backgroundColor: "var(--hiho-glow-color, #00ff00)",
            animation: "hiho-pulse var(--hiho-pulse-speed, 8s) ease-in-out infinite",
          }}
        />
        <span className="truncate">{displayText}<span className="animate-pulse">_</span></span>
      </div>
    </footer>
  );
}
