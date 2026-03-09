"use client";

import Image from "next/image";

export type TriuneMode = "knower" | "thinker" | "doer";

interface TriuneNavProps {
  activeMode: TriuneMode;
  onModeChange: (mode: TriuneMode) => void;
  connected: boolean;
  onAnimaClick?: () => void;
}

const MODES: { id: TriuneMode; label: string; subtitle: string }[] = [
  { id: "knower", label: "KNOWER", subtitle: "Observatory" },
  { id: "thinker", label: "THINKER", subtitle: "Vault" },
  { id: "doer", label: "DOER", subtitle: "Cockpit" },
];

/**
 * Triune Self navigation header (FR12).
 * Three cognitive modes with the Anima Sigil breathing indicator.
 */
export default function TriuneNav({
  activeMode,
  onModeChange,
  connected,
  onAnimaClick,
}: TriuneNavProps) {
  return (
    <header className="flex items-center justify-between px-6 py-4 border-b border-white/5 bg-black/40 backdrop-blur-xl sticky top-0 z-50">
      {/* Logo + Brand */}
      <div className="flex items-center gap-3">
        <Image
          src="/cohezion-logo.png"
          alt="COHEZION"
          width={36}
          height={36}
          className="rounded-lg"
        />
        <div>
          <h1 className="text-sm font-bold tracking-[0.2em] text-white/90 font-mono">
            COHEZION
          </h1>
          <p className="text-[10px] text-gray-500 font-mono tracking-wider">
            The Nexus of Coherence
          </p>
        </div>
      </div>

      {/* Mode Tabs */}
      <nav className="flex gap-1">
        {MODES.map((mode) => {
          const active = activeMode === mode.id;
          return (
            <button
              key={mode.id}
              onClick={() => onModeChange(mode.id)}
              className={`
                px-5 py-2 rounded-lg font-mono text-xs tracking-wider transition-all duration-300
                ${
                  active
                    ? "bg-white/10 text-white border border-white/10 shadow-[0_0_12px_var(--hiho-glow-color,#00ff00)20]"
                    : "text-gray-500 hover:text-gray-300 hover:bg-white/5"
                }
              `}
              style={
                active
                  ? {
                      borderBottomColor: "var(--hiho-glow-color, #00ff00)",
                      borderBottomWidth: "2px",
                    }
                  : undefined
              }
            >
              <div className="font-bold">{mode.label}</div>
              <div className="text-[9px] text-gray-400">{mode.subtitle}</div>
            </button>
          );
        })}
      </nav>

      {/* Anima Sigil — breathing indicator (click opens chat) */}
      <div className="flex items-center gap-3">
        <div
          onClick={onAnimaClick}
          className="w-9 h-9 rounded-full flex items-center justify-center text-lg font-bold cursor-pointer transition-all hover:scale-110"
          style={{
            color: "var(--hiho-glow-color, #00ff00)",
            animation: `hiho-pulse var(--hiho-pulse-speed, 8s) ease-in-out infinite`,
            border: "1px solid var(--hiho-glow-color, #00ff00)",
          }}
          title="Anima — system voice"
        >
          C
        </div>
        <div className="flex flex-col items-end">
          <span
            className="text-[10px] font-mono font-bold tracking-widest"
            style={{ color: connected ? "var(--hiho-glow-color)" : "#FF3B3B" }}
          >
            {connected ? "ONLINE" : "OFFLINE"}
          </span>
          <span className="text-[9px] text-gray-600 font-mono">ANIMA</span>
        </div>
      </div>
    </header>
  );
}
