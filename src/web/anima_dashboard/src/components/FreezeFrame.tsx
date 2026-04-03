"use client";

import { useState } from "react";
import { useUniverse } from "@/context/UniverseProvider";

/**
 * Freeze-Frame Capture (Layer 5).
 * Snapshots current universe state and saves as a vault Decision.
 */
export default function FreezeFrame() {
  const { state } = useUniverse();
  const [annotation, setAnnotation] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [saved, setSaved] = useState(false);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

  const handleSave = async () => {
    if (!state) return;
    const decision = {
      question: `Save freeze-frame: Tick ${state.tick}, coherence ${(state.coherence ?? 0).toFixed(4)}. Annotation: ${annotation}`,
    };
    try {
      await fetch(`${API_BASE}/api/anima/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(decision),
      });
      setSaved(true);
      setTimeout(() => {
        setShowModal(false);
        setSaved(false);
        setAnnotation("");
      }, 2000);
    } catch {
      // Non-blocking
    }
  };

  return (
    <>
      <button
        onClick={() => setShowModal(true)}
        className="w-full py-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs tracking-widest font-mono font-bold text-gray-300 transition-all"
      >
        FREEZE FRAME — CAPTURE STATE
      </button>

      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
          <div className="max-w-md w-full mx-4 p-6 bg-[#0a0a0a] border border-white/10 rounded-2xl">
            <h3
              className="text-lg font-bold font-mono tracking-wider mb-4"
              style={{ color: "var(--hiho-glow-color, #00ff00)" }}
            >
              FREEZE FRAME
            </h3>
            <div className="space-y-3 text-xs font-mono text-gray-400 mb-4">
              <div className="flex justify-between">
                <span>Tick</span>
                <span className="text-white">{state?.tick ?? 0}</span>
              </div>
              <div className="flex justify-between">
                <span>Coherence</span>
                <span className="text-white">
                  {(state?.coherence ?? 0.5).toFixed(4)}
                </span>
              </div>
              <div className="flex justify-between">
                <span>EVOs</span>
                <span className="text-white">{state?.evo_states.length ?? 0}</span>
              </div>
            </div>
            <textarea
              value={annotation}
              onChange={(e) => setAnnotation(e.target.value)}
              placeholder="Add annotation..."
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm font-mono text-white placeholder-gray-600 focus:outline-none mb-4 resize-none h-20"
            />
            <div className="flex gap-2">
              <button
                onClick={handleSave}
                disabled={saved}
                className="flex-1 py-2 rounded-lg font-mono text-xs font-bold tracking-wider"
                style={{
                  backgroundColor: saved
                    ? "rgba(0,255,0,0.2)"
                    : "rgba(0,255,0,0.1)",
                  color: "var(--hiho-glow-color, #00ff00)",
                  border: "1px solid var(--hiho-glow-color, #00ff00)40",
                }}
              >
                {saved ? "SAVED" : "SAVE TO VAULT"}
              </button>
              <button
                onClick={() => {
                  setShowModal(false);
                  setAnnotation("");
                }}
                className="px-4 py-2 text-gray-500 hover:text-white text-xs font-mono"
              >
                CANCEL
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
