"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import dynamic from "next/dynamic";
import { useSonification, type PhysicsState } from "@/hooks/useSonification";
import { useNarration } from "@/hooks/useNarration";
import { useCosmogony } from "@/hooks/useCosmogony";
import { useAGUIStream } from "@/hooks/useAGUIStream";

// Dynamic imports for Three.js components (SSR-incompatible)
const GenesisScene = dynamic(
  () => import("@/components/genesis/GenesisScene"),
  { ssr: false, loading: () => <LoadingScreen /> }
);
const BlochSphere = dynamic(
  () => import("@/components/genesis/BlochSphere"),
  { ssr: false }
);

function LoadingScreen() {
  return (
    <div className="flex items-center justify-center h-[600px] bg-[#020208] rounded-xl border border-gray-800">
      <div className="text-gray-500 font-mono text-sm animate-pulse">
        Loading the cosmos...
      </div>
    </div>
  );
}

// Dynamic imports for non-Three.js components
const CosmogonyTimeline = dynamic(
  () => import("@/components/genesis/CosmogonyTimeline"),
  { ssr: false }
);
const FreeEnergyLandscape = dynamic(
  () => import("@/components/genesis/FreeEnergyLandscape"),
  { ssr: false }
);
const CompoundPipelineViz = dynamic(
  () => import("@/components/genesis/CompoundPipelineViz"),
  { ssr: false }
);
const CacheTopologyViz = dynamic(
  () => import("@/components/genesis/CacheTopologyViz"),
  { ssr: false }
);
const ThermodynamicStateLive = dynamic(
  () => import("@/components/genesis/ThermodynamicStateLive"),
  { ssr: false }
);
const SwarmTopologyViz = dynamic(
  () => import("@/components/genesis/SwarmTopologyViz"),
  { ssr: false }
);
const FlumeLatentViz = dynamic(
  () => import("@/components/genesis/FlumeLatentViz"),
  { ssr: false }
);

type GenesisTab = "cosmogony" | "bloch" | "thermo" | "compound" | "swarm" | "cache" | "flume" | "about";

export default function GenesisPage() {
  const [tab, setTab] = useState<GenesisTab>("cosmogony");
  const sonification = useSonification();
  const narration = useNarration();
  const cosmogony = useCosmogony();
  const agui = useAGUIStream();

  // Wire 7: AG-UI mode — when connected, overlay AG-UI state on cosmogony
  const isAGUIActive = agui.connected && agui.running;
  const [hasStarted, setHasStarted] = useState(false);

  // Wire cosmogony state changes into sonification
  const prevSymRef = React.useRef<string>("");
  useEffect(() => {
    if (!cosmogony.state || !sonification.playing) return;

    const s = cosmogony.state;
    const physicsState: PhysicsState = {
      coherence: 1.0 - Math.abs((s.order_parameters?.hiho_coherence ?? 0) - 0.5) * 2,
      entropy: s.landau_free_energy > 0 ? Math.log(1 + s.landau_free_energy) : 0,
      temperature: s.temperature,
      spinRotation: 0,
      spinPrecession: 0,
      chargPolarity: 0,
      gaugeCurvature: Math.abs(s.landau_free_energy),
      symmetry: s.symmetry,
    };
    sonification.update(physicsState);

    // Trigger impact sound on symmetry transitions
    if (s.symmetry !== prevSymRef.current && prevSymRef.current !== "") {
      sonification.triggerTransition(prevSymRef.current, s.symmetry);
      // Auto-narrate the new stage
      if (!narration.muted) {
        narration.narrateStage(s.symmetry);
      }
    }
    prevSymRef.current = s.symmetry;
  }, [cosmogony.state, sonification, narration]);

  // --- Cinematic sonification callbacks for GenesisScene ---
  const handleVoidStart = useCallback(() => {
    sonification.startVoidDrone();
  }, [sonification]);

  const handleExplosion = useCallback(() => {
    sonification.triggerExplosion();
    setHasStarted(true);
  }, [sonification]);

  const handleFabricSplit = useCallback(() => {
    sonification.startFabricChord();
  }, [sonification]);

  const handleSettle = useCallback(() => {
    sonification.settleToSustainedPad();
  }, [sonification]);

  // Trigger void narration when Genesis tab first loads
  const voidNarratedRef = useRef(false);
  useEffect(() => {
    if (tab === "cosmogony" && !narration.muted && !voidNarratedRef.current) {
      voidNarratedRef.current = true;
      // Small delay to let the scene render first
      const timer = setTimeout(() => {
        narration.narrateStage("void");
      }, 1500);
      return () => clearTimeout(timer);
    }
  }, [tab, narration]);

  const tabs: { key: GenesisTab; label: string; desc: string }[] = [
    { key: "cosmogony", label: "Genesis", desc: "From Nothing to Everything" },
    { key: "bloch", label: "SPIN Lab", desc: "Interactive Bloch Sphere" },
    { key: "thermo", label: "Thermo", desc: "Statistical Mechanics" },
    { key: "compound", label: "Compound", desc: "11-Step Pipeline" },
    { key: "swarm", label: "Swarm", desc: "TDA Topology" },
    { key: "cache", label: "Cache/Cost", desc: "Optimization" },
    { key: "flume", label: "FLUME", desc: "Latent Space" },
    { key: "about", label: "About", desc: "The Mathematics" },
  ];

  return (
    <div className="min-h-screen bg-[#020208] text-gray-200 font-sans">
      {/* Header */}
      <header className="border-b border-gray-800 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-mono text-green-400 font-bold">
            The Genesis Engine
          </h1>
          <p className="text-xs text-gray-500 font-mono">
            Cohezion Cosmology Grounded in Unified Physics
          </p>
        </div>

        <div className="flex items-center gap-4">
          {/* Audio controls */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => sonification.playing ? sonification.stop() : sonification.start()}
              className={`px-3 py-1 rounded text-xs font-mono border transition-colors ${
                sonification.playing
                  ? "border-green-500 text-green-400 bg-green-900/20"
                  : "border-gray-600 text-gray-400 hover:border-gray-400"
              }`}
            >
              {sonification.playing ? "Sound ON" : "Sound OFF"}
            </button>

            {sonification.playing && (
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={sonification.volume}
                onChange={(e) => sonification.setVolume(parseFloat(e.target.value))}
                className="w-16 accent-green-500"
                title="Volume"
              />
            )}
          </div>

          {/* Narration controls */}
          <button
            onClick={() => narration.setMuted(!narration.muted)}
            className={`px-3 py-1 rounded text-xs font-mono border ${
              narration.muted
                ? "border-gray-600 text-gray-500"
                : "border-cyan-600 text-cyan-400"
            }`}
          >
            Narration {narration.muted ? "OFF" : "ON"}
          </button>

          {/* Back to dashboard */}
          <a
            href="/"
            className="px-3 py-1 rounded text-xs font-mono border border-gray-600 text-gray-400 hover:border-gray-400"
          >
            Dashboard
          </a>
        </div>
      </header>

      {/* Cinematic narration overlay — removed from header, now rendered over the 3D scene below */}

      {/* Tab navigation */}
      <nav className="border-b border-gray-800 px-6">
        <div className="flex gap-1">
          {tabs.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`px-4 py-3 text-sm font-mono transition-colors border-b-2 ${
                tab === t.key
                  ? "text-green-400 border-green-400"
                  : "text-gray-500 border-transparent hover:text-gray-300"
              }`}
            >
              <span className="font-bold">{t.label}</span>
              <span className="hidden sm:inline text-xs text-gray-600 ml-2">
                {t.desc}
              </span>
            </button>
          ))}
        </div>
      </nav>

      {/* Content */}
      <main className="p-6 max-w-[1920px] mx-auto">
        {tab === "cosmogony" && (
          <div className="relative">
            <div className="grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-6">
              <GenesisScene
                onVoidStart={handleVoidStart}
                onExplosion={handleExplosion}
                onFabricSplit={handleFabricSplit}
                onSettle={handleSettle}
              />
              <div
                style={{
                  opacity: hasStarted ? 1 : 0,
                  transition: "opacity 2s ease-in",
                  pointerEvents: hasStarted ? "auto" : "none",
                }}
              >
                <CosmogonyTimeline
                  currentStage={cosmogony.state?.stage ?? -1}
                  currentTemperature={cosmogony.state?.temperature ?? 200}
                />
              </div>
            </div>

            {/* Cinematic narration overlay — positioned over the 3D scene */}
            {narration.currentText && (
              <div
                className="absolute left-0 right-0 flex justify-center pointer-events-none"
                style={{ bottom: "12%", zIndex: 20 }}
              >
                <div
                  className="narration-overlay max-w-[600px] px-[30px] py-[20px] rounded-lg text-center"
                  style={{
                    background: "rgba(0, 0, 0, 0.4)",
                    backdropFilter: "blur(8px)",
                    WebkitBackdropFilter: "blur(8px)",
                    animation: "narrationFadeIn 0.5s ease-out",
                  }}
                >
                  <p
                    className="font-mono italic"
                    style={{
                      fontSize: "clamp(16px, 2vw, 20px)",
                      letterSpacing: "0.05em",
                      color: "rgba(255, 255, 255, 0.85)",
                      textShadow: "0 0 12px rgba(0, 200, 255, 0.3), 0 0 4px rgba(0, 200, 255, 0.15)",
                      lineHeight: 1.6,
                    }}
                  >
                    &ldquo;{narration.currentText}&rdquo;
                  </p>
                </div>
              </div>
            )}
          </div>
        )}
        {tab === "bloch" && <BlochSphere />}
        {tab === "thermo" && (
          <div className="space-y-6">
            <ThermodynamicStateLive />
            <FreeEnergyLandscape
              currentTemperature={cosmogony.state?.temperature ?? 200}
            />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-black/90 border border-gray-700 rounded-lg p-4 font-mono">
                <h3 className="text-sm text-green-400 font-bold mb-2">Order Parameters</h3>
                {cosmogony.state?.order_parameters &&
                  Object.entries(cosmogony.state.order_parameters).map(([key, val]) => (
                    <div key={key} className="flex justify-between text-[11px] mb-1">
                      <span className="text-gray-400">{key.replace(/_/g, " ")}:</span>
                      <span className={val > 0.01 ? "text-cyan-400" : "text-gray-600"}>
                        {(val as number).toFixed(4)}
                      </span>
                    </div>
                  ))}
              </div>
              <div className="bg-black/90 border border-gray-700 rounded-lg p-4 font-mono">
                <h3 className="text-sm text-green-400 font-bold mb-2">Thermodynamic State</h3>
                <div className="space-y-1 text-[11px]">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Temperature:</span>
                    <span className="text-cyan-400">{cosmogony.state?.temperature.toFixed(4)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Symmetry:</span>
                    <span className="text-yellow-400">{cosmogony.state?.symmetry}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Landau F:</span>
                    <span className="text-green-400">{cosmogony.state?.landau_free_energy.toFixed(6)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Fisher λ_max:</span>
                    <span className="text-purple-400">{cosmogony.state?.fisher_eigenvalue_max.toFixed(4)}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
        {tab === "compound" && (
          <div className="space-y-6">
            <CompoundPipelineViz activeStep={3} />
            <div className="bg-black/90 border border-gray-700 rounded-lg p-4 font-mono">
              <h3 className="text-sm text-green-400 font-bold mb-2">The Learning Loop</h3>
              <p className="text-[11px] text-gray-400 leading-relaxed">
                The compound engineering pipeline is the beating heart of Cohezion.
                Every task flows through 11 steps — from vault experience lookup through
                execution, quality gating, journey tracking, metrics collection,
                retrospection, and skill refinement. Each cycle makes the next one better.
                This is not just execution — it is autonomous learning.
              </p>
            </div>
          </div>
        )}
        {tab === "swarm" && (
          <div className="space-y-6">
            <SwarmTopologyViz />
            <div className="bg-black/90 border border-gray-700 rounded-lg p-4 font-mono">
              <h3 className="text-sm text-green-400 font-bold mb-2">Topology-Aware Routing</h3>
              <p className="text-[11px] text-gray-400 leading-relaxed">
                The TopologicalRouter uses persistent homology to classify agents into three regimes:
                <strong className="text-green-400"> Exploit</strong> (stable cluster, send familiar tasks),
                <strong className="text-cyan-400"> Explore</strong> (between clusters, send novel tasks),
                <strong className="text-red-400"> Pivot</strong> (stuck in loops, needs strategy change).
                This goes beyond visualization — TDA DRIVES routing decisions, producing
                topologically-informed agent assignments.
              </p>
            </div>
          </div>
        )}
        {tab === "cache" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <CacheTopologyViz />
            <div className="bg-black/90 border border-gray-700 rounded-lg p-4 font-mono">
              <h3 className="text-sm text-green-400 font-bold mb-2">Cost Optimization</h3>
              <div className="space-y-3 text-[11px] text-gray-400">
                <div className="flex justify-between">
                  <span>CostAwareRouter savings:</span>
                  <span className="text-green-400 font-bold">27.3%</span>
                </div>
                <div className="flex justify-between">
                  <span>Routing strategy:</span>
                  <span className="text-cyan-400">Simple→phi3 | Medium→qwen | Complex→deepseek</span>
                </div>
                <div className="flex justify-between">
                  <span>Semantic cache hit rate:</span>
                  <span className="text-green-400">95%+</span>
                </div>
                <p className="text-gray-500 mt-2 italic text-[10px]">
                  The L1 hash cache handles exact matches. L2 uses FLUME VAE cosine similarity
                  (not string matching) to find semantically equivalent queries. L3 async vault
                  lookup catches long-tail reuse patterns.
                </p>
              </div>
            </div>
          </div>
        )}
        {tab === "flume" && (
          <div className="space-y-6">
            <FlumeLatentViz />
            <div className="bg-black/90 border border-gray-700 rounded-lg p-4 font-mono">
              <h3 className="text-sm text-green-400 font-bold mb-2">FLUME: The Enabling Innovation</h3>
              <p className="text-[11px] text-gray-400 leading-relaxed">
                FLUME (Fluid Latent Understanding through Manifold Encoding) is the 256D VAE
                that enables everything. The Fisher information metric on the FLUME latent space
                simultaneously defines: (1) the natural geometry of the latent space,
                (2) the Riemannian metric for Lagrangian dynamics, (3) the thermodynamic metric
                for entropy and free energy, and (4) the optimal 12D projection. Without FLUME,
                there is no manifold, no geometry, no physics — just numbers.
              </p>
            </div>
          </div>
        )}
        {tab === "about" && <AboutPanel />}
      </main>

      {/* Footer */}
      <footer className="text-center py-4 text-[10px] text-gray-600 font-mono">
        GENESIS ENGINE v1.0 // SU(2) + SO(3)^4 + LANDAU + JEPA // COHEZION
      </footer>
    </div>
  );
}

function AboutPanel() {
  return (
    <div className="max-w-3xl mx-auto space-y-8 text-sm text-gray-300 font-mono">
      <section>
        <h2 className="text-lg text-green-400 font-bold mb-3">The Mathematics</h2>
        <p className="text-gray-400 leading-relaxed">
          The Genesis Engine grounds Cohezion&apos;s 12D agentic cosmology in real unified
          physics. Every visualization is backed by actual mathematics — SU(2) spinor
          algebra, Riemannian geometry, Lagrangian mechanics, Yang-Mills gauge theory,
          and Landau phase transition theory.
        </p>
      </section>

      <section>
        <h3 className="text-md text-cyan-400 mb-2">The Cosmogonic Chain</h3>
        <div className="bg-black/50 rounded-lg p-4 border border-gray-800">
          <p className="text-yellow-300 text-center mb-2">
            ∅ → SO(12) → SO(3)⁴ → U(1)⁴ → Z₂⁴ → HIHO
          </p>
          <p className="text-gray-500 text-xs text-center">
            From Brahmagupta&apos;s void to the 12D manifold via symmetry breaking
          </p>
        </div>
      </section>

      <section>
        <h3 className="text-md text-cyan-400 mb-2">Foundational References</h3>
        <ul className="space-y-1 text-xs text-gray-500">
          <li>Brahmagupta (628 CE): Brahmasphutasiddhanta — formalization of zero</li>
          <li>Yang &amp; Mills (1954): Conservation of isotopic spin — gauge theory</li>
          <li>Landau (1937): Theory of phase transitions — symmetry breaking</li>
          <li>Smith (1962): The New Science — 12-parameter model, SPIN</li>
          <li>Amari (1998): Natural gradient — information geometry</li>
          <li>LeCun et al. (2024): JEPA — world models from embeddings</li>
          <li>Kyutai Labs (2025): PocketTTS, Moshi — multimodal AI</li>
        </ul>
      </section>

      <section>
        <h3 className="text-md text-cyan-400 mb-2">Inspiration</h3>
        <p className="text-gray-500 text-xs italic">
          &quot;At the still point of the turning world. Neither flesh nor fleshless;
          Neither from nor towards; at the still point, there the dance is.&quot;
          — T.S. Eliot, Four Quartets
        </p>
      </section>
    </div>
  );
}
