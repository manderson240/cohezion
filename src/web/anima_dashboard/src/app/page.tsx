"use client";

import { useState } from "react";
import { UniverseProvider, useUniverse } from "@/context/UniverseProvider";
import HIHOBridge from "@/components/HIHOBridge";
import TriuneNav, { type TriuneMode } from "@/components/TriuneNav";
import AnimaNarrationBar from "@/components/AnimaNarrationBar";
import AnimaChatPanel from "@/components/AnimaChatPanel";
import ObservatoryMode from "@/components/modes/ObservatoryMode";
import VaultMode from "@/components/modes/VaultMode";
import CockpitMode from "@/components/modes/CockpitMode";

const MODE_CLASSES: Record<TriuneMode, string> = {
  knower: "mode-enter-knower",
  thinker: "mode-enter-thinker",
  doer: "mode-enter-doer",
};

export default function Home() {
  return (
    <UniverseProvider>
      <AnimaDashboard />
    </UniverseProvider>
  );
}

function AnimaDashboard() {
  const [mode, setMode] = useState<TriuneMode>("knower");
  const [chatOpen, setChatOpen] = useState(false);
  const { connected } = useUniverse();

  return (
    <div className="min-h-screen bg-[var(--background)] text-[var(--foreground)] font-sans relative overflow-hidden">
      {/* HIHO CSS Bridge (headless — sets CSS vars from coherence) */}
      <HIHOBridge />

      {/* Ambient background glow driven by HIHO state */}
      <div
        className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] blur-[120px] rounded-full pointer-events-none opacity-10"
        style={{ backgroundColor: "var(--hiho-glow-color, #00ff00)" }}
      />
      <div
        className="absolute bottom-[-20%] right-[-10%] w-[60%] h-[60%] blur-[150px] rounded-full pointer-events-none opacity-10"
        style={{ backgroundColor: "var(--hiho-glow-color, #00ff00)" }}
      />

      {/* Triune Navigation Header */}
      <TriuneNav
        activeMode={mode}
        onModeChange={setMode}
        connected={connected}
        onAnimaClick={() => setChatOpen((p) => !p)}
      />

      {/* Mode Content with ritualized transitions (NFR12) */}
      <main className="p-6 lg:p-12 relative z-10 max-w-[1920px] mx-auto pb-20">
        <div key={mode} className={MODE_CLASSES[mode]}>
          {mode === "knower" && <ObservatoryMode />}
          {mode === "thinker" && <VaultMode />}
          {mode === "doer" && <CockpitMode />}
        </div>
      </main>

      {/* Anima Chat Panel (slide-out from right, unmounted when closed) */}
      {chatOpen && <AnimaChatPanel open={chatOpen} onClose={() => setChatOpen(false)} />}

      {/* Anima Narration Bar (Tier 1: template) */}
      <AnimaNarrationBar />

      {/* Footer */}
      <footer className="fixed bottom-12 left-0 right-0 text-center text-[10px] text-gray-600 font-mono z-30">
        COHEZION v1.0.2 // TRIUNE SELF // 12D COMPOUND ENGINEERING
      </footer>
    </div>
  );
}
